"""Shared utility functions for ETL scripts.

This module contains common helper functions used across multiple ETL scripts
to avoid code duplication.
"""

import re
from datetime import date

# NBA founded in 1946, so valid seasons start from 1946-47
MIN_SEASON_YEAR = 1946
MAX_SEASON_YEAR = 2100  # Reasonable upper bound for validation

# Valid season type values
VALID_SEASON_TYPES = {"Regular Season", "Playoffs"}


def get_current_season() -> str:
    """Determine the current NBA season based on current date.

    Returns:
        Season string in format 'YYYY-YY' (e.g., '2024-25').
    """
    today = date.today()
    year = today.year
    month = today.month

    # NBA season runs from October to June
    # If we're before July, we're in the season that started the previous year
    start_year = year - 1 if month < 7 else year

    end_year = (start_year + 1) % 100
    return f"{start_year}-{end_year:02d}"


def validate_season_format(season: str) -> bool:
    """Validate season string format.

    Args:
        season: Season string to validate.

    Returns:
        True if valid, False otherwise.

    Valid format: 'YYYY-YY' (e.g., '2024-25')
    """
    if not season or not isinstance(season, str):
        return False

    # Pattern: 4-digit year, hyphen, 2-digit year
    pattern = r"^\d{4}-\d{2}$"
    if not re.match(pattern, season):
        return False

    try:
        parts = season.split("-")
        start_year = int(parts[0])
        end_year_short = int(parts[1])
        end_year = (start_year // 100) * 100 + end_year_short

        # Validate year ranges
        if not (MIN_SEASON_YEAR <= start_year <= MAX_SEASON_YEAR):
            return False

        # End year should be start_year + 1
        return end_year == start_year + 1
    except (ValueError, IndexError):
        return False


def parse_season_to_year(season: str) -> int:
    """Parse season string to season year.

    Args:
        season: Season string in format 'YYYY-YY' (e.g., '2024-25').

    Returns:
        Season year (the year the season started).

    Raises:
        ValueError: If season format is invalid.
    """
    if not validate_season_format(season):
        raise ValueError(
            f"Invalid season format: '{season}'. "
            f"Expected format: 'YYYY-YY' (e.g., '2024-25'). "
            f"Year must be between {MIN_SEASON_YEAR} and {MAX_SEASON_YEAR}."
        )

    return int(season.split("-")[0])


def validate_season_type(season_type: str) -> str:
    """Validate and normalize season type.

    Args:
        season_type: Season type string to validate.

    Returns:
        Normalized season type string.

    Raises:
        ValueError: If season type is invalid.
    """
    if not season_type or not isinstance(season_type, str):
        raise ValueError("Season type cannot be empty")

    # Normalize: title case and strip whitespace
    normalized = season_type.strip()

    if normalized not in VALID_SEASON_TYPES:
        valid_types_str = ", ".join(f"'{t}'" for t in VALID_SEASON_TYPES)
        raise ValueError(f"Invalid season type: '{season_type}'. Must be one of: {valid_types_str}")

    return normalized
