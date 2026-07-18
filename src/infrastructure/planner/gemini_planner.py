import json
from typing import Any, List, Optional
import google.generativeai as genai
from src.config.settings import settings
from src.domain.interfaces.planner_service import AbstractPlannerService
from src.utils.logging import get_logger

logger = get_logger("gemini_planner")


class GeminiPlannerService(AbstractPlannerService):
    """Gemini-powered Task Planner Service.

    Decomposes complex requests into a queue of structured tool-invocation steps.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.use_real_api = (
            self.api_key is not None and self.api_key != "your_gemini_api_key_here"
        )

        if self.use_real_api:
            genai.configure(api_key=self.api_key)  # type: ignore[attr-defined]

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
        if not self.use_real_api:
            logger.info("Offline/Mock mode: Generating static fallback task plan.")
            return self._get_mock_plan(task_description)

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

        try:
            model = genai.GenerativeModel(  # type: ignore[attr-defined]
                model_name=self.model_name,
                system_instruction=system_instruction,
            )
            response = model.generate_content(
                contents=task_description,
                generation_config={"response_mime_type": "application/json"},
            )
            plan = json.loads(response.text)
            if isinstance(plan, list):
                return plan
        except Exception as e:
            logger.error(f"Failed to generate Gemini plan: {e}. Falling back to mock.")

        return self._get_mock_plan(task_description)

    def replan(
        self,
        task_description: str,
        failed_step: dict[str, Any],
        error_msg: str,
        remaining_steps: List[dict[str, Any]],
        tools: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        if not self.use_real_api:
            logger.info("Offline/Mock mode: Generating static fallback replan.")
            # Mock fallback: return remaining steps directly
            return remaining_steps

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

        try:
            model = genai.GenerativeModel(  # type: ignore[attr-defined]
                model_name=self.model_name,
                system_instruction=system_instruction,
            )
            response = model.generate_content(
                contents="Re-evaluate remaining task queue steps and return updated list.",
                generation_config={"response_mime_type": "application/json"},
            )
            plan = json.loads(response.text)
            if isinstance(plan, list):
                return plan
        except Exception as e:
            logger.error(f"Failed to replan with Gemini: {e}")

        return remaining_steps
