"""Core validation classes for data integrity checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import duckdb

from scripts.ingestion.logger import get_logger
from scripts.ingestion.validation.sql_validators import (
    VALIDATE_DUPLICATE_GAMES,
    VALIDATE_DUPLICATE_PLAYER_GAMES,
    VALIDATE_DUPLICATE_PLAYERS,
    VALIDATE_FOREIGN_KEYS_GAMES,
    VALIDATE_FOREIGN_KEYS_PLAYERS,
    VALIDATE_FOREIGN_KEYS_SEASONS,
    VALIDATE_FOREIGN_KEYS_TEAMS,
    VALIDATE_GAME_QUARTER_SUMS,
    VALIDATE_GAME_SCORES,
    VALIDATE_GAME_TIES,
    VALIDATE_GAME_WINNERS,
    VALIDATE_PLAYER_AGES,
    VALIDATE_PLAYER_CAREER_SEASONS,
    VALIDATE_PLAYER_CAREER_SPAN,
    VALIDATE_POINTS_CALCULATION,
    VALIDATE_POINTS_CALCULATION_SEASON,
    VALIDATE_SEASON_RANGES,
    VALIDATE_STAT_PERCENTAGES,
    VALIDATE_STAT_PERCENTAGES_GAME,
    VALIDATE_TEAM_ACTIVE_YEARS,
    VALIDATE_TEAM_SEASON_CONTINUITY,
)

logger = get_logger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""

    severity: ValidationSeverity
    message: str
    table: str = ""
    row_id: Any = None
    details: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of a validation check."""

    check_name: str
    passed: bool = False
    issues: list[ValidationIssue] = field(default_factory=list)
    duration_ms: float = 0.0
    row_count: int = 0

    def has_errors(self) -> bool:
        """Check if result has any error or critical issues."""
        return any(
            issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
            for issue in self.issues
        )

    def has_warnings(self) -> bool:
        """Check if result has any warnings."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)


class DataValidator:
    """Main validation class for data integrity checks."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self.logger = get_logger(self.__class__.__name__)

    def run_all_validations(self) -> list[ValidationResult]:
        """Run all validation checks and return results."""
        results = []

        # Foreign key validations
        results.append(self.validate_foreign_keys_players())
        results.append(self.validate_foreign_keys_teams())
        results.append(self.validate_foreign_keys_games())
        results.append(self.validate_foreign_keys_seasons())

        # Duplicate validations
        results.append(self.validate_duplicate_players())
        results.append(self.validate_duplicate_games())
        results.append(self.validate_duplicate_player_games())

        # Data integrity validations
        results.append(self.validate_points_calculation())
        results.append(self.validate_points_calculation_season())
        results.append(self.validate_game_winners())
        results.append(self.validate_game_ties())
        results.append(self.validate_game_scores())
        results.append(self.validate_game_quarter_sums())
        results.append(self.validate_stat_percentages())
        results.append(self.validate_stat_percentages_game())

        # Range validations
        results.append(self.validate_season_ranges())
        results.append(self.validate_player_career_seasons())
        results.append(self.validate_player_ages())
        results.append(self.validate_player_career_span())
        results.append(self.validate_team_season_continuity())
        results.append(self.validate_team_active_years())

        return results

    def _execute_query(self, query: str, description: str) -> list:
        """Execute a validation query and return results."""
        try:
            result = self.conn.execute(query).fetchall()
            return result
        except Exception as e:
            self.logger.error(f"Failed to execute {description}: {e}")
            return []

    def validate_foreign_keys_players(self) -> ValidationResult:
        """Validate that all player references in player_game_stats exist in players table."""
        result = ValidationResult(check_name="Foreign Keys: Players")

        orphans = self._execute_query(VALIDATE_FOREIGN_KEYS_PLAYERS, "foreign key players check")

        if orphans:
            result.passed = False
            for row in orphans[:10]:  # Limit to first 10
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Orphan player_id: {row[0]} with {row[1]} records",
                        table="player_game_stats",
                        row_id=row[0],
                        details={"orphan_count": row[1]},
                    )
                )
        else:
            result.passed = True

        return result

    def validate_foreign_keys_teams(self) -> ValidationResult:
        """Validate that all team references exist in teams table."""
        result = ValidationResult(check_name="Foreign Keys: Teams")

        orphans = self._execute_query(VALIDATE_FOREIGN_KEYS_TEAMS, "foreign key teams check")

        if orphans:
            result.passed = False
            for row in orphans[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Orphan team_id: {row[0]} with {row[1]} records",
                        table="player_game_stats",
                        row_id=row[0],
                        details={"orphan_count": row[1]},
                    )
                )
        else:
            result.passed = True

        return result

    def validate_foreign_keys_games(self) -> ValidationResult:
        """Validate that all game references exist in games table."""
        result = ValidationResult(check_name="Foreign Keys: Games")

        orphans = self._execute_query(VALIDATE_FOREIGN_KEYS_GAMES, "foreign key games check")

        if orphans:
            result.passed = False
            for row in orphans[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Orphan game_id: {row[0]} with {row[1]} records",
                        table="player_game_stats",
                        row_id=row[0],
                        details={"orphan_count": row[1]},
                    )
                )
        else:
            result.passed = True

        return result

    def validate_foreign_keys_seasons(self) -> ValidationResult:
        """Validate that all season references exist in seasons table."""
        result = ValidationResult(check_name="Foreign Keys: Seasons")

        orphans = self._execute_query(VALIDATE_FOREIGN_KEYS_SEASONS, "foreign key seasons check")

        if orphans:
            result.passed = False
            for row in orphans[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Orphan season_id: {row[0]} with {row[1]} records",
                        table="player_season_stats",
                        row_id=row[0],
                        details={"orphan_count": row[1]},
                    )
                )
        else:
            result.passed = True

        return result

    def validate_duplicate_players(self) -> ValidationResult:
        """Validate no duplicate players exist."""
        result = ValidationResult(check_name="Duplicate: Players")

        duplicates = self._execute_query(VALIDATE_DUPLICATE_PLAYERS, "duplicate players check")

        if duplicates:
            result.passed = False
            for row in duplicates[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Duplicate player_id: {row[0]} with {row[1]} records",
                        table="players",
                        row_id=row[0],
                        details={"duplicate_count": row[1]},
                    )
                )
        else:
            result.passed = True

        return result

    def validate_duplicate_games(self) -> ValidationResult:
        """Validate no duplicate games exist."""
        result = ValidationResult(check_name="Duplicate: Games")

        duplicates = self._execute_query(VALIDATE_DUPLICATE_GAMES, "duplicate games check")

        if duplicates:
            result.passed = False
            for row in duplicates[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Duplicate game_id: {row[0]} with {row[1]} records",
                        table="games",
                        row_id=row[0],
                        details={"duplicate_count": row[1]},
                    )
                )
        else:
            result.passed = True

        return result

    def validate_duplicate_player_games(self) -> ValidationResult:
        """Validate no duplicate player-game combinations exist."""
        result = ValidationResult(check_name="Duplicate: Player Games")

        duplicates = self._execute_query(
            VALIDATE_DUPLICATE_PLAYER_GAMES, "duplicate player games check"
        )

        if duplicates:
            result.passed = False
            for row in duplicates[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Duplicate player-game: ({row[0]}, {row[1]}) with {row[2]} records",
                        table="player_game_stats",
                        details={"player_id": row[0], "game_id": row[1], "duplicate_count": row[2]},
                    )
                )
        else:
            result.passed = True

        return result

    def validate_points_calculation(self) -> ValidationResult:
        """Validate points calculation in player_game_stats."""
        result = ValidationResult(check_name="Points Calculation: Games")

        invalid = self._execute_query(VALIDATE_POINTS_CALCULATION, "points calculation check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid points calculation: {row[2]} != {row[3]} (diff: {row[4]})",
                        table="player_game_stats",
                        row_id=row[0],
                        details={
                            "player_id": row[0],
                            "game_id": row[1],
                            "points": row[2],
                            "calculated": row[3],
                        },
                    )
                )
        else:
            result.passed = True

        return result

    def validate_points_calculation_season(self) -> ValidationResult:
        """Validate points calculation in player_season_stats."""
        result = ValidationResult(check_name="Points Calculation: Seasons")

        invalid = self._execute_query(
            VALIDATE_POINTS_CALCULATION_SEASON, "season points calculation check"
        )

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid season points calculation: {row[2]} != {row[3]} (diff: {row[4]})",
                        table="player_season_stats",
                        row_id=row[0],
                        details={
                            "player_id": row[0],
                            "season_id": row[1],
                            "points": row[2],
                            "calculated": row[3],
                        },
                    )
                )
        else:
            result.passed = True

        return result

    def validate_game_winners(self) -> ValidationResult:
        """Validate game winners match calculated winners."""
        result = ValidationResult(check_name="Game Winners")

        invalid = self._execute_query(VALIDATE_GAME_WINNERS, "game winners check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Incorrect winner: {row[4]} (should be {row[6]})",
                        table="games",
                        row_id=row[0],
                        details={
                            "game_id": row[0],
                            "winner_team_id": row[4],
                            "calculated_winner": row[6],
                        },
                    )
                )
        else:
            result.passed = True

        return result

    def validate_game_ties(self) -> ValidationResult:
        """Validate tie games have no winner."""
        result = ValidationResult(check_name="Game Ties")

        invalid = self._execute_query(VALIDATE_GAME_TIES, "game ties check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Tie game has winner: {row[4]}",
                        table="games",
                        row_id=row[0],
                        details={
                            "game_id": row[0],
                            "home_score": row[2],
                            "away_score": row[3],
                            "winner": row[4],
                        },
                    )
                )
        else:
            result.passed = True

        return result

    def validate_game_scores(self) -> ValidationResult:
        """Validate game scores are within reasonable ranges."""
        result = ValidationResult(check_name="Game Scores")

        invalid = self._execute_query(VALIDATE_GAME_SCORES, "game scores check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid score - Home: {row[3]}, Away: {row[4]}",
                        table="games",
                        row_id=row[0],
                        details={"game_id": row[0], "home_score": row[3], "away_score": row[4]},
                    )
                )
        else:
            result.passed = True

        return result

    def validate_game_quarter_sums(self) -> ValidationResult:
        """Validate quarter sums match final scores."""
        result = ValidationResult(check_name="Game Quarter Sums")

        invalid = self._execute_query(VALIDATE_GAME_QUARTER_SUMS, "quarter sums check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message="Quarter sum mismatch",
                        table="games",
                        row_id=row[0],
                        details={
                            "game_id": row[0],
                            "home_score": row[1],
                            "calc_home": row[2],
                            "away_score": row[3],
                            "calc_away": row[4],
                        },
                    )
                )
        else:
            result.passed = True

        return result

    def validate_stat_percentages(self) -> ValidationResult:
        """Validate statistical percentages are between 0 and 1."""
        result = ValidationResult(check_name="Stat Percentages")

        invalid = self._execute_query(VALIDATE_STAT_PERCENTAGES, "stat percentages check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid percentage - FG: {row[2]}, 3P: {row[3]}, FT: {row[4]}",
                        table="player_season_stats",
                        row_id=row[0],
                        details={
                            "player_id": row[0],
                            "season_id": row[1],
                            "fg_pct": row[2],
                            "fg3_pct": row[3],
                            "ft_pct": row[4],
                        },
                    )
                )
        else:
            result.passed = True

        return result

    def validate_stat_percentages_game(self) -> ValidationResult:
        """Validate game log percentage calculations."""
        result = ValidationResult(check_name="Stat Percentages: Games")

        # Check if player_game_logs table exists
        try:
            result_exists = self.conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'player_game_logs'"
            ).fetchone()
            if not result_exists or result_exists[0] == 0:
                result.passed = True
                return result
        except Exception:
            result.passed = True
            return result

        invalid = self._execute_query(VALIDATE_STAT_PERCENTAGES_GAME, "game percentages check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid game percentage - FG: {row[2]}, 3P: {row[3]}, FT: {row[4]}",
                        table="player_game_logs",
                        row_id=row[0],
                        details={
                            "player_id": row[0],
                            "game_id": row[1],
                            "fg_pct": row[2],
                            "fg3_pct": row[3],
                            "ft_pct": row[4],
                        },
                    )
                )
        else:
            result.passed = True

        return result

    def validate_season_ranges(self) -> ValidationResult:
        """Validate season ranges are valid."""
        result = ValidationResult(check_name="Season Ranges")

        invalid = self._execute_query(VALIDATE_SEASON_RANGES, "season ranges check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid season range: {row[0]} ({row[1]}-{row[2]})",
                        table="seasons",
                        row_id=row[0],
                        details={"season_id": row[0], "year_start": row[1], "year_end": row[2]},
                    )
                )
        else:
            result.passed = True

        return result

    def validate_player_career_seasons(self) -> ValidationResult:
        """Validate player career seasons are within valid ranges."""
        result = ValidationResult(check_name="Player Career Seasons")

        invalid = self._execute_query(VALIDATE_PLAYER_CAREER_SEASONS, "player career seasons check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Invalid career span for {row[1]}: {row[3]}-{row[4]}",
                        table="players",
                        row_id=row[0],
                        details={
                            "player_id": row[0],
                            "name": row[1],
                            "draft_year": row[2],
                            "career_start": row[3],
                            "career_end": row[4],
                        },
                    )
                )
        else:
            result.passed = True

        return result

    def validate_player_ages(self) -> ValidationResult:
        """Validate player ages are reasonable."""
        result = ValidationResult(check_name="Player Ages")

        invalid = self._execute_query(VALIDATE_PLAYER_AGES, "player ages check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Unusual age for {row[1]}: {row[4]}",
                        table="player_season_stats",
                        row_id=row[0],
                        details={
                            "player_id": row[0],
                            "name": row[1],
                            "birth_date": row[2],
                            "season_id": row[3],
                            "age": row[4],
                        },
                    )
                )
        else:
            result.passed = True

        return result

    def validate_player_career_span(self) -> ValidationResult:
        """Validate player career spans are reasonable."""
        result = ValidationResult(check_name="Player Career Span")

        invalid = self._execute_query(VALIDATE_PLAYER_CAREER_SPAN, "player career span check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Unusual career span for {row[1]}",
                        table="players",
                        row_id=row[0],
                        details={
                            "player_id": row[0],
                            "name": row[1],
                            "birth_date": row[2],
                            "career_start": row[3],
                            "career_end": row[4],
                            "age_at_career_end": row[5],
                        },
                    )
                )
        else:
            result.passed = True

        return result

    def validate_team_season_continuity(self) -> ValidationResult:
        """Validate team season continuity."""
        result = ValidationResult(check_name="Team Season Continuity")

        invalid = self._execute_query(
            VALIDATE_TEAM_SEASON_CONTINUITY, "team season continuity check"
        )

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Season gap for team {row[0]}: {row[1]} (gap: {row[3]} years)",
                        table="team_season_stats",
                        row_id=row[0],
                        details={
                            "team_id": row[0],
                            "season_year": row[1],
                            "prev_season": row[2],
                            "gap": row[3],
                        },
                    )
                )
        else:
            result.passed = True

        return result

    def validate_team_active_years(self) -> ValidationResult:
        """Validate team active years match statistics."""
        result = ValidationResult(check_name="Team Active Years")

        invalid = self._execute_query(VALIDATE_TEAM_ACTIVE_YEARS, "team active years check")

        if invalid:
            result.passed = False
            for row in invalid[:10]:
                result.issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Team {row[1]} stats mismatch",
                        table="teams",
                        row_id=row[0],
                        details={
                            "team_id": row[0],
                            "team_name": row[1],
                            "year_founded": row[2],
                            "first_season": row[3],
                            "last_season": row[4],
                        },
                    )
                )
        else:
            result.passed = True

        return result
