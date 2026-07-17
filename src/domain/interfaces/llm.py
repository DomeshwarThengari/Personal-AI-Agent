from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities import Message, AgentResponse
from src.domain.interfaces.tool import AbstractTool


class AbstractLLMService(ABC):
    """Port interface defining interaction with Language Model services.

    Separates the domain logic from direct dependencies on vendor SDKs.
    """

    @abstractmethod
    def generate_response(
        self,
        messages: List[Message],
        system_instruction: Optional[str] = None,
        tools: Optional[List[AbstractTool]] = None,
    ) -> AgentResponse:
        """Generates a response from the LLM based on the conversation history.

        Args:
            messages: A list of messages representing the chat history.
            system_instruction: Optional instruction defining the persona/role.
            tools: Optional list of executable tools the LLM can invoke.

        Returns:
            An AgentResponse containing the generated message and potential actions.
        """
        pass
