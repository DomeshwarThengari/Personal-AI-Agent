from typing import Dict, List, Optional
from src.domain.interfaces.tool import AbstractTool
from src.utils.logging import get_logger

logger = get_logger("tool_registry")


class ToolRegistry:
    """Central registry class to register, track, and retrieve application tools."""

    def __init__(self) -> None:
        """Initializes empty dictionary mappings."""
        self._tools: Dict[str, AbstractTool] = {}

    def register(self, tool: AbstractTool) -> None:
        """Registers a tool inside the repository.

        Args:
            tool: Concrete implementation of AbstractTool.
        """
        name = tool.name
        if name in self._tools:
            logger.warning(
                f"Tool '{name}' is already registered. Overwriting existing entry."
            )
        self._tools[name] = tool
        logger.debug(f"Successfully registered tool: '{name}'")

    def get_tool(self, name: str) -> Optional[AbstractTool]:
        """Retrieves a registered tool by its identifier.

        Args:
            name: String identifier of the tool.

        Returns:
            The AbstractTool instance if found, else None.
        """
        return self._tools.get(name)

    def list_tools(self) -> List[AbstractTool]:
        """Returns all registered tool instances.

        Returns:
            List of AbstractTool objects.
        """
        return list(self._tools.values())
