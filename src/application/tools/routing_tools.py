from typing import Any, Dict
from src.domain.interfaces.tool import AbstractTool


class RouteToAgentTool(AbstractTool):
    """Orchestration routing tool enabling Brain Agent to delegate tasks to specialists."""

    @property
    def name(self) -> str:
        return "route_to_agent"

    @property
    def description(self) -> str:
        return (
            "Delegates a specialized subtask to one of the specialist agents: "
            "'planner', 'browser', 'application', 'file', 'system', 'memory', or 'devops'."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_agent": {
                    "type": "string",
                    "enum": [
                        "planner",
                        "browser",
                        "application",
                        "file",
                        "system",
                        "memory",
                        "devops",
                    ],
                    "description": "The destination specialist agent.",
                },
                "task_details": {
                    "type": "string",
                    "description": "Specific query or instruction details to delegate to the agent.",
                },
            },
            "required": ["target_agent", "task_details"],
        }

    def execute(self, **kwargs: Any) -> str:
        target = kwargs.get("target_agent", "").strip()
        details = kwargs.get("task_details", "").strip()
        if not target or not details:
            return "Error: Both 'target_agent' and 'task_details' are required."
        return f"Successfully routed task to '{target}' agent: {details}"
