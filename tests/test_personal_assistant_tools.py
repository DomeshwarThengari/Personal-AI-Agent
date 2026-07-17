from typing import Any
from unittest.mock import patch
from src.application.tools.personal_assistant_tools import (
    AssistantCalendarTool,
    AssistantTodoTool,
    AssistantNotesTool,
    AssistantGetWeatherTool,
    AssistantGetNewsTool,
    AssistantSummarizeEmailsTool,
    AssistantSendNotificationTool,
    AssistantDailyBriefingTool,
    AssistantTriggerRoutineTool,
)


def test_calendar_tool() -> None:
    tool = AssistantCalendarTool()
    assert tool.name == "assistant_calendar"

    # Add Event
    res_add = tool.execute(
        action="add",
        title="Sync Meeting",
        description="Weekly Sync",
        start_time="2026-07-18 10:00",
        end_time="2026-07-18 11:00",
    )
    assert "Successfully added event" in res_add
    assert "Sync Meeting" in res_add

    # List Events
    res_list = tool.execute(action="list")
    assert "Sync Meeting" in res_list

    # Extract ID
    # Format is "- [id] title..."
    lines = res_list.split("\n")
    event_line = [line for line in lines if "Sync Meeting" in line][0]
    event_id = event_line.split("]")[0].split("[")[1]

    # Delete Event
    res_del = tool.execute(action="delete", event_id=event_id)
    assert "Successfully deleted event" in res_del


def test_todo_tool() -> None:
    tool = AssistantTodoTool()
    assert tool.name == "assistant_todo"

    # Add Todo
    res_add = tool.execute(action="add", task="Buy groceries", due_date="2026-07-19")
    assert "Successfully added todo" in res_add

    # List Todos
    res_list = tool.execute(action="list")
    assert "Buy groceries" in res_list

    # Extract ID
    lines = res_list.split("\n")
    todo_line = [line for line in lines if "Buy groceries" in line][0]
    todo_id = todo_line.split("]")[1].split("[")[1]

    # Complete Todo
    res_complete = tool.execute(action="complete", todo_id=todo_id)
    assert "Successfully completed todo" in res_complete

    # Delete Todo
    res_del = tool.execute(action="delete", todo_id=todo_id)
    assert "Successfully deleted todo" in res_del


def test_notes_tool() -> None:
    tool = AssistantNotesTool()
    assert tool.name == "assistant_notes"

    # Create Note
    res_create = tool.execute(
        action="create", title="App Ideas", content="1. Visual memory assistant."
    )
    assert "Successfully created note" in res_create

    # List Notes
    res_list = tool.execute(action="list")
    assert "App Ideas" in res_list

    # Extract ID
    lines = res_list.split("\n")
    note_line = [line for line in lines if "App Ideas" in line][0]
    note_id = note_line.split("]")[0].split("[")[1]

    # View Note by ID
    res_view = tool.execute(action="view", note_id=note_id)
    assert "Visual memory assistant" in res_view

    # Delete Note
    res_del = tool.execute(action="delete", note_id=note_id)
    assert "Successfully deleted note" in res_del


def test_weather_tool() -> None:
    tool = AssistantGetWeatherTool()
    assert tool.name == "assistant_get_weather"
    res = tool.execute(location="San Francisco")
    assert "San Francisco" in res
    assert "Sunny" in res


def test_news_tool() -> None:
    tool = AssistantGetNewsTool()
    assert tool.name == "assistant_get_news"

    res_general = tool.execute(category="general")
    assert "Global summit" in res_general

    res_tech = tool.execute(category="technology")
    assert "quantum computing" in res_tech


def test_email_summaries_tool() -> None:
    tool = AssistantSummarizeEmailsTool()
    assert tool.name == "assistant_summarize_emails"
    res = tool.execute(limit=2)
    assert "Inbox Summary:" in res
    assert "GitHub Notifications" in res


@patch("subprocess.run")
def test_send_notification_tool(mock_run: Any) -> None:
    mock_run.return_value.returncode = 0
    tool = AssistantSendNotificationTool()
    assert tool.name == "assistant_send_notification"

    res = tool.execute(title="Test Alert", message="Hello World")
    assert "Notification successfully sent" in res
    mock_run.assert_called_once_with(
        ["notify-send", "Test Alert", "Hello World"],
        capture_output=True,
        text=True,
        timeout=5,
    )


def test_daily_briefing_tool() -> None:
    # Set up some temp calendar & todo items to verify briefing inclusion
    cal_tool = AssistantCalendarTool()
    todo_tool = AssistantTodoTool()

    cal_tool.execute(
        action="add",
        title="Sync Team",
        start_time="2026-07-18 10:00",
        end_time="2026-07-18 11:00",
    )
    todo_tool.execute(action="add", task="Read documentation")

    brief_tool = AssistantDailyBriefingTool()
    res = brief_tool.execute(location="Seattle")

    assert "Seattle" in res
    assert "Sync Team" in res
    assert "Read documentation" in res


def test_trigger_routine_tool() -> None:
    tool = AssistantTriggerRoutineTool()
    assert tool.name == "assistant_trigger_routine"

    res_morning = tool.execute(routine="morning")
    assert "Morning Routine Triggered" in res_morning

    res_work = tool.execute(routine="work_start")
    assert "Work Start Routine Triggered" in res_work

    res_evening = tool.execute(routine="evening")
    assert "Evening Routine Triggered" in res_evening
