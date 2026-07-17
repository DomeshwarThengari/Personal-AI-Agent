from abc import ABC, abstractmethod
from typing import Optional


class AbstractBrowserService(ABC):
    """Port interface defining interaction with Browser automation services.

    Decouples domain tools/logic from direct Playwright dependency.
    """

    @abstractmethod
    def open_url(self, url: str) -> str:
        """Navigates to the specified URL. Launches the browser if not already open."""
        pass

    @abstractmethod
    def search_google(self, query: str) -> str:
        """Navigates to Google and performs a query."""
        pass

    @abstractmethod
    def search_youtube(self, query: str) -> str:
        """Navigates to YouTube and performs a query."""
        pass

    @abstractmethod
    def play_youtube_video(self, query: str) -> str:
        """Searches YouTube and plays the first matching video."""
        pass

    @abstractmethod
    def click_element(self, selector: str) -> str:
        """Clicks an element matching the given CSS selector or text."""
        pass

    @abstractmethod
    def scroll_page(self, direction: str, amount: Optional[int] = None) -> str:
        """Scrolls the page either 'up' or 'down' by a pixel amount."""
        pass

    @abstractmethod
    def fill_form(self, selector: str, text: str) -> str:
        """Fills an input field matching the selector with the specified text."""
        pass

    @abstractmethod
    def download_file(self, target_url_or_selector: str) -> str:
        """Downloads a file by either navigating to a direct URL or clicking a selector."""
        pass

    @abstractmethod
    def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Takes a screenshot of the current page viewport."""
        pass

    @abstractmethod
    def read_page_content(self) -> str:
        """Extracts and returns cleaned text content from the current page body."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes all active pages, contexts, and browser processes gracefully."""
        pass
