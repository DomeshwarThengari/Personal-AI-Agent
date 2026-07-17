import sqlite3
from pathlib import Path
from src.infrastructure.database.sqlite_memory import SQLiteMemoryService
from src.infrastructure.database.sqlite_repo import SQLiteChatRepository
from src.application.services.security_manager import SecurityManager


def _get_indexes(db_path: Path) -> list[str]:
    """Queries sqlite_master to fetch all index names in the database."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type = 'index';")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows if row[0] is not None]


def test_database_indexes_exist(tmp_path: Path) -> None:
    """Verifies that all required performance indexes are correctly generated during service initialization."""
    db_file = tmp_path / "test_perf.db"

    # Initialize services targeting the temporary test DB
    SQLiteMemoryService(db_path=str(db_file))
    SQLiteChatRepository(db_path=str(db_file))
    SecurityManager(db_path=str(db_file))

    # Retrieve all created index names
    indexes = _get_indexes(db_file)

    # Assert that key indexes exist
    assert "idx_preferences_key" in indexes
    assert "idx_command_history_timestamp" in indexes
    assert "idx_messages_session" in indexes
    assert "idx_messages_session_time" in indexes
    assert "idx_audit_logs_timestamp" in indexes


def test_preferences_query_speed(tmp_path: Path) -> None:
    """Asserts that preference retrieval is extremely fast under high loads."""
    db_file = tmp_path / "test_load.db"
    memory_service = SQLiteMemoryService(db_path=str(db_file))

    # Populate database with 5,000 dummy preferences
    with sqlite3.connect(str(db_file)) as conn:
        cursor = conn.cursor()
        data = [(f"key_{i}", f"value_{i}", "2026-07-17T23:00:00Z") for i in range(5000)]
        cursor.executemany(
            "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?);",
            data,
        )
        conn.commit()

    import time

    # Measure time to query a specific preference
    start = time.perf_counter()
    val = memory_service.get_preference("key_2500")
    end = time.perf_counter()

    duration_ms = (end - start) * 1000.0

    assert val == "value_2500"
    # Query must complete in under 5 milliseconds (normally < 0.1ms with indexes)
    assert duration_ms < 5.0
