"""Retry utilities with exponential backoff for API calls.

This module provides decorators and utilities for implementing retry logic
with exponential backoff for handling transient failures in API calls.
"""

import functools
import logging
import random
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        backoff_factor: Factor to multiply delay by after each retry.
        jitter: Whether to add random jitter to delay.
        exceptions: Tuple of exception types to catch and retry.

    Returns:
        Decorated function with retry logic.

    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def fetch_data():
            return api.get_data()
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    # Calculate delay with optional jitter
                    actual_delay = delay
                    if jitter:
                        actual_delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {actual_delay:.2f} seconds..."
                    )

                    time.sleep(actual_delay)

                    # Exponential backoff with cap
                    delay = min(delay * backoff_factor, max_delay)

            # Should never reach here
            raise RuntimeError("Unexpected end of retry loop")

        return wrapper

    return decorator


def retry_api_call(
    max_retries: int = 3,
    initial_delay: float = 0.6,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Specialized retry decorator for NBA API calls.

    Uses shorter initial delay suitable for rate-limited APIs.

    Args:
        max_retries: Maximum number of retry attempts (default: 3).
        initial_delay: Initial delay in seconds (default: 0.6).
        max_delay: Maximum delay in seconds (default: 30.0).
        backoff_factor: Backoff multiplier (default: 2.0).

    Returns:
        Decorated function with API-specific retry logic.
    """
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_factor=backoff_factor,
        jitter=True,
        exceptions=(Exception,),
    )
