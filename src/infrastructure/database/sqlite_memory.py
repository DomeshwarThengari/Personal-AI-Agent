import hashlib
import json
import random
import sqlite3
import struct
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
from src.domain.interfaces.memory_service import AbstractMemoryService
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger("sqlite_memory")


class SQLiteMemoryService(AbstractMemoryService):
    """SQLite implementation of AbstractMemoryService.

    Provides a clean, SQL-based memory system for preferences, projects, command logs,
    and a local vector search engine.
    """

    def __init__(self, db_path: str = settings.SQLITE_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        """Creates the SQLite tables if they do not exist."""
        logger.info(f"Initializing Memory tables in SQLite at: {self.db_path}")

        create_preferences_sql = """
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """

        create_projects_sql = """
        CREATE TABLE IF NOT EXISTS projects (
            name TEXT PRIMARY KEY,
            description TEXT,
            tech_stack TEXT, -- JSON serialized list
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """

        create_command_history_sql = """
        CREATE TABLE IF NOT EXISTS command_history (
            id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            executed_by TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        """

        create_vector_memories_sql = """
        CREATE TABLE IF NOT EXISTS vector_memories (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            embedding BLOB NOT NULL, -- Binary packed float array
            metadata TEXT NOT NULL,  -- JSON serialized dict
            created_at TEXT NOT NULL
        );
        """

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_preferences_sql)
                cursor.execute(create_projects_sql)
                cursor.execute(create_command_history_sql)
                cursor.execute(create_vector_memories_sql)
                conn.commit()
            logger.debug("Memory tables initialized successfully.")
        except Exception as e:
            logger.critical(
                f"Failed to initialize memory database tables: {e}", exc_info=True
            )
            raise RuntimeError(f"Memory database setup error: {e}") from e

    # --- User Preferences ---

    def get_preference(self, key: str) -> Optional[str]:
        select_sql = "SELECT value FROM preferences WHERE key = ?;"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (key,))
                row = cursor.fetchone()
                return str(row[0]) if row else None
        except Exception as e:
            logger.error(f"Error fetching preference for '{key}': {e}")
            return None

    def set_preference(self, key: str, value: str) -> None:
        insert_sql = """
        INSERT OR REPLACE INTO preferences (key, value, updated_at)
        VALUES (?, ?, ?);
        """
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(insert_sql, (key, value, now))
                conn.commit()
        except Exception as e:
            logger.error(f"Error setting preference '{key}': {e}")
            raise e

    def delete_preference(self, key: str) -> None:
        delete_sql = "DELETE FROM preferences WHERE key = ?;"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(delete_sql, (key,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error deleting preference '{key}': {e}")
            raise e

    def list_preferences(self) -> dict[str, str]:
        select_sql = "SELECT key, value FROM preferences;"
        prefs = {}
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql)
                rows = cursor.fetchall()
                for row in rows:
                    prefs[row[0]] = row[1]
        except Exception as e:
            logger.error(f"Error listing preferences: {e}")
        return prefs

    # --- Projects ---

    def save_project(
        self,
        name: str,
        description: Optional[str] = None,
        tech_stack: Optional[List[str]] = None,
    ) -> None:
        insert_sql = """
        INSERT OR REPLACE INTO projects (name, description, tech_stack, created_at, updated_at)
        VALUES (?, ?, ?, COALESCE((SELECT created_at FROM projects WHERE name = ?), ?), ?);
        """
        now = datetime.now(timezone.utc).isoformat()
        stack_json = json.dumps(tech_stack or [])
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    insert_sql, (name, description, stack_json, name, now, now)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving project '{name}': {e}")
            raise e

    def get_project(self, name: str) -> Optional[dict[str, Any]]:
        select_sql = "SELECT description, tech_stack, created_at, updated_at FROM projects WHERE name = ?;"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (name,))
                row = cursor.fetchone()
                if row:
                    stack = json.loads(row[1])
                    return {
                        "name": name,
                        "description": row[0],
                        "tech_stack": stack,
                        "created_at": row[2],
                        "updated_at": row[3],
                    }
        except Exception as e:
            logger.error(f"Error getting project '{name}': {e}")
        return None

    def list_projects(self) -> List[dict[str, Any]]:
        select_sql = "SELECT name, description, tech_stack, created_at, updated_at FROM projects;"
        projects = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql)
                rows = cursor.fetchall()
                for row in rows:
                    stack = json.loads(row[2])
                    projects.append(
                        {
                            "name": row[0],
                            "description": row[1],
                            "tech_stack": stack,
                            "created_at": row[3],
                            "updated_at": row[4],
                        }
                    )
        except Exception as e:
            logger.error(f"Error listing projects: {e}")
        return projects

    def delete_project(self, name: str) -> None:
        delete_sql = "DELETE FROM projects WHERE name = ?;"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(delete_sql, (name,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error deleting project '{name}': {e}")
            raise e

    # --- Command History ---

    def log_command(self, command: str, executed_by: str, status: str) -> None:
        insert_sql = """
        INSERT INTO command_history (id, command, executed_by, status, timestamp)
        VALUES (?, ?, ?, ?, ?);
        """
        cmd_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(insert_sql, (cmd_id, command, executed_by, status, now))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging command: {e}")

    def get_command_history(self, limit: int = 50) -> List[dict[str, Any]]:
        select_sql = """
        SELECT command, executed_by, status, timestamp
        FROM command_history
        ORDER BY timestamp DESC
        LIMIT ?;
        """
        history = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (limit,))
                rows = cursor.fetchall()
                for row in rows:
                    history.append(
                        {
                            "command": row[0],
                            "executed_by": row[1],
                            "status": row[2],
                            "timestamp": row[3],
                        }
                    )
        except Exception as e:
            logger.error(f"Error getting command history: {e}")
        return history

    # --- Semantic Vector Memory ---

    def _pack_embedding(self, emb: List[float]) -> bytes:
        return struct.pack(f"{len(emb)}f", *emb)

    def _unpack_embedding(self, emb_bytes: bytes) -> List[float]:
        num_floats = len(emb_bytes) // 4
        return list(struct.unpack(f"{num_floats}f", emb_bytes))

    def save_vector_memory(
        self,
        text: str,
        embedding: List[float],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        insert_sql = """
        INSERT INTO vector_memories (id, text, embedding, metadata, created_at)
        VALUES (?, ?, ?, ?, ?);
        """
        mem_id = str(uuid.uuid4())
        packed_emb = self._pack_embedding(embedding)
        meta_json = json.dumps(metadata or {})
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(insert_sql, (mem_id, text, packed_emb, meta_json, now))
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving vector memory: {e}")
            raise e

    def search_vector_memory(
        self, embedding: List[float], limit: int = 5
    ) -> List[dict[str, Any]]:
        """Computes cosine similarity between the query embedding and all records in SQLite."""
        select_sql = (
            "SELECT text, embedding, metadata, created_at FROM vector_memories;"
        )
        results = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql)
                rows = cursor.fetchall()

                for row in rows:
                    text, packed_emb, meta_json, created_at = row
                    stored_emb = self._unpack_embedding(packed_emb)
                    similarity = self._cosine_similarity(embedding, stored_emb)
                    results.append(
                        {
                            "text": text,
                            "metadata": json.loads(meta_json),
                            "created_at": created_at,
                            "score": similarity,
                        }
                    )
        except Exception as e:
            logger.error(f"Error searching vector memory: {e}")
            return []

        # Sort by similarity score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Computes the cosine similarity of two float vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    def _get_mock_embedding(self, text: str) -> List[float]:
        """Generates reproducible, deterministic pseudorandom float vectors of 768 dimensions."""
        h = hashlib.md5(text.encode("utf-8")).hexdigest()
        seed = int(h, 16)
        rng = random.Random(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(768)]

    def get_embedding(self, text: str) -> List[float]:
        """Calculates embeddings via Gemini models or falls back to local mock hash embeddings."""
        if (
            not settings.GEMINI_API_KEY
            or settings.GEMINI_API_KEY == "your_gemini_api_key_here"
        ):
            return self._get_mock_embedding(text)
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]
            response = genai.embed_content(  # type: ignore[attr-defined]
                model="models/text-embedding-004", content=text
            )
            emb = response.get("embedding", [])
            if emb:
                return [float(x) for x in emb]
        except Exception as e:
            logger.warning(
                f"Gemini embedding API call failed: {e}. Falling back to mock embedding."
            )
        return self._get_mock_embedding(text)
