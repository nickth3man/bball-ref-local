"""ETL script for extracting and loading NBA player game statistics.

Usage:
    python scripts/etl_stats.py
    python scripts/etl_stats.py --season 2023-24
    python scripts/etl_stats.py --season-type Playoffs

Fetches player game logs from nba_api and inserts into DuckDB player_game_stats table.
"""

import argparse
import hashlib
import logging
import sys
import time
from pathlib import Path

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nba_api.stats.endpoints import PlayerGameLogs

from app.services.database import close_db_connection, get_db_connection
from scripts.etl_utils import get_current_season, validate_season_format, validate_season_type
from scripts.ingestion.exceptions import APIError, DatabaseError, DataTransformationError, ETLError

# Configure logging
from scripts.logging_utils import setup_etl_logging
from scripts.retry_utils import retry_api_call

logger = setup_etl_logging(__name__)

# Rate limiting delay (seconds)
RATE_LIMIT_DELAY = 0.6
# Batch size for bulk inserts
BATCH_SIZE = 1000


def _to_int(value: object) -> int:
    """Safely convert a value to int, handling None and non-numeric values."""
    if value is None:
        return 0
    try:
        return int(value)  # type: ignore
    except (ValueError, TypeError):
        return 0


def generate_stat_id(player_id: int, game_id: str) -> int:
    """Generate deterministic stat_id from player_id and game_id.

    Uses SHA256 hash to ensure the same ID is generated across runs.

    Args:
        player_id: The player's ID.
        game_id: The game's ID.

    Returns:
        A deterministic integer stat_id.
    """
    key = f"{player_id}_{game_id}"
    hash_bytes = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(hash_bytes[:4], "big") % (2**31)


def parse_minutes_played(min_str: str | float | None) -> float | None:
    """Parse minutes played string to float.

    Args:
        min_str: Minutes string (e.g., '35:42' or 35.7).

    Returns:
        Minutes as float or None if invalid.
    """
    if min_str is None or min_str == "":
        return None

    if isinstance(min_str, (int, float)):
        return float(min_str) if min_str >= 0 else None

    try:
        # Handle format like "35:42" (minutes:seconds)
        if ":" in str(min_str):
            parts = str(min_str).split(":")
            minutes = float(parts[0])
            seconds = float(parts[1]) if len(parts) > 1 else 0
            return minutes + seconds / 60
        else:
            return float(min_str)
    except (ValueError, TypeError):
        return None


@retry_api_call(max_retries=3, initial_delay=0.6)
def extract_player_stats(season: str, season_type: str = "Regular Season") -> pd.DataFrame:
    """Extract player game statistics from nba_api.

    Args:
        season: Season string (e.g., '2024-25').
        season_type: Type of season ('Regular Season' or 'Playoffs').

    Returns:
        DataFrame with raw player game statistics.

    Raises:
        ValueError: If season or season_type is invalid.
    """
    # Validate inputs
    if not validate_season_format(season):
        raise ValueError(f"Invalid season format: '{season}'. Expected format: 'YYYY-YY'")
    season_type = validate_season_type(season_type)

    logger.info(f"Extracting player game stats for season {season} ({season_type})...")

    endpoint = PlayerGameLogs(
        season_nullable=season,
        season_type_nullable=season_type,
    )
    df = endpoint.get_data_frames()[0]

    if len(df) == 0:
        logger.info("No player game stats returned for given season/season_type")
    else:
        logger.info(f"Fetched {len(df)} records from PlayerGameLogs")

    time.sleep(RATE_LIMIT_DELAY)
    return df


def transform_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Transform raw player game stats to match database schema.

    Args:
        df: Raw player game stats from nba_api.

    Returns:
        Transformed DataFrame matching PlayerGameStats model.
    """
    logger.info("Transforming player game stats...")

    # Convert column names to lowercase
    df.columns = df.columns.str.lower().str.strip()

    # Map nba_api fields to our schema
    # PlayerGameLogs columns include:
    # player_id, player_name, team_id, team_abbreviation, game_id, game_date,
    # min, pts, fgm, fga, fg_pct, fg3m, fg3a, fg3_pct, ftm, fta, ft_pct,
    # oreb, dreb, reb, ast, stl, blk, tov, pf, plus_minus, etc.

    column_mapping = {
        "player_id": "player_id",
        "team_id": "team_id",
        "game_id": "game_id",
        "min": "minutes_played",
        "pts": "points",
        "oreb": "rebounds_offensive",
        "dreb": "rebounds_defensive",
        "ast": "assists",
        "stl": "steals",
        "blk": "blocks",
        "tov": "turnovers",
        "pf": "personal_fouls",
        "fgm": "fg_made",
        "fga": "fg_attempted",
        "fg3m": "fg3_made",
        "fg3a": "fg3_attempted",
        "ftm": "ft_made",
        "fta": "ft_attempted",
    }

    # Only map columns that exist
    existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
    df = df.rename(columns=existing_mapping)

    # Generate stat_id using deterministic hash
    df["stat_id"] = df.apply(lambda row: generate_stat_id(row["player_id"], row["game_id"]), axis=1)

    # Parse minutes played
    if "minutes_played" in df.columns:
        df["minutes_played"] = df["minutes_played"].apply(parse_minutes_played)

    # Ensure numeric columns are numeric
    numeric_columns = [
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

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = 0

    # Ensure required IDs are proper types (string to match Pydantic models)
    df["player_id"] = df["player_id"].astype(str)
    df["team_id"] = df["team_id"].astype(str)
    df["game_id"] = df["game_id"].astype(str)

    # Select only columns that exist in our database schema
    db_columns = [
        "stat_id",
        "game_id",
        "player_id",
        "team_id",
        "minutes_played",
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

    # Ensure all required columns exist
    for col in db_columns:
        if col not in df.columns:
            if col == "stat_id":
                continue  # Already generated
            df[col] = 0

    df = df[db_columns]

    # Remove duplicates
    df = df.drop_duplicates(subset=["stat_id"])

    logger.info(f"Transformed {len(df)} player game stats")
    return df


def load_player_stats(df: pd.DataFrame, batch_size: int = BATCH_SIZE) -> int:
    """Load player game stats into DuckDB using batch upsert.

    Args:
        df: Transformed player game stats.
        batch_size: Number of records to insert per batch.

    Returns:
        Number of rows loaded.
    """
    logger.info("Loading player game stats into database...")

    conn = get_db_connection()
    rows_loaded = 0

    try:
        # Process in batches for better performance using executemany
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]

            # Use itertuples for better performance than iterrows
            data = [
                (
                    _to_int(row.stat_id),
                    str(row.game_id),
                    str(row.player_id),
                    str(row.team_id),
                    row.minutes_played,
                    _to_int(row.points),
                    _to_int(row.rebounds_offensive),
                    _to_int(row.rebounds_defensive),
                    _to_int(row.assists),
                    _to_int(row.steals),
                    _to_int(row.blocks),
                    _to_int(row.turnovers),
                    _to_int(row.personal_fouls),
                    _to_int(row.fg_made),
                    _to_int(row.fg_attempted),
                    _to_int(row.fg3_made),
                    _to_int(row.fg3_attempted),
                    _to_int(row.ft_made),
                    _to_int(row.ft_attempted),
                )
                for row in batch.itertuples(index=False)
            ]

            if data:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO player_game_stats (
                        stat_id, game_id, player_id, team_id, minutes_played,
                        points, rebounds_offensive, rebounds_defensive, assists,
                        steals, blocks, turnovers, personal_fouls,
                        fg_made, fg_attempted, fg3_made, fg3_attempted,
                        ft_made, ft_attempted, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    data,
                )
                rows_loaded += len(data)

            logger.info(f"Loaded batch {i // batch_size + 1}/{(len(df) - 1) // batch_size + 1}")

        logger.info(f"Successfully loaded {rows_loaded} player game stats")
        return rows_loaded

    except Exception as e:
        logger.error(f"Failed to load player game stats: {e}")
        raise DatabaseError(
            "Failed to load player game stats into database",
            operation="load_player_stats",
            original_error=e,
        ) from e


def run_etl(
    season: str | None = None, season_type: str = "Regular Season", batch_size: int = BATCH_SIZE
) -> dict:
    """Run the complete player stats ETL pipeline.

    Args:
        season: Season string (e.g., '2024-25'). Uses current season if None.
        season_type: Type of season ('Regular Season' or 'Playoffs').
        batch_size: Number of records to insert per batch.

    Returns:
        Dictionary with ETL results.
    """
    result = {
        "extracted": 0,
        "loaded": 0,
        "season": season,
        "season_type": season_type,
        "status": "success",
        "error": None,
    }

    if season is None:
        season = get_current_season()

    result["season"] = season

    try:
        # Extract
        df = extract_player_stats(season, season_type)
        result["extracted"] = len(df)

        if len(df) == 0:
            logger.warning("No stats found for the specified criteria")
            return result

        # Transform
        df = transform_player_stats(df)

        # Load
        result["loaded"] = load_player_stats(df, batch_size)

    except APIError as e:
        result["status"] = "failed"
        result["error"] = f"API error during extraction: {e}"
        logger.error(f"Stats ETL API error: {e}")
    except DatabaseError as e:
        result["status"] = "failed"
        result["error"] = f"Database error during loading: {e}"
        logger.error(f"Stats ETL database error: {e}")
    except DataTransformationError as e:
        result["status"] = "failed"
        result["error"] = f"Data transformation error: {e}"
        logger.error(f"Stats ETL transformation error: {e}")
    except ETLError as e:
        result["status"] = "failed"
        result["error"] = f"ETL error: {e}"
        logger.error(f"Stats ETL error: {e}")
    except (ValueError, TypeError) as e:
        result["status"] = "failed"
        result["error"] = f"Data validation error: {e}"
        logger.error(f"Stats ETL validation error: {e}")

    finally:
        close_db_connection()

    return result


def main() -> int:
    """Main entry point for player stats ETL.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(description="ETL for NBA player game statistics")
    parser.add_argument(
        "--season",
        "-s",
        type=str,
        default=None,
        help="Season string (e.g., '2024-25'). Uses current season if not specified.",
    )
    parser.add_argument(
        "--season-type",
        "-t",
        type=str,
        choices=["Regular Season", "Playoffs"],
        default="Regular Season",
        help="Type of season (default: Regular Season)",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size for inserts (default: {BATCH_SIZE})",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    season = args.season
    if season is None:
        season = get_current_season()

    logger.info(f"Starting player stats ETL for season {season} ({args.season_type})...")
    result = run_etl(season=season, season_type=args.season_type, batch_size=args.batch_size)

    if result["status"] == "success":
        logger.info(
            f"Player stats ETL completed: {result['extracted']} extracted, "
            f"{result['loaded']} loaded"
        )
        return 0
    else:
        logger.error(f"Player stats ETL failed: {result['error']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
