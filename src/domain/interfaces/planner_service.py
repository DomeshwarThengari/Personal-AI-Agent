from abc import ABC, abstractmethod
from typing import Any, List


class AbstractPlannerService(ABC):
    """Port interface defining capability to decompose requests into structured plan sequences."""

    @abstractmethod
    def generate_plan(
        self, task_description: str, tools: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        """Decomposes a complex request into a list of structured task step definitions."""
        pass

    @abstractmethod
    def replan(
        self,
        task_description: str,
        failed_step: dict[str, Any],
        error_msg: str,
        remaining_steps: List[dict[str, Any]],
        tools: List[dict[str, Any]],
    ) -> List[dict[str, Any]]:
        """Re-evaluates remaining plan steps and returns an updated sequence considering a tool failure."""
        pass
