"""Data loaders for ingesting basketball reference data.

This package provides specialized loaders for different types of data files,
all extending the BaseLoader class to ensure consistent behavior.

Example:
    from scripts.ingestion.loaders import TeamLoader, PlayerLoader

    team_loader = TeamLoader()
    teams = team_loader.load()

    player_loader = PlayerLoader()
    players = player_loader.load()
"""

from .awards_loaders import AwardsLoader, DraftLoader
from .game_loaders import GamesLoader, PlayerGameStatsLoader, TeamGameStatsLoader
from .parquet_loaders import ParquetLoader
from .reference_loaders import PlayerLoader, TeamLoader
from .stats_loaders import PlayerSeasonStatsLoader, TeamSeasonStatsLoader

__all__ = [
    # Reference loaders
    "TeamLoader",
    "PlayerLoader",
    # Game loaders
    "GamesLoader",
    "PlayerGameStatsLoader",
    "TeamGameStatsLoader",
    # Stats loaders
    "PlayerSeasonStatsLoader",
    "TeamSeasonStatsLoader",
    # Awards loaders
    "AwardsLoader",
    "DraftLoader",
    # Parquet loader
    "ParquetLoader",
]
