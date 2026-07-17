from unittest.mock import MagicMock
import pytest
from src.domain.interfaces.browser_service import AbstractBrowserService
from src.application.tools.browser_tools import (
    BrowserOpenTool,
    BrowserSearchGoogleTool,
    BrowserSearchYoutubeTool,
    BrowserPlayYoutubeTool,
    BrowserClickTool,
    BrowserScrollTool,
    BrowserFillTool,
    BrowserDownloadTool,
    BrowserScreenshotTool,
    BrowserReadContentTool,
)


@pytest.fixture
def mock_service() -> MagicMock:
    return MagicMock(spec=AbstractBrowserService)


def test_browser_open_tool(mock_service: MagicMock) -> None:
    tool = BrowserOpenTool(mock_service)
    assert tool.name == "browser_open_url"
    assert "url" in tool.parameters["required"]

    mock_service.open_url.return_value = "Opened"
    res = tool.execute(url="example.com")
    assert res == "Opened"
    mock_service.open_url.assert_called_once_with("example.com")


def test_browser_search_google_tool(mock_service: MagicMock) -> None:
    tool = BrowserSearchGoogleTool(mock_service)
    assert tool.name == "browser_search_google"

    mock_service.search_google.return_value = "Google Searched"
    res = tool.execute(query="playwright python")
    assert res == "Google Searched"
    mock_service.search_google.assert_called_once_with("playwright python")


def test_browser_search_youtube_tool(mock_service: MagicMock) -> None:
    tool = BrowserSearchYoutubeTool(mock_service)
    assert tool.name == "browser_search_youtube"

    mock_service.search_youtube.return_value = "YouTube Searched"
    res = tool.execute(query="lofi")
    assert res == "YouTube Searched"
    mock_service.search_youtube.assert_called_once_with("lofi")


def test_browser_play_youtube_tool(mock_service: MagicMock) -> None:
    tool = BrowserPlayYoutubeTool(mock_service)
    assert tool.name == "browser_play_youtube"

    mock_service.play_youtube_video.return_value = "Video Playing"
    res = tool.execute(query="lofi beats")
    assert res == "Video Playing"
    mock_service.play_youtube_video.assert_called_once_with("lofi beats")


def test_browser_click_tool(mock_service: MagicMock) -> None:
    tool = BrowserClickTool(mock_service)
    assert tool.name == "browser_click_element"

    mock_service.click_element.return_value = "Clicked"
    res = tool.execute(selector="#submit")
    assert res == "Clicked"
    mock_service.click_element.assert_called_once_with("#submit")


def test_browser_scroll_tool(mock_service: MagicMock) -> None:
    tool = BrowserScrollTool(mock_service)
    assert tool.name == "browser_scroll_page"

    mock_service.scroll_page.return_value = "Scrolled"
    res = tool.execute(direction="down", amount=500)
    assert res == "Scrolled"
    mock_service.scroll_page.assert_called_once_with("down", 500)


def test_browser_fill_tool(mock_service: MagicMock) -> None:
    tool = BrowserFillTool(mock_service)
    assert tool.name == "browser_fill_input"

    mock_service.fill_form.return_value = "Filled"
    res = tool.execute(selector="#input", text="admin")
    assert res == "Filled"
    mock_service.fill_form.assert_called_once_with("#input", "admin")


def test_browser_download_tool(mock_service: MagicMock) -> None:
    tool = BrowserDownloadTool(mock_service)
    assert tool.name == "browser_download_file"

    mock_service.download_file.return_value = "Downloaded"
    res = tool.execute(target="http://example.com/file.zip")
    assert res == "Downloaded"
    mock_service.download_file.assert_called_once_with("http://example.com/file.zip")


def test_browser_screenshot_tool(mock_service: MagicMock) -> None:
    tool = BrowserScreenshotTool(mock_service)
    assert tool.name == "browser_take_screenshot"

    mock_service.take_screenshot.return_value = "Screenshotted"
    res = tool.execute(filename="my_page")
    assert res == "Screenshotted"
    mock_service.take_screenshot.assert_called_once_with("my_page")


def test_browser_read_content_tool(mock_service: MagicMock) -> None:
    tool = BrowserReadContentTool(mock_service)
    assert tool.name == "browser_read_page_content"

    mock_service.read_page_content.return_value = "Page Content Text"
    res = tool.execute()
    assert res == "Page Content Text"
    mock_service.read_page_content.assert_called_once()
