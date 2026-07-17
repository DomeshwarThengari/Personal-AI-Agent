from unittest.mock import MagicMock
from src.application.chat_use_case import ChatUseCase
from src.domain.entities import AgentResponse, Message
from src.domain.interfaces.llm import AbstractLLMService


def test_chat_use_case_execution() -> None:
    """Verifies that the ChatUseCase correctly constructs and appends history and triggers the LLM."""
    # 1. Setup Mock Service
    mock_llm_service = MagicMock(spec=AbstractLLMService)

    mock_agent_response = AgentResponse(
        message=Message(role="assistant", content="Hello response"),
        metadata={"model": "mock-model"},
    )
    mock_llm_service.generate_response.return_value = mock_agent_response

    # 2. Instantiate and Execute Use Case
    chat_use_case = ChatUseCase(llm_service=mock_llm_service)

    history = [
        Message(role="user", content="Hi"),
        Message(role="assistant", content="Hello there!"),
    ]

    response = chat_use_case.execute(
        history=history,
        user_input="What is 2+2?",
        system_instruction="System persona text",
    )

    # 3. Asserts
    # Verify use case return value matches mock response
    assert response == mock_agent_response
    assert response.message.content == "Hello response"

    # Verify that LLM service was invoked with updated history (user message appended)
    called_args, called_kwargs = mock_llm_service.generate_response.call_args
    called_messages = called_kwargs.get("messages") or called_args[0]
    called_sys_inst = called_kwargs.get("system_instruction")

    assert len(called_messages) == 3
    assert called_messages[0].role == "user"
    assert called_messages[0].content == "Hi"
    assert called_messages[1].role == "assistant"
    assert called_messages[1].content == "Hello there!"
    assert called_messages[2].role == "user"
    assert called_messages[2].content == "What is 2+2?"

    assert called_sys_inst == "System persona text"
