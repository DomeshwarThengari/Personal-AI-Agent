import os
import shutil
import subprocess
from typing import Any, Dict, List
import psutil
from src.domain.interfaces.tool import AbstractTool
from src.application.tools.desktop_parser import scan_installed_apps
from src.utils.logging import get_logger

logger = get_logger("app_agent_tools")

# Maps popular application names to categories for suggestion fallback queries
APP_CATEGORY_LOOKUP = {
    "safari": "WebBrowser",
    "edge": "WebBrowser",
    "chrome": "WebBrowser",
    "chromium": "WebBrowser",
    "firefox": "WebBrowser",
    "opera": "WebBrowser",
    "internet explorer": "WebBrowser",
    "photoshop": "Graphics",
    "gimp": "Graphics",
    "illustrator": "Graphics",
    "inkscape": "Graphics",
    "spotify": "Audio",
    "rhythmbox": "Audio",
    "vlc": "Video",
    "calculator": "Utility",
    "excel": "Office",
    "word": "Office",
    "powerpoint": "Office",
    "vscode": "Development",
    "code": "Development",
    "sublime": "Development",
    "vim": "Development",
}


class SearchAppsTool(AbstractTool):
    """Tool that searches for installed applications matching a name or category query."""

    @property
    def name(self) -> str:
        return "search_applications"

    @property
    def description(self) -> str:
        return (
            "Searches installed GUI applications on the local system by query keyword."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term matching application name, categories, or keywords.",
                }
            },
            "required": ["query"],
        }

    def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query", "").strip().lower()
        if not query:
            raise ValueError("Query string is required for searching.")

        installed_apps = scan_installed_apps()
        matches = []

        for app in installed_apps:
            # Check for matches in Name, GenericName, Categories, and Keywords
            name_match = query in app.name.lower()
            generic_match = app.generic_name and query in app.generic_name.lower()
            category_match = any(query in cat.lower() for cat in app.categories)
            keyword_match = any(query in kw.lower() for kw in app.keywords)

            if name_match or generic_match or category_match or keyword_match:
                matches.append(app)

        if not matches:
            return f"No installed applications matched query: '{query}'."

        result_lines = [f"Found {len(matches)} matching application(s):"]
        for app in matches:
            gen_info = f" ({app.generic_name})" if app.generic_name else ""
            result_lines.append(f"- {app.name}{gen_info} (Exec: {app.exec_command})")

        return "\n".join(result_lines)


class LaunchAppTool(AbstractTool):
    """Tool that opens an application by name. Recommends installed alternatives on failure."""

    @property
    def name(self) -> str:
        return "launch_application"

    @property
    def description(self) -> str:
        return (
            "Launches an application by name. Suggests similar apps if not installed."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the application to open.",
                }
            },
            "required": ["app_name"],
        }

    def execute(self, **kwargs: Any) -> str:
        app_name = kwargs.get("app_name", "").strip()
        if not app_name:
            raise ValueError("Application name is required.")

        installed_apps = scan_installed_apps()
        target_app = None

        # 1. Look for exact match
        for app in installed_apps:
            if app.name.lower() == app_name.lower():
                target_app = app
                break

        # 2. Substring matching fallback
        if not target_app:
            for app in installed_apps:
                if app_name.lower() in app.name.lower():
                    target_app = app
                    break

        if target_app:
            logger.info(
                f"Launching application '{target_app.name}' via Exec: '{target_app.exec_command}'"
            )
            try:
                subprocess.Popen(
                    target_app.exec_command.split(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return f"Successfully opened {target_app.name}."
            except Exception as e:
                logger.error(
                    f"Failed to launch command '{target_app.exec_command}': {e}"
                )
                raise RuntimeError(f"Error launching {target_app.name}: {e}") from e

        # 3. Application not found suggestions logic
        logger.warning(f"Application '{app_name}' is not installed.")
        suggested_apps = self._suggest_similar_apps(app_name, installed_apps)

        if suggested_apps:
            suggestions_str = ", ".join(suggested_apps)
            return (
                f"Application '{app_name}' is not installed on this system. "
                f"Did you mean to open one of these similar installed applications: {suggestions_str}?"
            )

        return (
            f"Application '{app_name}' is not installed on this system, "
            f"and no similar alternatives were found."
        )

    def _suggest_similar_apps(
        self, app_name: str, installed_apps: List[Any]
    ) -> List[str]:
        """Identifies alternative applications sharing categories or keywords."""
        target_category = APP_CATEGORY_LOOKUP.get(app_name.lower())
        suggestions = []

        if target_category:
            for app in installed_apps:
                # Matches by Category list or GenericName substring matches
                has_category = any(
                    target_category.lower() in cat.lower() for cat in app.categories
                )
                has_generic = (
                    app.generic_name
                    and target_category.lower() in app.generic_name.lower()
                )

                if has_category or has_generic:
                    suggestions.append(app.name)

        # Cap suggestions to top 3
        return suggestions[:3]


class CloseAppTool(AbstractTool):
    """Tool that finds and terminates processes matching an application name."""

    @property
    def name(self) -> str:
        return "close_application"

    @property
    def description(self) -> str:
        return "Closes a running application by terminating its active processes."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the application to close (e.g. Chrome, Firefox).",
                }
            },
            "required": ["app_name"],
        }

    def execute(self, **kwargs: Any) -> str:
        app_name = kwargs.get("app_name", "").strip().lower()
        if not app_name:
            raise ValueError("Application name is required.")

        closed_count = 0
        logger.info(f"Scanning running processes to close app: '{app_name}'")

        # Iterate over all running system processes
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            if proc.pid == os.getpid():
                continue
            try:
                proc_info = proc.info
                p_name = proc_info.get("name") or ""
                p_cmd = proc_info.get("cmdline") or []
                cmd_line_str = " ".join(p_cmd).lower()

                # Match if app_name is a substring of the process name or the start command
                name_matches = app_name in p_name.lower()
                cmd_matches = app_name in cmd_line_str

                if name_matches or cmd_matches:
                    logger.info(
                        f"Terminating matched process: PID={proc.pid}, Name='{p_name}'"
                    )
                    proc.terminate()
                    closed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if closed_count > 0:
            return f"Closed {closed_count} running instance(s) of '{app_name}'."
        return f"No running processes found matching '{app_name}'."


class FocusAppTool(AbstractTool):
    """Tool that focus shifts a window to the foreground using wmctrl."""

    @property
    def name(self) -> str:
        return "bring_application_to_foreground"

    @property
    def description(self) -> str:
        return "Shifts focus and brings a running application window to the foreground."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the application window to bring forward.",
                }
            },
            "required": ["app_name"],
        }

    def execute(self, **kwargs: Any) -> str:
        app_name = kwargs.get("app_name", "").strip()
        if not app_name:
            raise ValueError("Application name is required.")

        # Check if wmctrl tool is installed
        wmctrl_path = shutil.which("wmctrl")
        if not wmctrl_path:
            logger.warning("wmctrl utility is not installed on this system.")
            return (
                f"Attempted to focus '{app_name}', but the 'wmctrl' window management "
                f"utility is not installed on this Linux host. "
                f"Please run 'sudo apt install wmctrl' to enable window focus control."
            )

        logger.info(f"Invoking wmctrl focus shift for: '{app_name}'")
        try:
            # wmctrl -a matches window title case-insensitively
            res = subprocess.run(
                [wmctrl_path, "-a", app_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if res.returncode == 0:
                return f"Successfully brought '{app_name}' to the foreground."
            else:
                return (
                    f"Could not find an active window title matching '{app_name}' "
                    f"using wmctrl (stderr: {res.stderr.strip()})."
                )
        except Exception as e:
            logger.error(f"Error shifting focus with wmctrl: {e}", exc_info=True)
            return f"Failed to focus application '{app_name}': {e}"
