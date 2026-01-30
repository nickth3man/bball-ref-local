"""ETL script for extracting and loading NBA game data.

Usage:
    python scripts/etl_games.py
    python scripts/etl_games.py --season 2023-24
    python scripts/etl_games.py --season-type Playoffs

Fetches games from nba_api and inserts into DuckDB games table.
"""

import argparse
import logging
import sys
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nba_api.stats.endpoints import LeagueGameFinder

from app.services.database import close_db_connection, get_db_connection
from scripts.etl_utils import get_current_season, parse_season_to_year

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Rate limiting delay (seconds)
RATE_LIMIT_DELAY = 0.6


def parse_game_date(date_str: str | None) -> date | None:
    """Parse game date string to date object.

    Args:
        date_str: Date string in various formats.

    Returns:
        Date object or None if invalid.
    """
    if not date_str or date_str == "":
        return None

    try:
        # Try common date formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y"]:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        # Fallback to pandas parser
        return pd.to_datetime(date_str).date()
    except (ValueError, TypeError):
        return None


def extract_games(season: str, season_type: str = "Regular Season") -> pd.DataFrame:
    """Extract game data from nba_api.

    Args:
        season: Season string (e.g., '2024-25').
        season_type: Type of season ('Regular Season' or 'Playoffs').

    Returns:
        DataFrame with raw game data.
    """
    logger.info(f"Extracting games for season {season} ({season_type})...")

    # LeagueGameFinder returns one row per team per game
    # So each game appears twice (once for each team)
    endpoint = LeagueGameFinder(
        season_nullable=season,
        season_type_nullable=season_type,
        player_or_team_abbreviation="T",  # Team-level data
    )
    df = endpoint.get_data_frames()[0]

    logger.info(f"Extracted {len(df)} team-game records")
    time.sleep(RATE_LIMIT_DELAY)

    return df


def transform_games(df: pd.DataFrame, season: str, season_type: str) -> pd.DataFrame:
    """Transform raw game data to match database schema.

    Args:
        df: Raw game data from nba_api.
        season: Season string.
        season_type: Type of season.

    Returns:
        Transformed DataFrame matching Game model.
    """
    logger.info("Transforming game data...")

    # Handle empty DataFrame
    if df.empty:
        logger.warning("Empty game data received, returning empty DataFrame")
        return pd.DataFrame(
            columns=[
                "game_id",
                "season",
                "season_type",
                "game_date",
                "home_team_id",
                "away_team_id",
                "home_score",
                "away_score",
                "winner_team_id",
                "status",
            ]
        )

    # Convert column names to lowercase
    df.columns = df.columns.str.lower().str.strip()

    # LeagueGameFinder returns one row per team per game
    # We need to pivot this to one row per game with home and away teams

    # Identify matchup patterns
    # 'vs.' indicates home game, '@' indicates away game
    df["is_home"] = df["matchup"].str.contains("vs.", na=False)

    # Separate home and away records
    home_df = df[df["is_home"]].copy()
    away_df = df[~df["is_home"]].copy()

    # Merge home and away on game_id
    home_game_ids = set(home_df["game_id"])
    away_game_ids = set(away_df["game_id"])
    unmatched = home_game_ids ^ away_game_ids
    if unmatched:
        logger.warning(f"Dropping {len(unmatched)} games with missing home/away records")

    games = home_df.merge(away_df, on="game_id", suffixes=("_home", "_away"), how="inner")

    # Handle empty result (no matching home/away records)
    if games.empty:
        logger.warning("No complete games found after merging home/away records")
        return pd.DataFrame(
            columns=[
                "game_id",
                "season",
                "season_type",
                "game_date",
                "home_team_id",
                "away_team_id",
                "home_score",
                "away_score",
                "winner_team_id",
                "status",
            ]
        )

    # Map columns to our schema
    games["season"] = parse_season_to_year(season)
    games["season_type"] = season_type
    games["game_date"] = games["game_date_home"].apply(parse_game_date)
    games["home_team_id"] = pd.to_numeric(games["team_id_home"], errors="coerce").astype(int)
    games["away_team_id"] = pd.to_numeric(games["team_id_away"], errors="coerce").astype(int)
    games["home_score"] = pd.to_numeric(games["pts_home"], errors="coerce").astype("Int64")
    games["away_score"] = pd.to_numeric(games["pts_away"], errors="coerce").astype("Int64")

    # Determine winner (only if scores are available)
    def determine_winner(row):
        if pd.isna(row["home_score"]) or pd.isna(row["away_score"]):
            return None
        if row["home_score"] > row["away_score"]:
            return row["home_team_id"]
        if row["away_score"] > row["home_score"]:
            return row["away_team_id"]
        return None

    games["winner_team_id"] = games.apply(determine_winner, axis=1)

    # Determine game status
    # If game_date is in the future -> scheduled
    # If wl (win/loss) is present and scores are present -> final
    # Otherwise -> live or scheduled
    today = date.today()

    def determine_status(row) -> str:
        game_date = row["game_date"]
        has_score = pd.notna(row["home_score"]) and pd.notna(row["away_score"])

        if game_date and game_date > today:
            return "scheduled"
        elif has_score:
            return "final"
        else:
            return "live"

    games["status"] = games.apply(determine_status, axis=1)

    # Select only columns that exist in our database schema
    db_columns = [
        "game_id",
        "season",
        "season_type",
        "game_date",
        "home_team_id",
        "away_team_id",
        "home_score",
        "away_score",
        "winner_team_id",
        "status",
    ]

    games = games[db_columns]

    # Remove duplicates (shouldn't be any after merge)
    games = games.drop_duplicates(subset=["game_id"])

    logger.info(f"Transformed {len(games)} games")
    return games


def load_games(df: pd.DataFrame) -> int:
    """Load games into DuckDB using upsert.

    Args:
        df: Transformed game data.

    Returns:
        Number of rows loaded.
    """
    logger.info("Loading games into database...")

    conn = get_db_connection()
    rows_loaded = 0

    try:
        for _, row in df.iterrows():
            conn.execute(
                """
                INSERT OR REPLACE INTO games (
                    game_id, season, season_type, game_date,
                    home_team_id, away_team_id, home_score, away_score,
                    winner_team_id, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                [
                    str(row.get("game_id")),
                    row.get("season"),
                    row.get("season_type"),
                    row.get("game_date"),
                    row.get("home_team_id"),
                    row.get("away_team_id"),
                    row.get("home_score"),
                    row.get("away_score"),
                    row.get("winner_team_id"),
                    row.get("status"),
                ],
            )
            rows_loaded += 1

        logger.info(f"Successfully loaded {rows_loaded} games")
        return rows_loaded

    except Exception as e:
        logger.error(f"Failed to load games: {e}")
        raise


def run_etl(season: str | None = None, season_type: str = "Regular Season") -> dict:
    """Run the complete games ETL pipeline.

    Args:
        season: Season string (e.g., '2024-25'). Uses current season if None.
        season_type: Type of season ('Regular Season' or 'Playoffs').

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
        df = extract_games(season, season_type)
        result["extracted"] = len(df)

        # Transform
        df = transform_games(df, season, season_type)

        # Load
        result["loaded"] = load_games(df)

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        logger.error(f"ETL failed: {e}")

    finally:
        close_db_connection()

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
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

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
