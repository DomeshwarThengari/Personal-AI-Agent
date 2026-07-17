from typing import Any, Optional
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
        security_manager: Optional[Any] = None,
    ) -> None:
        """Initializes the engine with a central tool registry, optional memory service,

        and security manager integration.
        """
        self.registry = registry
        self.memory_service = memory_service

        from src.application.services.security_manager import SecurityManager

        self.security_manager = security_manager or SecurityManager()

    def execute_action(self, action: Action) -> ActionResult:
        """Looks up the matched tool and executes it with mapped arguments after validating security constraints."""
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

        # Enforce security manager verification policies
        security_status = self.security_manager.verify_execution(
            tool_name, action.parameters
        )
        if security_status == "denied":
            error_msg = f"Security Violation: Access Denied. User role '{self.security_manager.get_user_role().value}' is not authorized to execute tool '{tool_name}'."
            logger.warning(error_msg)
            return ActionResult(
                action_id=action.id,
                status="failure",
                error_message=error_msg,
            )
        elif security_status == "confirmation_required":
            error_msg = f"Security Confirmation Required: Execution of High risk tool '{tool_name}' requires confirmation. Please retry with confirmed=True."
            logger.warning(error_msg)
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
