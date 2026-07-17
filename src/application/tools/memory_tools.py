from typing import Any, Dict
from src.domain.interfaces.tool import AbstractTool
from src.domain.interfaces.memory_service import AbstractMemoryService


class PreferenceSetTool(AbstractTool):
    """Sets a user preference."""

    def __init__(self, memory_service: AbstractMemoryService) -> None:
        self.memory_service = memory_service

    @property
    def name(self) -> str:
        return "memory_set_preference"

    @property
    def description(self) -> str:
        return "Set or replace a user preference or personal detail (e.g. favorite coding languages, name, theme, tone)."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The preference key identifier (e.g. 'user_name', 'theme').",
                },
                "value": {
                    "type": "string",
                    "description": "The value to store for the preference key.",
                },
            },
            "required": ["key", "value"],
        }

    def execute(self, **kwargs: Any) -> str:
        key = kwargs.get("key")
        value = kwargs.get("value")
        if not key or not value:
            return "Error: Both 'key' and 'value' parameters are required."

        self.memory_service.set_preference(key, value)
        return f"Successfully set preference '{key}' to '{value}'."


class PreferenceGetTool(AbstractTool):
    """Retrieves a user preference by key."""

    def __init__(self, memory_service: AbstractMemoryService) -> None:
        self.memory_service = memory_service

    @property
    def name(self) -> str:
        return "memory_get_preference"

    @property
    def description(self) -> str:
        return "Retrieve a stored user preference or personal detail by key."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The preference key to retrieve.",
                }
            },
            "required": ["key"],
        }

    def execute(self, **kwargs: Any) -> str:
        key = kwargs.get("key")
        if not key:
            return "Error: Parameter 'key' is required."

        val = self.memory_service.get_preference(key)
        if val is None:
            return f"Preference '{key}' is not set."
        return f"Preference '{key}': '{val}'"


class ProjectSaveTool(AbstractTool):
    """Stores details about a project."""

    def __init__(self, memory_service: AbstractMemoryService) -> None:
        self.memory_service = memory_service

    @property
    def name(self) -> str:
        return "memory_save_project"

    @property
    def description(self) -> str:
        return "Store details about a project the user is working on, including stack/languages."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the project.",
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what the project does.",
                },
                "tech_stack": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of technologies/languages used (e.g. ['python', 'nextjs']).",
                },
            },
            "required": ["name"],
        }

    def execute(self, **kwargs: Any) -> str:
        name = kwargs.get("name")
        description = kwargs.get("description")
        tech_stack = kwargs.get("tech_stack", [])
        if not name:
            return "Error: Project 'name' is required."

        self.memory_service.save_project(name, description, tech_stack)
        return f"Successfully saved project '{name}' context details."


class CommandHistoryTool(AbstractTool):
    """Retrieves executed commands log."""

    def __init__(self, memory_service: AbstractMemoryService) -> None:
        self.memory_service = memory_service

    @property
    def name(self) -> str:
        return "memory_get_command_history"

    @property
    def description(self) -> str:
        return "Get the log of recently executed shell commands or browser actions."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of history logs to fetch (default: 10).",
                }
            },
            "required": [],
        }

    def execute(self, **kwargs: Any) -> str:
        limit = kwargs.get("limit", 10)
        try:
            limit_val = int(limit)
        except ValueError:
            limit_val = 10

        hist = self.memory_service.get_command_history(limit=limit_val)
        if not hist:
            return "No command execution history has been logged yet."

        res = []
        for idx, entry in enumerate(hist, 1):
            res.append(
                f"{idx}. [{entry['timestamp']}] ({entry['executed_by']}): {entry['command']} -> Status: {entry['status']}"
            )
        return "\n".join(res)


class MemorySaveTool(AbstractTool):
    """Saves a semantic textual memory."""

    def __init__(self, memory_service: AbstractMemoryService) -> None:
        self.memory_service = memory_service

    @property
    def name(self) -> str:
        return "memory_save"

    @property
    def description(self) -> str:
        return "Save a new fact, observation, or memory chunk about the user to the long-term semantic memory."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The fact or observation text to memorize.",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category description (e.g. 'work', 'interests').",
                },
            },
            "required": ["text"],
        }

    def execute(self, **kwargs: Any) -> str:
        text = kwargs.get("text")
        category = kwargs.get("category", "general")
        if not text:
            return "Error: Memory 'text' parameter is required."

        # Fetch embedding using the SQLiteMemoryService helper method
        embedding = self.memory_service.get_embedding(text)

        metadata = {"category": category}
        self.memory_service.save_vector_memory(text, embedding, metadata)
        return f"Successfully saved fact/memory: '{text}' (Category: {category})."


class MemorySearchTool(AbstractTool):
    """Searches long-term memories using semantic vector matching."""

    def __init__(self, memory_service: AbstractMemoryService) -> None:
        self.memory_service = memory_service

    @property
    def name(self) -> str:
        return "memory_search"

    @property
    def description(self) -> str:
        return "Perform a semantic vector search over the user's stored long-term memories to recall facts."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to match memories semantically.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum match items to return (default: 3).",
                },
            },
            "required": ["query"],
        }

    def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query")
        limit = kwargs.get("limit", 3)
        if not query:
            return "Error: Search 'query' parameter is required."

        try:
            limit_val = int(limit)
        except ValueError:
            limit_val = 3

        embedding = self.memory_service.get_embedding(query)
        results = self.memory_service.search_vector_memory(embedding, limit=limit_val)
        if not results:
            return f"No memories found matching query '{query}'."

        res = []
        for idx, item in enumerate(results, 1):
            category = item["metadata"].get("category", "general")
            res.append(
                f"{idx}. Match Score: {item['score']:.4f} | Category: {category}\n   Memory: '{item['text']}'"
            )
        return "\n".join(res)
