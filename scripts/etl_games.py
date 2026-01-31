"""ETL script for extracting and loading NBA game data.

Usage:
    python scripts/etl_games.py
    python scripts/etl_games.py --season 2023-24
    python scripts/etl_games.py --season-type Playoffs

Fetches games from nba_api and inserts into DuckDB games table.

TODO: MEDIUM - Missing quarter score data
The database schema includes quarter columns (home_q1-4, away_q1-4, home_ot, away_ot)
but they are not populated because LeagueGameFinder endpoint doesn't provide them.
To populate:
  1. Use BoxScore endpoint for each game (500+ API calls per season)
  2. Use Basketball Reference CSV data via ingestion framework (recommended)

TODO: MEDIUM - Missing arena and attendance data
Database schema has arena and attendance columns but they are not populated.
These fields are available in BoxScore endpoint.

TODO: LOW - Verify is_overtime flag
Currently hardcoded to False - see implementation below for details
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nba_api.stats.endpoints import LeagueGameFinder

from app.config import settings
from app.services.database import get_db_connection
from scripts.etl_base import BaseETL
from scripts.etl_utils import (
    get_current_season,
    parse_season_to_year,
    validate_season_format,
    validate_season_type,
)
from scripts.ingestion.exceptions import DatabaseError
from scripts.logging_utils import enable_verbose_logging, setup_etl_logging
from scripts.retry_utils import retry_api_call

logger = setup_etl_logging(__name__)


def parse_game_date(date_str: str) -> date | None:
    """Parse game date string to date object.

    Args:
        date_str: Date string (e.g., '2023-10-24').

    Returns:
        Date object or None if parsing fails.
    """
    if not date_str:
        return None

    formats = ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    try:
        # Try pandas parser as fallback
        return pd.to_datetime(date_str).date()
    except Exception:
        return None


class GamesETL(BaseETL):
    """ETL process for NBA games."""

    def __init__(self):
        super().__init__("games_etl")
        self.season = None
        self.season_type = None

    @retry_api_call(max_retries=3, initial_delay=0.6)
    def extract(
        self, season: str | None = None, season_type: str = "Regular Season"
    ) -> pd.DataFrame:
        """Extract games from nba_api.

        Args:
            season: Season string (e.g., '2023-24').
            season_type: Season type ('Regular Season', 'Playoffs').

        Returns:
            DataFrame with raw game data.
        """
        # Store context for transform/load steps
        self.season = season
        self.season_type = season_type

        logger.info(f"Extracting games for {season} ({season_type})...")

        game_finder = LeagueGameFinder(
            season_nullable=season,
            season_type_nullable=season_type,
            league_id_nullable="00",  # NBA
        )

        df = game_finder.get_data_frames()[0]

        logger.info(f"Extracted {len(df)} team-game records")
        self._apply_rate_limit()

        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform raw game data to match database schema.

        Args:
            df: Raw game data from nba_api.

        Returns:
            Transformed DataFrame with one row per game.
        """
        logger.info("Transforming game data...")

        if df.empty:
            return pd.DataFrame()

        # Deduplicate games (LeagueGameFinder returns 2 rows per game - one for each team)
        # We need to consolidate into one row per game with home/away details

        # Identify home and away teams
        # Matchup format: "BOS vs. MIA" (Home) or "BOS @ MIA" (Away)
        df["is_home"] = df["MATCHUP"].str.contains(" vs. ")

        # Split into home and away dataframes
        home_games = df[df["is_home"]].copy()
        away_games = df[~df["is_home"]].copy()

        # Rename columns to distinguish home/away
        home_games = home_games.rename(
            columns={
                "TEAM_ID": "home_team_id",
                "PTS": "home_score",
                "WL": "home_wl",
                "MIN": "minutes",
            }
        )

        away_games = away_games.rename(
            columns={
                "TEAM_ID": "away_team_id",
                "PTS": "away_score",
                "WL": "away_wl",
            }
        )

        # Merge on Game ID
        # Note: Using inner join to ensure we have data for both teams
        games = pd.merge(
            home_games[["GAME_ID", "GAME_DATE", "home_team_id", "home_score", "home_wl"]],
            away_games[["GAME_ID", "away_team_id", "away_score", "away_wl"]],
            on="GAME_ID",
            how="inner",
        )

        # Calculate additional fields
        games["game_id"] = games["GAME_ID"].astype(str)
        games["game_date"] = games["GAME_DATE"].apply(parse_game_date)
        games["season"] = parse_season_to_year(self.season) if self.season else None
        # Create season_id (e.g., "2023-24")
        games["season_id"] = self.season if self.season else get_current_season()
        games["season_type"] = self.season_type
        games["is_playoff"] = self.season_type == "Playoffs"
        # TODO: MEDIUM - Fetch actual overtime data
        # Current: is_overtime is hardcoded to False
        # Issue: LeagueGameFinder endpoint doesn't provide quarter scores or OT flag
        # Solution: Fetch from BoxScore endpoint for each game (expensive)
        # Alternative: Use play-by-play data to calculate
        # Note: Database schema has is_overtime column ready
        games["is_overtime"] = False  # Not easily available from LeagueGameFinder
        games["status"] = games.apply(
            lambda x: "Final"
            if x["home_score"] is not None and x["away_score"] is not None
            else "Scheduled",
            axis=1,
        )

        # Determine winner
        games["winner_team_id"] = games.apply(
            lambda x: x["home_team_id"]
            if x["home_score"] is not None
            and x["away_score"] is not None
            and x["home_score"] > x["away_score"]
            else x["away_team_id"]
            if x["home_score"] is not None
            and x["away_score"] is not None
            and x["away_score"] > x["home_score"]
            else None,
            axis=1,
        )

        # Select db columns
        db_columns = [
            "game_id",
            "season_id",
            "season",
            "season_type",
            "game_date",
            "home_team_id",
            "away_team_id",
            "home_score",
            "away_score",
            "winner_team_id",
            "is_playoff",
            "is_overtime",
            "status",
        ]

        result_df = games[db_columns]

        logger.info(f"Transformed into {len(result_df)} unique games")
        return result_df

    def load(self, df: pd.DataFrame) -> int:
        """Load games into DuckDB.

        Args:
            df: Transformed game data.

        Returns:
            Number of games loaded.
        """
        logger.info("Loading games into database...")

        conn = get_db_connection()

        try:
            # Convert game_id to string explicitly to match schema
            if "game_id" in df.columns:
                df["game_id"] = df["game_id"].astype(str)

            data = [
                (
                    row.game_id,
                    row.season_id,
                    row.season,
                    row.season_type,
                    row.game_date,
                    row.home_team_id,
                    row.away_team_id,
                    row.home_score,
                    row.away_score,
                    row.winner_team_id,
                    row.is_playoff,
                    row.is_overtime,
                    row.status,
                )
                for row in df.itertuples(index=False)
            ]

            if not data:
                logger.info("No games to load")
                return 0

            conn.executemany(
                """
                INSERT OR REPLACE INTO games (
                    game_id, season_id, season, season_type, game_date,
                    home_team_id, away_team_id, home_score, away_score,
                    winner_team_id, is_playoff, is_overtime, status,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                data,
            )

            rows_loaded = len(data)
            logger.info(f"Successfully loaded {rows_loaded} games")
            return rows_loaded

        except Exception as e:
            logger.error(f"Failed to load games: {e}")
            raise DatabaseError(
                "Failed to load games into database",
                operation="load_games",
                original_error=e,
            ) from e


def run_etl(season: str | None = None, season_type: str = "Regular Season") -> dict[str, Any]:
    """Run the complete games ETL pipeline.

    Args:
        season: Season string (e.g., '2023-24'). Uses current season if None.
        season_type: Season type ('Regular Season' or 'Playoffs').

    Returns:
        Dictionary with ETL results.
    """
    if season is None:
        season = get_current_season()

    if not validate_season_format(season):
        raise ValueError(f"Invalid season format: {season}. Expected format: YYYY-YY")

    if not validate_season_type(season_type):
        raise ValueError(f"Invalid season type: {season_type}")

    etl = GamesETL()
    # Pass arguments to run, which forwards them to extract
    result = etl.run(season=season, season_type=season_type)

    # Add metadata to result for consistency with old return format
    result["season"] = season
    result["season_type"] = season_type

    return result


def main() -> int:
    """Main entry point for games ETL.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(description="ETL for NBA game data")
    parser.add_argument(
        "--season",
        "-s",
        type=str,
        help="Season in YYYY-YY format (e.g., 2023-24). Defaults to current season.",
    )
    parser.add_argument(
        "--season-type",
        "-t",
        type=str,
        default="Regular Season",
        choices=["Regular Season", "Playoffs"],
        help="Season type (Regular Season or Playoffs)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        enable_verbose_logging()

    season = args.season
    if season is None:
        season = get_current_season()

    logger.info(f"Starting games ETL for season {season} ({args.season_type})...")
    result = run_etl(season=season, season_type=args.season_type)

    if result["status"] == "success":
        logger.info(
            f"Games ETL completed: {result['extracted']} team-game records extracted, "
            f"{result['loaded']} games loaded"
        )
        return 0
    else:
        logger.error(f"Games ETL failed: {result['error']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
