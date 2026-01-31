"""Player ETL module for extracting and loading player data.

This module handles the extraction of player data from the NBA API,
transformation of the data to match our schema, and loading into DuckDB.
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

from nba_api.stats.endpoints import CommonAllPlayers

from app.config import settings
from app.services.database import get_db_connection
from scripts.etl_base import BaseETL
from scripts.etl_utils import get_current_season
from scripts.ingestion.exceptions import DatabaseError
from scripts.logging_utils import enable_verbose_logging, setup_etl_logging
from scripts.retry_utils import retry_api_call

logger = setup_etl_logging(__name__)


# TODO: LOW - Use parse_height() helper function
# This function is defined but never called because height data isn't fetched
# Once player bio data is populated (see TODO in transform method), use this
# to convert "6-6" format to centimeters for the height_cm database column
def parse_height(height_str: str | None) -> tuple[str | None, int | None]:
    """Parse height string (e.g., '6-6') to string and cm.

    Args:
        height_str: Height string in feet-inches format.

    Returns:
        Tuple of (height_str, height_cm).
    """
    if not height_str:
        return None, None

    try:
        feet, inches = map(int, height_str.split("-"))
        total_inches = feet * 12 + inches
        height_cm = int(total_inches * 2.54)
        return height_str, height_cm
    except (ValueError, AttributeError):
        return None, None


# TODO: LOW - Use parse_birth_date() helper function
# This function is defined but never called because birth_date isn't fetched
# Once player bio data is populated (see TODO in transform method), use this
# to convert various date formats to Python date objects
def parse_birth_date(date_str: str | None) -> date | None:
    """Parse birth date string.

    Args:
        date_str: Date string (e.g., 'OCT 04, 1988' or ISO format).

    Returns:
        Date object or None.
    """
    if not date_str:
        return None

    # Common formats returned by API
    formats = [
        "%b %d, %Y",  # OCT 04, 1988
        "%Y-%m-%d",  # ISO
        "%Y-%m-%dT%H:%M:%S",  # ISO with time
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    try:
        # Fallback to pandas
        return pd.to_datetime(date_str).date()
    except Exception:
        return None


class PlayersETL(BaseETL):
    """ETL process for NBA players."""

    def __init__(self):
        super().__init__("players_etl")

    @retry_api_call(max_retries=3, initial_delay=0.6)
    def extract(self, active_only: bool = True) -> pd.DataFrame:
        """Extract player data from NBA API.

        Args:
            active_only: If True, only fetch active players. If False, fetch all.

        Returns:
            DataFrame with raw player data from NBA API.
        """
        season = get_current_season()
        is_only_current_season = 1 if active_only else 0

        logger.info(f"Fetching {'active' if active_only else 'all'} players for season {season}...")

        # CommonAllPlayers endpoint
        # IsOnlyCurrentSeason: 1 for active players, 0 for all players
        player_info = CommonAllPlayers(is_only_current_season=is_only_current_season, season=season)

        df = player_info.get_data_frames()[0]

        logger.info(f"Extracted {len(df)} players")
        self._apply_rate_limit()

        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform raw player data to match database schema.

        Args:
            df: Raw player data from NBA API.

        Returns:
            Transformed DataFrame matching Player model.
        """
        logger.info("Transforming player data...")

        # Rename columns to match schema
        column_mapping = {
            "PERSON_ID": "player_id",
            "DISPLAY_FIRST_LAST": "full_name",
            "DISPLAY_LAST_COMMA_FIRST": "last_comma_first",
            "FROM_YEAR": "draft_year",  # Approximate, actually career start
            "TEAM_ID": "team_id",
            "TEAM_CITY": "team_city",
            "TEAM_NAME": "team_name",
            "TEAM_ABBREVIATION": "team_abbreviation",
            "GAMES_PLAYED_FLAG": "active",
        }

        df = df.rename(columns=column_mapping)

        # Basic transformations
        df["player_id"] = df["player_id"].astype(str)
        df["team_id"] = df["team_id"].astype(str)

        # Handle team_id '0' (free agents / retired)
        df.loc[df["team_id"] == "0", "team_id"] = None

        # Split full name into first/last (approximation)
        # Note: API doesn't provide clean separate fields in this endpoint
        if "full_name" in df.columns:
            name_parts = df["full_name"].str.split(" ", n=1, expand=True)
            df["first_name"] = name_parts[0]
            df["last_name"] = name_parts[1] if name_parts.shape[1] > 1 else ""

        # Parse active status (Y/N -> True/False)
        if "active" in df.columns:
            df["active"] = df["active"] == "Y"

        # TODO: HIGH - Populate player bio fields from NBA API
        # Current implementation: All bio fields are NULL/placeholder
        # Issue: CommonAllPlayers endpoint doesn't include detailed bio information
        #
        # Missing Fields (all currently NULL):
        #   Physical: position, jersey_number, height, height_cm, weight, weight_kg
        #   Birth: birth_date, birth_place, birth_country, country
        #   Draft: draft_round, draft_number, draft_team_id
        #   Other: college, shoots, hall_of_fame
        #
        # Potential Solutions:
        #   1. Fetch CommonPlayerInfo endpoint for each player (expensive - 5000+ API calls)
        #   2. Use Basketball Reference CSV data via ingestion framework (recommended)
        #   3. Fetch active roster only from CommonTeamRoster endpoint (limited data)
        #
        # Related Code:
        #   - Helper functions parse_height() and parse_birth_date() defined but unused
        #   - Database schema has all columns ready in app/services/database.py
        #   - Player model expects these fields in app/models/player.py
        #
        # Priority: HIGH - Required for complete player profiles
        # Add missing fields that aren't in CommonAllPlayers
        # For a full implementation, we'd need to fetch CommonPlayerInfo for each player
        # but that would be too many API calls. We'll use placeholders.
        missing_cols = [
            "position",
            "jersey_number",
            "height",
            "height_cm",
            "weight",
            "weight_kg",
            "birth_date",
            "birth_place",
            "birth_country",
            "country",
            "college",
            "draft_round",
            "draft_number",
            "draft_team_id",
            "shoots",
            "hall_of_fame",
        ]

        for col in missing_cols:
            if col not in df.columns:
                df[col] = None

        # Ensure correct types
        numeric_cols = ["draft_year", "jersey_number", "height_cm", "weight", "weight_kg"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        logger.info(f"Transformed {len(df)} players")
        return df

    def load(self, df: pd.DataFrame) -> int:
        """Load players into DuckDB.

        Args:
            df: Transformed player data.

        Returns:
            Number of players loaded.
        """
        logger.info("Loading players into database...")

        conn = get_db_connection()

        try:
            # Handle NaN values for SQL insertion
            # Replace NaN in numeric columns with None
            df = df.where(pd.notnull(df), None)

            data = [
                (
                    row.player_id,
                    row.first_name,
                    row.last_name,
                    row.full_name,
                    row.team_id,
                    row.position,
                    row.jersey_number,
                    row.height,
                    row.height_cm,
                    row.weight,
                    row.weight_kg,
                    row.birth_date,
                    row.birth_place,
                    row.birth_country,
                    row.country,
                    row.college,
                    row.draft_year,
                    row.draft_round,
                    row.draft_number,
                    row.draft_team_id,
                    row.shoots,
                    row.active,
                    row.hall_of_fame,
                )
                for row in df.itertuples(index=False)
            ]

            if not data:
                logger.info("No players to load")
                return 0

            # Batch insert
            batch_size = settings.insert_batch_size
            total_loaded = 0

            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO players (
                        player_id, first_name, last_name, full_name, team_id,
                        position, jersey_number, height, height_cm, weight, weight_kg,
                        birth_date, birth_place, birth_country, country, college,
                        draft_year, draft_round, draft_number, draft_team_id,
                        shoots, active, hall_of_fame, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                    )
                """,
                    batch,
                )
                total_loaded += len(batch)
                logger.info(f"Loaded {total_loaded}/{len(data)} players")

            logger.info(f"Successfully loaded {total_loaded} players")
            return total_loaded

        except Exception as e:
            logger.error(f"Failed to load players: {e}")
            raise DatabaseError(
                "Failed to load players into database",
                operation="load_players",
                original_error=e,
            ) from e


def run_etl(active_only: bool = True) -> dict[str, Any]:
    """Run the complete players ETL pipeline.

    Args:
        active_only: If True, only fetch active players.

    Returns:
        Dictionary with ETL results.
    """
    etl = PlayersETL()
    return etl.run(active_only=active_only)


def main() -> int:
    """Main entry point for players ETL.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(description="ETL for NBA player data")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all players (including inactive/retired)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        enable_verbose_logging()

    active_only = not args.all

    logger.info(f"Starting players ETL (active_only={active_only})...")
    result = run_etl(active_only=active_only)

    if result["status"] == "success":
        logger.info(
            f"Players ETL completed: {result['extracted']} players extracted, "
            f"{result['loaded']} loaded"
        )
        return 0
    else:
        logger.error(f"Players ETL failed: {result['error']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
