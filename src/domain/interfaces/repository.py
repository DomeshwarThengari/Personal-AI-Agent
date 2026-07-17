from abc import ABC, abstractmethod
from typing import List
from src.domain.entities import Message


class AbstractChatRepository(ABC):
    """Port interface defining conversation persistence operations.

    Ensures application use cases can load and save history without referencing SQLite.
    """

    @abstractmethod
    def save_message(self, session_id: str, message: Message) -> None:
        """Saves a single Message associated with a specific session ID.

        Args:
            session_id: Unique identifier for the conversation session.
            message: The Message domain entity to save.
        """
        pass

    @abstractmethod
    def get_session_messages(self, session_id: str) -> List[Message]:
        """Retrieves all Messages in chronological order for a specific session ID.

        Args:
            session_id: Unique identifier for the conversation session.

        Returns:
            A list of Message entities.
        """
        pass

    @abstractmethod
    def clear_session(self, session_id: str) -> None:
        """Deletes all conversation history associated with a specific session ID.

        Args:
            session_id: Unique identifier for the conversation session.
        """
        pass
