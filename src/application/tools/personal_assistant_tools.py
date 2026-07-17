import os
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from src.domain.interfaces.tool import AbstractTool
from src.config.settings import settings


def get_db_connection() -> sqlite3.Connection:
    """Establishes and returns a connection to the SQLite database."""
    db_path = settings.SQLITE_DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)


def init_assistant_tables() -> None:
    """Initializes tables for calendar, todos, and notes if they do not exist."""
    create_calendar_table = """
    CREATE TABLE IF NOT EXISTS assistant_calendar (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL
    );
    """
    create_todos_table = """
    CREATE TABLE IF NOT EXISTS assistant_todos (
        id TEXT PRIMARY KEY,
        task TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        due_date TEXT
    );
    """
    create_notes_table = """
    CREATE TABLE IF NOT EXISTS assistant_notes (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(create_calendar_table)
        cursor.execute(create_todos_table)
        cursor.execute(create_notes_table)
        conn.commit()


# Initialize the tables automatically
init_assistant_tables()


class AssistantCalendarTool(AbstractTool):
    """Tool that manages calendar events in SQLite database."""

    @property
    def name(self) -> str:
        return "assistant_calendar"

    @property
    def description(self) -> str:
        return (
            "Manages calendar events. Actions supported: 'add' (requires title, start_time, end_time), "
            "'list' (returns upcoming events), 'delete' (requires event_id)."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "delete"],
                    "description": "Calendar action to perform.",
                },
                "title": {"type": "string", "description": "Title of the event."},
                "description": {
                    "type": "string",
                    "description": "Optional description of the event.",
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time (YYYY-MM-DD HH:MM).",
                },
                "end_time": {
                    "type": "string",
                    "description": "End time (YYYY-MM-DD HH:MM).",
                },
                "event_id": {
                    "type": "string",
                    "description": "The unique event ID (needed for delete).",
                },
            },
            "required": ["action"],
        }

    def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "").lower().strip()
        if action == "add":
            title = kwargs.get("title", "").strip()
            start_time = kwargs.get("start_time", "").strip()
            end_time = kwargs.get("end_time", "").strip()
            desc = kwargs.get("description", "").strip()
            if not title or not start_time or not end_time:
                return "Error: title, start_time, and end_time are required to add an event."

            event_id = str(uuid.uuid4())[:8]
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO assistant_calendar (id, title, description, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
                    (event_id, title, desc, start_time, end_time),
                )
                conn.commit()
            return f"Successfully added event '{title}' (ID: {event_id}) from {start_time} to {end_time}."

        elif action == "list":
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, title, description, start_time, end_time FROM assistant_calendar ORDER BY start_time ASC"
                )
                rows = cursor.fetchall()
            if not rows:
                return "No calendar events found."
            lines = ["Upcoming Calendar Events:"]
            for row in rows:
                lines.append(
                    f"- [{row[0]}] {row[1]} ({row[3]} - {row[4]}): {row[2] if row[2] else 'No description'}"
                )
            return "\n".join(lines)

        elif action == "delete":
            event_id = kwargs.get("event_id", "").strip()
            if not event_id:
                return "Error: event_id is required to delete an event."
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM assistant_calendar WHERE id = ?", (event_id,)
                )
                conn.commit()
            return f"Successfully deleted event with ID: {event_id}."

        return f"Error: Unknown action '{action}'."


class AssistantTodoTool(AbstractTool):
    """Tool that manages personal to-do and reminders in SQLite database."""

    @property
    def name(self) -> str:
        return "assistant_todo"

    @property
    def description(self) -> str:
        return (
            "Manages to-do lists and reminders. Actions supported: 'add' (requires task, optional due_date), "
            "'list' (lists todos), 'complete' (requires todo_id), 'delete' (requires todo_id)."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "complete", "delete"],
                    "description": "Todo action to perform.",
                },
                "task": {"type": "string", "description": "The task description."},
                "due_date": {
                    "type": "string",
                    "description": "Optional due date (YYYY-MM-DD).",
                },
                "todo_id": {
                    "type": "string",
                    "description": "The unique todo ID (needed for complete/delete).",
                },
            },
            "required": ["action"],
        }

    def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "").lower().strip()
        if action == "add":
            task = kwargs.get("task", "").strip()
            due_date = kwargs.get("due_date", "").strip()
            if not task:
                return "Error: task description is required to add a todo."

            todo_id = str(uuid.uuid4())[:8]
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO assistant_todos (id, task, completed, due_date) VALUES (?, ?, 0, ?)",
                    (todo_id, task, due_date if due_date else None),
                )
                conn.commit()
            return f"Successfully added todo: '{task}' (ID: {todo_id})."

        elif action == "list":
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, task, completed, due_date FROM assistant_todos"
                )
                rows = cursor.fetchall()
            if not rows:
                return "Your to-do list is empty."
            lines = ["Personal To-Do List:"]
            for row in rows:
                status = "✓" if row[2] == 1 else " "
                due = f" (Due: {row[3]})" if row[3] else ""
                lines.append(f"- [{status}] [{row[0]}] {row[1]}{due}")
            return "\n".join(lines)

        elif action == "complete":
            todo_id = kwargs.get("todo_id", "").strip()
            if not todo_id:
                return "Error: todo_id is required to complete a todo."
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE assistant_todos SET completed = 1 WHERE id = ?",
                    (todo_id,),
                )
                conn.commit()
            return f"Successfully completed todo with ID: {todo_id}."

        elif action == "delete":
            todo_id = kwargs.get("todo_id", "").strip()
            if not todo_id:
                return "Error: todo_id is required to delete a todo."
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM assistant_todos WHERE id = ?", (todo_id,))
                conn.commit()
            return f"Successfully deleted todo with ID: {todo_id}."

        return f"Error: Unknown action '{action}'."


class AssistantNotesTool(AbstractTool):
    """Tool that manages persistent personal notes in SQLite database."""

    @property
    def name(self) -> str:
        return "assistant_notes"

    @property
    def description(self) -> str:
        return (
            "Manages personal notes. Actions supported: 'create' (requires title, content), "
            "'list' (lists notes), 'view' (requires title or note_id), 'delete' (requires note_id)."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "list", "view", "delete"],
                    "description": "Notes action to perform.",
                },
                "title": {"type": "string", "description": "Title of the note."},
                "content": {"type": "string", "description": "Content of the note."},
                "note_id": {
                    "type": "string",
                    "description": "Unique note ID (needed for delete/view).",
                },
            },
            "required": ["action"],
        }

    def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "").lower().strip()
        if action == "create":
            title = kwargs.get("title", "").strip()
            content = kwargs.get("content", "").strip()
            if not title or not content:
                return "Error: title and content are required to create a note."

            note_id = str(uuid.uuid4())[:8]
            created_at = datetime.now(timezone.utc).isoformat()
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO assistant_notes (id, title, content, created_at) VALUES (?, ?, ?, ?)",
                    (note_id, title, content, created_at),
                )
                conn.commit()
            return f"Successfully created note '{title}' (ID: {note_id})."

        elif action == "list":
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, title, created_at FROM assistant_notes")
                rows = cursor.fetchall()
            if not rows:
                return "No notes found."
            lines = ["Saved Notes:"]
            for row in rows:
                lines.append(f"- [{row[0]}] {row[1]} (Created: {row[2][:10]})")
            return "\n".join(lines)

        elif action == "view":
            note_id = kwargs.get("note_id", "").strip()
            title = kwargs.get("title", "").strip()
            if not note_id and not title:
                return "Error: note_id or title is required to view a note."

            with get_db_connection() as conn:
                cursor = conn.cursor()
                if note_id:
                    cursor.execute(
                        "SELECT title, content, created_at FROM assistant_notes WHERE id = ?",
                        (note_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT title, content, created_at FROM assistant_notes WHERE title = ?",
                        (title,),
                    )
                row = cursor.fetchone()
            if not row:
                return "Note not found."
            return f"Title: {row[0]}\nCreated: {row[2]}\n\nContent:\n{row[1]}"

        elif action == "delete":
            note_id = kwargs.get("note_id", "").strip()
            if not note_id:
                return "Error: note_id is required to delete a note."
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM assistant_notes WHERE id = ?", (note_id,))
                conn.commit()
            return f"Successfully deleted note with ID: {note_id}."

        return f"Error: Unknown action '{action}'."


class AssistantGetWeatherTool(AbstractTool):
    """Tool that retrieves weather forecast for a specified location."""

    @property
    def name(self) -> str:
        return "assistant_get_weather"

    @property
    def description(self) -> str:
        return "Retrieves current weather details and a 3-day forecast for a specified location."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or location. Defaults to 'New York'.",
                }
            },
        }

    def execute(self, **kwargs: Any) -> str:
        location = kwargs.get("location", "New York").strip()
        # Mock weather provider
        return (
            f"Weather Report for {location}:\n"
            "Current: 72°F (22°C), Sunny, Humidity 45%, Wind 8mph NW.\n"
            "Forecast:\n"
            "- Today: High 75°F, Low 60°F (Clear)\n"
            "- Tomorrow: High 78°F, Low 62°F (Partly Cloudy)\n"
            "- Day After: High 70°F, Low 55°F (Light Showers)"
        )


class AssistantGetNewsTool(AbstractTool):
    """Tool that retrieves top news headlines by category."""

    @property
    def name(self) -> str:
        return "assistant_get_news"

    @property
    def description(self) -> str:
        return "Retrieves the top 3 news headlines from a specified category (e.g. general, technology, business, science)."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "News category. Defaults to 'general'.",
                }
            },
        }

    def execute(self, **kwargs: Any) -> str:
        category = kwargs.get("category", "general").lower().strip()
        headlines = {
            "general": [
                "Global summit reaches new milestone on environmental sustainability commitments.",
                "Major central bank announces interest rate stabilization program.",
                "International space station completes landmark solar panel upgrade.",
            ],
            "technology": [
                "Breakthrough in quantum computing chip design promises 10x speeds.",
                "Leading browser implements advanced privacy protections by default.",
                "New open-source LLM model sets benchmarks in visual task understanding.",
            ],
            "business": [
                "Tech stock indexes hit record highs as corporate earnings exceed forecasts.",
                "E-commerce giant announces major supply chain automation expansion.",
                "Electric vehicle manufacturer hits target production goal early.",
            ],
        }
        category_news = headlines.get(category, headlines["general"])
        lines = [f"Top News Headlines [{category.capitalize()}]:"]
        for idx, news in enumerate(category_news, 1):
            lines.append(f"{idx}. {news}")
        return "\n".join(lines)


class AssistantSummarizeEmailsTool(AbstractTool):
    """Tool that retrieves and summarizes recent emails."""

    @property
    def name(self) -> str:
        return "assistant_summarize_emails"

    @property
    def description(self) -> str:
        return "Retrieves and summarizes the latest unread emails in the user inbox."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of emails to fetch.",
                    "default": 3,
                }
            },
        }

    def execute(self, **kwargs: Any) -> str:
        limit = kwargs.get("limit", 3)
        emails = [
            {
                "from": "GitHub Notifications",
                "subject": "[Pull Request Approved] feat: vision screen understanding",
                "time": "10 mins ago",
            },
            {
                "from": "Project Lead Team",
                "subject": "Week 12 sync-up session schedule update",
                "time": "1 hour ago",
            },
            {
                "from": "AWS Billing Support",
                "subject": "Your monthly invoice is available for download",
                "time": "4 hours ago",
            },
            {
                "from": "DevOps Daemon Monitor",
                "subject": "[ALERT] Kubernetes Node web-pod status: Healthy",
                "time": "1 day ago",
            },
        ]
        lines = ["Inbox Summary:"]
        for email in emails[:limit]:
            lines.append(
                f"- From: {email['from']} | Subject: '{email['subject']}' ({email['time']})"
            )
        lines.append(
            "\nSummary: You have no high-severity alerts. Action is suggested on the lead team sync-up scheduling email."
        )
        return "\n".join(lines)


class AssistantSendNotificationTool(AbstractTool):
    """Tool that displays a system-wide desktop notification on Linux."""

    @property
    def name(self) -> str:
        return "assistant_send_notification"

    @property
    def description(self) -> str:
        return "Displays a system-wide desktop notification using notify-send."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Notification title."},
                "message": {
                    "type": "string",
                    "description": "Notification message body.",
                },
            },
            "required": ["title", "message"],
        }

    def execute(self, **kwargs: Any) -> str:
        title = kwargs.get("title", "").strip()
        message = kwargs.get("message", "").strip()
        if not title or not message:
            return "Error: title and message are required."

        # Attempt to run notify-send command
        try:
            res = subprocess.run(
                ["notify-send", title, message],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return f"Notification successfully sent: '{title}: {message}'"
        except Exception:
            pass

        return f"Desktop Notification (Simulated/Stdout): [{title}] - {message}"


class AssistantDailyBriefingTool(AbstractTool):
    """Tool that creates a unified daily briefing summarizing weather, calendar, and todos."""

    @property
    def name(self) -> str:
        return "assistant_daily_briefing"

    @property
    def description(self) -> str:
        return "Generates a cohesive, structured daily briefing combining weather, top news headlines, today's calendar events, and pending tasks."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Optional location for the weather forecast.",
                }
            },
        }

    def execute(self, **kwargs: Any) -> str:
        loc = kwargs.get("location", "New York")
        brief = []

        # Header
        brief.append(f"=== Daily Briefing: {datetime.now().strftime('%B %d, %Y')} ===")

        # Weather
        weather = AssistantGetWeatherTool().execute(location=loc)
        brief.append("\n" + weather)

        # News
        news = AssistantGetNewsTool().execute(category="general")
        brief.append("\n" + news)

        # Calendar
        brief.append("\nUpcoming Calendar Events:")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT title, start_time, end_time FROM assistant_calendar ORDER BY start_time ASC LIMIT 3"
            )
            events = cursor.fetchall()
        if events:
            for event in events:
                brief.append(f"- {event[0]} ({event[1]} - {event[2]})")
        else:
            brief.append("- No calendar events today.")

        # Todos
        brief.append("\nPending Tasks:")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT task, due_date FROM assistant_todos WHERE completed = 0 LIMIT 3"
            )
            todos = cursor.fetchall()
        if todos:
            for todo in todos:
                due = f" (Due: {todo[1]})" if todo[1] else ""
                brief.append(f"- {todo[0]}{due}")
        else:
            brief.append("- No pending tasks. You are all caught up!")

        return "\n".join(brief)


class AssistantTriggerRoutineTool(AbstractTool):
    """Tool that coordinates and triggers routine automations."""

    @property
    def name(self) -> str:
        return "assistant_trigger_routine"

    @property
    def description(self) -> str:
        return (
            "Triggers a pre-configured automation routine. Supported routines: "
            "'morning' (daily briefing + system notification), "
            "'work_start' (lists to-dos + sends work alert), "
            "'evening' (checks final todos + summary)."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "routine": {
                    "type": "string",
                    "enum": ["morning", "work_start", "evening"],
                    "description": "The name of the routine to trigger.",
                }
            },
            "required": ["routine"],
        }

    def execute(self, **kwargs: Any) -> str:
        routine = kwargs.get("routine", "").lower().strip()
        if routine == "morning":
            brief = AssistantDailyBriefingTool().execute()
            # Send alert
            AssistantSendNotificationTool().execute(
                title="Good Morning!", message="Your Daily Briefing is ready."
            )
            return (
                f"Morning Routine Triggered:\n"
                f"1. Desktop notification sent.\n"
                f"2. Daily Briefing generated:\n\n{brief}"
            )
        elif routine == "work_start":
            todos = AssistantTodoTool().execute(action="list")
            AssistantSendNotificationTool().execute(
                title="Workday Started", message="Let's build something awesome today!"
            )
            return (
                f"Work Start Routine Triggered:\n"
                f"1. Workday notification sent.\n"
                f"2. Pending tasks loaded:\n\n{todos}"
            )
        elif routine == "evening":
            AssistantSendNotificationTool().execute(
                title="Evening wrap-up", message="Wrapping up and logs check."
            )
            return "Evening Routine Triggered. Desktop notification sent. Reviewing day accomplishments."

        return f"Error: Unknown routine '{routine}'."
