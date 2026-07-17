from src.application.tools.system_time import SystemTimeTool


def test_system_time_tool_properties() -> None:
    """Verifies that the SystemTimeTool declares correct parameters and metadata."""
    tool = SystemTimeTool()

    assert tool.name == "get_system_time"
    assert "local date" in tool.description.lower()
    assert isinstance(tool.parameters, dict)
    assert tool.parameters["type"] == "object"


def test_system_time_tool_execution() -> None:
    """Verifies execution output is a formatted string."""
    tool = SystemTimeTool()
    result = tool.execute()

    assert isinstance(result, str)
    assert len(result) > 0

    # It output should contain calendar details, e.g., year, month, or time colon separators
    assert ":" in result
