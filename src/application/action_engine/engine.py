from typing import Optional
from src.domain.entities import Action, ActionResult
from src.domain.interfaces.action_engine import AbstractActionEngine
from src.domain.interfaces.memory_service import AbstractMemoryService
from src.application.tools.registry import ToolRegistry
from src.utils.logging import get_logger

logger = get_logger("action_engine")


class ActionEngine(AbstractActionEngine):
    """Concrete implementation of the Action Engine execution orchestrator."""

    def __init__(
        self,
        registry: ToolRegistry,
        memory_service: Optional[AbstractMemoryService] = None,
    ) -> None:
        """Initializes the engine with a central tool registry and optional memory service.

        Args:
            registry: The ToolRegistry instance containing registered tools.
            memory_service: The optional memory service to log command history.
        """
        self.registry = registry
        self.memory_service = memory_service

    def execute_action(self, action: Action) -> ActionResult:
        """Looks up the matched tool and executes it with mapped arguments."""
        tool_name = action.action_type
        logger.info(f"Action Engine executing request for tool: '{tool_name}'")

        # Find registered tool
        tool = self.registry.get_tool(tool_name)
        if not tool:
            error_msg = f"No registered tool found matching name: '{tool_name}'"
            logger.error(error_msg)
            return ActionResult(
                action_id=action.id,
                status="failure",
                error_message=error_msg,
            )

        try:
            # Execute tool logic with params
            logger.debug(
                f"Executing tool '{tool_name}' with parameters: {action.parameters}"
            )
            output = tool.execute(**action.parameters)

            if self.memory_service:
                self.memory_service.log_command(
                    command=f"Tool: {tool_name} with params: {action.parameters}",
                    executed_by="assistant",
                    status="success",
                )

            # Return success ActionResult
            return ActionResult(
                action_id=action.id,
                status="success",
                output=str(output),
            )

        except Exception as e:
            # Safely capture any execution failures
            error_msg = f"Exception raised during tool execution: {e}"
            logger.error(f"Tool '{tool_name}' failed to execute: {e}", exc_info=True)

            if self.memory_service:
                self.memory_service.log_command(
                    command=f"Tool: {tool_name} with params: {action.parameters}",
                    executed_by="assistant",
                    status=f"failure: {e}",
                )

            return ActionResult(
                action_id=action.id,
                status="failure",
                error_message=error_msg,
            )
