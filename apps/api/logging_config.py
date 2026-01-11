"""Logging configuration for API server."""

from pathlib import Path

from apps.logger import logger


def setup_logging():
    """
    Configure logging for the API server.

    Sets up access logs in logs/access.log and error logs in logs/error.log
    """
    # Get project root
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    logs_dir = project_root / "logs"

    # Ensure logs directory exists
    logs_dir.mkdir(exist_ok=True)

    # Add access log handler (for INFO and SUCCESS messages)
    access_log_path = logs_dir / "access.log"
    logger.add(
        str(access_log_path),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="30 days",  # Keep logs for 30 days
        compression="zip",  # Compress rotated logs
        enqueue=True,  # Thread-safe logging
    )

    # Add error log handler (for WARNING, ERROR, and CRITICAL messages)
    error_log_path = logs_dir / "error.log"
    logger.add(
        str(error_log_path),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
        level="WARNING",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
    )

    logger.info(
        "Logging configured - Access logs: {}, Error logs: {}",
        str(access_log_path),
        str(error_log_path),
    )
