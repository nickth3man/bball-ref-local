"""Team ID mapper for bridging different team naming conventions."""

import csv
from pathlib import Path

from scripts.ingestion.logger import get_logger

from .manual_mappings import FRANCHISE_MAPPINGS, TEAM_ABBREV_HISTORY, TEAM_NAME_NORMALIZATIONS

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
    ):
        """Build comprehensive team ID mapping."""
        logger.info("Building team ID mapping...")

        # Load team data
        team_abbrev_data = self._load_abbrev_csv(team_abbrev_csv_path)
        team_histories = self._load_histories_csv(team_histories_csv_path)

        logger.info(f"Loaded {len(team_abbrev_data)} team abbreviations")
        logger.info(f"Loaded {len(team_histories)} team history records")

        # Build abbreviation to team_id mapping
        for record in team_abbrev_data:
            team_id = record.get("team_id")
            abbrev = record.get("abbreviation", "").strip().upper()
            team_name = record.get("team", "").strip()

            if team_id and abbrev:
                self.abbrev_to_team_id[abbrev] = team_id
                self.team_id_to_abbrev[team_id] = abbrev

            if team_id and team_name:
                self.team_id_to_name[team_id] = team_name
                normalized = self.normalize_team_name(team_name)
                if normalized:
                    self.name_cache[normalized] = team_id

        # Build seasonal mappings from team histories
        for record in team_histories:
            team_id = record.get("team_id")
            abbrev = record.get("team_abbrev", "").strip().upper()
            team_city = record.get("team_city", "").strip()
            team_name = record.get("team_name", "").strip()
            season_active_from = record.get("season_active_from")
            season_active_till = record.get("season_active_till")

            if not team_id:
                continue

            # Store full team info
            if team_id not in self.team_data:
                self.team_data[team_id] = {
                    "team_id": team_id,
                    "abbreviation": abbrev,
                    "city": team_city,
                    "name": team_name,
                    "seasons": [],
                }

            # Add seasonal info
            if season_active_from and season_active_till:
                try:
                    start_year = int(season_active_from)
                    end_year = int(season_active_till)
                    self.team_data[team_id]["seasons"].append(
                        {
                            "start": start_year,
                            "end": end_year,
                            "abbreviation": abbrev,
                            "city": team_city,
                            "name": team_name,
                        }
                    )
                except (ValueError, TypeError):
                    pass

        # Build abbreviation seasonal mappings
        for team_id, data in self.team_data.items():
            for season_info in data.get("seasons", []):
                abbrev = season_info.get("abbreviation", "").strip().upper()
                if abbrev and season_info.get("start") and season_info.get("end"):
                    for year in range(season_info["start"], season_info["end"] + 1):
                        key = (abbrev, year)
                        self.seasonal_mappings[key] = team_id

        logger.info(f"Built mappings for {len(self.abbrev_to_team_id)} teams")
        logger.info(f"Built {len(self.seasonal_mappings)} seasonal mappings")

        return {
            "teams": len(self.abbrev_to_team_id),
            "seasonal_mappings": len(self.seasonal_mappings),
            "status": "ok",
        }

    def _load_abbrev_csv(self, csv_path: Path) -> list:
        """Load team abbreviations from CSV."""
        teams = []
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        teams.append(
                            {
                                "team_id": int(row.get("teamId", 0)),
                                "abbreviation": row.get("abbreviation", ""),
                                "team": row.get("team", ""),
                                "min_year": row.get("min_year", ""),
                                "max_year": row.get("max_year", ""),
                            }
                        )
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Error parsing team abbrev row: {e}")
        except FileNotFoundError:
            logger.error(f"Team abbrev CSV not found: {csv_path}")
        return teams

    def _load_histories_csv(self, csv_path: Path) -> list:
        """Load team histories from CSV."""
        histories = []
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    histories.append(
                        {
                            "team_id": row.get("teamId"),
                            "team_abbrev": row.get("team_abbrev", ""),
                            "team_city": row.get("team_city", ""),
                            "team_name": row.get("team_name", ""),
                            "season_active_from": row.get("season_active_from", ""),
                            "season_active_till": row.get("season_active_till", ""),
                            "is_active": row.get("is_active", "FALSE").upper() == "TRUE",
                        }
                    )
        except FileNotFoundError:
            logger.error(f"Team histories CSV not found: {csv_path}")
        return histories

    def get_team_id(self, abbreviation: str, season: int | None = None) -> int | None:
        """Get teamId from abbreviation and season."""
        if not abbreviation:
            return None

        abbrev = abbreviation.strip().upper()

        # Normalize the abbreviation
        normalized_abbrev = self._normalize_abbreviation(abbrev)

        # Check franchise mappings for historical teams
        if normalized_abbrev in FRANCHISE_MAPPINGS:
            franchise_info = FRANCHISE_MAPPINGS[normalized_abbrev]
            if season:
                # Find the correct team for the season
                for entry in franchise_info:
                    start_year = entry.get("start_year", 0)
                    end_year = entry.get("end_year", 9999)
                    if start_year <= season <= end_year:
                        team_id = entry.get("team_id")
                        if team_id:
                            return team_id
                        break
            else:
                # Return current/most recent team
                for entry in reversed(franchise_info):
                    team_id = entry.get("team_id")
                    if team_id:
                        return team_id

        # Try seasonal mapping
        if season:
            key = (normalized_abbrev, season)
            if key in self.seasonal_mappings:
                return self.seasonal_mappings[key]

        # Try direct abbreviation mapping
        if normalized_abbrev in self.abbrev_to_team_id:
            return self.abbrev_to_team_id[normalized_abbrev]

        # Check abbreviation history
        if normalized_abbrev in TEAM_ABBREV_HISTORY:
            history = TEAM_ABBREV_HISTORY[normalized_abbrev]
            if season:
                # Find the correct abbreviation for the season
                for entry in history:
                    start_year = entry.get("start_year", 0)
                    end_year = entry.get("end_year", 9999)
                    if start_year <= season <= end_year:
                        team_id = entry.get("team_id")
                        if team_id:
                            return team_id
                        # Get current abbreviation for this period
                        current_abbrev = entry.get("abbreviation", normalized_abbrev)
                        if current_abbrev in self.abbrev_to_team_id:
                            return self.abbrev_to_team_id[current_abbrev]
            else:
                # Use most recent mapping
                current_abbrev = (
                    history[-1].get("abbreviation", normalized_abbrev)
                    if history
                    else normalized_abbrev
                )
                if current_abbrev in self.abbrev_to_team_id:
                    return self.abbrev_to_team_id[current_abbrev]

        logger.debug(f"Could not resolve team abbreviation: {abbreviation} (season: {season})")
        return None

    def get_abbreviation(self, team_id: int, season: int | None = None) -> str | None:
        """Get abbreviation from teamId and season."""
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
        if team_id in self.team_id_to_abbrev:
            return self.team_id_to_abbrev[team_id]

        return None

    def get_full_name(self, team_id: int) -> str | None:
        """Get full team name from teamId."""
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
        if team_id in self.team_id_to_name:
            return self.team_id_to_name[team_id]

        return None

    def normalize_team_name(self, name: str) -> str:
        """Normalize variations."""
        if not name:
            return ""
        normalized = TEAM_NAME_NORMALIZATIONS.get(name, name)
        return " ".join(normalized.split())

    def _normalize_abbreviation(self, abbrev: str) -> str:
        """Normalize team abbreviation."""
        if not abbrev:
            return ""
        return abbrev.strip().upper()
