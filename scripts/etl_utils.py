"""Shared utility functions for ETL scripts.

This module contains common helper functions used across multiple ETL scripts
to avoid code duplication.
"""

from datetime import date


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
    if month < 7:
        start_year = year - 1
    else:
        start_year = year
    
    end_year = (start_year + 1) % 100
    return f"{start_year}-{end_year:02d}"


def parse_season_to_year(season: str) -> int:
    """Parse season string to season year.
    
    Args:
        season: Season string in format 'YYYY-YY' (e.g., '2024-25').
        
    Returns:
        Season year (the year the season started).
    """
    return int(season.split("-")[0])
