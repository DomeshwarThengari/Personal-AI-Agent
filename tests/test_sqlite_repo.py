from pathlib import Path
from src.domain.entities import Message
from src.infrastructure.database.sqlite_repo import SQLiteChatRepository


def test_sqlite_repo_lifecycle(tmp_path: Path) -> None:
    """Verifies table setup, message insertions, history loading, and session clearing."""
    db_file = tmp_path / "test_assistant.db"

    # Initialize Repo
    repo = SQLiteChatRepository(db_path=str(db_file))

    assert db_file.exists() is True

    # 1. Assert history is initially empty
    initial_history = repo.get_session_messages("test_sess")
    assert len(initial_history) == 0

    # 2. Insert messages
    msg1 = Message(role="user", content="Hello, test query")
    msg2 = Message(role="assistant", content="Response output")

    repo.save_message(session_id="test_sess", message=msg1)
    repo.save_message(session_id="test_sess", message=msg2)

    # 3. Retrieve and assert order
    history = repo.get_session_messages("test_sess")
    assert len(history) == 2
    assert history[0].id == msg1.id
    assert history[0].role == "user"
    assert history[0].content == "Hello, test query"
    assert history[1].id == msg2.id
    assert history[1].role == "assistant"
    assert history[1].content == "Response output"

    # Verify isolation (different session ID is empty)
    other_history = repo.get_session_messages("other_sess")
    assert len(other_history) == 0

    # 4. Clear session
    repo.clear_session("test_sess")
    cleared_history = repo.get_session_messages("test_sess")
    assert len(cleared_history) == 0
