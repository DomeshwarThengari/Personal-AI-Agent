from abc import ABC, abstractmethod
from src.domain.entities import Action, ActionResult


class AbstractActionEngine(ABC):
    """Port interface defining core Action Engine executions.

    Allows routing mechanisms and the conversational flow to trigger OS actions
    without direct dependency on tool registry implementations.
    """

    @abstractmethod
    def execute_action(self, action: Action) -> ActionResult:
        """Executes a parsed domain action and maps output to a standardized ActionResult.

        Args:
            action: The Action domain entity containing type and parameters.

        Returns:
            An ActionResult domain entity detailing outcome, output, or error state.
        """
        pass
