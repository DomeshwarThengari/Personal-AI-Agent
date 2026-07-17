import sys
from pathlib import Path
from src.config.settings import PROJECT_ROOT, settings
from src.utils.logging import get_logger, setup_logging

# Initialize logging before printing or doing anything else
setup_logging()
logger = get_logger("setup_health_check")


def check_directories() -> bool:
    """Verifies that vital application directories exist or creates them."""
    logger.info("Verifying application directories...")
    success = True

    # Directories to verify/create
    dirs_to_verify = [
        ("Logs Directory", PROJECT_ROOT / "logs"),
        ("Database Directory", Path(settings.SQLITE_DB_PATH).parent),
        ("ChromaDB Directory", Path(settings.CHROMA_DB_PATH)),
    ]

    for label, path in dirs_to_verify:
        try:
            if not path.exists():
                logger.info(f"Creating missing {label}: {path}")
                path.mkdir(parents=True, exist_ok=True)
            else:
                logger.debug(f"{label} verified at: {path}")
        except Exception as e:
            logger.error(f"Failed to verify/create {label} at {path}: {e}")
            success = False

    return success


def check_configuration() -> bool:
    """Validates the correctness of settings loaded from the environment."""
    logger.info("Validating configurations...")
    is_valid = True

    # Check Gemini API Key
    if not settings.GEMINI_API_KEY:
        logger.warning(
            "GEMINI_API_KEY environment variable is not defined or is empty."
        )
        is_valid = False
    elif settings.GEMINI_API_KEY == "your_gemini_api_key_here":
        logger.warning(
            "GEMINI_API_KEY is still set to the default placeholder in .env."
        )
        is_valid = False
    else:
        logger.info("GEMINI_API_KEY format check passed.")

    # Check other environment variables
    logger.info(f"Environment mode: {settings.ENVIRONMENT}")
    logger.info(f"Log Level config: {settings.LOG_LEVEL}")
    logger.info(f"SQLite Path: {settings.SQLITE_DB_PATH}")
    logger.info(f"ChromaDB Path: {settings.CHROMA_DB_PATH}")

    return is_valid


def run_health_check() -> int:
    """Runs the full health check suite and returns an exit code."""
    logger.info("==============================================")
    logger.info("Starting Personal AI Agent Health Check Suite")
    logger.info("==============================================")

    dir_status = check_directories()
    config_status = check_configuration()

    logger.info("----------------------------------------------")
    if dir_status and config_status:
        logger.info("System status: HEALTHY (All checks passed)")
        logger.info("==============================================")
        return 0
    elif dir_status and not config_status:
        logger.warning("System status: DEGRADED (Check warnings above)")
        logger.info("==============================================")
        return 0  # Still warning/degraded, but executable
    else:
        logger.critical("System status: UNHEALTHY (Critical errors found)")
        logger.info("==============================================")
        return 1


if __name__ == "__main__":
    exit_code = run_health_check()
    sys.exit(exit_code)
