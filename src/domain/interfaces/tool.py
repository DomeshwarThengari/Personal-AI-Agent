from abc import ABC, abstractmethod
from typing import Any, Dict


class AbstractTool(ABC):
    """Port interface defining a system action/tool.

    Any custom capability (like play music, look up web pages, run terminal commands)
    must implement this interface to be registered and invoked by the LangGraph core.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier name of the tool passed to the LLM (e.g. 'get_system_time')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed documentation explaining when and how to invoke this tool."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON schema describing arguments required by this tool."""
        pass

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Runs the concrete tool logic and returns the output payload.

        Args:
            **kwargs: Arguments parsed and mapped from the LLM tool invocation.

        Returns:
            The raw execution output (should be serializable to string).
        """
        pass
