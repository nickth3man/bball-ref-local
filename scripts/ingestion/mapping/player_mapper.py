"""Player ID mapper for bridging personId and player_id systems."""

from pathlib import Path

from scripts.ingestion.logger import get_logger

from .fuzzy_matcher import FuzzyMatcher
from .manual_mappings import CONFIDENCE_THRESHOLDS, MANUAL_PLAYER_MAPPINGS
from .utils import load_csv, normalize_name

logger = get_logger(__name__)


class PlayerMapper:
    """Maps between personId (numeric) and player_id (string)."""

    def __init__(self, conn):
        self.conn = conn
        self.mapping_cache = {}
        self.reverse_cache = {}
        self.unmatched = []
        self.fuzzy_matcher = FuzzyMatcher(
            threshold=CONFIDENCE_THRESHOLDS["fuzzy_name_match_medium"]
        )
        self.player_data = {}

    def build_mapping(
        self, players_csv_path: Path, career_info_csv_path: Path
    ) -> dict[str, int]:
        """Build mapping table from Players.csv and Player_Career_Info.csv.

        Args:
            players_csv_path: Path to Players.csv
            career_info_csv_path: Path to Player_Career_Info.csv

        Returns:
            Dictionary with mapping statistics
        """
        logger.info("Building player ID mapping...")

        players_data = self._load_players_csv(players_csv_path)
        career_data = self._load_career_info_csv(career_info_csv_path)

        logger.info(f"Loaded {len(players_data)} players from Players.csv")
        logger.info(f"Loaded {len(career_data)} players from Player_Career_Info.csv")

        # Build name-based index for fuzzy matching
        name_to_career = self._build_name_index(career_data)

        # Match players from both sources
        matched_count, manual_mapped_count = self._match_players(
            players_data, name_to_career
        )

        # Store player data for lookups
        for player in players_data:
            self.player_data[player.get("person_id")] = player

        self._log_results(matched_count, manual_mapped_count, len(players_data))

        return {
            "total_players": len(players_data),
            "matched": matched_count,
            "manual": manual_mapped_count,
            "unmatched": len(self.unmatched),
        }

    def _build_name_index(self, career_data: list[dict]) -> dict[str, dict]:
        """Build name-based index for fuzzy matching."""
        name_to_career = {}
        for career in career_data:
            normalized_name = normalize_name(career.get("player", ""))
            if normalized_name:
                name_to_career[normalized_name] = career
        return name_to_career

    def _match_players(
        self, players_data: list[dict], name_to_career: dict[str, dict]
    ) -> tuple[int, int]:
        """Match players from both data sources.

        Args:
            players_data: List of player data from Players.csv
            name_to_career: Mapping of normalized names to career data

        Returns:
            Tuple of (matched_count, manual_mapped_count)
        """
        matched_count = 0
        manual_mapped_count = 0

        for player in players_data:
            person_id = player.get("person_id")
            full_name = self._build_full_name(player)
            reverse_name = self._build_reverse_name(player)

            player_id = self._resolve_player_id(
                person_id, full_name, reverse_name, name_to_career
            )

            if player_id:
                self.mapping_cache[person_id] = player_id
                self.reverse_cache[player_id] = person_id
                matched_count += 1
            else:
                self.unmatched.append({"person_id": person_id, "name": full_name})

        return matched_count, manual_mapped_count

    def _build_full_name(self, player: dict) -> str:
        """Build full name from player data."""
        first_name = player.get("first_name", "")
        last_name = player.get("last_name", "")
        return f"{first_name} {last_name}".strip()

    def _build_reverse_name(self, player: dict) -> str:
        """Build reverse name (Last, First) from player data."""
        first_name = player.get("first_name", "")
        last_name = player.get("last_name", "")
        return f"{last_name}, {first_name}".strip()

    def _resolve_player_id(
        self,
        person_id: int,
        full_name: str,
        reverse_name: str,
        name_to_career: dict[str, dict],
    ) -> str | None:
        """Resolve player_id for a given person_id.

        Args:
            person_id: Numeric person ID
            full_name: Full name of the player
            reverse_name: Reverse formatted name (Last, First)
            name_to_career: Name index for matching

        Returns:
            String player_id or None if not found
        """
        # Check manual mappings first
        if person_id in MANUAL_PLAYER_MAPPINGS:
            logger.debug(f"Manual mapping: {person_id} -> {MANUAL_PLAYER_MAPPINGS[person_id]}")
            return MANUAL_PLAYER_MAPPINGS[person_id]

        normalized_full = normalize_name(full_name)
        normalized_reverse = normalize_name(reverse_name)

        # Try exact match
        if normalized_full in name_to_career:
            return name_to_career[normalized_full]["player_id"]
        if normalized_reverse in name_to_career:
            return name_to_career[normalized_reverse]["player_id"]

        # Try fuzzy matching
        return self._fuzzy_match_player(normalized_full, name_to_career)

    def _fuzzy_match_player(
        self, normalized_name: str, name_to_career: dict[str, dict]
    ) -> str | None:
        """Find best matching player using fuzzy matching."""
        best_match = None
        best_score = 0.0

        for norm_name, career in name_to_career.items():
            score = self.fuzzy_matcher.similarity(normalized_name, norm_name)
            if score > best_score and score >= CONFIDENCE_THRESHOLDS["fuzzy_name_match_medium"]:
                best_score = score
                best_match = career

        if best_match:
            logger.debug(
                f"Fuzzy match: '{normalized_name}' -> '{best_match.get('player')}' "
                f"(score: {best_score:.2f})"
            )
            return best_match["player_id"]

        return None

    def _log_results(
        self, matched_count: int, manual_mapped_count: int, total_players: int
    ) -> None:
        """Log mapping results."""
        if total_players > 0:
            percentage = matched_count / total_players * 100
            logger.info(
                f"Successfully matched {matched_count}/{total_players} players ({percentage:.1f}%)"
            )

        if manual_mapped_count > 0:
            logger.info(f"Used {manual_mapped_count} manual mappings")

        if self.unmatched:
            logger.warning(f"Could not match {len(self.unmatched)} players")

    def _load_players_csv(self, csv_path: Path) -> list[dict]:
        """Load players from CSV file."""
        def parse_row(row: dict) -> dict | None:
            try:
                return {
                    "person_id": int(row["personId"]),
                    "first_name": row.get("firstName", ""),
                    "last_name": row.get("lastName", ""),
                    "birth_date": row.get("birthdate", ""),
                    "country": row.get("country", ""),
                    "height": row.get("height", ""),
                    "weight": row.get("body_weight", ""),
                }
            except (ValueError, KeyError) as e:
                logger.warning(f"Error parsing player row: {e}")
                return None

        return load_csv(csv_path, parse_row, ["personId"])

    def _load_career_info_csv(self, csv_path: Path) -> list[dict]:
        """Load career info from CSV file."""
        def parse_row(row: dict) -> dict | None:
            return {
                "player_id": row.get("player_id", ""),
                "player": row.get("player", ""),
                "birth_date": row.get("birth_date", ""),
                "from_year": row.get("from", ""),
                "to_year": row.get("to", ""),
                "pos": row.get("pos", ""),
                "ht": row.get("ht", ""),
                "wt": row.get("wt", ""),
            }

        return load_csv(csv_path, parse_row)

    def get_player_id(self, person_id: int) -> str | None:
        """Get string player_id from numeric personId.

        Args:
            person_id: Numeric person ID

        Returns:
            String player_id or None if not found
        """
        if person_id is None:
            return None

        # Check cache
        if person_id in self.mapping_cache:
            return self.mapping_cache[person_id]

        # Check manual mappings
        if person_id in MANUAL_PLAYER_MAPPINGS:
            return MANUAL_PLAYER_MAPPINGS[person_id]

        logger.debug(f"No mapping found for person_id: {person_id}")
        return None

    def get_person_id(self, player_id: str) -> int | None:
        """Get numeric personId from string player_id.

        Args:
            player_id: String player ID

        Returns:
            Numeric person_id or None if not found
        """
        if not player_id:
            return None

        # Check cache
        if player_id in self.reverse_cache:
            return self.reverse_cache[player_id]

        # Check reverse manual mappings
        for person_id, mapped_id in MANUAL_PLAYER_MAPPINGS.items():
            if mapped_id == player_id:
                return person_id

        return None

    def get_player_info(self, person_id: int) -> dict | None:
        """Get player info by person_id.

        Args:
            person_id: Numeric person ID

        Returns:
            Player info dictionary or None if not found
        """
        return self.player_data.get(person_id)

    def find_unmatched_players(self) -> list[dict]:
        """Identify players that could not be matched.

        Returns:
            List of unmatched player dictionaries
        """
        return self.unmatched

    def add_manual_mapping(self, person_id: int, player_id: str | None) -> None:
        """Add manual override for edge cases.

        Args:
            person_id: Numeric person ID
            player_id: String player ID or None to mark as explicitly unmatched
        """
        if person_id and player_id:
            self.mapping_cache[person_id] = player_id
            self.reverse_cache[player_id] = person_id
            logger.info(f"Added manual mapping: {person_id} -> {player_id}")
        elif person_id and player_id is None:
            # Mark as explicitly unmatched
            logger.info(f"Marked {person_id} as explicitly unmatched")
