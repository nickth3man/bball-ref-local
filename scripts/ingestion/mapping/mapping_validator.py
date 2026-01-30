"""Mapping validation for ID resolution system."""

from scripts.ingestion.logger import get_logger

logger = get_logger(__name__)


class MappingValidator:
    """Validates ID mappings for consistency."""

    def __init__(self, conn):
        self.conn = conn
        self.validation_results = []

    def validate_player_mappings(self):
        """Check player mappings for issues."""
        issues = []

        try:
            # Check for duplicate player_id mappings
            duplicates = self.conn.execute("""
                SELECT player_id, COUNT(*) as cnt
                FROM id_mapping_players
                GROUP BY player_id
                HAVING COUNT(*) > 1
            """).fetchall()

            for row in duplicates:
                issues.append(
                    {
                        "type": "duplicate_player_id",
                        "player_id": row[0],
                        "count": row[1],
                        "severity": "error",
                    }
                )

            # Check for duplicate personId mappings
            duplicate_persons = self.conn.execute("""
                SELECT person_id, COUNT(*) as cnt
                FROM id_mapping_players
                GROUP BY person_id
                HAVING COUNT(*) > 1
            """).fetchall()

            for row in duplicate_persons:
                issues.append(
                    {
                        "type": "duplicate_person_id",
                        "person_id": row[0],
                        "count": row[1],
                        "severity": "error",
                    }
                )

            # Check for null values
            null_player_ids = self.conn.execute("""
                SELECT COUNT(*) 
                FROM id_mapping_players 
                WHERE player_id IS NULL OR player_id = ''
            """).fetchone()

            if null_player_ids and null_player_ids[0] > 0:
                issues.append(
                    {"type": "null_player_id", "count": null_player_ids[0], "severity": "error"}
                )

            # Check for mappings that don't exist in players table
            orphaned = self.conn.execute("""
                SELECT imp.player_id
                FROM id_mapping_players imp
                LEFT JOIN players p ON imp.player_id = p.player_id
                WHERE p.player_id IS NULL
                LIMIT 10
            """).fetchall()

            for row in orphaned:
                issues.append(
                    {"type": "orphaned_mapping", "player_id": row[0], "severity": "warning"}
                )

            logger.info(f"Player mapping validation found {len(issues)} issues")

        except Exception as e:
            logger.error(f"Error validating player mappings: {e}")
            issues.append({"type": "validation_error", "message": str(e), "severity": "error"})

        return issues

    def validate_team_mappings(self):
        """Check team mappings across seasons."""
        issues = []

        try:
            # Check for teams without any mappings
            unmapped_teams = self.conn.execute("""
                SELECT t.team_id, t.abbreviation
                FROM teams t
                LEFT JOIN id_mapping_teams imt ON t.team_id = imt.team_id
                WHERE imt.team_id IS NULL
                LIMIT 10
            """).fetchall()

            for row in unmapped_teams:
                issues.append(
                    {
                        "type": "unmapped_team",
                        "team_id": row[0],
                        "abbreviation": row[1],
                        "severity": "warning",
                    }
                )

            # Check for abbreviation changes without history
            multi_abbrev_teams = self.conn.execute("""
                SELECT team_id, COUNT(DISTINCT abbreviation) as abbrev_count
                FROM id_mapping_teams
                GROUP BY team_id
                HAVING COUNT(DISTINCT abbreviation) > 1
            """).fetchall()

            for row in multi_abbrev_teams:
                issues.append(
                    {
                        "type": "multiple_abbreviations",
                        "team_id": row[0],
                        "abbreviation_count": row[1],
                        "severity": "info",
                    }
                )

            # Check for invalid season ranges
            invalid_seasons = self.conn.execute("""
                SELECT team_id, season, abbreviation
                FROM id_mapping_teams
                WHERE season IS NOT NULL
                  AND (season < 1946 OR season > 2030)
            """).fetchall()

            for row in invalid_seasons:
                issues.append(
                    {
                        "type": "invalid_season",
                        "team_id": row[0],
                        "season": row[1],
                        "abbreviation": row[2],
                        "severity": "warning",
                    }
                )

            logger.info(f"Team mapping validation found {len(issues)} issues")

        except Exception as e:
            logger.error(f"Error validating team mappings: {e}")
            issues.append({"type": "validation_error", "message": str(e), "severity": "error"})

        return issues

    def check_data_integrity(self, sample_size: int = 100):
        """Verify mapped IDs work for actual data joins."""
        issues = []

        try:
            # Sample player game stats and verify player_id mapping works
            sample_players = self.conn.execute(f"""
                SELECT DISTINCT pgs.player_id, p.player
                FROM player_game_statistics pgs
                JOIN player_master p ON pgs.player_id = p.player_id
                LIMIT {sample_size}
            """).fetchall()

            if not sample_players:
                issues.append({"type": "no_player_samples", "severity": "warning"})
            else:
                logger.info(f"Verified {len(sample_players)} player mappings in game stats")

            # Sample games and verify team_id mapping works
            sample_teams = self.conn.execute(f"""
                SELECT DISTINCT g.home_team_id, t.team_abbrev
                FROM games_historical g
                JOIN team_abbreviations t ON g.home_team_id = t.team_id
                LIMIT {sample_size}
            """).fetchall()

            if not sample_teams:
                issues.append({"type": "no_team_samples", "severity": "warning"})
            else:
                logger.info(f"Verified {len(sample_teams)} team mappings in games")

        except Exception as e:
            logger.error(f"Error checking data integrity: {e}")
            issues.append({"type": "integrity_error", "message": str(e), "severity": "error"})

        return issues

    def generate_validation_report(self) -> str:
        """Generate comprehensive validation report."""
        lines = []
        lines.append("=" * 60)
        lines.append("MAPPING VALIDATION REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Player mapping issues
        player_issues = self.validate_player_mappings()
        lines.append(f"Player Mapping Issues: {len(player_issues)}")
        for issue in player_issues[:10]:
            lines.append(f"  [{issue['severity'].upper()}] {issue['type']}: {issue}")
        if len(player_issues) > 10:
            lines.append(f"  ... and {len(player_issues) - 10} more")
        lines.append("")

        # Team mapping issues
        team_issues = self.validate_team_mappings()
        lines.append(f"Team Mapping Issues: {len(team_issues)}")
        for issue in team_issues[:10]:
            lines.append(f"  [{issue['severity'].upper()}] {issue['type']}: {issue}")
        if len(team_issues) > 10:
            lines.append(f"  ... and {len(team_issues) - 10} more")
        lines.append("")

        # Data integrity check
        integrity_issues = self.check_data_integrity()
        lines.append(f"Data Integrity Issues: {len(integrity_issues)}")
        for issue in integrity_issues:
            lines.append(f"  [{issue['severity'].upper()}] {issue['type']}")
        lines.append("")

        return "\n".join(lines)

    def run_all_validations(self):
        """Run all validation checks."""
        player_issues = self.validate_player_mappings()
        team_issues = self.validate_team_mappings()
        integrity_issues = self.check_data_integrity()

        all_issues = player_issues + team_issues + integrity_issues

        errors = sum(1 for i in all_issues if i.get("severity") == "error")
        warnings = sum(1 for i in all_issues if i.get("severity") == "warning")

        self.validation_results = {
            "player_issues": player_issues,
            "team_issues": team_issues,
            "integrity_issues": integrity_issues,
            "total_issues": len(all_issues),
            "errors": errors,
            "warnings": warnings,
            "valid": errors == 0,
        }

        logger.info(f"Validation complete: {errors} errors, {warnings} warnings")

        return self.validation_results
