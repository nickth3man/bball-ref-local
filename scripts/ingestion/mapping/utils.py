"""Utility functions for the mapping module."""

import csv
from pathlib import Path
from typing import Any

from scripts.ingestion.logger import get_logger

logger = get_logger(__name__)


def load_csv(
    csv_path: Path,
    row_parser: callable,
    required_columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Load and parse a CSV file.

    Args:
        csv_path: Path to the CSV file
        row_parser: Function to parse each row into a dictionary
        required_columns: List of columns that must be present in the CSV

    Returns:
        List of parsed row dictionaries
    """
    results = []

    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Validate required columns
            if required_columns and reader.fieldnames:
                missing = set(required_columns) - set(reader.fieldnames)
                if missing:
                    logger.warning(f"Missing columns in {csv_path}: {missing}")

            for row in reader:
                try:
                    parsed = row_parser(row)
                    if parsed is not None:
                        results.append(parsed)
                except (ValueError, KeyError) as e:
                    logger.debug(f"Error parsing row in {csv_path}: {e}")

    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_path}")
    except csv.Error as e:
        logger.error(f"CSV parsing error in {csv_path}: {e}")

    return results


def safe_int(value: str | None, default: int | None = None) -> int | None:
    """Safely convert a value to integer.

    Args:
        value: String value to convert
        default: Default value if conversion fails

    Returns:
        Integer value or default
    """
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: str | None, default: str = "") -> str:
    """Safely get a string value.

    Args:
        value: Value to convert to string
        default: Default value if None

    Returns:
        String value
    """
    if value is None:
        return default
    return str(value).strip()


def normalize_name(name: str) -> str:
    """Normalize a name for comparison.

    Args:
        name: Name to normalize

    Returns:
        Normalized name (lowercase, single spaces)
    """
    if not name:
        return ""
    return " ".join(name.split()).lower()
