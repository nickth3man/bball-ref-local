"""ETL script for extracting and loading NBA player data.

Usage:
    python scripts/etl_players.py
    python scripts/etl_players.py --active-only

Fetches NBA players from nba_api and upserts into DuckDB players table.
"""

import argparse
import logging
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nba_api.stats.endpoints import CommonAllPlayers

from app.services.database import close_db_connection, get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Rate limiting delay (seconds)
RATE_LIMIT_DELAY = 0.6


def parse_height(height_str: str | None) -> int | None:
    """Parse height string (e.g., '6-9') to inches.
    
    Args:
        height_str: Height in format "feet-inches".
        
    Returns:
        Height in inches or None if invalid.
    """
    if not height_str or height_str == "":
        return None
    
    try:
        parts = height_str.split("-")
        if len(parts) != 2:
            return None
        feet = int(parts[0])
        inches = int(parts[1])
        return feet * 12 + inches
    except (ValueError, AttributeError):
        return None


def parse_birth_date(date_str: str | None) -> date | None:
    """Parse birth date string to date object.
    
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
                return pd.to_datetime(date_str, format=fmt).date()
            except ValueError:
                continue
        # Fallback to pandas parser
        return pd.to_datetime(date_str).date()
    except (ValueError, TypeError):
        return None


def extract_players(active_only: bool = True) -> pd.DataFrame:
    """Extract player data from nba_api.
    
    Args:
        active_only: If True, fetch only active players.
        
    Returns:
        DataFrame with raw player data.
    """
    logger.info(f"Extracting {'active' if active_only else 'all'} players from nba_api...")
    
    # is_only_current_season=1 for active players, 0 for all
    is_only_current_season = 1 if active_only else 0
    
    endpoint = CommonAllPlayers(is_only_current_season=is_only_current_season)
    df = endpoint.get_data_frames()[0]
    
    logger.info(f"Extracted {len(df)} players")
    time.sleep(RATE_LIMIT_DELAY)
    
    return df


def transform_players(df: pd.DataFrame) -> pd.DataFrame:
    """Transform raw player data to match database schema.
    
    Args:
        df: Raw player data from nba_api.
        
    Returns:
        Transformed DataFrame matching Player model.
    """
    logger.info("Transforming player data...")
    
    # Convert column names to lowercase and clean up
    df.columns = df.columns.str.lower().str.strip()
    
    # Map nba_api fields to our schema
    # CommonAllPlayers columns: PERSON_ID, DISPLAY_FIRST_LAST, FIRST_NAME, LAST_NAME,
    # TEAM_ID, TEAM_NAME, TEAM_ABBREVIATION, TEAM_CODE, PLAYER_SLUG, ROSTERSTATUS,
    # FROM_YEAR, TO_YEAR, etc.
    column_mapping = {
        "person_id": "player_id",
        "team_id": "team_id",
    }
    
    df = df.rename(columns=column_mapping)
    
    # Extract first and last name from display name or separate fields
    if "display_first_last" in df.columns:
        df["first_name"] = df["display_first_last"].str.split(" ", n=1).str[0].fillna("")
        df["last_name"] = df["display_first_last"].str.split(" ", n=1).str[1].fillna("")
    elif "first_name" in df.columns and "last_name" in df.columns:
        df["first_name"] = df["first_name"].fillna("")
        df["last_name"] = df["last_name"].fillna("")
    
    # Map position (nba_api uses different position format)
    # Common positions: F, G, C, F-C, G-F, F-G, C-F
    position_map = {
        "PG": "PG",
        "SG": "SG",
        "SF": "SF",
        "PF": "PF",
        "C": "C",
        "G": "PG",  # Default to PG for guards
        "F": "SF",  # Default to SF for forwards
        "G-F": "SG",
        "F-G": "SF",
        "F-C": "PF",
        "C-F": "C",
        "C-G": "PG",
        "G-C": "C",
    }
    
    if "position" in df.columns:
        df["position"] = df["position"].map(position_map).fillna("PG")
    else:
        # Default position if not provided
        df["position"] = "PG"
    
    # Parse height if available
    if "height" in df.columns:
        df["height"] = df["height"].apply(parse_height)
    else:
        df["height"] = None
    
    # Parse weight if available
    if "weight" in df.columns:
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
        df["weight"] = df["weight"].where(df["weight"] > 0, None)
    else:
        df["weight"] = None
    
    # Parse birth date
    if "birth_date" in df.columns:
        df["birth_date"] = df["birth_date"].apply(parse_birth_date)
    else:
        df["birth_date"] = None
    
    # Clean country
    if "country" in df.columns:
        df["country"] = df["country"].replace("", None)
    else:
        df["country"] = None
    
    # Draft info (may not be in CommonAllPlayers)
    for col in ["draft_year", "draft_round", "draft_number"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].where(df[col] > 0, None)
        else:
            df[col] = None
    
    # Jersey number
    if "jersey" in df.columns:
        df["jersey_number"] = pd.to_numeric(df["jersey"], errors="coerce")
        df["jersey_number"] = df["jersey_number"].where(df["jersey_number"] >= 0, None)
    else:
        df["jersey_number"] = None
    
    # Ensure team_id is numeric
    df["team_id"] = pd.to_numeric(df["team_id"], errors="coerce").fillna(0).astype(int)
    
    # Select only columns that exist in our database schema
    db_columns = [
        "player_id", "first_name", "last_name", "team_id", "position",
        "jersey_number", "height", "weight", "birth_date", "country",
        "draft_year", "draft_round", "draft_number"
    ]
    
    # Ensure all required columns exist
    for col in db_columns:
        if col not in df.columns:
            df[col] = None
    
    df = df[db_columns]
    
    # Remove rows with missing player_id
    df = df.dropna(subset=["player_id"])
    df["player_id"] = df["player_id"].astype(int)
    
    logger.info(f"Transformed {len(df)} players")
    return df


def load_players(df: pd.DataFrame, batch_size: int = 500) -> int:
    """Load players into DuckDB using upsert with batching.
    
    Args:
        df: Transformed player data.
        batch_size: Number of records to insert per batch.
        
    Returns:
        Number of rows loaded.
    """
    logger.info("Loading players into database...")
    
    conn = get_db_connection()
    rows_loaded = 0
    
    try:
        # Prepare data as list of tuples for batch insert
        records = [
            (
                row.get("player_id"),
                row.get("first_name"),
                row.get("last_name"),
                row.get("team_id"),
                row.get("position"),
                row.get("jersey_number"),
                row.get("height"),
                row.get("weight"),
                row.get("birth_date"),
                row.get("country"),
                row.get("draft_year"),
                row.get("draft_round"),
                row.get("draft_number"),
            )
            for _, row in df.iterrows()
        ]
        
        # Process in batches for better performance
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            conn.executemany("""
                INSERT OR REPLACE INTO players (
                    player_id, first_name, last_name, team_id, position,
                    jersey_number, height, weight, birth_date, country,
                    draft_year, draft_round, draft_number, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, batch)
            rows_loaded += len(batch)
            logger.info(f"Loaded batch {i // batch_size + 1}/{(len(records) - 1) // batch_size + 1}")
        
        logger.info(f"Successfully loaded {rows_loaded} players")
        return rows_loaded
        
    except Exception:
        logger.exception("Failed to load players")
        raise


def run_etl(active_only: bool = True, batch_size: int = 500) -> dict:
    """Run the complete players ETL pipeline.
    
    Args:
        active_only: If True, process only active players.
        batch_size: Number of records to insert per batch.
        
    Returns:
        Dictionary with ETL results.
    """
    result = {"extracted": 0, "loaded": 0, "status": "success", "error": None}
    
    try:
        # Extract
        df = extract_players(active_only=active_only)
        result["extracted"] = len(df)
        
        # Transform
        df = transform_players(df)
        
        # Load
        result["loaded"] = load_players(df, batch_size)
        
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        logger.exception("ETL failed")
        
    finally:
        close_db_connection()
    
    return result


def main() -> int:
    """Main entry point for players ETL.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(description="ETL for NBA player data")
    parser.add_argument(
        "--all-players",
        action="store_true",
        help="Fetch all players including inactive (default: active players only)"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=500,
        help="Batch size for inserts (default: 500)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    active_only = not args.all_players
    
    logger.info("Starting players ETL...")
    result = run_etl(active_only=active_only, batch_size=args.batch_size)
    
    if result["status"] == "success":
        logger.info(
            f"Players ETL completed: {result['extracted']} extracted, "
            f"{result['loaded']} loaded"
        )
        return 0
    else:
        logger.error(f"Players ETL failed: {result['error']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
