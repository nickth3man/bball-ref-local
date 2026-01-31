"""Configuration management for the data ingestion pipeline.

This module provides backward-compatible configuration constants that delegate
to the unified app.config.Settings.
"""

from typing import Final

from app.config import (
    BACKUP_TABLE_SUFFIX,
    BATCH_SIZE,
    BULK_INSERT_OPTIMIZATIONS,
    DATA_SOURCE_CSV,
    DATA_SOURCE_PARQUET,
    INSERT_BATCH_SIZE,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    LOG_LEVEL,
    MAX_SEASON,
    MIN_SEASON,
    PLANNING_CSV_DIR,
    PLANNING_PARQ_DIR,
    TEMP_TABLE_SUFFIX,
)

# Re-export all constants
__all__ = [
    "PLANNING_CSV_DIR",
    "PLANNING_PARQ_DIR",
    "BATCH_SIZE",
    "INSERT_BATCH_SIZE",
    "DATA_SOURCE_CSV",
    "DATA_SOURCE_PARQUET",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "LOG_DATE_FORMAT",
    "MIN_SEASON",
    "MAX_SEASON",
    "BULK_INSERT_OPTIMIZATIONS",
    "TEMP_TABLE_SUFFIX",
    "BACKUP_TABLE_SUFFIX",
    "CSV_ENCODING",
    "CSV_DELIMITER",
    "EXPECTED_CSV_FILES",
    "EXPECTED_PARQUET_FILES",
    "INGESTION_PHASES",
    "PHASE_DEPENDENCIES",
]

# File Type Mapping (Keep these here as they are specific to ingestion implementation details)
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

# Ingestion Phases
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
