import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from src.config.settings import PROJECT_ROOT, settings

# Ensure logs directory exists relative to project root
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE_PATH = LOGS_DIR / "assistant.log"


class ConsoleColorFormatter(logging.Formatter):
    """Custom formatter to add color and structure to console output in development."""

    # ANSI Color Escape Codes
    GREY = "\x1b[38;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    GREEN = "\x1b[32;20m"
    CYAN = "\x1b[36;20m"
    RESET = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: CYAN
        + "%(asctime)s [%(levelname)s] (%(name)s:%(filename)s:%(lineno)d) - %(message)s"
        + RESET,
        logging.INFO: GREEN
        + "%(asctime)s [%(levelname)s] (%(name)s) - %(message)s"
        + RESET,
        logging.WARNING: YELLOW
        + "%(asctime)s [%(levelname)s] (%(name)s) - %(message)s"
        + RESET,
        logging.ERROR: RED
        + "%(asctime)s [%(levelname)s] (%(name)s:%(filename)s:%(lineno)d) - %(message)s"
        + RESET,
        logging.CRITICAL: BOLD_RED
        + "%(asctime)s [%(levelname)s] (%(name)s:%(filename)s:%(lineno)d) - %(message)s"
        + RESET,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno, self.GREY)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging() -> None:
    """Configures global application logging handlers.

    Sets up a colorized console handler and a daily rotating file handler.
    """
    log_level_num = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_num)

    # Clear existing handlers to prevent duplicate logging
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 1. Console Handler (for readable logs in terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ConsoleColorFormatter())
    console_handler.setLevel(log_level_num)
    root_logger.addHandler(console_handler)

    # 2. Daily Rotating File Handler (for persistent, structured logs)
    file_handler = TimedRotatingFileHandler(
        filename=str(LOG_FILE_PATH),
        when="midnight",
        interval=1,
        backupCount=30,  # Retain logs for 30 days
        encoding="utf-8",
    )
    file_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(process)d:%(threadName)s] (%(name)s:%(filename)s:%(lineno)d) - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level_num)
    root_logger.addHandler(file_handler)

    # Disable propagation/duplicate logs for third party library logs if needed
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance with the specified name."""
    return logging.getLogger(name)
