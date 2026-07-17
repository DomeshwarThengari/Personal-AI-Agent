from pathlib import Path
from src.infrastructure.database.sqlite_memory import SQLiteMemoryService


def test_sqlite_memory_preferences(tmp_path: Path) -> None:
    db_file = tmp_path / "test_memory.db"
    service = SQLiteMemoryService(db_path=str(db_file))

    # Test initial empty state
    assert service.get_preference("theme") is None
    assert service.list_preferences() == {}

    # Test set preference
    service.set_preference("theme", "dark")
    assert service.get_preference("theme") == "dark"

    # Test update preference
    service.set_preference("theme", "light")
    assert service.get_preference("theme") == "light"

    # Test list preferences
    service.set_preference("font_size", "14")
    prefs = service.list_preferences()
    assert prefs == {"theme": "light", "font_size": "14"}

    # Test delete preference
    service.delete_preference("theme")
    assert service.get_preference("theme") is None
    assert service.list_preferences() == {"font_size": "14"}


def test_sqlite_memory_projects(tmp_path: Path) -> None:
    db_file = tmp_path / "test_memory.db"
    service = SQLiteMemoryService(db_path=str(db_file))

    # Test initial empty state
    assert service.get_project("antigravity") is None
    assert service.list_projects() == []

    # Test save project
    service.save_project(
        name="antigravity",
        description="A powerful coding agent",
        tech_stack=["python", "langgraph"],
    )

    project = service.get_project("antigravity")
    assert project is not None
    assert project["name"] == "antigravity"
    assert project["description"] == "A powerful coding agent"
    assert project["tech_stack"] == ["python", "langgraph"]

    # Test list projects
    service.save_project(
        name="web_ui", description="Web frontend", tech_stack=["nextjs"]
    )
    projects = service.list_projects()
    assert len(projects) == 2
    names = [p["name"] for p in projects]
    assert "antigravity" in names
    assert "web_ui" in names

    # Test delete project
    service.delete_project("web_ui")
    assert service.get_project("web_ui") is None
    assert len(service.list_projects()) == 1


def test_sqlite_memory_command_history(tmp_path: Path) -> None:
    db_file = tmp_path / "test_memory.db"
    service = SQLiteMemoryService(db_path=str(db_file))

    # Test initial empty state
    assert service.get_command_history() == []

    # Log commands
    service.log_command("git status", "user", "success")
    service.log_command("pytest", "assistant", "success")

    history = service.get_command_history()
    assert len(history) == 2
    assert history[0]["command"] == "pytest"  # Sorted by timestamp descending
    assert history[0]["executed_by"] == "assistant"
    assert history[0]["status"] == "success"

    assert history[1]["command"] == "git status"
    assert history[1]["executed_by"] == "user"
    assert history[1]["status"] == "success"


def test_sqlite_memory_vector_search(tmp_path: Path) -> None:
    db_file = tmp_path / "test_memory.db"
    service = SQLiteMemoryService(db_path=str(db_file))

    # Test cosine similarity
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]  # Identical
    vec_c = [0.0, 1.0, 0.0]  # Orthogonal
    vec_d = [-1.0, 0.0, 0.0]  # Opposite

    assert abs(service._cosine_similarity(vec_a, vec_b) - 1.0) < 1e-6
    assert abs(service._cosine_similarity(vec_a, vec_c) - 0.0) < 1e-6
    assert abs(service._cosine_similarity(vec_a, vec_d) - (-1.0)) < 1e-6

    # Test mock embedding generation
    emb1 = service.get_embedding("user likes python coding")
    emb2 = service.get_embedding("user prefers coffee over tea")
    assert len(emb1) == 768
    assert len(emb2) == 768

    # Save to vector memory
    service.save_vector_memory(
        "user prefers dark mode", [1.0, 1.0, 0.0], {"category": "ui"}
    )
    service.save_vector_memory(
        "user prefers python", [0.0, 0.0, 1.0], {"category": "coding"}
    )

    # Search with a query vector close to [1.0, 1.0, 0.0] (dark mode)
    results = service.search_vector_memory([1.0, 0.9, 0.0], limit=2)
    assert len(results) == 2
    assert results[0]["text"] == "user prefers dark mode"
    assert results[0]["metadata"]["category"] == "ui"
    assert results[0]["score"] > 0.9
