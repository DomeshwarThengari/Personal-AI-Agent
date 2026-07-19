import json
import urllib.request
from typing import Any, List, Optional
from src.config.settings import settings
from src.domain.interfaces.planner_service import AbstractPlannerService
from src.utils.logging import get_logger

logger = get_logger("ollama_planner")


class OllamaPlannerService(AbstractPlannerService):
    """Ollama-powered Task Planner Service.

    Decomposes complex requests into a queue of structured tool-invocation steps.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.host = host or settings.OLLAMA_HOST
        self.model_name = model_name or settings.OLLAMA_MODEL

    def _get_mock_plan(self, task_description: str) -> List[dict[str, Any]]:
        """Provides a deterministic mock plan for testing and offline environments."""
        desc_lower = task_description.lower()
        if "youtube" in desc_lower and "play" in desc_lower:
            return [
                {
                    "id": "step_1",
                    "description": "Open browser and navigate to YouTube",
                    "tool_name": "browser_open_url",
                    "arguments": {"url": "https://www.youtube.com"},
                },
                {
                    "id": "step_2",
                    "description": "Search YouTube for Kubernetes tutorials",
                    "tool_name": "browser_search_youtube",
                    "arguments": {"query": "Kubernetes tutorials"},
                },
                {
                    "id": "step_3",
                    "description": "Play first YouTube video",
                    "tool_name": "browser_play_youtube",
                    "arguments": {"query": "Kubernetes tutorials"},
                },
            ]

        # Generic default mock plan
        return [
            {
                "id": "step_1",
                "description": "Read CPU load",
                "tool_name": "system_read_cpu",
                "arguments": {},
            },
            {
                "id": "step_2",
                "description": "Read RAM status",
                "tool_name": "system_read_ram",
                "arguments": {},
            },
        ]

    def generate_plan(
        self, task_description: str, tools: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        tools_text = json.dumps(tools, indent=2)
        system_instruction = (
            "You are a task planning engine for an AI assistant. "
            "Your job is to break down a complex user request into a sequence of steps.\n"
            "Each step MUST map to one of the available tools listed below. "
            "Return the plan strictly as a JSON array of objects with the exact keys: "
            "'id', 'description', 'tool_name', 'arguments'.\n"
            "Do not return any extra markdown text outside the JSON array.\n\n"
            f"Available Tools Schema:\n{tools_text}"
        )

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": task_description},
            ],
            "format": "json",
            "stream": False,
        }

        url = f"{self.host.rstrip('/')}/api/chat"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                response_data = json.loads(res.read().decode("utf-8"))
            content = response_data.get("message", {}).get("content", "")
            plan = json.loads(content)
            if isinstance(plan, list):
                return plan
        except Exception as e:
            logger.error(f"Failed to generate Ollama plan: {e}. Falling back to mock.")

        return self._get_mock_plan(task_description)

    def replan(
        self,
        task_description: str,
        failed_step: dict[str, Any],
        error_msg: str,
        remaining_steps: List[dict[str, Any]],
        tools: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        tools_text = json.dumps(tools, indent=2)
        system_instruction = (
            "You are a task planning engine. An error occurred during the execution of a multi-step task.\n"
            f"Original task: {task_description}\n"
            f"Failed step details: {json.dumps(failed_step)}\n"
            f"Error encountered: {error_msg}\n"
            f"Remaining steps: {json.dumps(remaining_steps)}\n\n"
            "Adjust the remaining steps, fix parameter issues, or inject new ones to recover from this failure. "
            "Return the updated plan strictly as a JSON array of objects containing keys: "
            "'id', 'description', 'tool_name', 'arguments'.\n"
            f"Available Tools Schema:\n{tools_text}"
        )

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {
                    "role": "user",
                    "content": "Re-evaluate remaining task queue steps and return updated list.",
                },
            ],
            "format": "json",
            "stream": False,
        }

        url = f"{self.host.rstrip('/')}/api/chat"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                response_data = json.loads(res.read().decode("utf-8"))
            content = response_data.get("message", {}).get("content", "")
            plan = json.loads(content)
            if isinstance(plan, list):
                return plan
        except Exception as e:
            logger.error(f"Failed to replan with Ollama: {e}")

        return remaining_steps
