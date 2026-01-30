"""ETL script for extracting and loading NBA team data.

Usage:
    python scripts/etl_teams.py

Fetches all NBA teams from nba_api and upserts into DuckDB teams table.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nba_api.stats.static.teams import get_teams

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


def extract_teams() -> pd.DataFrame:
    """Extract team data from nba_api.
    
    Returns:
        DataFrame with raw team data.
    """
    logger.info("Extracting team data from nba_api...")
    
    teams = get_teams()
    df = pd.DataFrame(teams)
    
    logger.info(f"Extracted {len(df)} teams")
    time.sleep(RATE_LIMIT_DELAY)
    
    return df


def transform_teams(df: pd.DataFrame) -> pd.DataFrame:
    """Transform raw team data to match database schema.
    
    Args:
        df: Raw team data from nba_api.
        
    Returns:
        Transformed DataFrame matching Team model.
    """
    logger.info("Transforming team data...")
    
    # Map nba_api fields to our schema
    # Note: nba_api static teams provides: id, full_name, abbreviation, nickname, city, state, year_founded
    column_mapping = {
        "id": "team_id",
        "full_name": "full_name",
        "abbreviation": "abbreviation",
        "nickname": "nickname",
        "city": "city",
        "state": "state",
        "year_founded": "year_founded",
    }
    
    df = df.rename(columns=column_mapping)
    
    # Ensure required columns exist with defaults for missing data
    required_columns = [
        "team_id", "full_name", "abbreviation", "nickname", 
        "city", "conference", "division"
    ]
    
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    
    # Set default values for fields not provided by static API
    df["arena"] = df.get("arena", None)
    df["owner"] = df.get("owner", None)
    df["general_manager"] = df.get("general_manager", None)
    df["head_coach"] = df.get("head_coach", None)
    
    # Map conferences and divisions based on team IDs (NBA team IDs are stable)
    conference_map = {
        # Eastern Conference
        1610612738: "Eastern",  # Celtics
        1610612751: "Eastern",  # Nets
        1610612752: "Eastern",  # Knicks
        1610612755: "Eastern",  # 76ers
        1610612761: "Eastern",  # Raptors
        1610612741: "Eastern",  # Bulls
        1610612739: "Eastern",  # Cavaliers
        1610612765: "Eastern",  # Pistons
        1610612754: "Eastern",  # Pacers
        1610612749: "Eastern",  # Bucks
        1610612737: "Eastern",  # Hawks
        1610612766: "Eastern",  # Hornets
        1610612748: "Eastern",  # Heat
        1610612753: "Eastern",  # Magic
        1610612764: "Eastern",  # Wizards
        # Western Conference
        1610612743: "Western",  # Nuggets
        1610612750: "Western",  # Timberwolves
        1610612760: "Western",  # Thunder
        1610612757: "Western",  # Trail Blazers
        1610612762: "Western",  # Jazz
        1610612744: "Western",  # Warriors
        1610612746: "Western",  # Clippers
        1610612747: "Western",  # Lakers
        1610612756: "Western",  # Suns
        1610612758: "Western",  # Kings
        1610612742: "Western",  # Mavericks
        1610612745: "Western",  # Rockets
        1610612763: "Western",  # Grizzlies
        1610612740: "Western",  # Pelicans
        1610612759: "Western",  # Spurs
    }
    
    division_map = {
        # Atlantic
        1610612738: "Atlantic", 1610612751: "Atlantic", 1610612752: "Atlantic",
        1610612755: "Atlantic", 1610612761: "Atlantic",
        # Central
        1610612741: "Central", 1610612739: "Central", 1610612765: "Central",
        1610612754: "Central", 1610612749: "Central",
        # Southeast
        1610612737: "Southeast", 1610612766: "Southeast", 1610612748: "Southeast",
        1610612753: "Southeast", 1610612764: "Southeast",
        # Northwest
        1610612743: "Northwest", 1610612750: "Northwest", 1610612760: "Northwest",
        1610612757: "Northwest", 1610612762: "Northwest",
        # Pacific
        1610612744: "Pacific", 1610612746: "Pacific", 1610612747: "Pacific",
        1610612756: "Pacific", 1610612758: "Pacific",
        # Southwest
        1610612742: "Southwest", 1610612745: "Southwest", 1610612763: "Southwest",
        1610612740: "Southwest", 1610612759: "Southwest",
    }
    
    df["conference"] = df["team_id"].map(conference_map).fillna("Eastern")
    df["division"] = df["team_id"].map(division_map).fillna("Atlantic")
    
    # Select only columns that exist in our database schema
    db_columns = [
        "team_id", "full_name", "abbreviation", "nickname", "city",
        "state", "year_founded", "arena", "owner", "general_manager",
        "head_coach", "conference", "division"
    ]
    
    df = df[[col for col in db_columns if col in df.columns]]
    
    logger.info(f"Transformed {len(df)} teams")
    return df


def load_teams(df: pd.DataFrame) -> int:
    """Load teams into DuckDB using batch upsert.
    
    Args:
        df: Transformed team data.
        
    Returns:
        Number of rows loaded.
    """
    logger.info("Loading teams into database...")
    
    conn = get_db_connection()
    
    try:
        # Use to_numpy() for better performance and executemany for batch insert
        # This handles column names more reliably than itertuples
        data = [
            (
                row["team_id"],
                row["full_name"],
                row["abbreviation"],
                row["nickname"],
                row["city"],
                row["state"],
                row["year_founded"],
                row.get("arena"),
                row.get("owner"),
                row.get("general_manager"),
                row.get("head_coach"),
                row["conference"],
                row["division"],
            )
            for _, row in df.iterrows()
        ]
        
        if not data:
            logger.info("No teams to load")
            return 0
        
        conn.executemany("""
            INSERT OR REPLACE INTO teams (
                team_id, full_name, abbreviation, nickname, city,
                state, year_founded, arena, owner, general_manager,
                head_coach, conference, division, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, data)
        
        rows_loaded = len(data)
        logger.info(f"Successfully loaded {rows_loaded} teams")
        return rows_loaded
        
    except Exception as e:
        logger.error(f"Failed to load teams: {e}")
        raise


def run_etl() -> dict:
    """Run the complete teams ETL pipeline.
    
    Returns:
        Dictionary with ETL results.
    """
    result = {"extracted": 0, "loaded": 0, "status": "success", "error": None}
    
    try:
        # Extract
        df = extract_teams()
        result["extracted"] = len(df)
        
        # Transform
        df = transform_teams(df)
        
        # Load
        result["loaded"] = load_teams(df)
        
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        logger.error(f"ETL failed: {e}")
        
    finally:
        close_db_connection()
    
    return result


def main() -> int:
    """Main entry point for teams ETL.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(description="ETL for NBA team data")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting teams ETL...")
    result = run_etl()
    
    if result["status"] == "success":
        logger.info(
            f"Teams ETL completed: {result['extracted']} extracted, "
            f"{result['loaded']} loaded"
        )
        return 0
    else:
        logger.error(f"Teams ETL failed: {result['error']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
