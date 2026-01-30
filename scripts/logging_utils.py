"""Shared logging configuration for ETL scripts.

This module provides standardized logging setup for all ETL scripts
to ensure consistent log formatting across the application.
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Default logging format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_LEVEL = logging.INFO


def setup_etl_logging(
    name: str,
    level: int = DEFAULT_LOG_LEVEL,
    format_str: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
    log_file: Path | None = None,
) -> logging.Logger:
    """Set up standardized logging for ETL scripts.

    Args:
        name: Logger name (typically __name__).
        level: Logging level (default: INFO).
        format_str: Log message format string.
        date_format: Date format string.
        log_file: Optional file path to log to file as well as console.

    Returns:
        Configured logger instance.

    Example:
        >>> logger = setup_etl_logging(__name__)
        >>> logger.info("Starting ETL process...")
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(format_str, datefmt=date_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def set_verbose_logging(logger_name: str | None = None) -> None:
    """Enable verbose (DEBUG) logging.

    Args:
        logger_name: Specific logger name to set to DEBUG, or None for root logger.
    """
    if logger_name:
        logging.getLogger(logger_name).setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.DEBUG)


class ETLLogger:
    """Context manager for ETL logging with timing and status tracking.

    Example:
        >>> with ETLLogger(logger, "games_etl") as etl_log:
        ...     result = run_etl()
        ...     etl_log.set_result(result)
    """

    def __init__(self, logger: logging.Logger, operation: str, verbose: bool = False):
        """Initialize ETL logger context.

        Args:
            logger: Logger instance to use.
            operation: Name of the ETL operation (e.g., 'games_etl').
            verbose: Whether to enable verbose logging.
        """
        self.logger = logger
        self.operation = operation
        self.verbose = verbose
        self.start_time: float | None = None
        self.result: dict[str, Any] | None = None

    def __enter__(self):
        """Enter context and start timing."""
        import time

        self.start_time = time.time()
        self.logger.info(f"Starting {self.operation}...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and log completion."""
        import time

        duration = time.time() - (self.start_time or 0)

        if exc_type is not None:
            self.logger.error(f"{self.operation} failed after {duration:.2f}s: {exc_val}")
            return False  # Don't suppress the exception

        if self.result:
            extracted = self.result.get("extracted", 0)
            loaded = self.result.get("loaded", 0)
            self.logger.info(
                f"{self.operation} completed in {duration:.2f}s: "
                f"{extracted} extracted, {loaded} loaded"
            )
        else:
            self.logger.info(f"{self.operation} completed in {duration:.2f}s")

        return True

    def set_result(self, result: dict[str, Any]) -> None:
        """Set the ETL result for logging.

        Args:
            result: Dictionary with ETL results (e.g., {'extracted': 100, 'loaded': 100}).
        """
        self.result = result

    def log_progress(self, message: str, level: int = logging.INFO) -> None:
        """Log a progress message.

        Args:
            message: Progress message to log.
            level: Logging level (default: INFO).
        """
        self.logger.log(level, f"[{self.operation}] {message}")
