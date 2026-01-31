"""Team ID mapper for bridging different team naming conventions."""

from pathlib import Path
from typing import Any

from scripts.ingestion.logger import get_logger

from .manual_mappings import FRANCHISE_MAPPINGS, TEAM_ABBREV_HISTORY, TEAM_NAME_NORMALIZATIONS
from .utils import load_csv, safe_int, safe_str

logger = get_logger(__name__)


class TeamMapper:
    """Maps between team naming conventions."""

    def __init__(self, conn):
        self.conn = conn
        self.abbrev_cache = {}
        self.name_cache = {}
        self.team_data = {}
        self.abbrev_to_team_id = {}
        self.team_id_to_abbrev = {}
        self.team_id_to_name = {}
        self.seasonal_mappings = {}

    def build_mapping(
        self,
        team_histories_csv_path: Path,
        team_abbrev_csv_path: Path,
        team_totals_csv_path: Path | None = None,
    ) -> dict[str, Any]:
        """Build comprehensive team ID mapping.

        Args:
            team_histories_csv_path: Path to TeamHistories.csv
            team_abbrev_csv_path: Path to Team_Abbrev.csv
            team_totals_csv_path: Optional path to Team_Totals.csv

        Returns:
            Dictionary with mapping statistics
        """
        logger.info("Building team ID mapping...")

        team_abbrev_data = self._load_abbrev_csv(team_abbrev_csv_path)
        team_histories = self._load_histories_csv(team_histories_csv_path)

        logger.info(f"Loaded {len(team_abbrev_data)} team abbreviations")
        logger.info(f"Loaded {len(team_histories)} team history records")

        self._build_abbrev_mappings(team_abbrev_data)
        self._build_seasonal_mappings(team_histories)

        logger.info(f"Built mappings for {len(self.abbrev_to_team_id)} teams")
        logger.info(f"Built {len(self.seasonal_mappings)} seasonal mappings")

        return {
            "teams": len(self.abbrev_to_team_id),
            "seasonal_mappings": len(self.seasonal_mappings),
            "status": "ok",
        }

    def _build_abbrev_mappings(self, team_abbrev_data: list[dict]) -> None:
        """Build abbreviation to team_id mappings from abbrev data."""
        for record in team_abbrev_data:
            team_id = record.get("team_id")
            abbrev = safe_str(record.get("abbreviation")).upper()
            team_name = safe_str(record.get("team"))

            if not team_id or not abbrev:
                continue

            self.abbrev_to_team_id[abbrev] = team_id
            self.team_id_to_abbrev[team_id] = abbrev

            if team_name:
                self.team_id_to_name[team_id] = team_name
                normalized = self.normalize_team_name(team_name)
                if normalized:
                    self.name_cache[normalized] = team_id

    def _build_seasonal_mappings(self, team_histories: list[dict]) -> None:
        """Build seasonal mappings from team history data."""
        for record in team_histories:
            team_id = record.get("team_id")
            if not team_id:
                continue

            abbrev = safe_str(record.get("team_abbrev")).upper()
            team_city = safe_str(record.get("team_city"))
            team_name = safe_str(record.get("team_name"))
            season_start = safe_int(record.get("season_active_from"))
            season_end = safe_int(record.get("season_active_till"))

            # Store full team info
            self._store_team_info(team_id, abbrev, team_city, team_name, season_start, season_end)

            # Build seasonal abbreviation mappings
            if abbrev and season_start and season_end:
                for year in range(season_start, season_end + 1):
                    key = (abbrev, year)
                    self.seasonal_mappings[key] = team_id

    def _store_team_info(
        self,
        team_id: int,
        abbrev: str,
        city: str,
        name: str,
        season_start: int | None,
        season_end: int | None,
    ) -> None:
        """Store team information for lookups."""
        if team_id not in self.team_data:
            self.team_data[team_id] = {
                "team_id": team_id,
                "abbreviation": abbrev,
                "city": city,
                "name": name,
                "seasons": [],
            }

        if season_start and season_end:
            self.team_data[team_id]["seasons"].append({
                "start": season_start,
                "end": season_end,
                "abbreviation": abbrev,
                "city": city,
                "name": name,
            })

    def _load_abbrev_csv(self, csv_path: Path) -> list[dict]:
        """Load team abbreviations from CSV."""
        def parse_row(row: dict) -> dict | None:
            return {
                "team_id": safe_int(row.get("teamId")),
                "abbreviation": row.get("abbreviation", ""),
                "team": row.get("team", ""),
                "min_year": row.get("min_year", ""),
                "max_year": row.get("max_year", ""),
            }

        return load_csv(csv_path, parse_row, ["teamId", "abbreviation"])

    def _load_histories_csv(self, csv_path: Path) -> list[dict]:
        """Load team histories from CSV."""
        def parse_row(row: dict) -> dict | None:
            return {
                "team_id": safe_int(row.get("teamId")),
                "team_abbrev": row.get("team_abbrev", ""),
                "team_city": row.get("team_city", ""),
                "team_name": row.get("team_name", ""),
                "season_active_from": row.get("season_active_from", ""),
                "season_active_till": row.get("season_active_till", ""),
                "is_active": row.get("is_active", "FALSE").upper() == "TRUE",
            }

        return load_csv(csv_path, parse_row)

    def get_team_id(self, abbreviation: str, season: int | None = None) -> int | None:
        """Get teamId from abbreviation and season.

        Args:
            abbreviation: Team abbreviation
            season: Optional season year for historical lookups

        Returns:
            Team ID or None if not found
        """
        if not abbreviation:
            return None

        abbrev = abbreviation.strip().upper()

        # Try franchise mappings first (handles relocated teams)
        team_id = self._resolve_franchise_mapping(abbrev, season)
        if team_id:
            return team_id

        # Try seasonal mapping
        if season:
            key = (abbrev, season)
            if key in self.seasonal_mappings:
                return self.seasonal_mappings[key]

        # Try direct abbreviation mapping
        if abbrev in self.abbrev_to_team_id:
            return self.abbrev_to_team_id[abbrev]

        # Check abbreviation history
        team_id = self._resolve_abbrev_history(abbrev, season)
        if team_id:
            return team_id

        logger.debug(f"Could not resolve team abbreviation: {abbreviation} (season: {season})")
        return None

    def _resolve_franchise_mapping(self, abbrev: str, season: int | None) -> int | None:
        """Resolve team ID from franchise mappings for relocated teams."""
        if abbrev not in FRANCHISE_MAPPINGS:
            return None

        franchise_info = FRANCHISE_MAPPINGS[abbrev]

        if season:
            # Find the correct team for the season
            for entry in franchise_info:
                start_year = entry.get("start_year", 0)
                end_year = entry.get("end_year", 9999)
                if start_year <= season <= end_year:
                    return entry.get("team_id")
        else:
            # Return current/most recent team
            for entry in reversed(franchise_info):
                if team_id := entry.get("team_id"):
                    return team_id

        return None

    def _resolve_abbrev_history(self, abbrev: str, season: int | None) -> int | None:
        """Resolve team ID from abbreviation history."""
        if abbrev not in TEAM_ABBREV_HISTORY:
            return None

        history = TEAM_ABBREV_HISTORY[abbrev]

        if season:
            # Find the correct abbreviation for the season
            for entry in history:
                start_year = entry.get("start_year", 0)
                end_year = entry.get("end_year", 9999)
                if start_year <= season <= end_year:
                    if team_id := entry.get("team_id"):
                        return team_id
                    current_abbrev = entry.get("abbreviation", abbrev)
                    if current_abbrev in self.abbrev_to_team_id:
                        return self.abbrev_to_team_id[current_abbrev]
        else:
            # Use most recent mapping
            if history:
                current_abbrev = history[-1].get("abbreviation", abbrev)
                if current_abbrev in self.abbrev_to_team_id:
                    return self.abbrev_to_team_id[current_abbrev]

        return None

    def get_abbreviation(self, team_id: int, season: int | None = None) -> str | None:
        """Get abbreviation from teamId and season.

        Args:
            team_id: Team ID
            season: Optional season year for historical lookups

        Returns:
            Team abbreviation or None if not found
        """
        if not team_id:
            return None

        team_id_str = str(team_id)

        # Check if we have team data
        if team_id_str in self.team_data:
            team_info = self.team_data[team_id_str]

            # Find abbreviation for specific season
            if season:
                for season_info in team_info.get("seasons", []):
                    if season_info.get("start") <= season <= season_info.get("end"):
                        return season_info.get("abbreviation")

            # Return current abbreviation
            return team_info.get("abbreviation")

        # Check cache
        return self.team_id_to_abbrev.get(team_id)

    def get_full_name(self, team_id: int) -> str | None:
        """Get full team name from teamId.

        Args:
            team_id: Team ID

        Returns:
            Full team name (City + Name) or None if not found
        """
        if not team_id:
            return None

        team_id_str = str(team_id)

        # Check team data
        if team_id_str in self.team_data:
            team_info = self.team_data[team_id_str]
            city = team_info.get("city", "")
            name = team_info.get("name", "")
            if city and name:
                return f"{city} {name}"
            return city or name

        # Check cache
        return self.team_id_to_name.get(team_id)

    @staticmethod
    def normalize_team_name(name: str) -> str:
        """Normalize variations.

        Args:
            name: Team name to normalize

        Returns:
            Normalized team name
        """
        if not name:
            return ""
        normalized = TEAM_NAME_NORMALIZATIONS.get(name, name)
        return " ".join(normalized.split())
