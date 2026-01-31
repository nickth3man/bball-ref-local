"""Cross-source consistency checks for validation."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConsistencyResult:
    """Result of a consistency check."""

    def __init__(self, check_name: str, passed: bool, details: dict[str, Any] | None = None):
        self.check_name = check_name
        self.passed = passed
        self.details = details or {}
        self.discrepancies = []

    def add_discrepancy(self, expected: Any, actual: Any, context: str = ""):
        """Add a discrepancy to the result."""
        self.discrepancies.append({"expected": expected, "actual": actual, "context": context})

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "discrepancy_count": len(self.discrepancies),
            "discrepancies": self.discrepancies[:10],  # Limit to first 10
        }


class ConsistencyChecker:
    """Checks consistency between overlapping data sources."""

    def __init__(self, conn):
        self.conn = conn
        self.results: list[ConsistencyResult] = []

    def check_player_totals_consistency(self) -> ConsistencyResult:
        """Verify Player_Totals.csv matches sum of PlayerStatistics.csv."""
        result = ConsistencyResult("player_totals_consistency", True)

        try:
            # Query to compare aggregated game stats with season totals
            query = """
            WITH game_totals AS (
                SELECT 
                    season,
                    player_id,
                    COUNT(*) as games_from_games,
                    SUM(points) as points_from_games,
                    SUM(field_goals_made) as fg_from_games,
                    SUM(assists) as ast_from_games
                FROM player_game_statistics
                GROUP BY season, player_id
            ),
            season_totals AS (
                SELECT 
                    season,
                    player_id,
                    games_played as games_from_totals,
                    points as points_from_totals,
                    field_goals as fg_from_totals,
                    assists as ast_from_totals
                FROM player_season_totals
            )
            SELECT 
                g.season,
                g.player_id,
                g.games_from_games,
                s.games_from_totals,
                g.points_from_games,
                s.points_from_totals,
                ABS(g.games_from_games - s.games_from_totals) as game_diff,
                ABS(g.points_from_games - s.points_from_totals) as point_diff
            FROM game_totals g
            JOIN season_totals s ON g.season = s.season AND g.player_id = s.player_id
            WHERE ABS(g.games_from_games - s.games_from_totals) > 2
               OR ABS(g.points_from_games - s.points_from_totals) > 50
            LIMIT 100
            """

            discrepancies = self.conn.execute(query).fetchall()

            if discrepancies:
                result.passed = False
                for row in discrepancies:
                    result.add_discrepancy(
                        expected=f"Games: {row[3]}, Points: {row[5]}",
                        actual=f"Games: {row[2]}, Points: {row[4]}",
                        context=f"Season {row[0]}, Player {row[1]}",
                    )
                logger.warning(f"Found {len(discrepancies)} player totals discrepancies")
            else:
                logger.info("Player totals consistency check passed")

        except Exception as e:
            logger.error(f"Error in player totals consistency check: {e}")
            result.passed = False
            result.add_discrepancy("Check failed", str(e), "exception")

        self.results.append(result)
        return result

    def check_game_scores_consistency(self) -> ConsistencyResult:
        """Verify Games.csv scores match TeamStatistics.csv."""
        result = ConsistencyResult("game_scores_consistency", True)

        try:
            query = """
            SELECT 
                g.game_id,
                g.home_score,
                g.away_score,
                ht.team_score as home_from_team_stats,
                at.team_score as away_from_team_stats
            FROM games_historical g
            LEFT JOIN team_game_statistics ht ON g.game_id = ht.game_id AND ht.is_home = TRUE
            LEFT JOIN team_game_statistics at ON g.game_id = at.game_id AND at.is_home = FALSE
            WHERE (g.home_score != ht.team_score OR g.away_score != at.team_score)
               AND ht.team_score IS NOT NULL
            LIMIT 100
            """

            discrepancies = self.conn.execute(query).fetchall()

            if discrepancies:
                result.passed = False
                for row in discrepancies:
                    result.add_discrepancy(
                        expected=f"Home: {row[1]}, Away: {row[2]}",
                        actual=f"Home: {row[3]}, Away: {row[4]}",
                        context=f"Game {row[0]}",
                    )
                logger.warning(f"Found {len(discrepancies)} game score discrepancies")
            else:
                logger.info("Game scores consistency check passed")

        except Exception as e:
            logger.error(f"Error in game scores consistency check: {e}")
            result.passed = False
            result.add_discrepancy("Check failed", str(e), "exception")

        self.results.append(result)
        return result

    def check_team_totals_consistency(self) -> ConsistencyResult:
        """Verify team season totals match sum of game stats."""
        result = ConsistencyResult("team_totals_consistency", True)

        try:
            query = """
            WITH game_totals AS (
                SELECT 
                    season,
                    team_id,
                    COUNT(*) as games,
                    SUM(team_score) as points_for,
                    SUM(opponent_score) as points_against
                FROM team_game_statistics
                GROUP BY season, team_id
            ),
            season_totals AS (
                SELECT 
                    season,
                    team_id,
                    games,
                    points as points_for_st
                FROM team_season_totals
            )
            SELECT 
                g.season,
                g.team_id,
                g.games,
                s.games as games_st,
                g.points_for,
                s.points_for_st
            FROM game_totals g
            JOIN season_totals s ON g.season = s.season AND g.team_id = s.team_id
            WHERE ABS(g.games - s.games) > 2
               OR ABS(g.points_for - s.points_for_st) > 100
            LIMIT 50
            """

            discrepancies = self.conn.execute(query).fetchall()

            if discrepancies:
                result.passed = False
                for row in discrepancies:
                    result.add_discrepancy(
                        expected=f"Games: {row[3]}, Points: {row[5]}",
                        actual=f"Games: {row[2]}, Points: {row[4]}",
                        context=f"Season {row[0]}, Team {row[1]}",
                    )
                logger.warning(f"Found {len(discrepancies)} team totals discrepancies")
            else:
                logger.info("Team totals consistency check passed")

        except Exception as e:
            logger.error(f"Error in team totals consistency check: {e}")
            result.passed = False
            result.add_discrepancy("Check failed", str(e), "exception")

        self.results.append(result)
        return result

    def check_player_season_completeness(self) -> ConsistencyResult:
        """Check that all players in player_season_stats have player records."""
        result = ConsistencyResult("player_season_completeness", True)

        try:
            query = """
            SELECT DISTINCT ps.player_id
            FROM player_season_totals ps
            LEFT JOIN player_master pm ON ps.player_id = pm.player_id
            WHERE pm.player_id IS NULL
            LIMIT 100
            """

            orphaned = self.conn.execute(query).fetchall()

            if orphaned:
                result.passed = False
                for row in orphaned:
                    result.add_discrepancy(
                        expected="Player exists in player_master",
                        actual="Player not found",
                        context=f"Player ID: {row[0]}",
                    )
                logger.warning(f"Found {len(orphaned)} orphaned player season records")
            else:
                logger.info("Player season completeness check passed")

        except Exception as e:
            logger.error(f"Error in player season completeness check: {e}")
            result.passed = False
            result.add_discrepancy("Check failed", str(e), "exception")

        self.results.append(result)
        return result

    def check_awards_consistency(self) -> ConsistencyResult:
        """Verify award winners match player records."""
        result = ConsistencyResult("awards_consistency", True)

        try:
            query = """
            SELECT DISTINCT award_season, award_name, player_id
            FROM player_award_shares
            WHERE player_id NOT IN (SELECT player_id FROM player_master)
            LIMIT 50
            """

            orphaned = self.conn.execute(query).fetchall()

            if orphaned:
                result.passed = False
                for row in orphaned:
                    result.add_discrepancy(
                        expected="Player exists in player_master",
                        actual="Player not found",
                        context=f"Award: {row[1]} {row[0]}, Player: {row[2]}",
                    )
                logger.warning(f"Found {len(orphaned)} orphaned award records")
            else:
                logger.info("Awards consistency check passed")

        except Exception as e:
            logger.error(f"Error in awards consistency check: {e}")
            result.passed = False
            result.add_discrepancy("Check failed", str(e), "exception")

        self.results.append(result)
        return result

    def check_draft_consistency(self) -> ConsistencyResult:
        """Verify draft picks have player records."""
        result = ConsistencyResult("draft_consistency", True)

        try:
            query = """
            SELECT season, overall_pick, player_id, player_name
            FROM draft_pick_history
            WHERE player_id IS NOT NULL
              AND player_id NOT IN (SELECT player_id FROM player_master)
            LIMIT 50
            """

            orphaned = self.conn.execute(query).fetchall()

            if orphaned:
                result.passed = False
                for row in orphaned:
                    result.add_discrepancy(
                        expected="Player exists in player_master",
                        actual="Player not found",
                        context=f"Draft {row[0]} Pick #{row[1]}: {row[3]}",
                    )
                logger.warning(f"Found {len(orphaned)} orphaned draft records")
            else:
                logger.info("Draft consistency check passed")

        except Exception as e:
            logger.error(f"Error in draft consistency check: {e}")
            result.passed = False
            result.add_discrepancy("Check failed", str(e), "exception")

        self.results.append(result)
        return result

    def run_all_checks(self) -> list[ConsistencyResult]:
        """Run all consistency checks."""
        logger.info("Running all consistency checks...")

        self.check_player_totals_consistency()
        self.check_game_scores_consistency()
        self.check_team_totals_consistency()
        self.check_player_season_completeness()
        self.check_awards_consistency()
        self.check_draft_consistency()

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        logger.info(f"Consistency checks complete: {passed}/{total} passed")

        return self.results

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all consistency checks."""
        return {
            "total_checks": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "checks": [r.to_dict() for r in self.results],
        }
