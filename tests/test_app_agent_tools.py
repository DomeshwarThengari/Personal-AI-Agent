from unittest.mock import MagicMock, patch
from src.application.tools.app_agent_tools import (
    SearchAppsTool,
    LaunchAppTool,
    CloseAppTool,
    FocusAppTool,
)
from src.domain.entities import InstalledApp


@patch("src.application.tools.app_agent_tools.scan_installed_apps")
def test_search_applications_tool(mock_scan: MagicMock) -> None:
    """Verifies that search tool filters applications by name, keywords, and categories."""
    app1 = InstalledApp(
        name="Firefox",
        exec_command="firefox-bin",
        generic_name="Web Browser",
        categories=["Network", "WebBrowser"],
        keywords=["browser", "internet"],
    )
    app2 = InstalledApp(
        name="KCalc",
        exec_command="kcalc",
        generic_name="Calculator",
        categories=["Utility", "Calculator"],
        keywords=["math", "sum"],
    )
    mock_scan.return_value = [app1, app2]

    tool = SearchAppsTool()

    # Search by category query
    res = tool.execute(query="webbrowser")
    assert "Firefox" in res
    assert "KCalc" not in res

    # Search by keyword query
    res2 = tool.execute(query="math")
    assert "KCalc" in res2
    assert "Firefox" not in res2

    # Search empty results
    res3 = tool.execute(query="nonexistent")
    assert "no installed applications matched" in res3.lower()


@patch("subprocess.Popen")
@patch("src.application.tools.app_agent_tools.scan_installed_apps")
def test_launch_application_success(
    mock_scan: MagicMock, mock_popen: MagicMock
) -> None:
    """Verifies successful launch query resolves Exec command parameters."""
    app = InstalledApp(
        name="VLC Media Player",
        exec_command="vlc --qt-start-minimized",
        categories=["AudioVideo"],
    )
    mock_scan.return_value = [app]

    tool = LaunchAppTool()
    res = tool.execute(app_name="vlc")

    assert "Successfully opened VLC Media Player." in res
    mock_popen.assert_called_once_with(
        ["vlc", "--qt-start-minimized"],
        stdout=-3,  # DEVNULL
        stderr=-3,  # DEVNULL
        stdin=-3,  # DEVNULL
        start_new_session=True,
    )


@patch("src.application.tools.app_agent_tools.scan_installed_apps")
def test_launch_application_fallback_suggestions(mock_scan: MagicMock) -> None:
    """Verifies uninstalled application queries run category similarity fallbacks."""
    # Safari target category is WebBrowser. Let's mock Firefox as installed.
    firefox = InstalledApp(
        name="Firefox",
        exec_command="firefox",
        categories=["WebBrowser", "Network"],
    )
    mock_scan.return_value = [firefox]

    tool = LaunchAppTool()
    res = tool.execute(app_name="Safari")

    assert "is not installed" in res
    assert "similar installed applications: Firefox" in res


@patch("psutil.process_iter")
def test_close_application_tool(mock_process_iter: MagicMock) -> None:
    """Verifies that CloseAppTool matches processes and calls terminate."""
    mock_proc1 = MagicMock()
    mock_proc1.info = {"name": "firefox-bin", "cmdline": ["/usr/bin/firefox"]}
    mock_proc1.pid = 1234

    mock_proc2 = MagicMock()
    mock_proc2.info = {"name": "bash", "cmdline": ["/bin/bash"]}
    mock_proc2.pid = 5678

    mock_process_iter.return_value = [mock_proc1, mock_proc2]

    tool = CloseAppTool()
    res = tool.execute(app_name="firefox")

    assert "Closed 1 running instance" in res
    mock_proc1.terminate.assert_called_once()
    mock_proc2.terminate.assert_not_called()


@patch("shutil.which")
def test_focus_application_missing_wmctrl(mock_which: MagicMock) -> None:
    """Verifies FocusAppTool handles missing focus commands gracefully."""
    mock_which.return_value = None

    tool = FocusAppTool()
    res = tool.execute(app_name="Chrome")

    assert "window management utility is not installed" in res


@patch("subprocess.run")
@patch("shutil.which")
def test_focus_application_wmctrl_success(
    mock_which: MagicMock, mock_run: MagicMock
) -> None:
    """Verifies FocusAppTool triggers wmctrl with correct window focus parameters."""
    mock_which.return_value = "/usr/bin/wmctrl"

    mock_response = MagicMock()
    mock_response.returncode = 0
    mock_run.return_value = mock_response

    tool = FocusAppTool()
    res = tool.execute(app_name="VLC")

    assert "brought 'vlc' to the foreground" in res.lower()
    mock_run.assert_called_once_with(
        ["/usr/bin/wmctrl", "-a", "VLC"],
        stdout=-1,  # PIPE
        stderr=-1,  # PIPE
        text=True,
    )
