"""Main ID resolution coordinator."""

from scripts.ingestion.config import PLANNING_CSV_DIR
from scripts.ingestion.logger import get_logger

from .mapping_validator import MappingValidator
from .player_mapper import PlayerMapper
from .team_mapper import TeamMapper

logger = get_logger(__name__)


class IDResolver:
    """Resolves all ID mappings during ingestion."""

    def __init__(self, conn):
        self.player_mapper = PlayerMapper(conn)
        self.team_mapper = TeamMapper(conn)
        self.mapping_validator = MappingValidator(conn)
        self.unresolved = {"players": [], "teams": []}
        self.conn = conn

    def build_all_mappings(self):
        """Build all ID mappings from planning data."""
        logger.info("Building all ID mappings...")

        # Build player mappings
        players_csv = PLANNING_CSV_DIR / "Players.csv"
        career_csv = PLANNING_CSV_DIR / "Player_Career_Info.csv"
        self.player_mapper.build_mapping(players_csv, career_csv)

        # Build team mappings
        team_histories_csv = PLANNING_CSV_DIR / "TeamHistories.csv"
        team_abbrev_csv = PLANNING_CSV_DIR / "Team_Abbrev.csv"
        team_totals_csv = PLANNING_CSV_DIR / "Team_Totals.csv"
        self.team_mapper.build_mapping(team_histories_csv, team_abbrev_csv, team_totals_csv)

        logger.info("All ID mappings built successfully")

    def resolve_player_id(self, identifier, id_type: str = "auto") -> str | None:
        """Resolve any player identifier to canonical player_id."""
        if identifier is None:
            return None

        # If already a string player_id, return it
        if isinstance(identifier, str) and not identifier.isdigit():
            return identifier

        # If numeric, try to map from person_id
        if isinstance(identifier, (int, str)):
            try:
                person_id = int(identifier)
                player_id = self.player_mapper.get_player_id(person_id)
                if player_id:
                    return player_id
                else:
                    if person_id not in self.unresolved["players"]:
                        self.unresolved["players"].append(person_id)
                        logger.warning(f"Unresolved player person_id: {person_id}")
            except ValueError:
                pass

        # Try as string
        if isinstance(identifier, str):
            # Try direct lookup
            result = self.player_mapper.get_person_id(identifier)
            if result:
                return identifier

        self.unresolved["players"].append(str(identifier))
        logger.warning(f"Could not resolve player identifier: {identifier}")
        return None

    def resolve_team_id(
        self, identifier, season: int | None = None, id_type: str = "auto"
    ) -> int | None:
        """Resolve any team identifier to canonical team_id."""
        if identifier is None:
            return None

        # If already numeric team_id
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            return int(identifier)

        # Try to resolve from abbreviation
        if isinstance(identifier, str):
            team_id = self.team_mapper.get_team_id(identifier, season)
            if team_id:
                return team_id

        self.unresolved["teams"].append({"identifier": identifier, "season": season})
        logger.warning(f"Could not resolve team identifier: {identifier}")
        return None

    def resolve_game_id(self, game_date: str, home_team_id: int, away_team_id: int) -> str | None:
        """Resolve game identifier or create if new."""
        try:
            # Try to find existing game
            result = self.conn.execute(
                """
                SELECT game_id FROM games 
                WHERE game_date = ? AND home_team_id = ? AND away_team_id = ?
            """,
                [game_date, home_team_id, away_team_id],
            ).fetchone()

            if result:
                return result[0]

            # Try with teams swapped
            result = self.conn.execute(
                """
                SELECT game_id FROM games 
                WHERE game_date = ? AND home_team_id = ? AND away_team_id = ?
            """,
                [game_date, away_team_id, home_team_id],
            ).fetchone()

            if result:
                return result[0]

            return None
        except Exception as e:
            logger.error(f"Error resolving game: {e}")
            return None

    def get_unresolved_count(self):
        """Get count of unresolved IDs."""
        return {
            "players": len(self.unresolved["players"]),
            "teams": len(self.unresolved["teams"]),
            "total": len(self.unresolved["players"]) + len(self.unresolved["teams"]),
        }

    def generate_unresolved_report(self) -> str:
        """Generate report of all unresolved IDs."""
        lines = ["=" * 60]
        lines.append("UNRESOLVED ID REPORT")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Unresolved Players: {len(self.unresolved['players'])}")
        for player_id in self.unresolved["players"][:10]:
            lines.append(f"  - {player_id}")
        if len(self.unresolved["players"]) > 10:
            lines.append(f"  ... and {len(self.unresolved['players']) - 10} more")
        lines.append("")
        lines.append(f"Unresolved Teams: {len(self.unresolved['teams'])}")
        for team_info in self.unresolved["teams"][:10]:
            lines.append(f"  - {team_info}")
        if len(self.unresolved["teams"]) > 10:
            lines.append(f"  ... and {len(self.unresolved['teams']) - 10} more")

        return "\n".join(lines)

    def persist_unresolved(self):
        """Persist unresolved IDs to database for later review."""
        try:
            # Create table if not exists
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS unresolved_ids (
                    id_type VARCHAR,
                    identifier VARCHAR,
                    season INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Clear existing
            self.conn.execute("DELETE FROM unresolved_ids")

            # Insert unresolved players
            for player_id in self.unresolved["players"]:
                self.conn.execute(
                    "INSERT INTO unresolved_ids (id_type, identifier) VALUES (?, ?)",
                    ["player", str(player_id)],
                )

            # Insert unresolved teams
            for team_info in self.unresolved["teams"]:
                identifier = (
                    team_info.get("identifier") if isinstance(team_info, dict) else str(team_info)
                )
                season = team_info.get("season") if isinstance(team_info, dict) else None
                self.conn.execute(
                    "INSERT INTO unresolved_ids (id_type, identifier, season) VALUES (?, ?, ?)",
                    ["team", str(identifier), season],
                )

            logger.info("Unresolved IDs persisted to database")
        except Exception as e:
            logger.error(f"Failed to persist unresolved IDs: {e}")

    def clear_unresolved(self):
        """Clear unresolved ID tracking."""
        self.unresolved = {"players": [], "teams": []}
        logger.info("Unresolved ID tracking cleared")

    def validate_mappings(self):
        """Run all mapping validations."""
        return self.mapping_validator.run_all_validations()
