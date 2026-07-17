import time
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel
from src.domain.entities import Action, ActionResult
from src.domain.interfaces.tool import AbstractTool
from src.domain.interfaces.action_engine import AbstractActionEngine
from src.domain.interfaces.planner_service import AbstractPlannerService
from src.utils.logging import get_logger

logger = get_logger("planner_tools")


class TaskStep(BaseModel):
    """Data model representing a single execution step in a multi-step plan."""

    id: str
    description: str
    tool_name: str
    arguments: Dict[str, Any]
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    result: Optional[str] = None
    error: Optional[str] = None


class TaskQueue:
    """Queue manager keeping track of step execution states and progress."""

    def __init__(self, steps: List[TaskStep]) -> None:
        self.steps = steps
        self.current_index = 0

    def get_next(self) -> Optional[TaskStep]:
        if self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    def mark_completed(self, step_id: str, result: str) -> None:
        for s in self.steps:
            if s.id == step_id:
                s.status = "completed"
                s.result = result
                break
        self.current_index += 1

    def mark_failed(self, step_id: str, error: str) -> None:
        for s in self.steps:
            if s.id == step_id:
                s.status = "failed"
                s.error = error
                break

    def get_progress_percent(self) -> int:
        if not self.steps:
            return 100
        completed = sum(1 for s in self.steps if s.status == "completed")
        return int((completed / len(self.steps)) * 100)

    def replan_remaining(self, new_steps: List[TaskStep]) -> None:
        """Slices out the failed/remaining steps and inserts newly planned steps."""
        # Keep completed steps up to current index
        completed_steps = self.steps[: self.current_index]
        self.steps = completed_steps + new_steps
        # The current index will now point to the first newly added step
        logger.info(f"Task Queue updated with {len(new_steps)} replanned steps.")


class MultiStepExecutionEngine:
    """Orchestrates multi-step executions, tracks progress, and initiates error recovery."""

    def __init__(
        self,
        action_engine: AbstractActionEngine,
        planner_service: AbstractPlannerService,
        tools: List[AbstractTool],
    ) -> None:
        self.action_engine = action_engine
        self.planner_service = planner_service
        self.tools = tools

    def _get_tools_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in self.tools
        ]

    def execute(self, task_description: str) -> str:
        # 1. Generate Initial Plan
        logger.info(f"Planning task: '{task_description}'")
        raw_steps = self.planner_service.generate_plan(
            task_description, self._get_tools_schema()
        )

        steps: List[TaskStep] = []
        for raw_s in raw_steps:
            steps.append(
                TaskStep(
                    id=raw_s.get("id", f"step_{len(steps)+1}"),
                    description=raw_s.get("description", "Executing step"),
                    tool_name=raw_s.get("tool_name", ""),
                    arguments=raw_s.get("arguments", {}),
                )
            )

        queue = TaskQueue(steps)
        logs = ["Plan Generation:"]
        for task_s in queue.steps:
            logs.append(f"  - [{task_s.id}] {task_s.description} ({task_s.tool_name})")

        # 2. Sequential Execution Loop
        while True:
            step = queue.get_next()
            if not step:
                break

            step.status = "running"
            progress = queue.get_progress_percent()
            status_msg = (
                f"[Progress {progress}%] Running: {step.description} ({step.tool_name})"
            )
            print(status_msg)
            logs.append(status_msg)

            # Define retry counter
            retry_count = 0
            max_retries = 1
            success = False
            last_error = ""
            outcome = ""

            # Attempt run with simple retry logic
            while retry_count <= max_retries:
                action = Action(action_type=step.tool_name, parameters=step.arguments)
                result: ActionResult = self.action_engine.execute_action(action)

                if result.status == "success":
                    success = True
                    outcome = result.output or "Success"
                    break
                else:
                    last_error = result.error_message or "Unknown failure"
                    retry_count += 1
                    if retry_count <= max_retries:
                        retry_msg = f"  -> Step failed: {last_error}. Retrying ({retry_count}/{max_retries})..."
                        print(retry_msg)
                        logs.append(retry_msg)
                        time.sleep(0.5)

            if success:
                queue.mark_completed(step.id, outcome)
                success_msg = f"  -> Completed step: {step.id}. Output: {outcome}"
                print(success_msg)
                logs.append(success_msg)
            else:
                queue.mark_failed(step.id, last_error)
                failure_msg = f"  -> Step {step.id} failed permanently: {last_error}."
                print(failure_msg)
                logs.append(failure_msg)

                # TRIGGER ERROR RECOVERY via Dynamic Replanning
                replan_log = (
                    "  -> Triggering error recovery: replanning remaining steps..."
                )
                print(replan_log)
                logs.append(replan_log)

                # Get remaining steps from the queue (excluding the failed step itself)
                remaining = []
                for queue_s in queue.steps[queue.current_index + 1 :]:
                    remaining.append(
                        {
                            "id": queue_s.id,
                            "description": queue_s.description,
                            "tool_name": queue_s.tool_name,
                            "arguments": queue_s.arguments,
                        }
                    )

                # Call replanner service
                failed_data = {
                    "id": step.id,
                    "description": step.description,
                    "tool_name": step.tool_name,
                    "arguments": step.arguments,
                }
                replanned_raw = self.planner_service.replan(
                    task_description,
                    failed_data,
                    last_error,
                    remaining,
                    self._get_tools_schema(),
                )

                if not replanned_raw:
                    # Replanner returned empty list, abort execution
                    abort_msg = "  -> Recovery replanning returned no steps. Aborting."
                    print(abort_msg)
                    logs.append(abort_msg)
                    break

                replanned_steps: List[TaskStep] = []
                for idx, r in enumerate(replanned_raw, 1):
                    replanned_steps.append(
                        TaskStep(
                            id=r.get("id", f"replan_{idx}"),
                            description=r.get("description", "Recovered step"),
                            tool_name=r.get("tool_name", ""),
                            arguments=r.get("arguments", {}),
                        )
                    )

                queue.replan_remaining(replanned_steps)

        final_progress = queue.get_progress_percent()
        summary = f"\nTask Execution Finished. Final progress: {final_progress}%"
        logs.append(summary)
        return "\n".join(logs)


class PlannerExecuteTaskTool(AbstractTool):
    """Tool allowing LLM to coordinate complex multi-step workflows."""

    def __init__(
        self,
        action_engine: AbstractActionEngine,
        planner_service: AbstractPlannerService,
        tools: List[AbstractTool],
    ) -> None:
        self.action_engine = action_engine
        self.planner_service = planner_service
        self.tools = tools

    @property
    def name(self) -> str:
        return "planner_execute_task"

    @property
    def description(self) -> str:
        return (
            "Decompose a complex, multi-step user task (e.g. searching YouTube, "
            "monitoring system stats, and saving files) into a planned queue, execute it, "
            "track progress, and handle error recovery dynamically."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "Full description of the complex multi-step request.",
                }
            },
            "required": ["task_description"],
        }

    def execute(self, **kwargs: Any) -> str:
        task_description = kwargs.get("task_description")
        if not task_description:
            return "Error: 'task_description' parameter is required."

        engine = MultiStepExecutionEngine(
            action_engine=self.action_engine,
            planner_service=self.planner_service,
            # Filter out the planner tool itself to prevent infinite loop planning
            tools=[t for t in self.tools if t.name != self.name],
        )
        return engine.execute(task_description)
