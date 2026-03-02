# automation-platform/src/automation/config/logging.py

"""
Logging setup for Email Automation Platform
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from automation.config.settings import settings


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Configure application logging

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Log file path (if None, console only)
        max_bytes: Maximum log file size
        backup_count: Number of archived log files

    Returns:
        Configured logger
    """

    # Create main logger
    logger = logging.getLogger("automation")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Logging format
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(console_handler)

    # File handler (if log file path is provided)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        logger.addHandler(file_handler)

    # Configure logging for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)

    logger.info(f"Logging setup completed. Level: {log_level}, File: {log_file}")

    return logger


def get_logger(name: str = "automation") -> logging.Logger:
    """Get logger by name"""
    return logging.getLogger(name)


# Configure logging at module import
log_file = Path(settings.log_dir) / "automation.log" if not settings.debug else None
setup_logging(log_level="DEBUG" if settings.debug else "INFO", log_file=log_file)
