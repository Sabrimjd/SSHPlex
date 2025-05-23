"""SSHplex logging configuration using loguru."""

import os
from pathlib import Path
from loguru import logger


def setup_logging(log_level: str = "INFO", log_file: str = "logs/sshplex.log") -> None:
    """Set up logging for SSHplex with file rotation.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove default logger
    logger.remove()

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


def get_logger():
    """Get the configured logger instance."""
    return logger
