import json
from unittest.mock import MagicMock, patch
import pytest
from src.domain.entities import Message
from src.domain.interfaces.tool import AbstractTool
from src.infrastructure.llm.ollama import OllamaLLMError, OllamaLLMService
from src.infrastructure.planner.ollama_planner import OllamaPlannerService


class MockTool(AbstractTool):
    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool for testing."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {"arg1": {"type": "string"}},
            "required": ["arg1"],
        }

    def execute(self, **kwargs) -> str:
        return "success"


def test_ollama_llm_service_initialization() -> None:
    """Verifies that OllamaLLMService configures settings properly."""
    service = OllamaLLMService(host="http://localhost:9999", model_name="test-llama")
    assert service.host == "http://localhost:9999"
    assert service.model_name == "test-llama"


def test_ollama_llm_message_mapping() -> None:
    """Verifies that messages are correctly mapped for the Ollama chat endpoint."""
    service = OllamaLLMService()
    messages = [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi! How can I help?"),
        Message(role="system", content="Force system prompt"),
    ]
    mapped = service._map_messages(messages, system_instruction="Persona prompt")

    assert len(mapped) == 4
    assert mapped[0] == {"role": "system", "content": "Persona prompt"}
    assert mapped[1] == {"role": "user", "content": "Hello"}
    assert mapped[2] == {"role": "assistant", "content": "Hi! How can I help?"}
    assert mapped[3] == {"role": "system", "content": "Force system prompt"}


def test_ollama_llm_tool_mapping() -> None:
    """Verifies that tool schemas are correctly formatted."""
    service = OllamaLLMService()
    tools = [MockTool()]
    mapped = service._map_tools(tools)

    assert len(mapped) == 1
    assert mapped[0]["type"] == "function"
    assert mapped[0]["function"]["name"] == "mock_tool"
    assert mapped[0]["function"]["parameters"]["properties"]["arg1"]["type"] == "string"


@patch("urllib.request.urlopen")
def test_ollama_generate_response_text_success(mock_urlopen: MagicMock) -> None:
    """Verifies successful text response generation mapping."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {
            "message": {
                "role": "assistant",
                "content": "This is a local response.",
                "tool_calls": [],
            }
        }
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    service = OllamaLLMService(host="http://localhost:11434", model_name="llama3.1")
    res = service.generate_response([Message(role="user", content="Hello")])

    assert res.message.role == "assistant"
    assert res.message.content == "This is a local response."
    assert len(res.actions) == 0


@patch("urllib.request.urlopen")
def test_ollama_generate_response_tool_call_success(mock_urlopen: MagicMock) -> None:
    """Verifies successful mapping of tool execution instructions."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "mock_tool",
                            "arguments": {"arg1": "value1"},
                        }
                    }
                ],
            }
        }
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    service = OllamaLLMService()
    res = service.generate_response(
        messages=[Message(role="user", content="run tool")], tools=[MockTool()]
    )

    assert len(res.actions) == 1
    assert res.actions[0].action_type == "mock_tool"
    assert res.actions[0].parameters == {"arg1": "value1"}


@patch("urllib.request.urlopen")
def test_ollama_generate_response_failure(mock_urlopen: MagicMock) -> None:
    """Verifies that API connection exceptions raise OllamaLLMError."""
    mock_urlopen.side_effect = Exception("Connection refused")
    service = OllamaLLMService()

    with pytest.raises(OllamaLLMError, match="Failed to generate response"):
        service.generate_response([Message(role="user", content="hello")])


@patch("urllib.request.urlopen")
def test_ollama_planner_success(mock_urlopen: MagicMock) -> None:
    """Verifies that OllamaPlannerService generates structured step lists successfully."""
    mock_response = MagicMock()
    mock_plan = [
        {
            "id": "step_1",
            "description": "Read CPU status",
            "tool_name": "system_read_cpu",
            "arguments": {},
        }
    ]
    mock_response.read.return_value = json.dumps(
        {"message": {"content": json.dumps(mock_plan)}}
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    planner = OllamaPlannerService()
    plan = planner.generate_plan("read cpu info", [])

    assert len(plan) == 1
    assert plan[0]["id"] == "step_1"
    assert plan[0]["tool_name"] == "system_read_cpu"


@patch("urllib.request.urlopen")
def test_ollama_planner_failure_fallback(mock_urlopen: MagicMock) -> None:
    """Verifies that planner service falls back gracefully to a mock plan on network failure."""
    mock_urlopen.side_effect = Exception("API Offline")

    planner = OllamaPlannerService()
    plan = planner.generate_plan("play youtube kubernetes video", [])

    assert len(plan) == 3
    assert plan[0]["tool_name"] == "browser_open_url"
    assert plan[1]["tool_name"] == "browser_search_youtube"
    assert plan[2]["tool_name"] == "browser_play_youtube"
