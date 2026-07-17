from abc import ABC, abstractmethod
from typing import List


class AbstractAgent(ABC):
    """Port interface defining an Agent's metadata and tool boundary."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier of the agent (e.g. 'browser', 'file')."""
        pass

    @property
    @abstractmethod
    def system_instruction(self) -> str:
        """The system instructions/persona defining the agent's behavior and scope."""
        pass

    @property
    @abstractmethod
    def tool_names(self) -> List[str]:
        """List of tools this agent is authorized to use."""
        pass
