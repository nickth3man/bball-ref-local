"""Player ID mapper for bridging personId and player_id systems."""

import csv
import re
from pathlib import Path

from scripts.ingestion.logger import get_logger

from .fuzzy_matcher import FuzzyMatcher
from .manual_mappings import CONFIDENCE_THRESHOLDS, MANUAL_PLAYER_MAPPINGS

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

    def build_mapping(self, players_csv_path: Path, career_info_csv_path: Path):
        """Build mapping table from Players.csv and Player_Career_Info.csv."""
        logger.info("Building player ID mapping...")

        players_data = self._load_players_csv(players_csv_path)
        career_data = self._load_career_info_csv(career_info_csv_path)

        logger.info(f"Loaded {len(players_data)} players from Players.csv")
        logger.info(f"Loaded {len(career_data)} players from Player_Career_Info.csv")

        # Build name-based index for fuzzy matching
        name_to_career = {}
        for career in career_data:
            normalized_name = self._normalize_name(career.get("player", ""))
            if normalized_name:
                name_to_career[normalized_name] = career

        # Match players from both sources
        matched_count = 0
        manual_mapped_count = 0

        for player in players_data:
            person_id = player.get("person_id")
            first_name = player.get("first_name", "")
            last_name = player.get("last_name", "")

            # Build full name variations
            full_name = f"{first_name} {last_name}".strip()
            reverse_name = f"{last_name}, {first_name}".strip()

            player_id = None

            # Check manual mappings first
            if person_id in MANUAL_PLAYER_MAPPINGS:
                player_id = MANUAL_PLAYER_MAPPINGS[person_id]
                manual_mapped_count += 1
                logger.debug(f"Manual mapping: {person_id} -> {player_id}")
            else:
                # Try exact match
                normalized_full = self._normalize_name(full_name)
                normalized_reverse = self._normalize_name(reverse_name)

                if normalized_full in name_to_career:
                    player_id = name_to_career[normalized_full]["player_id"]
                elif normalized_reverse in name_to_career:
                    player_id = name_to_career[normalized_reverse]["player_id"]
                else:
                    # Try fuzzy matching
                    best_match = None
                    best_score = 0

                    for norm_name, career in name_to_career.items():
                        score = self.fuzzy_matcher.similarity(normalized_full, norm_name)
                        if (
                            score > best_score
                            and score >= CONFIDENCE_THRESHOLDS["fuzzy_name_match_medium"]
                        ):
                            best_score = score
                            best_match = career

                    if best_match:
                        player_id = best_match["player_id"]
                        logger.debug(
                            f"Fuzzy match: '{full_name}' -> '{best_match.get('player')}' (score: {best_score:.2f})"
                        )

            if player_id:
                self.mapping_cache[person_id] = player_id
                self.reverse_cache[player_id] = person_id
                matched_count += 1
            else:
                self.unmatched.append(
                    {
                        "person_id": person_id,
                        "name": full_name,
                    }
                )

        logger.info(
            f"Successfully matched {matched_count}/{len(players_data)} players ({matched_count / len(players_data) * 100:.1f}%)"
        )
        if manual_mapped_count > 0:
            logger.info(f"Used {manual_mapped_count} manual mappings")
        if self.unmatched:
            logger.warning(f"Could not match {len(self.unmatched)} players")

        # Store player data for lookups
        for player in players_data:
            self.player_data[player.get("person_id")] = player

        return {
            "total_players": len(players_data),
            "matched": matched_count,
            "manual": manual_mapped_count,
            "unmatched": len(self.unmatched),
        }

    def _load_players_csv(self, csv_path: Path):
        """Load players from CSV file."""
        players = []
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    players.append(
                        {
                            "person_id": int(row["personId"]),
                            "first_name": row.get("firstName", ""),
                            "last_name": row.get("lastName", ""),
                            "birth_date": row.get("birthdate", ""),
                            "country": row.get("country", ""),
                            "height": row.get("height", ""),
                            "weight": row.get("body_weight", ""),
                        }
                    )
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing player row: {e}")
        return players

    def _load_career_info_csv(self, csv_path: Path):
        """Load career info from CSV file."""
        players = []
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                players.append(
                    {
                        "player_id": row.get("player_id", ""),
                        "player": row.get("player", ""),
                        "birth_date": row.get("birth_date", ""),
                        "from_year": row.get("from", ""),
                        "to_year": row.get("to", ""),
                        "pos": row.get("pos", ""),
                        "ht": row.get("ht", ""),
                        "wt": row.get("wt", ""),
                    }
                )
        return players

    def _normalize_name(self, name: str) -> str:
        """Normalize player name for matching."""
        if not name:
            return ""
        # Remove extra whitespace, convert to lowercase
        normalized = " ".join(name.split()).lower()
        # Remove special characters
        normalized = re.sub(r"[^a-z0-9\s,]", "", normalized)
        return normalized

    def get_player_id(self, person_id: int) -> str | None:
        """Get string player_id from numeric personId."""
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
        """Get numeric personId from string player_id."""
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
        """Get player info by person_id."""
        return self.player_data.get(person_id)

    def find_unmatched_players(self):
        """Identify players that could not be matched."""
        return self.unmatched

    def add_manual_mapping(self, person_id: int, player_id: str | None):
        """Add manual override for edge cases."""
        if person_id and player_id:
            self.mapping_cache[person_id] = player_id
            self.reverse_cache[player_id] = person_id
            logger.info(f"Added manual mapping: {person_id} -> {player_id}")
        elif person_id and player_id is None:
            # Mark as explicitly unmatched
            logger.info(f"Marked {person_id} as explicitly unmatched")
