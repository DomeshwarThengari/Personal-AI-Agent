import urllib.parse
from typing import Optional
from playwright.sync_api import (
    sync_playwright,
    Playwright,
    Browser,
    BrowserContext,
    Page,
)
from src.domain.interfaces.browser_service import AbstractBrowserService
from src.config.settings import settings, PROJECT_ROOT
from src.utils.logging import get_logger

logger = get_logger("playwright_service")


class PlaywrightBrowserService(AbstractBrowserService):
    """Concrete adapter implementing AbstractBrowserService using Playwright Sync API."""

    def __init__(self, headless: Optional[bool] = None) -> None:
        """Initializes settings, retaining references to lazy-loaded Playwright instances."""
        self._headless = (
            headless if headless is not None else settings.PLAYWRIGHT_HEADLESS
        )
        self._timeout = settings.PLAYWRIGHT_TIMEOUT

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def _ensure_browser(self) -> None:
        """Lazily starts Playwright and launches the browser/page context if not already open."""
        if self._page is None:
            logger.info(
                f"Starting Playwright session (headless={self._headless}, timeout={self._timeout}ms)"
            )
            try:
                playwright = sync_playwright().start()
                self._playwright = playwright

                browser = playwright.chromium.launch(
                    headless=self._headless,
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                )
                self._browser = browser

                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    accept_downloads=True,
                )
                self._context = context

                page = context.new_page()
                self._page = page

                page.set_default_timeout(self._timeout)
            except Exception as e:
                logger.error(f"Failed to initialize Playwright browser: {e}")
                self.close()
                raise RuntimeError(f"Playwright initialization failed: {e}") from e

    def open_url(self, url: str) -> str:
        if not (
            url.startswith("http://")
            or url.startswith("https://")
            or url.startswith("data:")
        ):
            url = f"https://{url}"

        self._ensure_browser()
        page = self._page
        assert page is not None
        try:
            logger.info(f"Navigating to URL: {url}")
            response = page.goto(url)
            status = response.status if response else "Unknown"
            return f"Successfully opened '{url}' (HTTP Status: {status})."
        except Exception as e:
            logger.error(f"Failed to navigate to '{url}': {e}")
            return f"Error navigating to '{url}': {e}"

    def search_google(self, query: str) -> str:
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded_query}"
        self._ensure_browser()
        page = self._page
        assert page is not None
        try:
            logger.info(f"Searching Google for: '{query}'")
            page.goto(url)
            page.wait_for_selector("#search", timeout=10000)
            return f"Successfully completed Google search for '{query}'."
        except Exception as e:
            logger.warning(
                f"Google search selector wait failed: {e}. Returning page state."
            )
            return f"Navigated to Google search for '{query}', but search container was not detected."

    def search_youtube(self, query: str) -> str:
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        self._ensure_browser()
        page = self._page
        assert page is not None
        try:
            logger.info(f"Searching YouTube for: '{query}'")
            page.goto(url)
            page.wait_for_selector("ytd-video-renderer", timeout=10000)
            return f"Successfully searched YouTube for '{query}'."
        except Exception as e:
            logger.warning(f"YouTube search results selector wait failed: {e}.")
            return f"Navigated to YouTube search for '{query}'."

    def play_youtube_video(self, query: str) -> str:
        self._ensure_browser()
        page = self._page
        assert page is not None
        try:
            # 1. Search YouTube
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            logger.info(f"Playing YouTube video search: '{query}'")
            page.goto(url)

            # 2. Find and click first video title or link
            selectors = [
                "ytd-video-renderer a#video-title",
                "ytd-video-renderer a.ytd-video-renderer",
                "a#video-title-link",
                "a.ytd-play-button-renderer",
            ]
            clicked = False
            for selector in selectors:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    page.click(selector)
                    clicked = True
                    break
                except Exception:
                    continue

            if not clicked:
                # Fallback: click any link containing watch?v=
                links = page.query_selector_all("a")
                for link in links:
                    href = link.get_attribute("href") or ""
                    if "watch?v=" in href:
                        link.click()
                        clicked = True
                        break

            if clicked:
                # 3. Wait for video element
                page.wait_for_selector("video.html5-main-video", timeout=10000)
                return f"Successfully found and started playing YouTube video matching '{query}'."
            else:
                return (
                    f"Searched YouTube for '{query}' but could not find a video link to play."
                )
        except Exception as e:
            logger.error(f"Error playing YouTube video '{query}': {e}")
            return f"Failed to play YouTube video '{query}': {e}"

    def click_element(self, selector: str) -> str:
        self._ensure_browser()
        page = self._page
        assert page is not None
        try:
            logger.info(f"Clicking element matching selector: '{selector}'")
            # Wait briefly for element visibility before click
            page.wait_for_selector(selector, timeout=5000)
            page.click(selector)
            return f"Successfully clicked element '{selector}'."
        except Exception as e:
            # Try xpath / text match helper if CSS selector fails
            try:
                logger.info(
                    f"CSS selector failed. Attempting text-based selector search for '{selector}'"
                )
                text_selector = f"text={selector}"
                page.click(text_selector, timeout=5000)
                return f"Successfully clicked text element '{selector}'."
            except Exception:
                pass
            logger.error(f"Failed to click element '{selector}': {e}")
            return f"Error clicking element '{selector}': {e}"

    def scroll_page(self, direction: str, amount: Optional[int] = None) -> str:
        self._ensure_browser()
        page = self._page
        assert page is not None
        direction_clean = direction.strip().lower()
        if direction_clean not in ("up", "down"):
            return "Error: Scroll direction must be 'up' or 'down'."

        scroll_amount = amount if amount is not None else 600
        sign = "-" if direction_clean == "up" else ""
        try:
            logger.info(f"Scrolling page {direction_clean} by {scroll_amount}px")
            page.evaluate(f"window.scrollBy(0, {sign}{scroll_amount})")
            return f"Successfully scrolled page {direction_clean} by {scroll_amount} pixels."
        except Exception as e:
            logger.error(f"Failed to scroll page: {e}")
            return f"Error scrolling page: {e}"

    def fill_form(self, selector: str, text: str) -> str:
        self._ensure_browser()
        page = self._page
        assert page is not None
        try:
            logger.info(f"Filing input '{selector}' with text.")
            page.wait_for_selector(selector, timeout=5000)
            # Focus, clear existing text, and fill new text
            page.focus(selector)
            page.fill(selector, "")
            page.type(selector, text)
            return f"Successfully filled field '{selector}' with text."
        except Exception as e:
            logger.error(f"Failed to fill input '{selector}': {e}")
            return f"Error filling form field '{selector}': {e}"

    def download_file(self, target_url_or_selector: str) -> str:
        self._ensure_browser()
        page = self._page
        context = self._context
        assert page is not None
        assert context is not None

        downloads_dir = PROJECT_ROOT / "downloads"
        downloads_dir.mkdir(exist_ok=True)

        # 1. Direct URL download
        if target_url_or_selector.startswith(
            "http://"
        ) or target_url_or_selector.startswith("https://"):
            try:
                logger.info(
                    f"Attempting direct navigation download for URL: '{target_url_or_selector}'"
                )
                with page.expect_download() as download_info:
                    page.goto(target_url_or_selector)
                download = download_info.value
                save_path = downloads_dir / download.suggested_filename
                download.save_as(str(save_path))
                return f"Successfully downloaded file to: {save_path.resolve()}"
            except Exception as e:
                logger.error(f"Direct download failed: {e}")
                return f"Error downloading from URL '{target_url_or_selector}': {e}"

        # 2. Click selector download
        else:
            try:
                logger.info(
                    f"Attempting download via clicking element selector: '{target_url_or_selector}'"
                )
                page.wait_for_selector(target_url_or_selector, timeout=5000)
                with page.expect_download() as download_info:
                    page.click(target_url_or_selector)
                download = download_info.value
                save_path = downloads_dir / download.suggested_filename
                download.save_as(str(save_path))
                return (
                    f"Successfully triggered click download to: {save_path.resolve()}"
                )
            except Exception as e:
                logger.error(f"Click download failed: {e}")
                return f"Error triggering click download on selector '{target_url_or_selector}': {e}"

    def take_screenshot(self, filename: Optional[str] = None) -> str:
        self._ensure_browser()
        page = self._page
        assert page is not None

        screenshots_dir = PROJECT_ROOT / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)

        if not filename:
            import time

            filename = f"screenshot_{int(time.time())}.png"
        elif not filename.endswith(".png"):
            filename = f"{filename}.png"

        screenshot_path = screenshots_dir / filename
        try:
            logger.info(f"Taking page screenshot to: '{screenshot_path}'")
            page.screenshot(path=str(screenshot_path))
            return f"Screenshot successfully saved to: {screenshot_path.resolve()}"
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return f"Error taking screenshot: {e}"

    def read_page_content(self) -> str:
        self._ensure_browser()
        page = self._page
        assert page is not None
        try:
            title = page.title()
            current_url = page.url
            logger.info(f"Reading text content from page: '{title}' ({current_url})")

            # Extract visible body text
            text_content = page.evaluate("""() => {
                const scripts = document.querySelectorAll('script, style, noscript');
                scripts.forEach(s => s.remove());
                return document.body.innerText || document.body.textContent || '';
            }""")

            # Clean whitespace
            lines = [line.strip() for line in text_content.splitlines() if line.strip()]
            cleaned_text = "\n".join(lines)

            # Limit character count to avoid LLM context overflow (cap at 8000 characters)
            max_chars = 8000
            if len(cleaned_text) > max_chars:
                cleaned_text = (
                    cleaned_text[:max_chars]
                    + "\n\n... [Content Truncated due to length] ..."
                )

            return f"Page Title: {title}\nPage URL: {current_url}\n\nVisible Content:\n{cleaned_text}"
        except Exception as e:
            logger.error(f"Failed to read page content: {e}")
            return f"Error reading page content: {e}"

    def close(self) -> None:
        """Gracefully closes all browser processes."""
        logger.info("Closing Playwright browser session")
        try:
            if self._page:
                self._page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error during browser cleanup: {e}")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
