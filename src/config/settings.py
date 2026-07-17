from pathlib import Path
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings class utilizing Pydantic Settings for validation.

    Loads configurations from environment variables and an optional .env file.
    """

    ENVIRONMENT: Literal["development", "testing", "production"] = Field(
        default="development"
    )
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )

    GEMINI_API_KEY: str = Field(default="")

    SQLITE_DB_PATH: str = Field(default="data/assistant.db")
    CHROMA_DB_PATH: str = Field(default="data/chroma")

    PLAYWRIGHT_HEADLESS: bool = Field(default=True)
    PLAYWRIGHT_TIMEOUT: int = Field(default=30000)

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @field_validator("SQLITE_DB_PATH", "CHROMA_DB_PATH", mode="after")
    @classmethod
    def resolve_paths(cls, value: str) -> str:
        """Resolves relative paths to be absolute, relative to the project root."""
        path = Path(value)
        if not path.is_absolute():
            return str((PROJECT_ROOT / path).resolve())
        return str(path.resolve())

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT == "testing"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


# Instantiate as a singleton configuration loader
settings = Settings()
