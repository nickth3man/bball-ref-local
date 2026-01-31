"""Core validation classes for data integrity checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import duckdb

from scripts.ingestion.logger import get_logger
from scripts.ingestion.validation.sql_validators import SQLValidators

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

    # Maximum number of issues to report per validation check
    MAX_ISSUES_PER_CHECK = 10

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
            return self.conn.execute(query).fetchall()
        except Exception as e:
            self.logger.error(f"Failed to execute {description}: {e}")
            return []

    def _create_issue(
        self,
        severity: ValidationSeverity,
        message: str,
        table: str = "",
        row_id: Any = None,
        details: dict | None = None,
    ) -> ValidationIssue:
        """Create a ValidationIssue with the given parameters."""
        return ValidationIssue(
            severity=severity,
            message=message,
            table=table,
            row_id=row_id,
            details=details or {},
        )

    def _create_result(
        self,
        check_name: str,
        rows: list,
        issue_builder: callable,
        passed: bool = True,
    ) -> ValidationResult:
        """Create a ValidationResult from query results.

        Args:
            check_name: Name of the validation check
            rows: Query result rows
            issue_builder: Callable that takes a row and returns a ValidationIssue
            passed: Default passed state if no rows

        Returns:
            ValidationResult with issues populated
        """
        result = ValidationResult(check_name=check_name)

        if rows:
            result.passed = False
            for row in rows[: self.MAX_ISSUES_PER_CHECK]:
                result.issues.append(issue_builder(row))
        else:
            result.passed = passed

        return result

    # =========================================================================
    # Foreign Key Validations
    # =========================================================================

    def validate_foreign_keys_players(self) -> ValidationResult:
        """Validate that all player references in player_game_stats exist in players table."""
        orphans = self._execute_query(
            SQLValidators.VALIDATE_FOREIGN_KEYS_PLAYERS, "foreign key players check"
        )

        def build_issue(row):
            return self._create_issue(
                severity=ValidationSeverity.ERROR,
                message=f"Orphan player_id: {row[0]} with {row[1]} records",
                table="player_game_stats",
                row_id=row[0],
                details={"orphan_count": row[1]},
            )

        return self._create_result("Foreign Keys: Players", orphans, build_issue)

    def validate_foreign_keys_teams(self) -> ValidationResult:
        """Validate that all team references exist in teams table."""
        orphans = self._execute_query(
            SQLValidators.VALIDATE_FOREIGN_KEYS_TEAMS, "foreign key teams check"
        )

        def build_issue(row):
            return self._create_issue(
                severity=ValidationSeverity.ERROR,
                message=f"Orphan team_id: {row[0]} with {row[1]} records",
                table="player_game_stats",
                row_id=row[0],
                details={"orphan_count": row[1]},
            )

        return self._create_result("Foreign Keys: Teams", orphans, build_issue)

    def validate_foreign_keys_games(self) -> ValidationResult:
        """Validate that all game references exist in games table."""
        orphans = self._execute_query(
            SQLValidators.VALIDATE_FOREIGN_KEYS_GAMES, "foreign key games check"
        )

        def build_issue(row):
            return self._create_issue(
                severity=ValidationSeverity.ERROR,
                message=f"Orphan game_id: {row[0]} with {row[1]} records",
                table="player_game_stats",
                row_id=row[0],
                details={"orphan_count": row[1]},
            )

        return self._create_result("Foreign Keys: Games", orphans, build_issue)

    def validate_foreign_keys_seasons(self) -> ValidationResult:
        """Validate that all season references exist in seasons table."""
        orphans = self._execute_query(
            SQLValidators.VALIDATE_FOREIGN_KEYS_SEASONS, "foreign key seasons check"
        )

        def build_issue(row):
            return self._create_issue(
                severity=ValidationSeverity.ERROR,
                message=f"Orphan season_id: {row[0]} with {row[1]} records",
                table="player_season_stats",
                row_id=row[0],
                details={"orphan_count": row[1]},
            )

        return self._create_result("Foreign Keys: Seasons", orphans, build_issue)

    # =========================================================================
    # Duplicate Validations
    # =========================================================================

    def validate_duplicate_players(self) -> ValidationResult:
        """Validate no duplicate players exist."""
        duplicates = self._execute_query(
            SQLValidators.VALIDATE_DUPLICATE_PLAYERS, "duplicate players check"
        )

        def build_issue(row):
            return self._create_issue(
                severity=ValidationSeverity.ERROR,
                message=f"Duplicate player_id: {row[0]} with {row[1]} records",
                table="players",
                row_id=row[0],
                details={"duplicate_count": row[1]},
            )

        return self._create_result("Duplicate: Players", duplicates, build_issue)

    def validate_duplicate_games(self) -> ValidationResult:
        """Validate no duplicate games exist."""
        duplicates = self._execute_query(
            SQLValidators.VALIDATE_DUPLICATE_GAMES, "duplicate games check"
        )

        def build_issue(row):
            return self._create_issue(
                severity=ValidationSeverity.ERROR,
                message=f"Duplicate game_id: {row[0]} with {row[1]} records",
                table="games",
                row_id=row[0],
                details={"duplicate_count": row[1]},
            )

        return self._create_result("Duplicate: Games", duplicates, build_issue)

    def validate_duplicate_player_games(self) -> ValidationResult:
        """Validate no duplicate player-game combinations exist."""
        duplicates = self._execute_query(
            SQLValidators.VALIDATE_DUPLICATE_PLAYER_GAMES, "duplicate player games check"
        )

        def build_issue(row):
            return self._create_issue(
                severity=ValidationSeverity.ERROR,
                message=f"Duplicate player-game: ({row[0]}, {row[1]}) with {row[2]} records",
                table="player_game_stats",
                details={"player_id": row[0], "game_id": row[1], "duplicate_count": row[2]},
            )

        return self._create_result("Duplicate: Player Games", duplicates, build_issue)

    # =========================================================================
    # Data Integrity Validations
    # =========================================================================

    def validate_points_calculation(self) -> ValidationResult:
        """Validate points calculation in player_game_stats."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_POINTS_CALCULATION_GAME, "points calculation check"
        )

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Points Calculation: Games", invalid, build_issue)

    def validate_points_calculation_season(self) -> ValidationResult:
        """Validate points calculation in player_season_stats."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_POINTS_CALCULATION_SEASON, "season points calculation check"
        )

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Points Calculation: Seasons", invalid, build_issue)

    def validate_game_winners(self) -> ValidationResult:
        """Validate game winners match calculated winners."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_GAME_WINNERS, "game winners check"
        )

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Game Winners", invalid, build_issue)

    def validate_game_ties(self) -> ValidationResult:
        """Validate tie games have no winner."""
        invalid = self._execute_query(SQLValidators.VALIDATE_GAME_TIES, "game ties check")

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Game Ties", invalid, build_issue)

    def validate_game_scores(self) -> ValidationResult:
        """Validate game scores are within reasonable ranges."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_GAME_SCORES, "game scores check"
        )

        def build_issue(row):
            return self._create_issue(
                severity=ValidationSeverity.ERROR,
                message=f"Invalid score - Home: {row[3]}, Away: {row[4]}",
                table="games",
                row_id=row[0],
                details={"game_id": row[0], "home_score": row[3], "away_score": row[4]},
            )

        return self._create_result("Game Scores", invalid, build_issue)

    def validate_game_quarter_sums(self) -> ValidationResult:
        """Validate quarter sums match final scores."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_GAME_QUARTER_SUMS, "quarter sums check"
        )

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Game Quarter Sums", invalid, build_issue)

    def validate_stat_percentages(self) -> ValidationResult:
        """Validate statistical percentages are between 0 and 1."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_STAT_PERCENTAGES_SEASON, "stat percentages check"
        )

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Stat Percentages", invalid, build_issue)

    def validate_stat_percentages_game(self) -> ValidationResult:
        """Validate game log percentage calculations."""
        result = ValidationResult(check_name="Stat Percentages: Games")

        # Check if player_game_logs table exists
        if not self._table_exists("player_game_logs"):
            result.passed = True
            return result

        invalid = self._execute_query(
            SQLValidators.VALIDATE_STAT_PERCENTAGES_GAME, "game percentages check"
        )

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Stat Percentages: Games", invalid, build_issue)

    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            result = self.conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                [table_name],
            ).fetchone()
            return result is not None and result[0] > 0
        except Exception:
            return False

    # =========================================================================
    # Range Validations
    # =========================================================================

    def validate_season_ranges(self) -> ValidationResult:
        """Validate season ranges are valid."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_SEASON_RANGES, "season ranges check"
        )

        def build_issue(row):
            return self._create_issue(
                severity=ValidationSeverity.ERROR,
                message=f"Invalid season range: {row[0]} ({row[1]}-{row[2]})",
                table="seasons",
                row_id=row[0],
                details={"season_id": row[0], "year_start": row[1], "year_end": row[2]},
            )

        return self._create_result("Season Ranges", invalid, build_issue)

    def validate_player_career_seasons(self) -> ValidationResult:
        """Validate player career seasons are within valid ranges."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_PLAYER_CAREER_SEASONS, "player career seasons check"
        )

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Player Career Seasons", invalid, build_issue)

    def validate_player_ages(self) -> ValidationResult:
        """Validate player ages are reasonable."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_PLAYER_AGES, "player ages check"
        )

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Player Ages", invalid, build_issue)

    def validate_player_career_span(self) -> ValidationResult:
        """Validate player career spans are reasonable."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_PLAYER_CAREER_SPAN, "player career span check"
        )

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Player Career Span", invalid, build_issue)

    def validate_team_season_continuity(self) -> ValidationResult:
        """Validate team season continuity."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_TEAM_SEASON_CONTINUITY, "team season continuity check"
        )

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Team Season Continuity", invalid, build_issue)

    def validate_team_active_years(self) -> ValidationResult:
        """Validate team active years match statistics."""
        invalid = self._execute_query(
            SQLValidators.VALIDATE_TEAM_ACTIVE_YEARS, "team active years check"
        )

        def build_issue(row):
            return self._create_issue(
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

        return self._create_result("Team Active Years", invalid, build_issue)
