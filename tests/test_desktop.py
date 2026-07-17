import os
from typing import Any
import pytest

# Skip GUI tests if running in a headless environment on Posix
has_display = True
if (
    os.name == "posix"
    and not os.environ.get("DISPLAY")
    and not os.environ.get("WAYLAND_DISPLAY")
):
    has_display = False


def test_desktop_imports() -> None:
    """Verifies that all GUI components, thread workers, and settings can be parsed and imported without issues."""
    from src.interface.desktop.main import MainWindow, AgentWorker, VoiceInputWorker

    assert MainWindow is not None
    assert AgentWorker is not None
    assert VoiceInputWorker is not None


@pytest.mark.skipif(
    not has_display, reason="Skipping GUI rendering tests in headless environment."
)
def test_desktop_window_ui(qtbot: Any) -> None:
    """Verifies UI component rendering, Tab views, and settings controls in display environment."""
    from src.interface.desktop.main import MainWindow

    # Instantiate window
    window = MainWindow()
    qtbot.addWidget(window)

    # 1. Assertions on titles and status
    assert window.windowTitle() == "AI Agent JOJO - Desktop Assistant"
    assert "Idle" in window.lbl_agent_status.text()

    # 2. Check tab counts and titles
    assert window.tabs.count() == 4
    assert window.tabs.tabText(0) == "Settings"
    assert window.tabs.tabText(1) == "Audit Logs"
    assert window.tabs.tabText(2) == "Memory Viewer"
    assert window.tabs.tabText(3) == "Status Monitor"

    # 3. Assert default settings states
    assert window.chk_safe_mode.isChecked() is True
    assert window.cmb_role.currentText() in ["viewer", "operator", "admin"]
