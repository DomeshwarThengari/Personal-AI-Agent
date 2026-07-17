from unittest.mock import MagicMock
from src.domain.interfaces.action_engine import AbstractActionEngine
from src.domain.interfaces.planner_service import AbstractPlannerService
from src.domain.entities import ActionResult
from src.domain.interfaces.tool import AbstractTool
from src.application.tools.planner_tools import (
    TaskStep,
    TaskQueue,
    MultiStepExecutionEngine,
    PlannerExecuteTaskTool,
)


def test_task_queue_operations() -> None:
    steps = [
        TaskStep(id="step_1", description="First", tool_name="tool_a", arguments={}),
        TaskStep(id="step_2", description="Second", tool_name="tool_b", arguments={}),
    ]
    queue = TaskQueue(steps)

    assert queue.get_progress_percent() == 0

    next_step = queue.get_next()
    assert next_step is not None
    assert next_step.id == "step_1"

    queue.mark_completed("step_1", "Result output")
    assert queue.get_progress_percent() == 50

    next_step = queue.get_next()
    assert next_step is not None
    assert next_step.id == "step_2"

    queue.mark_failed("step_2", "Error message")
    assert queue.get_progress_percent() == 50


def test_task_queue_replan_remaining() -> None:
    steps = [
        TaskStep(id="step_1", description="First", tool_name="tool_a", arguments={}),
        TaskStep(id="step_2", description="Second", tool_name="tool_b", arguments={}),
    ]
    queue = TaskQueue(steps)
    queue.mark_completed("step_1", "Done")

    # Replan remaining
    new_steps = [
        TaskStep(id="replan_1", description="Third", tool_name="tool_c", arguments={})
    ]
    queue.replan_remaining(new_steps)

    assert len(queue.steps) == 2
    assert queue.steps[0].id == "step_1"
    assert queue.steps[1].id == "replan_1"

    next_step = queue.get_next()
    assert next_step is not None
    assert next_step.id == "replan_1"


def test_execution_engine_success() -> None:
    mock_action_engine = MagicMock(spec=AbstractActionEngine)
    mock_action_engine.execute_action.return_value = ActionResult(
        action_id="step_1", status="success", output="Completed successfully"
    )

    mock_planner = MagicMock(spec=AbstractPlannerService)
    mock_planner.generate_plan.return_value = [
        {
            "id": "step_1",
            "description": "Step One",
            "tool_name": "tool_a",
            "arguments": {},
        }
    ]

    mock_tool = MagicMock(spec=AbstractTool)
    mock_tool.name = "tool_a"
    mock_tool.description = "Mock Tool A"
    mock_tool.parameters = {}

    engine = MultiStepExecutionEngine(
        action_engine=mock_action_engine,
        planner_service=mock_planner,
        tools=[mock_tool],
    )

    logs = engine.execute("Clean room")
    assert "Completed step: step_1" in logs
    assert "100%" in logs
    mock_action_engine.execute_action.assert_called_once()


def test_execution_engine_retry_and_replan() -> None:
    mock_action_engine = MagicMock(spec=AbstractActionEngine)
    # First call: failure, Second call: failure (trigger replan)
    mock_action_engine.execute_action.side_effect = [
        ActionResult(
            action_id="step_1", status="failure", error_message="Transient error"
        ),
        ActionResult(
            action_id="step_1", status="failure", error_message="Persistent error"
        ),
        # After replan, call to tool_b succeeds
        ActionResult(action_id="replan_1", status="success", output="Replanned output"),
    ]

    mock_planner = MagicMock(spec=AbstractPlannerService)
    mock_planner.generate_plan.return_value = [
        {
            "id": "step_1",
            "description": "Step One",
            "tool_name": "tool_a",
            "arguments": {},
        }
    ]
    mock_planner.replan.return_value = [
        {
            "id": "replan_1",
            "description": "Replanned Step",
            "tool_name": "tool_b",
            "arguments": {},
        }
    ]

    mock_tool_a = MagicMock(spec=AbstractTool)
    mock_tool_a.name = "tool_a"
    mock_tool_a.description = "Mock Tool A"
    mock_tool_a.parameters = {}

    mock_tool_b = MagicMock(spec=AbstractTool)
    mock_tool_b.name = "tool_b"
    mock_tool_b.description = "Mock Tool B"
    mock_tool_b.parameters = {}

    engine = MultiStepExecutionEngine(
        action_engine=mock_action_engine,
        planner_service=mock_planner,
        tools=[mock_tool_a, mock_tool_b],
    )

    logs = engine.execute("Clean room")
    assert "Retrying (1/1)" in logs
    assert "Triggering error recovery: replanning remaining steps" in logs
    assert "Completed step: replan_1" in logs
    assert (
        "Final progress: 100%" in logs
    )  # 1 of 1 active steps completed (step_1 discarded, replan_1 completed)


def test_planner_execute_task_tool() -> None:
    mock_action_engine = MagicMock(spec=AbstractActionEngine)
    mock_planner = MagicMock(spec=AbstractPlannerService)
    mock_planner.generate_plan.return_value = []

    tool = PlannerExecuteTaskTool(
        action_engine=mock_action_engine,
        planner_service=mock_planner,
        tools=[],
    )

    assert tool.name == "planner_execute_task"
    assert "task_description" in tool.parameters["properties"]

    res = tool.execute(task_description="Hello world")
    assert "Task Execution Finished" in res
