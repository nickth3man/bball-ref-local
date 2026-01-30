"""Fuzzy name matching for player and team names."""

import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    """Fuzzy matching for player/team names using SequenceMatcher."""

    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold

    def similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two names."""
        if not name1 or not name2:
            return 0.0
        normalized1 = " ".join(name1.lower().split())
        normalized2 = " ".join(name2.lower().split())
        if not normalized1 or not normalized2:
            return 0.0
        return SequenceMatcher(None, normalized1, normalized2).ratio()

    def is_match(self, name1: str, name2: str, threshold: float | None = None) -> bool:
        """Check if two names match within threshold."""
        thresh = threshold if threshold is not None else self.threshold
        return self.similarity(name1, name2) >= thresh

    def find_best_match(self, name: str, candidates: list, name_field: str = "name"):
        """Find best matching candidate from a list."""
        if not name or not candidates:
            return None
        best_match = None
        best_score = 0.0
        for candidate in candidates:
            candidate_name = candidate.get(name_field, "")
            score = self.similarity(name, candidate_name)
            if score > best_score:
                best_score = score
                best_match = candidate
        if best_match and best_score >= self.threshold:
            return (best_match, best_score)
        return None

    def token_sort_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity after sorting tokens."""
        if not name1 or not name2:
            return 0.0
        tokens1 = sorted(name1.lower().split())
        tokens2 = sorted(name2.lower().split())
        sorted1 = " ".join(tokens1)
        sorted2 = " ".join(tokens2)
        return SequenceMatcher(None, sorted1, sorted2).ratio()

    def partial_ratio(self, name1: str, name2: str) -> float:
        """Calculate partial string matching ratio."""
        if not name1 or not name2:
            return 0.0
        if len(name1) > len(name2):
            name1, name2 = name2, name1
        best_ratio = 0.0
        len1 = len(name1)
        for i in range(len(name2) - len1 + 1):
            substring = name2[i : i + len1]
            ratio = SequenceMatcher(None, name1.lower(), substring.lower()).ratio()
            best_ratio = max(best_ratio, ratio)
        return best_ratio
