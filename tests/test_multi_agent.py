from unittest.mock import MagicMock
from src.domain.entities import Action, ActionResult, AgentResponse, Message
from src.domain.interfaces.action_engine import AbstractActionEngine
from src.domain.interfaces.llm import AbstractLLMService
from src.domain.interfaces.tool import AbstractTool
from src.application.tools.devops_tools import DevOpsRunCommandTool
from src.application.tools.routing_tools import RouteToAgentTool
from src.application.multi_agent.workflow import (
    MultiAgentWorkflowRunner,
    AGENT_TOOL_MAPPING,
)


def test_devops_run_command_tool() -> None:
    tool = DevOpsRunCommandTool()
    assert tool.name == "devops_run_command"

    # Test blocked commands
    res_blocked = tool.execute(command="rm -rf /")
    assert "blocked for safety" in res_blocked

    res_sudo = tool.execute(command="sudo apt update")
    assert "blocked for safety" in res_sudo

    # Test safe command execution
    res_safe = tool.execute(command="echo 'DevOps Agent Test'")
    assert "DevOps Agent Test" in res_safe
    assert "Exit Code: 0" in res_safe


def test_route_to_agent_tool() -> None:
    tool = RouteToAgentTool()
    assert tool.name == "route_to_agent"

    res = tool.execute(target_agent="browser", task_details="Search Google")
    assert "routed task to 'browser'" in res


def test_agent_tool_boundaries() -> None:
    assert "brain" in AGENT_TOOL_MAPPING
    assert "planner" in AGENT_TOOL_MAPPING
    assert "browser" in AGENT_TOOL_MAPPING
    assert "application" in AGENT_TOOL_MAPPING
    assert "file" in AGENT_TOOL_MAPPING
    assert "system" in AGENT_TOOL_MAPPING
    assert "memory" in AGENT_TOOL_MAPPING
    assert "devops" in AGENT_TOOL_MAPPING

    # Verify tool boundaries are populated
    assert "route_to_agent" in AGENT_TOOL_MAPPING["brain"]
    assert "browser_open_url" in AGENT_TOOL_MAPPING["browser"]
    assert "devops_run_command" in AGENT_TOOL_MAPPING["devops"]


def test_workflow_runner_routing() -> None:
    mock_llm = MagicMock(spec=AbstractLLMService)
    # First response: Brain calls route_to_agent
    # Second response: Browser responds back
    # Third response: Brain gives final summary text
    mock_llm.generate_response.side_effect = [
        # Brain Agent
        AgentResponse(
            message=Message(role="assistant", content="Let me route this."),
            actions=[
                Action(
                    action_type="route_to_agent",
                    parameters={"target_agent": "browser", "task_details": "search"},
                )
            ],
        ),
        # Browser Agent
        AgentResponse(
            message=Message(role="assistant", content="Finished search."),
            actions=[],
        ),
        # Brain Agent (final answer)
        AgentResponse(
            message=Message(
                role="assistant", content="Here is your info from the browser."
            ),
            actions=[],
        ),
    ]

    mock_action_engine = MagicMock(spec=AbstractActionEngine)
    mock_action_engine.execute_action.return_value = ActionResult(
        action_id="123", status="success", output="Search results list"
    )

    # Instantiate registry tools
    mock_tool_route = MagicMock(spec=AbstractTool)
    mock_tool_route.name = "route_to_agent"

    mock_tool_browser = MagicMock(spec=AbstractTool)
    mock_tool_browser.name = "browser_search_google"

    runner = MultiAgentWorkflowRunner(
        llm_service=mock_llm,
        action_engine=mock_action_engine,
        tools=[mock_tool_route, mock_tool_browser],
    )

    res = runner.run(
        session_id="session_123", history=[], user_input="search google for cats"
    )

    assert res.message.content == "Here is your info from the browser."
    # Verify Brain node called route_to_agent
    mock_action_engine.execute_action.assert_called_once()
