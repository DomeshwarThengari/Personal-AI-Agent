from unittest.mock import MagicMock, patch
import pytest
from src.domain.entities import Message
from src.infrastructure.llm.gemini import GeminiLLMError, GeminiLLMService


def test_gemini_service_initialization() -> None:
    """Verifies that the GeminiLLMService sets up attributes properly."""
    service = GeminiLLMService(api_key="test_key", model_name="test-model")
    assert service.model_name == "test-model"
    assert service.api_key == "test_key"


def test_gemini_service_missing_api_key() -> None:
    """Verifies that generate_response raises a GeminiLLMError if no key is configured."""
    service = GeminiLLMService(api_key="your_gemini_api_key_here")
    with pytest.raises(GeminiLLMError, match="GEMINI_API_KEY is not configured"):
        service.generate_response([Message(role="user", content="Hello")])


@patch("google.generativeai.GenerativeModel")
@patch("google.generativeai.configure")
def test_gemini_generate_response_success(
    mock_configure: MagicMock, mock_model_class: MagicMock
) -> None:
    """Verifies successful request mapping, invocation, and response translation."""
    # 1. Setup Mocks
    mock_model_instance = MagicMock()
    mock_model_class.return_value = mock_model_instance

    mock_sdk_response = MagicMock()
    mock_sdk_response.text = "Hello user, how can I help you today?"
    mock_sdk_response.usage_metadata = MagicMock()
    mock_sdk_response.usage_metadata.prompt_token_count = 12
    mock_sdk_response.usage_metadata.candidates_token_count = 8
    mock_model_instance.generate_content.return_value = mock_sdk_response

    # 2. Instantiate Service & Invoke
    service = GeminiLLMService(api_key="test_key", model_name="gemini-1.5-flash")
    messages = [
        Message(role="user", content="Hi"),
        Message(role="assistant", content="Hello!"),
        Message(role="user", content="Help me"),
    ]

    response = service.generate_response(
        messages=messages, system_instruction="You are a helper."
    )

    # 3. Asserts
    # Verify API configure was called
    mock_configure.assert_called_once_with(api_key="test_key")

    # Verify model instantiation arguments
    mock_model_class.assert_called_once_with(
        model_name="gemini-1.5-flash",
        system_instruction="You are a helper.",
        tools=None,
    )

    # Verify input message mapping format
    expected_contents = [
        {"role": "user", "parts": [{"text": "Hi"}]},
        {"role": "model", "parts": [{"text": "Hello!"}]},
        {"role": "user", "parts": [{"text": "Help me"}]},
    ]
    mock_model_instance.generate_content.assert_called_once_with(
        contents=expected_contents
    )

    # Verify domain response formatting
    assert response.message.role == "assistant"
    assert response.message.content == "Hello user, how can I help you today?"
    assert response.metadata["model"] == "gemini-1.5-flash"
    assert response.metadata["prompt_tokens"] == 12
    assert response.metadata["candidates_tokens"] == 8
