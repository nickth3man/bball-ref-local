"""Shared logging configuration for ETL scripts and ingestion pipeline.

This module provides standardized logging setup for all ETL and ingestion scripts
to ensure consistent log formatting across the application.
"""

import io
import logging
import sys
from pathlib import Path
from typing import Any, Final

# Default logging format
DEFAULT_LOG_FORMAT: Final[str] = "%(asctime)s - %(levelname)s - %(message)s"
VERBOSE_LOG_FORMAT: Final[str] = (
    "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)-30s | %(filename)s:%(lineno)d | %(message)s"
)
DEFAULT_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
VERBOSE_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_LEVEL: Final[int] = logging.INFO

# Logger cache to avoid duplicate configuration
_LOGGER_CACHE: Final[dict[str, logging.Logger]] = {}


class ImmediateFlushStreamHandler(logging.StreamHandler):
    """Stream handler that flushes immediately on every log record.

    This ensures real-time output visibility for verbose debugging.
    Supports UTF-8 encoding for international characters.
    """

    def __init__(self, stream=None):
        """Initialize with UTF-8 encoding support."""
        if stream is None:
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


def setup_etl_logging(
    name: str,
    level: int = DEFAULT_LOG_LEVEL,
    format_str: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
    log_file: Path | None = None,
    verbose: bool = False,
) -> logging.Logger:
    """Set up standardized logging for ETL scripts.

    Args:
        name: Logger name (typically __name__).
        level: Logging level (default: INFO).
        format_str: Log message format string.
        date_format: Date format string.
        log_file: Optional file path to log to file as well as console.
        verbose: If True, use detailed format with file/line info and immediate flush.

    Returns:
        Configured logger instance.

    Example:
        >>> logger = setup_etl_logging(__name__)
        >>> logger.info("Starting ETL process...")
    """
    # Return cached logger if already configured
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()
    logger.propagate = False

    # Use verbose format if requested
    if verbose:
        fmt = VERBOSE_LOG_FORMAT
        datefmt = VERBOSE_DATE_FORMAT
        handler_class = ImmediateFlushStreamHandler
        stream = sys.stdout
    else:
        fmt = format_str
        datefmt = date_format
        handler_class = logging.StreamHandler
        stream = sys.stdout

    # Create formatter
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # Console handler
    console_handler = handler_class(stream)
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

    # Cache the configured logger
    _LOGGER_CACHE[name] = logger
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger (cached).

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.
    """
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]
    return setup_etl_logging(name)


def set_verbose_logging(logger_name: str | None = None) -> None:
    """Enable verbose (DEBUG) logging.

    Args:
        logger_name: Specific logger name to set to DEBUG, or None for all loggers.
    """
    if logger_name:
        logging.getLogger(logger_name).setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.DEBUG)
        # Also update all cached loggers
        for logger in _LOGGER_CACHE.values():
            logger.setLevel(logging.DEBUG)


def enable_verbose_logging() -> None:
    """Enable verbose logging for all cached loggers.

    This sets all cached loggers to DEBUG level with immediate flush
    and detailed formatting including file names and line numbers.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Reconfigure all cached loggers with verbose settings
    for name, logger in _LOGGER_CACHE.items():
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        # Use verbose format with immediate flush
        formatter = logging.Formatter(VERBOSE_LOG_FORMAT, datefmt=VERBOSE_DATE_FORMAT)
        handler = ImmediateFlushStreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

    root_logger.info("=" * 80)
    root_logger.info("VERBOSE LOGGING ENABLED")
    root_logger.info("All log output will show immediately with detailed context")
    root_logger.info("=" * 80)


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
