"""Player ETL module for extracting and loading player data.

This module handles the extraction of player data from the NBA API,
transformation of the data to match our schema, and loading into DuckDB.
"""

from time import sleep

import pandas as pd
from nba_api.stats.endpoints import CommonAllPlayers

from app.services.database import close_db_connection, get_db_connection
from scripts.etl_utils import get_current_season
from scripts.ingestion.exceptions import APIError, DatabaseError, DataTransformationError, ETLError

# Configure logging
from scripts.logging_utils import setup_etl_logging
from scripts.retry_utils import retry_api_call

logger = setup_etl_logging(__name__)

# Rate limiting delay (seconds) between API calls
RATE_LIMIT_DELAY = 0.6


@retry_api_call(max_retries=3, initial_delay=0.6)
def extract_players(active_only: bool = True) -> pd.DataFrame:
    """Extract player data from NBA API.

    Args:
        active_only: If True, only fetch active players. If False, fetch all.

    Returns:
        DataFrame with raw player data from NBA API.
    """
    season = get_current_season()
    is_only_current_season = 1 if active_only else 0

    logger.info(f"Fetching {'active' if active_only else 'all'} players for season {season}...")

    players_data = CommonAllPlayers(season=season, is_only_current_season=is_only_current_season)
    df = players_data.get_data_frames()[0]

    logger.info(f"Extracted {len(df)} players from NBA API")
    sleep(RATE_LIMIT_DELAY)  # Rate limiting
    return df


def parse_height(height_str: str | None) -> str | None:
    """Parse height string from NBA API format (e.g., '6-9') to standard format.

    Args:
        height_str: Height string from NBA API (e.g., '6-9').

    Returns:
        Parsed height string or None if input is invalid.
    """
    if not height_str or height_str == "":
        return None
    return height_str


def parse_birth_date(date_str: str | None) -> str | None:
    """Parse birth date from various formats to ISO format.

    Args:
        date_str: Date string in various formats.

    Returns:
        ISO formatted date string (YYYY-MM-DD) or None if parsing fails.
    """
    if not date_str or pd.isna(date_str) or date_str == "":
        return None

    try:
        # Try common date formats
        for fmt in ["%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y"]:
            try:
                parsed = pd.to_datetime(date_str, format=fmt)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # Fallback to pandas auto-parsing
        parsed = pd.to_datetime(date_str, errors="coerce")
        if pd.notna(parsed):
            return parsed.strftime("%Y-%m-%d")

        return None
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to parse birth date '{date_str}': {e}")
        return None


def transform_players(df: pd.DataFrame) -> pd.DataFrame:
    """Transform raw player data to match database schema.

    Args:
        df: Raw player DataFrame from NBA API.

    Returns:
        Transformed DataFrame matching database schema.
    """
    if df.empty:
        logger.warning("Empty player data received, returning empty DataFrame")
        return pd.DataFrame(
            columns=[
                "player_id",
                "first_name",
                "last_name",
                "team_id",
                "position",
                "jersey_number",
                "height",
                "weight",
                "birth_date",
                "country",
                "draft_year",
                "draft_round",
                "draft_number",
            ]
        )

    logger.info(f"Transforming {len(df)} player records...")

    # NBA API CommonAllPlayers returns: PERSON_ID, DISPLAY_FIRST_LAST, FIRST_NAME, LAST_NAME,
    # TEAM_ID, TEAM_NAME, TEAM_ABBREVIATION, JERSEY, POSITION, HEIGHT, WEIGHT, BIRTH_DATE, etc.

    transformed = pd.DataFrame()

    # Map NBA API fields to our schema
    transformed["player_id"] = df["PERSON_ID"].astype(str)
    transformed["first_name"] = df["FIRST_NAME"]
    transformed["last_name"] = df["LAST_NAME"]

    # Team ID (may be 0 for free agents)
    transformed["team_id"] = df["TEAM_ID"].astype(str)

    # Position
    transformed["position"] = df["POSITION"]

    # Jersey number
    transformed["jersey"] = df["JERSEY"]

    # Height
    transformed["height"] = df["HEIGHT"].apply(parse_height)

    # Weight
    transformed["weight"] = df["WEIGHT"]

    # Birth date
    transformed["birth_date"] = df["BIRTH_DATE"]

    # Country
    transformed["country"] = df["COUNTRY"]

    # Draft info
    transformed["draft_year"] = df.get("DRAFT_YEAR", pd.NA)
    transformed["draft_round"] = df.get("DRAFT_ROUND", pd.NA)
    transformed["draft_number"] = df.get("DRAFT_NUMBER", pd.NA)

    # Data type conversions and cleaning
    transformed["team_id"] = transformed["team_id"].replace("0", pd.NA)

    # Parse weight if available
    if "weight" in transformed.columns:
        transformed["weight"] = pd.to_numeric(transformed["weight"], errors="coerce")
        transformed.loc[transformed["weight"] <= 0, "weight"] = pd.NA
    else:
        transformed["weight"] = pd.NA

    # Parse birth date
    if "birth_date" in transformed.columns:
        transformed["birth_date"] = transformed["birth_date"].apply(parse_birth_date)
    else:
        transformed["birth_date"] = pd.NaT

    # Clean country
    if "country" in transformed.columns:
        transformed["country"] = transformed["country"].replace("", pd.NA)
    else:
        transformed["country"] = pd.NA

    # Draft info (may not be in CommonAllPlayers)
    for col in ["draft_year", "draft_round", "draft_number"]:
        if col in transformed.columns:
            transformed[col] = pd.to_numeric(transformed[col], errors="coerce")
            transformed.loc[transformed[col] <= 0, col] = pd.NA
        else:
            transformed[col] = pd.NA

    # Jersey number
    if "jersey" in transformed.columns:
        transformed["jersey_number"] = pd.to_numeric(transformed["jersey"], errors="coerce")
        transformed.loc[transformed["jersey_number"] < 0, "jersey_number"] = pd.NA
    else:
        transformed["jersey_number"] = pd.NA

    # Ensure team_id is numeric
    transformed["team_id"] = (
        pd.to_numeric(transformed["team_id"], errors="coerce").fillna(0).astype(int)
    )

    # Select only columns that exist in our database schema
    db_columns = [
        "player_id",
        "first_name",
        "last_name",
        "team_id",
        "position",
        "jersey_number",
        "height",
        "weight",
        "birth_date",
        "country",
        "draft_year",
        "draft_round",
        "draft_number",
    ]

    transformed = transformed[[col for col in db_columns if col in transformed.columns]]

    logger.info(f"Successfully transformed {len(transformed)} player records")
    return transformed


def load_players(df: pd.DataFrame) -> int:
    """Load transformed player data into DuckDB.

    Args:
        df: Transformed player DataFrame.

    Returns:
        Number of records loaded.
    """
    if df.empty:
        logger.warning("No player data to load")
        return 0

    conn = get_db_connection()

    try:
        # Truncate and load pattern for player reference data
        conn.execute("DELETE FROM players")

        # Batch insert for better performance using itertuples (faster than iterrows)
        # Handle NaN values by converting to None
        data = [
            (
                row.player_id,
                row.first_name,
                row.last_name,
                row.team_id,
                row.position,
                None if pd.isna(row.jersey_number) else row.jersey_number,
                row.height,
                None if pd.isna(row.weight) else row.weight,
                row.birth_date,
                row.country,
                None if pd.isna(row.draft_year) else row.draft_year,
                None if pd.isna(row.draft_round) else row.draft_round,
                None if pd.isna(row.draft_number) else row.draft_number,
            )
            for row in df.itertuples(index=False)
        ]

        conn.executemany(
            """
            INSERT INTO players (
                player_id, first_name, last_name, team_id, position,
                jersey_number, height, weight, birth_date, country,
                draft_year, draft_round, draft_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            data,
        )

        conn.commit()
        logger.info(f"Loaded {len(df)} players into database")
        return len(df)

    except Exception as e:
        logger.error(f"Error loading players: {e}")
        conn.rollback()
        raise DatabaseError(
            "Failed to load players into database",
            operation="load_players",
            original_error=e,
        ) from e

    finally:
        close_db_connection()


def run_etl(active_only: bool = True) -> dict:
    """Run the complete player ETL pipeline.

    Args:
        active_only: If True, only process active players.

    Returns:
        Dictionary with ETL results.
    """
    start_time = pd.Timestamp.now()
    result = {"status": "success", "extracted": 0, "loaded": 0, "error": None}

    try:
        # Extract
        raw_df = extract_players(active_only)
        result["extracted"] = len(raw_df)

        # Transform
        transformed_df = transform_players(raw_df)

        # Load
        loaded_count = load_players(transformed_df)
        result["loaded"] = loaded_count

        duration = (pd.Timestamp.now() - start_time).total_seconds()
        logger.info(f"Player ETL completed in {duration:.2f} seconds")

    except APIError as e:
        result["status"] = "failed"
        result["error"] = f"API error during extraction: {e}"
        logger.error(f"Player ETL API error: {e}")
    except DatabaseError as e:
        result["status"] = "failed"
        result["error"] = f"Database error during loading: {e}"
        logger.error(f"Player ETL database error: {e}")
    except DataTransformationError as e:
        result["status"] = "failed"
        result["error"] = f"Data transformation error: {e}"
        logger.error(f"Player ETL transformation error: {e}")
    except ETLError as e:
        result["status"] = "failed"
        result["error"] = f"ETL error: {e}"
        logger.error(f"Player ETL error: {e}")
    except (ValueError, TypeError) as e:
        result["status"] = "failed"
        result["error"] = f"Data validation error: {e}"
        logger.error(f"Player ETL validation error: {e}")

    return result


if __name__ == "__main__":
    # Run the ETL when script is executed directly
    result = run_etl(active_only=True)
    print(f"ETL Result: {result}")
