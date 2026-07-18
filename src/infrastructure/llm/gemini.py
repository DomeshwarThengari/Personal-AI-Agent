from typing import Any, List, Optional
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse
from src.config.settings import settings
from src.domain.entities import Action, AgentResponse, Message
from src.domain.interfaces.llm import AbstractLLMService
from src.domain.interfaces.tool import AbstractTool
from src.utils.logging import get_logger

logger = get_logger("gemini_service")


class GeminiLLMError(Exception):
    """Custom exception representing errors in Gemini LLM adapter."""

    pass


class GeminiLLMService(AbstractLLMService):
    """Infrastructure adapter for Google Gemini LLM API.

    Implements the AbstractLLMService interface.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
    ):
        """Initializes the Gemini generative model.

        Args:
            api_key: The Google Gemini API key. Defaults to settings.GEMINI_API_KEY.
            model_name: The Gemini model identifier. Defaults to gemini-1.5-flash.
        """
        self.model_name = model_name
        self.api_key = api_key or settings.GEMINI_API_KEY

        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.warning(
                "GeminiLLMService initialized without a valid GEMINI_API_KEY."
            )
            # We don't crash here so that offline mode/dry runs can run health checks.
        else:
            genai.configure(api_key=self.api_key)  # type: ignore[attr-defined]

    def _map_messages(self, messages: List[Message]) -> List[dict[str, Any]]:
        """Maps domain Message list to the structure expected by Gemini SDK.

        Gemini expects roles to be either 'user' or 'model'.
        """
        mapped = []
        for msg in messages:
            role = "user" if msg.role in ("user", "system") else "model"
            mapped.append(
                {
                    "role": role,
                    "parts": [{"text": msg.content}],
                }
            )
        return mapped

    def _clean_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Recursively removes keys not supported by the Gemini API Schema (e.g., 'default')."""
        if not isinstance(schema, dict):
            return schema

        cleaned: dict[str, Any] = {}
        for k, v in schema.items():
            if k == "default":
                continue
            if isinstance(v, dict):
                cleaned[k] = self._clean_schema(v)
            elif isinstance(v, list):
                cleaned[k] = [
                    self._clean_schema(item) if isinstance(item, dict) else item
                    for item in v
                ]
            else:
                cleaned[k] = v
        return cleaned

    def generate_response(
        self,
        messages: List[Message],
        system_instruction: Optional[str] = None,
        tools: Optional[List[AbstractTool]] = None,
    ) -> AgentResponse:
        """Generates a text response using Google Gemini API, with optional tool call schemas.

        Translates domain structures, coordinates API call, and encapsulates results.
        """
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise GeminiLLMError(
                "Cannot call Gemini API: GEMINI_API_KEY is not configured."
            )

        logger.debug(
            f"Sending request to Gemini ({self.model_name}) with {len(messages)} context messages and {len(tools or [])} tools."
        )

        try:
            # Map tools if provided
            gemini_tools = None
            if tools:
                declarations = []
                for t in tools:
                    cleaned_params = (
                        self._clean_schema(t.parameters) if t.parameters else None
                    )
                    declarations.append(
                        genai.types.FunctionDeclaration(
                            name=t.name,
                            description=t.description,
                            parameters=cleaned_params,
                        )
                    )
                gemini_tools = [genai.types.Tool(function_declarations=declarations)]

            # Dynamically instantiate the model with system instruction and tools if provided
            model = genai.GenerativeModel(  # type: ignore[attr-defined]
                model_name=self.model_name,
                system_instruction=system_instruction,
                tools=gemini_tools,
            )

            # Map the message list
            gemini_contents = self._map_messages(messages)

            # Invoke API
            raw_response: GenerateContentResponse = model.generate_content(
                contents=gemini_contents
            )

            # Safely extract text (may raise ValueError if only a tool call is returned)
            response_text = ""
            try:
                response_text = raw_response.text
            except ValueError:
                pass

            # Extract actions
            actions = []
            if hasattr(raw_response, "candidates") and raw_response.candidates:
                candidate = raw_response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.function_call:
                            actions.append(
                                Action(
                                    action_type=part.function_call.name,
                                    parameters=dict(part.function_call.args),
                                )
                            )

            logger.debug("Successfully received response from Gemini API.")

            # Construct clean domain Message
            assistant_msg = Message(role="assistant", content=response_text)

            # Return domain entity
            return AgentResponse(
                message=assistant_msg,
                actions=actions,
                metadata={
                    "model": self.model_name,
                    "prompt_tokens": getattr(raw_response, "usage_metadata", None)
                    and getattr(raw_response.usage_metadata, "prompt_token_count", 0),
                    "candidates_tokens": getattr(raw_response, "usage_metadata", None)
                    and getattr(
                        raw_response.usage_metadata, "candidates_token_count", 0
                    ),
                },
            )

        except Exception as e:
            logger.error(f"Error during Gemini API invocation: {e}", exc_info=True)
            raise GeminiLLMError(f"Failed to generate response: {e}") from e
