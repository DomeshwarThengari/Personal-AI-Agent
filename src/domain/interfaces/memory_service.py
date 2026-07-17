from abc import ABC, abstractmethod
from typing import Any, List, Optional


class AbstractMemoryService(ABC):
    """Port interface defining memory management capabilities for the agent.

    Covers user preferences, project tracking, command history, and future-ready
    semantic vector memory search.
    """

    # --- User Preferences ---
    @abstractmethod
    def get_preference(self, key: str) -> Optional[str]:
        """Retrieves a specific preference value by key."""
        pass

    @abstractmethod
    def set_preference(self, key: str, value: str) -> None:
        """Sets or replaces a preference key-value pair."""
        pass

    @abstractmethod
    def delete_preference(self, key: str) -> None:
        """Removes a preference key."""
        pass

    @abstractmethod
    def list_preferences(self) -> dict[str, str]:
        """Lists all user preferences currently stored."""
        pass

    # --- Projects ---
    @abstractmethod
    def save_project(
        self,
        name: str,
        description: Optional[str] = None,
        tech_stack: Optional[List[str]] = None,
    ) -> None:
        """Stores or updates a user project representation."""
        pass

    @abstractmethod
    def get_project(self, name: str) -> Optional[dict[str, Any]]:
        """Retrieves a project definition by its name."""
        pass

    @abstractmethod
    def list_projects(self) -> List[dict[str, Any]]:
        """Retrieves all stored user projects."""
        pass

    @abstractmethod
    def delete_project(self, name: str) -> None:
        """Deletes a project record from memory."""
        pass

    # --- Command History ---
    @abstractmethod
    def log_command(self, command: str, executed_by: str, status: str) -> None:
        """Logs a command execution log entry to the history log."""
        pass

    @abstractmethod
    def get_command_history(self, limit: int = 50) -> List[dict[str, Any]]:
        """Retrieves previously executed CLI/browser commands."""
        pass

    # --- Semantic Vector Memory ---
    @abstractmethod
    def save_vector_memory(
        self,
        text: str,
        embedding: List[float],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Stores a textual memory chunk alongside its high-dimensional float embedding."""
        pass

    @abstractmethod
    def search_vector_memory(
        self, embedding: List[float], limit: int = 5
    ) -> List[dict[str, Any]]:
        """Finds semantically similar memory records using cosine similarity scoring."""
        pass

    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Calculates embeddings for the given text query."""
        pass
