import json
import urllib.request
import urllib.error
from typing import Any, List, Optional
from src.config.settings import settings
from src.domain.entities import Action, AgentResponse, Message
from src.domain.interfaces.llm import AbstractLLMService
from src.domain.interfaces.tool import AbstractTool
from src.utils.logging import get_logger

logger = get_logger("ollama_service")


class OllamaLLMError(Exception):
    """Custom exception representing errors in Ollama LLM adapter."""

    pass


class OllamaLLMService(AbstractLLMService):
    """Infrastructure adapter for local Ollama LLM API."""

    def __init__(
        self,
        host: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """Initializes the Ollama LLM service config.

        Args:
            host: The Ollama host address. Defaults to settings.OLLAMA_HOST.
            model_name: The Ollama model name. Defaults to settings.OLLAMA_MODEL.
        """
        self.host = host or settings.OLLAMA_HOST
        self.model_name = model_name or settings.OLLAMA_MODEL

    def _map_messages(
        self, messages: List[Message], system_instruction: Optional[str] = None
    ) -> List[dict[str, Any]]:
        """Maps domain messages to the format expected by Ollama API."""
        mapped = []

        # If system instruction is provided, place it first in the chat history
        if system_instruction:
            mapped.append({"role": "system", "content": system_instruction})

        for msg in messages:
            # Map role cleanly to system, user, or assistant
            role = msg.role
            if role not in ("system", "user", "assistant"):
                role = "user"
            mapped.append({"role": role, "content": msg.content})

        return mapped

    def _map_tools(self, tools: List[AbstractTool]) -> List[dict[str, Any]]:
        """Maps tool domain entities to OpenAI-like tool schemas expected by Ollama."""
        mapped = []
        for t in tools:
            mapped.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": (
                            t.parameters
                            if t.parameters
                            else {"type": "object", "properties": {}, "required": []}
                        ),
                    },
                }
            )
        return mapped

    def generate_response(
        self,
        messages: List[Message],
        system_instruction: Optional[str] = None,
        tools: Optional[List[AbstractTool]] = None,
    ) -> AgentResponse:
        """Generates a text response and potential tool calls via Ollama API."""
        logger.debug(
            f"Sending request to Ollama ({self.model_name}) at {self.host} with "
            f"{len(messages)} messages and {len(tools or [])} tools."
        )

        mapped_messages = self._map_messages(messages, system_instruction)
        mapped_tools = self._map_tools(tools) if tools else None

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": mapped_messages,
            "stream": False,
        }
        if mapped_tools:
            payload["tools"] = mapped_tools

        url = f"{self.host.rstrip('/')}/api/chat"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                response_data = json.loads(res.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"Error invoking Ollama API at {url}: {e}", exc_info=True)
            raise OllamaLLMError(f"Failed to generate response: {e}") from e

        # Extract message content and potential tool calls
        message_data = response_data.get("message", {})
        content = message_data.get("content", "")
        tool_calls = message_data.get("tool_calls", [])

        actions = []
        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name")
            args = func.get("arguments", {})
            if name:
                # Ensure arguments are a dict
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                actions.append(Action(action_type=name, parameters=args))

        assistant_msg = Message(role="assistant", content=content)

        return AgentResponse(
            message=assistant_msg,
            actions=actions,
            metadata={
                "model": self.model_name,
                "provider": "ollama",
            },
        )
