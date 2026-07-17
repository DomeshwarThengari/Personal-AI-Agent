from unittest.mock import MagicMock, patch
import pytest
from src.application.tools.app_launcher import AppLauncherTool


@patch("shutil.which")
@patch("subprocess.Popen")
def test_app_launcher_success(mock_popen: MagicMock, mock_which: MagicMock) -> None:
    """Verifies that AppLauncherTool spawns subprocesses for supported apps."""
    tool = AppLauncherTool()

    # Mock that 'google-chrome' binary exists on system path
    mock_which.side_effect = lambda cmd: cmd == "google-chrome"

    result = tool.execute(app_name="chrome")

    # Assert correct success string is returned
    assert "successfully opened chrome" in result.lower()

    # Assert subprocess.Popen was called with google-chrome binary and detached flags
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert args[0] == ["google-chrome"]
    assert kwargs["start_new_session"] is True


def test_app_launcher_unsupported_app() -> None:
    """Verifies that passing an unsupported app name raises a ValueError."""
    tool = AppLauncherTool()
    with pytest.raises(ValueError, match="is not supported"):
        tool.execute(app_name="nonexistent_app")


@patch("shutil.which")
def test_app_launcher_missing_system_binary(mock_which: MagicMock) -> None:
    """Verifies that a FileNotFoundError is raised if no candidate command exists on the path."""
    tool = AppLauncherTool()

    # Mock that none of the candidates are available
    mock_which.return_value = None

    with pytest.raises(FileNotFoundError, match="Could not find any system binary"):
        tool.execute(app_name="chrome")
