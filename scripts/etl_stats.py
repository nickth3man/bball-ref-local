"""ETL script for extracting and loading NBA player game statistics.

Usage:
    python scripts/etl_stats.py
    python scripts/etl_stats.py --season 2023-24
    python scripts/etl_stats.py --season-type Playoffs

Fetches player game logs from nba_api and inserts into DuckDB player_game_stats table.

TODO: CRITICAL - This ETL only populates basic box score stats
Missing implementation for player_season_stats table with advanced metrics:
  - PER (Player Efficiency Rating)
  - WS (Win Shares)
  - WS/48 (Win Shares per 48 minutes)
  - BPM (Box Plus/Minus)
  - VORP (Value Over Replacement Player)
  - TS% (True Shooting % - at season level)
  - USG% (Usage Rate)
  - ORtg (Offensive Rating)
  - DRtg (Defensive Rating)

TODO: CRITICAL - Missing ETL for player_game_logs table
This table should contain enhanced game logs with:
  - plus_minus (from PlayerGameLogs API)
  - ts_pct (calculated per game)
  - efg_pct (calculated per game)
  - is_home, is_win flags

Note: Formulas verified correct per basketball-reference.com standards
See AUDIT_REPORT.md for complete formula reference
"""

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nba_api.stats.endpoints import PlayerGameLogs

from app.config import settings
from app.services.database import get_db_connection
from scripts.etl_base import BaseETL
from scripts.etl_utils import get_current_season, validate_season_format, validate_season_type
from scripts.ingestion.exceptions import DatabaseError
from scripts.logging_utils import enable_verbose_logging, setup_etl_logging
from scripts.retry_utils import retry_api_call

logger = setup_etl_logging(__name__)


def _to_int(value: object) -> int:
    """Safely convert a value to int, handling None and non-numeric values."""
    if value is None:
        return 0
    try:
        return int(value)  # type: ignore
    except (ValueError, TypeError):
        return 0


def generate_stat_id(player_id: int | str, game_id: str) -> int:
    """Generate deterministic stat_id from player_id and game_id.

    Args:
        player_id: Player ID.
        game_id: Game ID.

    Returns:
        Integer ID (hash).
    """
    unique_str = f"{player_id}-{game_id}"
    return int(hashlib.md5(unique_str.encode()).hexdigest(), 16) % (10**9)


class StatsETL(BaseETL):
    """ETL process for NBA player game statistics."""

    def __init__(self):
        super().__init__("stats_etl")
        self.season = None
        self.season_type = None
        self.batch_size = settings.insert_batch_size

    @retry_api_call(max_retries=3, initial_delay=0.6)
    def extract(
        self, season: str | None = None, season_type: str = "Regular Season"
    ) -> pd.DataFrame:
        """Extract player game logs from nba_api.

        Args:
            season: Season string.
            season_type: Season type.

        Returns:
            DataFrame with raw game logs.
        """
        # Store context
        self.season = season
        self.season_type = season_type

        logger.info(f"Extracting player stats for {season} ({season_type})...")

        # PlayerGameLogs fetches all game logs for all players for the specified season
        game_logs = PlayerGameLogs(
            season_nullable=season,
            season_type_nullable=season_type,
            league_id_nullable="00",
        )

        df = game_logs.get_data_frames()[0]

        logger.info(f"Extracted {len(df)} game log records")
        self._apply_rate_limit()

        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform raw game logs to match database schema.

        Args:
            df: Raw game logs.

        Returns:
            Transformed DataFrame.
        """
        logger.info("Transforming player stats...")

        if df.empty:
            return pd.DataFrame()

        # Rename columns to match schema
        column_mapping = {
            "GAME_ID": "game_id",
            "PLAYER_ID": "player_id",
            "TEAM_ID": "team_id",
            "MIN": "minutes_played",
            "PTS": "points",
            "OREB": "rebounds_offensive",
            "DREB": "rebounds_defensive",
            "AST": "assists",
            "STL": "steals",
            "BLK": "blocks",
            "TOV": "turnovers",
            "PF": "personal_fouls",
            "FGM": "fg_made",
            "FGA": "fg_attempted",
            "FG3M": "fg3_made",
            "FG3A": "fg3_attempted",
            "FTM": "ft_made",
            "FTA": "ft_attempted",
        }

        df = df.rename(columns=column_mapping)

        # Generate unique stat_id
        df["stat_id"] = df.apply(lambda x: generate_stat_id(x["player_id"], x["game_id"]), axis=1)

        # Convert types
        df["game_id"] = df["game_id"].astype(str)
        df["player_id"] = df["player_id"].astype(str)
        df["team_id"] = df["team_id"].astype(str)

        # Handle minutes (can be float or string like "24:30")
        # For simplicity, if it's a string, we might just keep the minute part or convert
        # But `PlayerGameLogs` usually returns float minutes in recent versions
        # We'll just force to float, dealing with errors
        df["minutes_played"] = pd.to_numeric(df["minutes_played"], errors="coerce").fillna(0.0)

        # Ensure integer columns
        int_cols = [
            "points",
            "rebounds_offensive",
            "rebounds_defensive",
            "assists",
            "steals",
            "blocks",
            "turnovers",
            "personal_fouls",
            "fg_made",
            "fg_attempted",
            "fg3_made",
            "fg3_attempted",
            "ft_made",
            "ft_attempted",
        ]

        for col in int_cols:
            if col in df.columns:
                df[col] = df[col].apply(_to_int)
            else:
                df[col] = 0

        # Select db columns
        db_columns = ["stat_id", "game_id", "player_id", "team_id", "minutes_played"] + int_cols

        # Filter for existing columns
        result_df = df[[col for col in db_columns if col in df.columns]]

        logger.info(f"Transformed {len(result_df)} stat records")
        return result_df

    def load(self, df: pd.DataFrame) -> int:
        """Load stats into DuckDB.

        Args:
            df: Transformed stats data.

        Returns:
            Number of rows loaded.
        """
        logger.info("Loading stats into database...")

        conn = get_db_connection()

        try:
            data = [tuple(row) for row in df.itertuples(index=False)]

            if not data:
                logger.info("No stats to load")
                return 0

            # Batch insert
            total_loaded = 0
            # Use instance batch size (can be overridden via init args if needed)
            batch_size = self.batch_size

            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO player_game_stats (
                        stat_id, game_id, player_id, team_id, minutes_played,
                        points, rebounds_offensive, rebounds_defensive, assists,
                        steals, blocks, turnovers, personal_fouls,
                        fg_made, fg_attempted, fg3_made, fg3_attempted,
                        ft_made, ft_attempted, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        CURRENT_TIMESTAMP
                    )
                """,
                    batch,
                )
                total_loaded += len(batch)
                logger.info(f"Loaded {total_loaded}/{len(data)} stats")

            logger.info(f"Successfully loaded {total_loaded} stat records")
            return total_loaded

        except Exception as e:
            logger.error(f"Failed to load stats: {e}")
            raise DatabaseError(
                "Failed to load stats into database",
                operation="load_stats",
                original_error=e,
            ) from e

    # Override run to accept batch_size param (though we handle it in init/load)
    # This is to match the signature expected by run_all_etl.py
    def run(self, *args, **kwargs) -> dict[str, Any]:
        if "batch_size" in kwargs:
            self.batch_size = kwargs.pop("batch_size")
        return super().run(*args, **kwargs)


def run_etl(
    season: str | None = None,
    season_type: str = "Regular Season",
    batch_size: int = 1000,
) -> dict[str, Any]:
    """Run the complete stats ETL pipeline.

    Args:
        season: Season string.
        season_type: Season type.
        batch_size: Batch size for inserts.

    Returns:
        Dictionary with ETL results.
    """
    if season is None:
        season = get_current_season()

    if not validate_season_format(season):
        raise ValueError(f"Invalid season format: {season}")

    if not validate_season_type(season_type):
        raise ValueError(f"Invalid season type: {season_type}")

    etl = StatsETL()
    # Pass batch_size via kwargs to run, which forwards to extract/transform/load if needed
    # But for StatsETL we overrode run() to capture batch_size
    return etl.run(season=season, season_type=season_type, batch_size=batch_size)


def main() -> int:
    """Main entry point for stats ETL.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(description="ETL for NBA player stats")
    parser.add_argument(
        "--season",
        "-s",
        type=str,
        help="Season in YYYY-YY format. Defaults to current.",
    )
    parser.add_argument(
        "--season-type",
        "-t",
        type=str,
        default="Regular Season",
        choices=["Regular Season", "Playoffs"],
        help="Season type",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=settings.insert_batch_size,
        help="Batch size for DB inserts",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        enable_verbose_logging()

    season = args.season
    if season is None:
        season = get_current_season()

    logger.info(f"Starting stats ETL for season {season}...")
    result = run_etl(
        season=season,
        season_type=args.season_type,
        batch_size=args.batch_size,
    )

    if result["status"] == "success":
        logger.info(
            f"Stats ETL completed: {result['extracted']} records extracted, "
            f"{result['loaded']} loaded"
        )
        return 0
    else:
        logger.error(f"Stats ETL failed: {result['error']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
