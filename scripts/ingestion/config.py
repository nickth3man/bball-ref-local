"""Configuration management for the data ingestion pipeline.

This module contains all configuration constants and settings used throughout
the ingestion pipeline, including paths, batch sizes, and validation thresholds.
"""

from pathlib import Path
from typing import Final

# =============================================================================
# Path Configuration
# =============================================================================

PLANNING_CSV_DIR: Final[Path] = Path(__file__).parent.parent.parent / "planning" / "csv_data"
PLANNING_PARQ_DIR: Final[Path] = Path(__file__).parent.parent.parent / "planning" / "parq_data"

# =============================================================================
# Batch Processing Configuration
# =============================================================================

BATCH_SIZE: Final[int] = 10000  # rows per batch for large files like PlayerStatistics.csv
INSERT_BATCH_SIZE: Final[int] = 1000  # rows per INSERT batch for database operations

# =============================================================================
# Data Source Identifiers
# =============================================================================

DATA_SOURCE_CSV: Final[str] = "planning_csv"
DATA_SOURCE_PARQUET: Final[str] = "planning_parquet"

# =============================================================================
# Logging Configuration
# =============================================================================

LOG_LEVEL: Final[str] = "INFO"
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Validation Thresholds
# =============================================================================

MIN_SEASON: Final[int] = 1946  # First NBA season
MAX_SEASON: Final[int] = 2026  # Future season buffer

# =============================================================================
# Database Configuration
# =============================================================================

# Connection settings for bulk operations
BULK_INSERT_OPTIMIZATIONS: Final[dict[str, str]] = {
    "memory_limit": "1GB",
    "threads": "4",
}

# Temp table suffix for staging operations
TEMP_TABLE_SUFFIX: Final[str] = "_temp"
BACKUP_TABLE_SUFFIX: Final[str] = "_backup"

# =============================================================================
# File Type Mapping
# =============================================================================

CSV_ENCODING: Final[str] = "utf-8"
CSV_DELIMITER: Final[str] = ","

# Expected CSV files in planning/csv_data/
EXPECTED_CSV_FILES: Final[list[str]] = [
    "Players.csv",
    "TeamStatistics.csv",
    "TeamHistories.csv",
    "PlayerStatistics.csv",
    "LeagueSchedule25_26.csv",
    "LeagueSchedule24_25.csv",
    "Games.csv",
    "Player_Career_Info.csv",
    "Player_Award_Shares.csv",
    "Player_Per_Game.csv",
    "Player_Play_By_Play.csv",
    "Team_Totals.csv",
    "Team_Summaries.csv",
    "Team_Stats_Per_Game.csv",
    "Team_Stats_Per_100_Poss.csv",
    "Team_Abbrev.csv",
    "Player_Totals.csv",
    "Player_Shooting.csv",
    "Player_Season_Info.csv",
    "Draft_Pick_History.csv",
    "All-Star Selections.csv",
    "Advanced.csv",
    "End_of_Season_Teams_(Voting).csv",
    "End_of_Season_Teams.csv",
    "Opponent_Totals.csv",
    "Opponent_Stats_Per_Game.csv",
    "Opponent_Stats_Per_100_Poss.csv",
    "Per_36_Minutes.csv",
    "Per_100_Poss.csv",
]

# Expected Parquet files in planning/parq_data/
EXPECTED_PARQUET_FILES: Final[list[str]] = [
    "advanced.parq",
    "per_game.parq",
    "roster.parq",
    "shooting.parq",
    "totals.parq",
]

# =============================================================================
# Ingestion Phases
# =============================================================================

INGESTION_PHASES: Final[list[str]] = [
    "reference",  # Teams, Players, Seasons - foundation tables
    "transaction",  # Games, Draft picks - tables with foreign keys to reference
    "stats",  # Player and team statistics
    "awards",  # Awards and honors
]

# Phase dependencies (which phases must complete before this one)
PHASE_DEPENDENCIES: Final[dict[str, list[str]]] = {
    "reference": [],
    "transaction": ["reference"],
    "stats": ["reference", "transaction"],
    "awards": ["reference", "transaction", "stats"],
}
