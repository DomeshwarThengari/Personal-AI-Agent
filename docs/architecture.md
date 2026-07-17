# System Architecture Manual

This document provides a comprehensive overview of the design patterns, databases schemas, agent coordination models, and security workflows governing the JOJO Personal AI Assistant.

---

## 🏛️ Architecture Principles

JOJO is built around **Clean Architecture** and **Domain-Driven Design (DDD)** principles:
1. **Separation of Concerns**: Presentation (UI), Business Use Cases (Agents), and External Resources (DB/LLM) are isolated.
2. **Dependency Inversion**: Outer layers depend on abstract interfaces declared in inner layers.
3. **Immutability**: Crucial data elements like `Message` and `AuditLog` are domain entities modeled using immutable dataclasses.

---

## 🗄️ Database & Memory Schema

JOJO uses an SQLite database (`data/assistant.db`) split into two service modules:

### 1. Conversation Repository (`SQLiteChatRepository`)
Handles chat message persistence.
- **Table**: `messages`
  ```sql
  CREATE TABLE IF NOT EXISTS messages (
      id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL,
      role TEXT NOT NULL,       -- 'user', 'assistant', 'system'
      content TEXT NOT NULL,
      timestamp TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_messages_session_time ON messages(session_id, timestamp);
  ```

### 2. Context & Vector Memory (`SQLiteMemoryService`)
Maintains user configuration settings, command history logs, and text embeddings.
- **Table**: `preferences`
  ```sql
  CREATE TABLE IF NOT EXISTS preferences (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TEXT NOT NULL
  );
  ```
- **Table**: `projects`
  ```sql
  CREATE TABLE IF NOT EXISTS projects (
      name TEXT PRIMARY KEY,
      description TEXT,
      tech_stack TEXT, -- JSON array of strings
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
  );
  ```
- **Table**: `command_history`
  ```sql
  CREATE TABLE IF NOT EXISTS command_history (
      id TEXT PRIMARY KEY,
      command TEXT NOT NULL,
      executed_by TEXT NOT NULL,
      status TEXT NOT NULL,
      timestamp TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_command_history_timestamp ON command_history(timestamp DESC);
  ```
- **Table**: `vector_memories`
  ```sql
  CREATE TABLE IF NOT EXISTS vector_memories (
      id TEXT PRIMARY KEY,
      text TEXT NOT NULL,
      embedding BLOB NOT NULL, -- Binary packed Float array (768 dimensions)
      metadata TEXT NOT NULL,  -- JSON dictionary
      created_at TEXT NOT NULL
  );
  ```

---

## 🤖 Multi-Agent Workflow State Machine

The multi-agent coordinator routes user requests through a state machine managed via a Graph-based orchestrator:

```
[User Message] 
       │
       ▼
┌──────────────┐
│ Brain Agent  │◄───────────────────┐
└──────┬───────┘                    │
       │                            │
       ├─► (Wants Web Action) ──► Browser Agent ─► [Playwright]
       │                                                    │
       ├─► (Needs Code/Cmds) ──► DevOps Agent ──► [System Exec]
       │                                                    │
       ├─► (Needs Plan Steps) ─► Planner Agent ─► [Action Engine]
       │                                                    │
       └─► (Needs Memory) ─────► Memory Agent ──► [SQLite DB]
                                                            │
                                                            │
                            [Response / Next Action State] ──┘
```

---

## 🔒 Security Gatekeeper & Permission Engine

All tool executions undergo rigorous security intercept inspections governed by the `SecurityManager`:

```
          [Tool Run Triggered]
                   │
                   ▼
       ┌───────────────────────┐
       │   Is Tool Mutation?   │──(No)──► [Execute Tool]
       └───────────┬───────────┘
                   │
                 (Yes)
                   ▼
       ┌───────────────────────┐
       │    Is Safe Mode On?   │──(No)──► [Execute Tool]
       └───────────┬───────────┘
                   │
                 (Yes)
                   ▼
       ┌───────────────────────┐
       │ Is User Role == Admin?│──(Yes)─► [Prompt Confirmation] ─(Approved)─► [Execute]
       └───────────┬───────────┘
                   │
                  (No)
                   ▼
           [BLOCK EXECUTION]
      (Logs status="DENIED" to Audit DB)
```

### Authorization Levels (RBAC)
1. **Viewer**: Read-only queries (e.g. read CPU status, get preferences, search memories).
2. **Operator**: Runs mild operations (e.g. create folder, Git commit, run tests).
3. **Admin**: Runs highly sensitive and destructive commands (e.g. file deletion, Terraform apply, AWS resource terminations).
