from unittest.mock import MagicMock
from src.application.action_engine.engine import ActionEngine
from src.application.tools.registry import ToolRegistry
from src.domain.entities import Action
from src.domain.interfaces.tool import AbstractTool


def test_action_engine_success() -> None:
    """Verifies that the ActionEngine runs the tool and returns a success status."""
    # Setup mocks
    mock_registry = MagicMock(spec=ToolRegistry)
    mock_tool = MagicMock(spec=AbstractTool)
    mock_tool.execute.return_value = "execution success text"
    mock_registry.get_tool.return_value = mock_tool

    # Instantiate engine with mock security manager
    mock_security = MagicMock()
    mock_security.verify_execution.return_value = "allowed"
    engine = ActionEngine(registry=mock_registry, security_manager=mock_security)
    action = Action(action_type="success_tool", parameters={"param1": "val1"})

    res = engine.execute_action(action)

    # Asserts
    assert res.action_id == action.id
    assert res.status == "success"
    assert res.output == "execution success text"
    assert res.error_message is None
    mock_tool.execute.assert_called_once_with(param1="val1")


def test_action_engine_tool_not_found() -> None:
    """Verifies that running an unregistered action name returns a failure status."""
    mock_registry = MagicMock(spec=ToolRegistry)
    mock_registry.get_tool.return_value = None

    engine = ActionEngine(registry=mock_registry)
    action = Action(action_type="unregistered_tool", parameters={})

    res = engine.execute_action(action)

    assert res.action_id == action.id
    assert res.status == "failure"
    assert res.error_message is not None
    assert "no registered tool found" in res.error_message.lower()


def test_action_engine_execution_crashes() -> None:
    """Verifies that exceptions raised by tools are caught and returned as failures."""
    mock_registry = MagicMock(spec=ToolRegistry)
    mock_tool = MagicMock(spec=AbstractTool)
    mock_tool.execute.side_effect = Exception("System error occurred")
    mock_registry.get_tool.return_value = mock_tool

    mock_security = MagicMock()
    mock_security.verify_execution.return_value = "allowed"
    engine = ActionEngine(registry=mock_registry, security_manager=mock_security)
    action = Action(action_type="crashing_tool", parameters={})

    res = engine.execute_action(action)

    assert res.action_id == action.id
    assert res.status == "failure"
    assert res.error_message is not None
    assert "system error occurred" in res.error_message.lower()
