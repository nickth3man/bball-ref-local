"""Logging configuration for the data ingestion pipeline (delegated to logging_utils).

This module re-exports logging utilities from scripts.logging_utils for backward compatibility.
New code should use scripts.logging_utils directly.
"""

import logging
from typing import Final

# Re-export all logging utilities from the unified module
from scripts.logging_utils import (
    DEFAULT_DATE_FORMAT,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    ETLLogger,
    ImmediateFlushStreamHandler,
    VERBOSE_DATE_FORMAT,
    VERBOSE_LOG_FORMAT,
    enable_verbose_logging,
    get_logger,
    log_stage,
    log_step,
    set_verbose_logging,
    setup_etl_logging,
)

# Keep root logger name constant for ingestion
_ROOT_LOGGER_NAME: Final[str] = "ingestion"


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
        log_level = DEFAULT_LOG_LEVEL

    # Use unified setup function with verbose mode
    return setup_etl_logging(_ROOT_LOGGER_NAME, level=log_level, verbose=verbose)


# For backward compatibility, maintain LOG_FORMAT, LOG_DATE_FORMAT, LOG_LEVEL
# These are imported from ingestion.config and used by the old code
# The unified logging_utils now handles these internally
