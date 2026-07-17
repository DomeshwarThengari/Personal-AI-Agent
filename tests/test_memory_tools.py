from unittest.mock import MagicMock
from src.domain.interfaces.memory_service import AbstractMemoryService
from src.application.tools.memory_tools import (
    PreferenceSetTool,
    PreferenceGetTool,
    ProjectSaveTool,
    CommandHistoryTool,
    MemorySaveTool,
    MemorySearchTool,
)


def test_preference_set_tool() -> None:
    mock_service = MagicMock(spec=AbstractMemoryService)
    tool = PreferenceSetTool(mock_service)

    assert tool.name == "memory_set_preference"
    assert "theme" in tool.parameters["properties"]["key"]["description"]

    # Execute successfully
    res = tool.execute(key="theme", value="dark")
    assert "Successfully set preference" in res
    mock_service.set_preference.assert_called_once_with("theme", "dark")

    # Missing parameters
    res_err = tool.execute(key="theme")
    assert "Error" in res_err


def test_preference_get_tool() -> None:
    mock_service = MagicMock(spec=AbstractMemoryService)
    mock_service.get_preference.return_value = "dark"
    tool = PreferenceGetTool(mock_service)

    assert tool.name == "memory_get_preference"

    # Get existing key
    res = tool.execute(key="theme")
    assert "Preference 'theme': 'dark'" in res
    mock_service.get_preference.assert_called_once_with("theme")

    # Get non-existing key
    mock_service.get_preference.return_value = None
    res_missing = tool.execute(key="font")
    assert "is not set" in res_missing


def test_project_save_tool() -> None:
    mock_service = MagicMock(spec=AbstractMemoryService)
    tool = ProjectSaveTool(mock_service)

    assert tool.name == "memory_save_project"

    res = tool.execute(
        name="antigravity", description="AI Agent", tech_stack=["python"]
    )
    assert "Successfully saved project" in res
    mock_service.save_project.assert_called_once_with(
        "antigravity", "AI Agent", ["python"]
    )


def test_command_history_tool() -> None:
    mock_service = MagicMock(spec=AbstractMemoryService)
    mock_service.get_command_history.return_value = [
        {
            "timestamp": "2026-07-17",
            "executed_by": "user",
            "command": "git status",
            "status": "success",
        }
    ]
    tool = CommandHistoryTool(mock_service)

    assert tool.name == "memory_get_command_history"

    res = tool.execute(limit=5)
    assert "git status" in res
    mock_service.get_command_history.assert_called_once_with(limit=5)


def test_memory_save_tool() -> None:
    mock_service = MagicMock(spec=AbstractMemoryService)
    # Mock embedding helper method
    mock_service.get_embedding.return_value = [0.1] * 768
    tool = MemorySaveTool(mock_service)

    assert tool.name == "memory_save"

    res = tool.execute(text="loves python programming", category="languages")
    assert "Successfully saved fact" in res
    mock_service.save_vector_memory.assert_called_once_with(
        "loves python programming", [0.1] * 768, {"category": "languages"}
    )


def test_memory_search_tool() -> None:
    mock_service = MagicMock(spec=AbstractMemoryService)
    mock_service.get_embedding.return_value = [0.1] * 768
    mock_service.search_vector_memory.return_value = [
        {
            "text": "likes python programming",
            "metadata": {"category": "languages"},
            "score": 0.95,
        }
    ]
    tool = MemorySearchTool(mock_service)

    assert tool.name == "memory_search"

    res = tool.execute(query="python", limit=2)
    assert "likes python programming" in res
    mock_service.search_vector_memory.assert_called_once_with([0.1] * 768, limit=2)
