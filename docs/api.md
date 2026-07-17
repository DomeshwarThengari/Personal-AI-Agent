# API Documentation

This document describes the primary python classes, module interfaces, and service methods within the JOJO Assistant repository.

---

## 🧠 Application Orchestration

### `MultiAgentWorkflowRunner`
Located in `src/application/multi_agent/workflow.py`. Integrates with the Gemini LLM service to dynamically route user text inputs to correct target agent states.

```python
class MultiAgentWorkflowRunner:
    def __init__(self, llm_service: AbstractLLMService, action_engine: ActionEngine, tools: List[BaseTool]) -> None:
        """Initializes the multi-agent graph with all registerable agent capabilities."""
        ...

    def run(self, session_id: str, history: List[Message], user_input: str, system_instruction: str) -> WorkflowResult:
        """Executes the orchestrator routing state machine and returns final answer."""
        ...
```

---

## 🛠️ Action Planning Engine

### `ActionEngine`
Located in `src/application/action_engine/engine.py`. Evaluates plans, schedules task sequences, and performs tool validation check routines.

```python
class ActionEngine:
    def __init__(self, registry: ToolRegistry, memory_service: AbstractMemoryService, security_manager: SecurityManager) -> None:
        """Initializes the stateful tool runtime scheduler."""
        ...

    def execute_plan(self, plan: list[dict[str, Any]]) -> dict[str, Any]:
        """Runs planned tasks sequentially with error-recovery handling."""
        ...
```

---

## 🔒 Security & Guardrail Managers

### `SecurityManager`
Located in `src/application/services/security_manager.py`. Manages user authorization roles, evaluates execution risks, and persists audit logs.

```python
class SecurityManager:
    def __init__(self, db_path: str = settings.SQLITE_DB_PATH) -> None:
        """Initializes security policies and SQLite audit log tables."""
        ...

    def verify_execution(self, tool_name: str, args: dict[str, Any]) -> tuple[bool, str]:
        """Intercepts execution requests. Returns confirmation requirement or rejection states."""
        ...

    def log_audit(self, tool_name: str, risk_level: str, status: str, details: str) -> None:
        """Saves execution audit entry into the logs table."""
        ...

    def get_audit_logs(self, limit: int = 50) -> List[dict[str, Any]]:
        """Retrieves descended audit logs."""
        ...
```

---

## 💾 Memory & Storage Services

### `SQLiteMemoryService`
Located in `src/infrastructure/database/sqlite_memory.py`. Extends `AbstractMemoryService` providing metadata storage, command tracking, and vector indexing.

```python
class SQLiteMemoryService(AbstractMemoryService):
    def get_preference(self, key: str) -> Optional[str]:
        """Fetches stored string setting values."""
        ...

    def set_preference(self, key: str, value: str) -> None:
        """Inserts or overwrites preference key values."""
        ...

    def save_vector_memory(self, text: str, embedding: List[float], metadata: Optional[dict[str, Any]] = None) -> None:
        """Stores text along with binary-packed coordinate arrays."""
        ...

    def search_vector_memory(self, embedding: List[float], limit: int = 5) -> List[dict[str, Any]]:
        """Calculates cosine similarity values and returns top matches."""
        ...
```

---

## 🎙️ Speech & Voice Utilities

### `VoiceService`
Located in `src/infrastructure/voice/voice_service.py`. Connects local hardware microphones and speakers for hands-free operations.

```python
class VoiceService:
    def is_audio_available(self) -> bool:
        """Returns True if input hardware microphone driver can be initialized."""
        ...

    def record_command(self, duration: float = 4.0) -> Optional[str]:
        """Captures microphone input and translates audio using Speech-to-Text APIs."""
        ...

    def speak_text(self, text: str) -> None:
        """Renders string text output into vocal voice responses."""
        ...
```
