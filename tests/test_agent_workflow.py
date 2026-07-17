from unittest.mock import MagicMock
from src.application.agent_workflow import AgentWorkflowRunner
from src.domain.entities import Action, AgentResponse, Message
from src.domain.interfaces.llm import AbstractLLMService
from src.domain.interfaces.tool import AbstractTool


def test_agent_workflow_tool_routing() -> None:
    """Verifies that the LangGraph workflow properly routes to tools and returns the final response."""
    # 1. Setup Mock LLM Service
    mock_llm = MagicMock(spec=AbstractLLMService)

    # First LLM execution generates a tool call
    action = Action(action_type="mock_tool", parameters={"data": "test_param"})
    response_with_tool = AgentResponse(
        message=Message(role="assistant", content=""),
        actions=[action],
    )

    # Second LLM execution provides the final textual response
    final_response = AgentResponse(
        message=Message(
            role="assistant", content="The local tool executed successfully!"
        ),
        actions=[],
    )

    mock_llm.generate_response.side_effect = [response_with_tool, final_response]

    # 2. Setup Mock Tool
    mock_tool = MagicMock(spec=AbstractTool)
    mock_tool.name = "mock_tool"
    mock_tool.description = "A mock tool for integration testing."
    mock_tool.parameters = {"type": "object", "properties": {}}
    mock_tool.execute.return_value = "Success output"

    from src.application.tools.registry import ToolRegistry
    from src.application.action_engine.engine import ActionEngine

    registry = ToolRegistry()
    registry.register(mock_tool)
    mock_security = MagicMock()
    mock_security.verify_execution.return_value = "allowed"
    action_engine = ActionEngine(registry=registry, security_manager=mock_security)

    # 3. Initialize Runner and Execute
    runner = AgentWorkflowRunner(
        llm_service=mock_llm,
        action_engine=action_engine,
        tools=[mock_tool],
    )

    res = runner.run(
        session_id="integration_sess",
        history=[],
        user_input="Run the tool, please",
        system_instruction="Be a tester",
    )

    # 4. Assertions
    # Verify final output text
    assert res.message.content == "The local tool executed successfully!"

    # Verify tool execution results are collected
    assert len(res.action_results) == 1
    assert res.action_results[0].action_id == action.id
    assert res.action_results[0].status == "success"
    assert res.action_results[0].output == "Success output"

    # Verify that the tool was actually executed with appropriate params
    mock_tool.execute.assert_called_once_with(data="test_param")

    # Verify the LLM was called exactly twice (once for query, once after tool returned)
    assert mock_llm.generate_response.call_count == 2
