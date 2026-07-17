from typing import Any, Dict
from src.domain.interfaces.tool import AbstractTool
from src.domain.interfaces.browser_service import AbstractBrowserService


class BrowserOpenTool(AbstractTool):
    """Tool that navigates to a specified URL."""

    def __init__(self, service: AbstractBrowserService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "browser_open_url"

    @property
    def description(self) -> str:
        return "Opens a browser window and navigates to the given website URL."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Website URL to navigate to (e.g. google.com, github.com).",
                }
            },
            "required": ["url"],
        }

    def execute(self, **kwargs: Any) -> str:
        url = kwargs.get("url", "").strip()
        if not url:
            raise ValueError("URL parameter is required.")
        return self._service.open_url(url)


class BrowserSearchGoogleTool(AbstractTool):
    """Tool that searches Google."""

    def __init__(self, service: AbstractBrowserService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "browser_search_google"

    @property
    def description(self) -> str:
        return "Searches Google for the specified search query query."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query terms.",
                }
            },
            "required": ["query"],
        }

    def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query", "").strip()
        if not query:
            raise ValueError("Query parameter is required.")
        return self._service.search_google(query)


class BrowserSearchYoutubeTool(AbstractTool):
    """Tool that searches YouTube."""

    def __init__(self, service: AbstractBrowserService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "browser_search_youtube"

    @property
    def description(self) -> str:
        return "Searches YouTube for a specified search query."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query terms.",
                }
            },
            "required": ["query"],
        }

    def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query", "").strip()
        if not query:
            raise ValueError("Query parameter is required.")
        return self._service.search_youtube(query)


class BrowserPlayYoutubeTool(AbstractTool):
    """Tool that finds and plays a YouTube video."""

    def __init__(self, service: AbstractBrowserService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "browser_play_youtube"

    @property
    def description(self) -> str:
        return "Searches YouTube for a video and starts playing the first result."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Video name or topic search terms to search and play.",
                }
            },
            "required": ["query"],
        }

    def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query", "").strip()
        if not query:
            raise ValueError("Query parameter is required.")
        return self._service.play_youtube_video(query)


class BrowserClickTool(AbstractTool):
    """Tool that clicks an element on the current page."""

    def __init__(self, service: AbstractBrowserService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "browser_click_element"

    @property
    def description(self) -> str:
        return (
            "Clicks an HTML element on the page using a CSS selector or visible text."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector or text match of the element to click (e.g. 'button#submit', 'Sign In').",
                }
            },
            "required": ["selector"],
        }

    def execute(self, **kwargs: Any) -> str:
        selector = kwargs.get("selector", "").strip()
        if not selector:
            raise ValueError("Selector parameter is required.")
        return self._service.click_element(selector)


class BrowserScrollTool(AbstractTool):
    """Tool that scrolls the active webpage."""

    def __init__(self, service: AbstractBrowserService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "browser_scroll_page"

    @property
    def description(self) -> str:
        return "Scrolls the page up or down by the specified pixel amount."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": ["up", "down"],
                    "description": "Direction to scroll.",
                },
                "amount": {
                    "type": "integer",
                    "description": "Optional pixel distance to scroll (defaults to 600).",
                },
            },
            "required": ["direction"],
        }

    def execute(self, **kwargs: Any) -> str:
        direction = kwargs.get("direction", "down").strip()
        amount = kwargs.get("amount")
        if amount is not None:
            try:
                amount = int(amount)
            except ValueError:
                raise ValueError("Amount parameter must be an integer.")
        return self._service.scroll_page(direction, amount)


class BrowserFillTool(AbstractTool):
    """Tool that fills form input fields."""

    def __init__(self, service: AbstractBrowserService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "browser_fill_input"

    @property
    def description(self) -> str:
        return "Fills a text input field on the page matching a selector with the given text value."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector matching the input field (e.g. 'input[type=text]', '#username').",
                },
                "text": {
                    "type": "string",
                    "description": "Text value to fill into the input field.",
                },
            },
            "required": ["selector", "text"],
        }

    def execute(self, **kwargs: Any) -> str:
        selector = kwargs.get("selector", "").strip()
        text = kwargs.get("text", "")
        if not selector:
            raise ValueError("Selector parameter is required.")
        return self._service.fill_form(selector, text)


class BrowserDownloadTool(AbstractTool):
    """Tool that handles downloads."""

    def __init__(self, service: AbstractBrowserService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "browser_download_file"

    @property
    def description(self) -> str:
        return "Downloads a file from a direct HTTP link, or by clicking a file download element."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Direct URL file link or CSS selector of the click-to-download element.",
                }
            },
            "required": ["target"],
        }

    def execute(self, **kwargs: Any) -> str:
        target = kwargs.get("target", "").strip()
        if not target:
            raise ValueError("Target parameter (URL or selector) is required.")
        return self._service.download_file(target)


class BrowserScreenshotTool(AbstractTool):
    """Tool that captures webpage screenshots."""

    def __init__(self, service: AbstractBrowserService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "browser_take_screenshot"

    @property
    def description(self) -> str:
        return "Takes a screenshot of the browser viewport and saves it to the local system."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Optional custom name for the file (e.g. 'google_results.png').",
                }
            },
        }

    def execute(self, **kwargs: Any) -> str:
        filename = kwargs.get("filename")
        if filename:
            filename = filename.strip()
        return self._service.take_screenshot(filename)


class BrowserReadContentTool(AbstractTool):
    """Tool that extracts textual content from the page body."""

    def __init__(self, service: AbstractBrowserService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "browser_read_page_content"

    @property
    def description(self) -> str:
        return (
            "Reads the page title, URL, and visible body text of the current webpage."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        return self._service.read_page_content()
