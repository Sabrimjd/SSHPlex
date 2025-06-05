"""SSHplex logging configuration using loguru."""

import os
from pathlib import Path
from typing import Any
from loguru import logger


def setup_logging(log_level: str = "INFO", log_file: str = "logs/sshplex.log", enabled: bool = True) -> None:
    """Set up logging for SSHplex with file rotation.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
        enabled: Whether logging is enabled (if False, only console errors will be shown)
    """
    # Remove default logger
    logger.remove()

    if not enabled:
        # When logging is disabled, only show ERROR and CRITICAL messages to console
        logger.add(
            sink=lambda msg: print(msg, end=""),
            level="ERROR",
            format="<red>ERROR</red> | <cyan>SSHplex</cyan> | {message}"
        )
        return

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Add console logging
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>SSHplex</cyan> | {message}"
    )

    # Add file logging with rotation
    logger.add(
        log_file,
        rotation="10 MB",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{line} | SSHplex | {message}"
    )

    logger.info(f"SSHplex logging initialized - Level: {log_level}, File: {log_file}")


def get_logger() -> Any:
    """Get the configured logger instance."""
    return logger
