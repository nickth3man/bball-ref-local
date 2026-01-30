"""Utility functions for the data ingestion pipeline."""

import re

import numpy as np

from scripts.ingestion.config import MAX_SEASON, MIN_SEASON
from scripts.ingestion.logger import get_logger

logger = get_logger(__name__)


def clean_column_names(columns):
    """Convert column names to snake_case."""
    cleaned = []
    for col in columns:
        name = str(col).lower().strip()
        name = name.replace("+/-", "plus_minus")
        name = name.replace("%", "_pct")
        name = name.replace("/", "_per_")
        name = name.replace("-", "_")
        name = name.replace(".", "")
        name = name.replace("(", "")
        name = name.replace(")", "")
        name = name.replace(" ", "_")
        name = re.sub(r"[^a-z0-9_]", "", name)
        name = re.sub(r"_+", "_", name)
        name = name.strip("_")
        if not name:
            name = "unnamed_column"
        cleaned.append(name)
    return cleaned


def parse_season(season_str):
    """Parse season string to integer year."""
    if season_str is None:
        return None
    if isinstance(season_str, int):
        return season_str if MIN_SEASON <= season_str <= MAX_SEASON else None
    season = str(season_str).strip()
    if not season:
        return None
    try:
        if season.isdigit():
            year = int(season)
            return year if MIN_SEASON <= year <= MAX_SEASON else None
    except (ValueError, IndexError):
        return None
    return None


TEAM_NAME_MAPPINGS = {
    "lal": "Los Angeles Lakers",
    "lakers": "Los Angeles Lakers",
    "gsw": "Golden State Warriors",
    "warriors": "Golden State Warriors",
}


def normalize_team_name(name):
    """Normalize team name variations."""
    if not name:
        return None
    normalized_input = str(name).lower().strip()
    if normalized_input in TEAM_NAME_MAPPINGS:
        return TEAM_NAME_MAPPINGS[normalized_input]
    return name


def safe_int(value, default=None):
    """Safely convert a value to integer."""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if np.isnan(value):
            return default
        return int(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in ("null", "none", "na", "n/a", "-", ""):
            return default
        cleaned = cleaned.replace(",", "")
        try:
            return int(float(cleaned))
        except (ValueError, TypeError):
            pass
    return default


def safe_float(value, default=None):
    """Safely convert a value to float."""
    if value is None:
        return default
    if isinstance(value, float):
        return value if not np.isnan(value) else default
    if isinstance(value, int):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in ("null", "none", "na", "n/a", "-", ""):
            return default
        cleaned = cleaned.replace(",", "")
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1]
            try:
                return float(cleaned) / 100
            except (ValueError, TypeError):
                pass
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            pass
    return default


def chunk_dataframe(df, chunk_size):
    """Split DataFrame into chunks for batch processing."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if df.empty:
        logger.warning("Empty DataFrame provided to chunk_dataframe")
        return
    total_rows = len(df)
    for i in range(0, total_rows, chunk_size):
        chunk = df.iloc[i : i + chunk_size].copy()
        yield chunk


def clean_string(value, default=None):
    """Clean and normalize a string value."""
    if value is None:
        return default
    cleaned = str(value).strip()
    if not cleaned:
        return default
    return cleaned


def parse_boolean(value, default=None):
    """Parse a value to boolean."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.lower().strip()
        if lowered in ("true", "yes", "y", "1", "t"):
            return True
        if lowered in ("false", "no", "n", "0", "f", ""):
            return False
    return default
