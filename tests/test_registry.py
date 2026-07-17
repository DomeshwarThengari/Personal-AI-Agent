from src.application.tools.registry import ToolRegistry
from src.application.tools.system_time import SystemTimeTool


def test_tool_registry_operations() -> None:
    """Verifies that registration, lookup, and list methods work correctly."""
    registry = ToolRegistry()

    # 1. Assert initially empty
    assert len(registry.list_tools()) == 0
    assert registry.get_tool("get_system_time") is None

    # 2. Register tool
    time_tool = SystemTimeTool()
    registry.register(time_tool)

    # 3. Lookup and list assertions
    assert len(registry.list_tools()) == 1
    assert registry.get_tool("get_system_time") == time_tool

    # 4. Duplicate registration (should overwrite)
    time_tool_new = SystemTimeTool()
    registry.register(time_tool_new)

    assert len(registry.list_tools()) == 1
    assert registry.get_tool("get_system_time") == time_tool_new
