from datetime import datetime
from typing import Any, Dict
from src.domain.interfaces.tool import AbstractTool


class SystemTimeTool(AbstractTool):
    """Concrete tool implementation that queries the local host system clock."""

    @property
    def name(self) -> str:
        return "get_system_time"

    @property
    def description(self) -> str:
        return (
            "Returns the current local date, time, and day of the week on the host system. "
            "Use this tool whenever the user asks for the time, date, or timezone."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        # Gemini expects standard JSON Schema format
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def execute(self, **kwargs: Any) -> str:
        """Retrieves and formats the current local time."""
        now = datetime.now()
        # Formats like: "Thursday, July 16, 2026 19:54:12"
        return now.strftime("%A, %B %d, %Y %H:%M:%S")
