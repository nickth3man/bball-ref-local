"""Orchestrator script to run all NBA data ETL pipelines.

Usage:
    python scripts/run_all_etl.py
    python scripts/run_all_etl.py --season 2023-24
    python scripts/run_all_etl.py --skip-teams --skip-players

Runs ETLs in order: teams → players → games → stats
Provides error handling and summary report.
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.database import close_db_connection, set_app_metadata
from scripts.etl_games import run_etl as run_games_etl
from scripts.etl_players import run_etl as run_players_etl
from scripts.etl_stats import run_etl as run_stats_etl

# Import ETL modules
from scripts.etl_teams import run_etl as run_teams_etl
from scripts.logging_utils import enable_verbose_logging, log_stage, setup_etl_logging

# Configure logging using unified system
logger = setup_etl_logging(__name__)


def run_etl_pipeline(
    season: str | None = None,
    season_type: str = "Regular Season",
    skip_teams: bool = False,
    skip_players: bool = False,
    skip_games: bool = False,
    skip_stats: bool = False,
    batch_size: int = 1000,
) -> dict[str, Any]:
    """Run the complete ETL pipeline in order.

    Order: teams → players → games → stats

    Args:
        season: Season string (e.g., '2024-25'). Uses current season if None.
        season_type: Type of season ('Regular Season' or 'Playoffs').
        skip_teams: Skip teams ETL.
        skip_players: Skip players ETL.
        skip_games: Skip games ETL.
        skip_stats: Skip stats ETL.
        batch_size: Batch size for stats inserts.

    Returns:
        Dictionary with ETL results for each step.
    """
    start_time = datetime.now(UTC)
    results: dict[str, Any] = {
        "start_time": start_time.isoformat(),
        "season": season,
        "season_type": season_type,
        "steps": {},
        "total_loaded": 0,
        "status": "success",
        "errors": [],
    }

    # Step 1: Teams ETL
    if not skip_teams:
        logger.info("=" * 50)
        logger.info("STEP 1/4: Teams ETL")
        logger.info("=" * 50)
        try:
            teams_result = run_teams_etl()
            results["steps"]["teams"] = teams_result
            results["total_loaded"] += teams_result.get("loaded", 0)

            if teams_result["status"] != "success":
                results["errors"].append(f"Teams ETL failed: {teams_result.get('error')}")
                logger.error("Teams ETL failed, continuing with next steps...")
        except Exception:
            error_msg = "Teams ETL error"
            results["errors"].append(error_msg)
            results["steps"]["teams"] = {"status": "failed", "error": error_msg}
            logger.exception(error_msg)
    else:
        logger.info("Skipping teams ETL")
        results["steps"]["teams"] = {"status": "skipped"}

    # Step 2: Players ETL
    if not skip_players:
        logger.info("=" * 50)
        logger.info("STEP 2/4: Players ETL")
        logger.info("=" * 50)
        try:
            players_result = run_players_etl(active_only=True)
            results["steps"]["players"] = players_result
            results["total_loaded"] += players_result.get("loaded", 0)

            if players_result["status"] != "success":
                results["errors"].append(f"Players ETL failed: {players_result.get('error')}")
                logger.error("Players ETL failed, continuing with next steps...")
        except Exception:
            error_msg = "Players ETL error"
            results["errors"].append(error_msg)
            results["steps"]["players"] = {"status": "failed", "error": error_msg}
            logger.exception(error_msg)
    else:
        logger.info("Skipping players ETL")
        results["steps"]["players"] = {"status": "skipped"}

    # Step 3: Games ETL
    if not skip_games:
        logger.info("=" * 50)
        logger.info("STEP 3/4: Games ETL")
        logger.info("=" * 50)
        try:
            games_result = run_games_etl(season=season, season_type=season_type)
            results["steps"]["games"] = games_result
            results["total_loaded"] += games_result.get("loaded", 0)

            if games_result["status"] != "success":
                results["errors"].append(f"Games ETL failed: {games_result.get('error')}")
                logger.error("Games ETL failed, continuing with next steps...")
        except Exception:
            error_msg = "Games ETL error"
            results["errors"].append(error_msg)
            results["steps"]["games"] = {"status": "failed", "error": error_msg}
            logger.exception(error_msg)
    else:
        logger.info("Skipping games ETL")
        results["steps"]["games"] = {"status": "skipped"}

    # Step 4: Stats ETL
    if not skip_stats:
        logger.info("=" * 50)
        logger.info("STEP 4/4: Player Stats ETL")
        logger.info("=" * 50)
        try:
            stats_result = run_stats_etl(
                season=season, season_type=season_type, batch_size=batch_size
            )
            results["steps"]["stats"] = stats_result
            results["total_loaded"] += stats_result.get("loaded", 0)

            if stats_result["status"] != "success":
                results["errors"].append(f"Stats ETL failed: {stats_result.get('error')}")
                logger.error("Stats ETL failed")
        except Exception:
            error_msg = "Stats ETL error"
            results["errors"].append(error_msg)
            results["steps"]["stats"] = {"status": "failed", "error": error_msg}
            logger.exception(error_msg)
    else:
        logger.info("Skipping stats ETL")
        results["steps"]["stats"] = {"status": "skipped"}

    # Calculate duration
    end_time = datetime.now(UTC)
    duration = (end_time - start_time).total_seconds()
    results["end_time"] = end_time.isoformat()
    results["duration_seconds"] = duration

    # Update overall status
    if results["errors"]:
        results["status"] = "completed_with_errors"

    # Update metadata
    try:
        set_app_metadata("last_etl_run", end_time.isoformat())
        set_app_metadata("last_etl_season", season or "current")
        set_app_metadata("last_etl_status", results["status"])
    except Exception as e:
        logger.warning(f"Failed to update metadata: {e}")
    finally:
        close_db_connection()

    return results


def print_summary(results: dict[str, Any]) -> None:
    """Print ETL execution summary.

    Args:
        results: ETL results dictionary.
    """
    logger.info("=" * 50)
    logger.info("ETL PIPELINE SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Season: {results.get('season', 'N/A')}")
    logger.info(f"Season Type: {results.get('season_type', 'N/A')}")
    logger.info(f"Status: {results.get('status', 'unknown')}")
    logger.info(f"Duration: {results.get('duration_seconds', 0):.2f} seconds")
    logger.info("")

    # Print each step
    for step_name, step_result in results.get("steps", {}).items():
        status = step_result.get("status", "unknown")
        extracted = step_result.get("extracted", 0)
        loaded = step_result.get("loaded", 0)

        status_icon = "✓" if status == "success" else "✗" if status == "failed" else "○"
        logger.info(f"{status_icon} {step_name.upper()}: {status}")

        if status == "success":
            logger.info(f"  Extracted: {extracted:,}")
            logger.info(f"  Loaded: {loaded:,}")
        elif status == "failed":
            error = step_result.get("error", "Unknown error")
            logger.info(f"  Error: {error}")

    logger.info("")
    logger.info(f"Total records loaded: {results.get('total_loaded', 0):,}")

    if results.get("errors"):
        logger.info("")
        logger.info("ERRORS:")
        for error in results["errors"]:
            logger.info(f"  - {error}")


def main() -> int:
    """Main entry point for the ETL orchestrator.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(
        description="Run all NBA data ETL pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_all_etl.py
  python scripts/run_all_etl.py --season 2023-24
  python scripts/run_all_etl.py --season-type Playoffs
  python scripts/run_all_etl.py --skip-teams --skip-players
  python scripts/run_all_etl.py --batch-size 500
        """,
    )

    parser.add_argument(
        "--season",
        "-s",
        type=str,
        default=None,
        help="Season string (e.g., '2024-25'). Uses current season if not specified.",
    )
    parser.add_argument(
        "--season-type",
        "-t",
        type=str,
        choices=["Regular Season", "Playoffs"],
        default="Regular Season",
        help="Type of season (default: Regular Season)",
    )
    parser.add_argument("--skip-teams", action="store_true", help="Skip teams ETL")
    parser.add_argument("--skip-players", action="store_true", help="Skip players ETL")
    parser.add_argument("--skip-games", action="store_true", help="Skip games ETL")
    parser.add_argument("--skip-stats", action="store_true", help="Skip player stats ETL")
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=1000,
        help="Batch size for stats inserts (default: 1000)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        enable_verbose_logging()

    # Validate that not all steps are skipped
    if all([args.skip_teams, args.skip_players, args.skip_games, args.skip_stats]):
        logger.error("Error: Cannot skip all ETL steps")
        return 1

    logger.info("Starting NBA data ETL pipeline...")

    # Run the pipeline
    results = run_etl_pipeline(
        season=args.season,
        season_type=args.season_type,
        skip_teams=args.skip_teams,
        skip_players=args.skip_players,
        skip_games=args.skip_games,
        skip_stats=args.skip_stats,
        batch_size=args.batch_size,
    )

    # Print summary
    print_summary(results)

    # Return appropriate exit code
    if results["status"] == "success":
        logger.info("ETL pipeline completed successfully")
        return 0
    elif results["status"] == "completed_with_errors":
        logger.warning("ETL pipeline completed with errors")
        return 0  # Still return 0 as some data was loaded
    else:
        logger.error("ETL pipeline failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
