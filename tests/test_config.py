from pathlib import Path
from src.config.settings import Settings


def test_settings_defaults() -> None:
    """Verifies that default configuration values are correctly initialized."""
    settings = Settings()
    assert settings.ENVIRONMENT == "development"
    assert settings.LOG_LEVEL == "INFO"
    assert settings.is_development is True
    assert settings.is_testing is False
    assert settings.is_production is False


def test_path_resolution() -> None:
    """Verifies that relative paths are automatically resolved to absolute paths."""
    settings = Settings()

    # The paths must be resolved to absolute paths within the project directory
    assert Path(settings.SQLITE_DB_PATH).is_absolute()
    assert Path(settings.CHROMA_DB_PATH).is_absolute()

    assert settings.SQLITE_DB_PATH.endswith("data/assistant.db")
    assert settings.CHROMA_DB_PATH.endswith("data/chroma")
