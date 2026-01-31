"""Logging configuration for the data ingestion pipeline.

This module provides comprehensive logging with immediate flush capabilities
for verbose debugging and detailed progress tracking.
"""

import logging
import sys
from typing import Final

from scripts.ingestion.config import LOG_DATE_FORMAT, LOG_FORMAT, LOG_LEVEL

_LOGGER_CACHE: Final[dict[str, logging.Logger]] = {}
_ROOT_LOGGER_NAME: Final[str] = "ingestion"


class ImmediateFlushStreamHandler(logging.StreamHandler):
    """Stream handler that flushes immediately on every log record.

    This ensures real-time output visibility for verbose debugging.
    Supports UTF-8 encoding for international characters.
    """

    def __init__(self, stream=None):
        # Use stdout with UTF-8 encoding support
        if stream is None:
            import io

            stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        super().__init__(stream)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a record and flush immediately."""
        try:
            super().emit(record)
            self.flush()
        except UnicodeEncodeError:
            # Fallback: encode with replacement for problematic characters
            msg = self.format(record)
            safe_msg = msg.encode("utf-8", errors="replace").decode("utf-8")
            self.stream.write(safe_msg + self.terminator)
            self.flush()

    def flush(self) -> None:
        """Flush the stream."""
        self.stream.flush()


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger for ingestion modules."""
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    full_name = f"{_ROOT_LOGGER_NAME}.{name}" if not name.startswith(_ROOT_LOGGER_NAME) else name
    logger = logging.getLogger(full_name)

    if not logger.handlers:
        _configure_logger(logger)

    _LOGGER_CACHE[name] = logger
    return logger


def configure_root_logger(level: str | int | None = None, verbose: bool = False) -> logging.Logger:
    """Configure the root ingestion logger.

    Args:
        level: Log level (overrides verbose setting if provided)
        verbose: If True, enable DEBUG level with detailed formatting

    Returns:
        Configured root logger
    """
    root_logger = logging.getLogger(_ROOT_LOGGER_NAME)

    if level is not None:
        log_level = level
    elif verbose:
        log_level = "DEBUG"
    else:
        log_level = LOG_LEVEL

    _configure_logger(root_logger, log_level, verbose)
    return root_logger


def _configure_logger(
    logger: logging.Logger, level: str | int | None = None, verbose: bool = False
) -> None:
    """Configure a logger with standard settings.

    Args:
        logger: Logger to configure
        level: Log level
        verbose: If True, use detailed format with file/line info and immediate flush
    """
    log_level = level if level is not None else LOG_LEVEL
    logger.setLevel(log_level)
    logger.propagate = False

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Use verbose format if requested
    if verbose:
        # Detailed format with module, line number, and timestamp with milliseconds
        fmt = (
            "%(asctime)s.%(msecs)03d | %(levelname)-8s | "
            "%(name)-30s | %(filename)s:%(lineno)d | %(message)s"
        )
        datefmt = "%Y-%m-%d %H:%M:%S"
        # Force stdout for verbose mode to ensure immediate visibility
        stream = sys.stdout
        handler_class = ImmediateFlushStreamHandler
    else:
        fmt = LOG_FORMAT
        datefmt = LOG_DATE_FORMAT
        stream = sys.stdout
        handler_class = logging.StreamHandler

    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # Add console handler
    console_handler = handler_class(stream)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    # Log configuration complete
    if verbose:
        logger.debug(f"Logger configured with level={log_level}, verbose={verbose}")


def enable_verbose_logging() -> None:
    """Enable verbose logging for all ingestion loggers.

    This sets the root logger to DEBUG level with immediate flush
    and detailed formatting including file names and line numbers.
    """
    configure_root_logger(level="DEBUG", verbose=True)

    # Also configure all cached loggers
    for _name, logger in _LOGGER_CACHE.items():
        _configure_logger(logger, level="DEBUG", verbose=True)

    root_logger = logging.getLogger(_ROOT_LOGGER_NAME)
    root_logger.info("=" * 80)
    root_logger.info("VERBOSE LOGGING ENABLED")
    root_logger.info("All log output will show immediately with detailed context")
    root_logger.info("=" * 80)


def log_stage(logger: logging.Logger, stage_name: str, action: str = "started") -> None:
    """Log a pipeline stage with clear visual separator.

    Args:
        logger: Logger instance
        stage_name: Name of the stage (e.g., "Phase 1: Reference Data")
        action: Action being performed (e.g., "started", "completed", "failed")
    """
    separator = "=" * 80
    if action == "started":
        logger.info(separator)
        logger.info(f"STAGE: {stage_name}")
        logger.info(separator)
    elif action == "completed":
        logger.info(f"[SUCCESS] {stage_name} completed")
        logger.info(separator)
    elif action == "failed":
        logger.error(f"[FAILED] {stage_name} failed")
        logger.info(separator)
    else:
        logger.info(f"[{action.upper()}] {stage_name}")


def log_step(
    logger: logging.Logger,
    step_number: int,
    total_steps: int,
    description: str,
    details: dict | None = None,
) -> None:
    """Log a detailed step within a stage.

    Args:
        logger: Logger instance
        step_number: Current step number
        total_steps: Total number of steps
        description: Description of what this step does
        details: Optional dictionary of additional details to log
    """
    progress = f"[{step_number}/{total_steps}]"
    logger.info(f"  {progress} {description}")

    if details and logger.isEnabledFor(logging.DEBUG):
        for key, value in details.items():
            logger.debug(f"    - {key}: {value}")
