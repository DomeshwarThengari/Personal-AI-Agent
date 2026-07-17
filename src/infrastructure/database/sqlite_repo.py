import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from src.config.settings import settings
from src.domain.entities import Message
from src.domain.interfaces.repository import AbstractChatRepository
from src.utils.logging import get_logger

logger = get_logger("sqlite_repo")


class SQLiteChatRepository(AbstractChatRepository):
    """SQLite implementation of conversation history memory repository."""

    def __init__(self, db_path: str = settings.SQLITE_DB_PATH):
        """Initializes database tables and establishes filepath structure."""
        self.db_path = Path(db_path)
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a standard sqlite3 Connection object."""
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        """Initializes schema and tables if they do not exist."""
        logger.info(f"Initializing SQLite database at: {self.db_path}")
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        """
        create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_table_sql)
                cursor.execute(create_index_sql)
                conn.commit()
            logger.debug("Database initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize database: {e}", exc_info=True)
            raise RuntimeError(f"Database setup error: {e}") from e

    def save_message(self, session_id: str, message: Message) -> None:
        """Inserts a new message entry into the database."""
        logger.debug(f"Saving message ({message.id}) for session: '{session_id}'")
        insert_sql = """
        INSERT OR REPLACE INTO messages (id, session_id, role, content, timestamp)
        VALUES (?, ?, ?, ?, ?);
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    insert_sql,
                    (
                        message.id,
                        session_id,
                        message.role,
                        message.content,
                        message.timestamp.isoformat(),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(
                f"Failed to save message {message.id} to SQLite: {e}",
                exc_info=True,
            )
            raise e

    def get_session_messages(self, session_id: str) -> List[Message]:
        """Retrieves session messages ordered by timestamp ascending."""
        logger.debug(f"Retrieving message history for session: '{session_id}'")
        select_sql = """
        SELECT id, role, content, timestamp
        FROM messages
        WHERE session_id = ?
        ORDER BY timestamp ASC;
        """
        messages = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (session_id,))
                rows = cursor.fetchall()

                for row in rows:
                    msg_id, role, content, ts_str = row
                    # Parse ISO timestamp back to timezone-aware UTC datetime
                    try:
                        ts = datetime.fromisoformat(ts_str)
                    except ValueError:
                        ts = datetime.now(timezone.utc)

                    messages.append(
                        Message(
                            id=msg_id,
                            role=role,
                            content=content,
                            timestamp=ts,
                        )
                    )
        except Exception as e:
            logger.error(
                f"Failed to load session messages for {session_id}: {e}",
                exc_info=True,
            )
            raise e

        logger.debug(
            f"Loaded {len(messages)} messages from SQLite for session '{session_id}'"
        )
        return messages

    def clear_session(self, session_id: str) -> None:
        """Deletes all messages for a session ID."""
        logger.info(f"Clearing conversation history for session: '{session_id}'")
        delete_sql = """
        DELETE FROM messages
        WHERE session_id = ?;
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(delete_sql, (session_id,))
                conn.commit()
        except Exception as e:
            logger.error(
                f"Failed to clear session {session_id} from SQLite: {e}",
                exc_info=True,
            )
            raise e
