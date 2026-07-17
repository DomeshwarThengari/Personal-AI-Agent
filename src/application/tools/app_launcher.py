import shutil
import subprocess
from typing import Any, Dict, List
from src.domain.interfaces.tool import AbstractTool
from src.utils.logging import get_logger

logger = get_logger("app_launcher")


class AppLauncherTool(AbstractTool):
    """Tool that launches installed Linux desktop applications in the background."""

    # Predefined binary candidates for common apps on Linux
    APP_COMMANDS_MAP: Dict[str, List[str]] = {
        "chrome": [
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
        ],
        "spotify": ["spotify"],
        "calculator": ["gnome-calculator", "kcalc", "xcalc"],
        "vscode": ["code"],
    }

    @property
    def name(self) -> str:
        return "open_application"

    @property
    def description(self) -> str:
        return (
            "Opens a local desktop application by its name. "
            "Supported applications are: 'chrome' (browser), 'spotify' (music), "
            "'calculator' (math solver), and 'vscode' (code editor)."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": (
                        "The exact name of the application to spawn. "
                        "Must be one of: 'chrome', 'spotify', 'calculator', 'vscode'."
                    ),
                    "enum": ["chrome", "spotify", "calculator", "vscode"],
                }
            },
            "required": ["app_name"],
        }

    def execute(self, **kwargs: Any) -> str:
        """Finds and executes the application binary in a detached process."""
        app_name = kwargs.get("app_name", "").strip().lower()
        if not app_name:
            raise ValueError("Parameter 'app_name' is required.")

        candidates = self.APP_COMMANDS_MAP.get(app_name)
        if not candidates:
            raise ValueError(
                f"Application '{app_name}' is not supported. "
                f"Allowed applications: {list(self.APP_COMMANDS_MAP.keys())}"
            )

        # Search for available binary on system path
        executable_cmd = None
        for cmd in candidates:
            if shutil.which(cmd):
                executable_cmd = cmd
                break

        if not executable_cmd:
            error_msg = (
                f"Could not find any system binary for application '{app_name}'. "
                f"Checked candidate executables: {candidates}"
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info(
            f"Spawning application '{app_name}' using system binary: '{executable_cmd}'..."
        )

        try:
            # Spawn the desktop application detached from the parent CLI shell session
            subprocess.Popen(
                [executable_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            return f"Successfully opened {app_name}."
        except Exception as e:
            logger.error(
                f"Failed to spawn subprocess for '{executable_cmd}': {e}",
                exc_info=True,
            )
            raise RuntimeError(f"Failed to execute application process: {e}") from e
