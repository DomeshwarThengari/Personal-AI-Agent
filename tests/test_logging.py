import logging
from src.config.settings import PROJECT_ROOT
from src.utils.logging import get_logger, setup_logging


def test_logging_setup() -> None:
    """Verifies that the logging utility configures standard and rotating file handlers correctly."""
    setup_logging()

    # Retrieve the root logger
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) >= 2

    # Verify handlers
    has_stream = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
    has_file = any(
        isinstance(h, logging.FileHandler)
        or isinstance(h, logging.handlers.BaseRotatingHandler)
        for h in root_logger.handlers
    )

    assert has_stream is True
    assert has_file is True


def test_get_logger() -> None:
    """Verifies that the get_logger utility returns a valid Logger instance."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"


def test_log_file_creation() -> None:
    """Verifies that running logging setup actually creates the log file in logs/ directory."""
    setup_logging()
    log_file = PROJECT_ROOT / "logs" / "assistant.log"
    assert log_file.exists() is True
    assert log_file.is_file() is True
