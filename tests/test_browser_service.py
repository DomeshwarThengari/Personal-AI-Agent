from typing import Generator
import pytest
from src.infrastructure.browser.playwright_service import PlaywrightBrowserService
from src.config.settings import PROJECT_ROOT


@pytest.fixture
def browser_service() -> Generator[PlaywrightBrowserService, None, None]:
    """Fixture that initializes a headless PlaywrightBrowserService and closes it after tests."""
    service = PlaywrightBrowserService(headless=True)
    yield service
    service.close()


def test_open_url_and_read_content(browser_service: PlaywrightBrowserService) -> None:
    # Use a simple HTML data URL
    html_content = "<html><head><title>Test Page</title></head><body><h1>Hello from Antigravity</h1><p>Testing the browser agent.</p></body></html>"
    data_url = f"data:text/html,{html_content}"

    res = browser_service.open_url(data_url)
    assert "Successfully opened" in res

    content = browser_service.read_page_content()
    assert "Page Title: Test Page" in content
    assert "Hello from Antigravity" in content
    assert "Testing the browser agent." in content


def test_fill_form_and_click(browser_service: PlaywrightBrowserService) -> None:
    html_content = (
        "<html><body>"
        "<input id='username' type='text' />"
        "<button id='submit' onclick=\"document.body.innerHTML = '<h1>Form Submitted</h1>'\">Submit</button>"
        "</body></html>"
    )
    data_url = f"data:text/html,{html_content}"

    browser_service.open_url(data_url)

    # Fill field
    fill_res = browser_service.fill_form("#username", "john_doe")
    assert "Successfully filled" in fill_res

    # Click submit
    click_res = browser_service.click_element("#submit")
    assert "Successfully clicked" in click_res

    # Verify content changed
    content = browser_service.read_page_content()
    assert "Form Submitted" in content


def test_scroll_page(browser_service: PlaywrightBrowserService) -> None:
    html_content = (
        "<html><body><div style='height: 2000px;'>Spaced Content</div></body></html>"
    )
    data_url = f"data:text/html,{html_content}"

    browser_service.open_url(data_url)

    scroll_res = browser_service.scroll_page("down", 500)
    assert "Successfully scrolled page down by 500" in scroll_res

    scroll_res_up = browser_service.scroll_page("up", 300)
    assert "Successfully scrolled page up by 300" in scroll_res_up


def test_take_screenshot(browser_service: PlaywrightBrowserService) -> None:
    html_content = "<html><body><h1>Screenshot Test</h1></body></html>"
    data_url = f"data:text/html,{html_content}"

    browser_service.open_url(data_url)

    test_filename = "test_screenshot_output.png"
    screenshot_path = PROJECT_ROOT / "screenshots" / test_filename

    # Remove if exists from prior runs
    if screenshot_path.exists():
        screenshot_path.unlink()

    res = browser_service.take_screenshot(test_filename)
    assert "Screenshot successfully saved" in res
    assert screenshot_path.exists()

    # Cleanup screenshot file
    if screenshot_path.exists():
        screenshot_path.unlink()


def test_download_file_failure_graceful(
    browser_service: PlaywrightBrowserService,
) -> None:
    # Verify that a non-existent element selector for click-download fails gracefully
    res = browser_service.download_file("#non-existent-download-link")
    assert "Error triggering click download" in res
