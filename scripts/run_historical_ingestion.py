#!/usr/bin/env python3
"""
Main integration script for ingesting historical NBA data.

This script orchestrates the complete ingestion pipeline:
1. Creates database schema
2. Builds ID mappings
3. Loads reference data (teams, players)
4. Loads transaction data (games, box scores)
5. Loads statistics (season totals, advanced stats)
6. Loads awards and draft data
7. Validates all data

Usage:
    python scripts/run_historical_ingestion.py --full
    python scripts/run_historical_ingestion.py --phase reference
    python scripts/run_historical_ingestion.py --validate-only
"""

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.ingestion.config import PLANNING_CSV_DIR, PLANNING_PARQ_DIR
from scripts.ingestion.database import (
    close_ingestion_connection,
    get_ingestion_connection,
)
from scripts.ingestion.loaders import (
    AwardsLoader,
    DraftLoader,
    GamesLoader,
    ParquetLoader,
    PlayerGameStatsLoader,
    PlayerLoader,
    PlayerSeasonStatsLoader,
    TeamGameStatsLoader,
    TeamLoader,
    TeamSeasonStatsLoader,
)
from scripts.ingestion.logger import (
    configure_root_logger,
    enable_verbose_logging,
    get_logger,
    log_stage,
    log_step,
)
from scripts.ingestion.mapping.id_resolver import IDResolver
from scripts.ingestion.validation import ConsistencyChecker, DataValidator, ValidationReport

logger = get_logger("historical_ingestion")


@dataclass
class LoaderConfig:
    """Configuration for a data loader."""

    name: str
    loader_class: type
    file_path: Path | None
    table_name: str
    loader_args: tuple = ()
    loader_kwargs: dict | None = None

    def __post_init__(self):
        if self.loader_kwargs is None:
            self.loader_kwargs = {}

    def create_loader(self):
        """Create a loader instance."""
        if self.file_path:
            return self.loader_class(
                self.file_path, self.table_name, *self.loader_args, **self.loader_kwargs
            )
        return self.loader_class(self.table_name, *self.loader_args, **self.loader_kwargs)


# Define phase configurations
REFERENCE_LOADERS = [
    LoaderConfig(
        name="Teams",
        loader_class=TeamLoader,
        file_path=PLANNING_CSV_DIR / "Team_Abbrev.csv",
        table_name="team_abbreviations",
    ),
    LoaderConfig(
        name="Players",
        loader_class=PlayerLoader,
        file_path=PLANNING_CSV_DIR / "Player_Career_Info.csv",
        table_name="player_master",
    ),
]

GAME_LOADERS = [
    LoaderConfig(
        name="Games",
        loader_class=GamesLoader,
        file_path=PLANNING_CSV_DIR / "Games.csv",
        table_name="games_historical",
    ),
    LoaderConfig(
        name="Player Game Statistics",
        loader_class=PlayerGameStatsLoader,
        file_path=PLANNING_CSV_DIR / "PlayerStatistics.csv",
        table_name="player_game_statistics",
    ),
    LoaderConfig(
        name="Team Game Statistics",
        loader_class=TeamGameStatsLoader,
        file_path=PLANNING_CSV_DIR / "TeamStatistics.csv",
        table_name="team_game_statistics",
    ),
]

SEASON_STAT_LOADERS = [
    # Player season stats
    LoaderConfig(
        name="Totals",
        loader_class=PlayerSeasonStatsLoader,
        file_path=PLANNING_CSV_DIR / "Player_Totals.csv",
        table_name="player_season_totals",
        loader_args=("totals",),
    ),
    LoaderConfig(
        name="Per Game",
        loader_class=PlayerSeasonStatsLoader,
        file_path=PLANNING_CSV_DIR / "Player_Per_Game.csv",
        table_name="player_season_per_game",
        loader_args=("per_game",),
    ),
    LoaderConfig(
        name="Advanced",
        loader_class=PlayerSeasonStatsLoader,
        file_path=PLANNING_CSV_DIR / "Advanced.csv",
        table_name="player_season_advanced",
        loader_args=("advanced",),
    ),
    LoaderConfig(
        name="Per 100 Poss",
        loader_class=PlayerSeasonStatsLoader,
        file_path=PLANNING_CSV_DIR / "Per_100_Poss.csv",
        table_name="player_season_per_100",
        loader_args=("per_100_poss",),
    ),
    LoaderConfig(
        name="Per 36 Minutes",
        loader_class=PlayerSeasonStatsLoader,
        file_path=PLANNING_CSV_DIR / "Per_36_Minutes.csv",
        table_name="player_season_per_36",
        loader_args=("per_36_minutes",),
    ),
    LoaderConfig(
        name="Shooting",
        loader_class=PlayerSeasonStatsLoader,
        file_path=PLANNING_CSV_DIR / "Player_Shooting.csv",
        table_name="player_season_shooting",
        loader_args=("shooting",),
    ),
    LoaderConfig(
        name="Play By Play",
        loader_class=PlayerSeasonStatsLoader,
        file_path=PLANNING_CSV_DIR / "Player_Play_By_Play.csv",
        table_name="player_season_play_by_play",
        loader_args=("play_by_play",),
    ),
    # Team season stats
    LoaderConfig(
        name="Team Totals",
        loader_class=TeamSeasonStatsLoader,
        file_path=PLANNING_CSV_DIR / "Team_Totals.csv",
        table_name="team_season_totals",
        loader_args=("totals",),
    ),
    LoaderConfig(
        name="Team Summaries",
        loader_class=TeamSeasonStatsLoader,
        file_path=PLANNING_CSV_DIR / "Team_Summaries.csv",
        table_name="team_season_summaries",
        loader_args=("summaries",),
    ),
    LoaderConfig(
        name="Team Per Game",
        loader_class=TeamSeasonStatsLoader,
        file_path=PLANNING_CSV_DIR / "Team_Stats_Per_Game.csv",
        table_name="team_season_per_game",
        loader_args=("per_game",),
    ),
    LoaderConfig(
        name="Opponent Totals",
        loader_class=TeamSeasonStatsLoader,
        file_path=PLANNING_CSV_DIR / "Opponent_Totals.csv",
        table_name="opponent_season_totals",
        loader_args=("opponent_totals",),
    ),
]

AWARD_LOADERS = [
    LoaderConfig(
        name="All-Star Selections",
        loader_class=AwardsLoader,
        file_path=PLANNING_CSV_DIR / "All-Star Selections.csv",
        table_name="awards_all_star",
        loader_args=("all_star",),
    ),
    LoaderConfig(
        name="End of Season Teams",
        loader_class=AwardsLoader,
        file_path=PLANNING_CSV_DIR / "End_of_Season_Teams.csv",
        table_name="awards_end_of_season_teams",
        loader_args=("end_of_season_teams",),
    ),
    LoaderConfig(
        name="End of Season Voting",
        loader_class=AwardsLoader,
        file_path=PLANNING_CSV_DIR / "End_of_Season_Teams_(Voting).csv",
        table_name="awards_end_of_season_voting",
        loader_args=("end_of_season_voting",),
    ),
    LoaderConfig(
        name="Award Shares",
        loader_class=AwardsLoader,
        file_path=PLANNING_CSV_DIR / "Player_Award_Shares.csv",
        table_name="awards_award_shares",
        loader_args=("award_shares",),
    ),
    LoaderConfig(
        name="Draft History",
        loader_class=DraftLoader,
        file_path=PLANNING_CSV_DIR / "Draft_Pick_History.csv",
        table_name="draft_pick_history",
    ),
]

PARQUET_LOADERS = [
    LoaderConfig(
        name="Roster Data",
        loader_class=ParquetLoader,
        file_path=PLANNING_PARQ_DIR / "roster.parq",
        table_name="player_demographics",
        loader_args=("roster",),
    ),
]


def create_schema(conn) -> bool:
    """Create all database tables from SQL files."""
    log_stage(logger, "Schema Creation", "started")
    logger.info("Creating database schema...")

    schema_dir = Path(__file__).parent / "ingestion" / "schema"
    sql_files = sorted(schema_dir.glob("*.sql"))

    if not sql_files:
        logger.error(f"No SQL files found in {schema_dir}")
        log_stage(logger, "Schema Creation", "failed")
        return False

    logger.debug(f"Found {len(sql_files)} SQL schema files")

    for idx, sql_file in enumerate(sql_files, 1):
        log_step(logger, idx, len(sql_files), f"Executing {sql_file.name}")
        try:
            logger.debug(f"Opening and reading {sql_file}")
            sql = sql_file.read_text(encoding="utf-8")
            conn.execute(sql)
            logger.info(f"  [OK] {sql_file.name}")
        except Exception as e:
            logger.error(f"  [FAILED] {sql_file.name}: {e}")
            log_stage(logger, "Schema Creation", "failed")
            return False

    logger.info(f"Schema created successfully ({len(sql_files)} files)")
    log_stage(logger, "Schema Creation", "completed")
    return True


def build_id_mappings(conn) -> bool:
    """Build ID mapping tables."""
    log_stage(logger, "ID Mappings", "started")
    logger.info("Building ID mappings...")

    try:
        resolver = IDResolver(conn)
        logger.debug("IDResolver initialized")

        resolver.build_all_mappings()
        logger.debug("build_all_mappings() completed")

        # Check for unresolved IDs
        unresolved = resolver.get_unresolved_count()
        if unresolved["players"] > 0 or unresolved["teams"] > 0:
            logger.warning(f"Found unresolved IDs: {unresolved}")
            resolver.generate_unresolved_report()
        else:
            logger.info("All IDs resolved successfully")

        log_stage(logger, "ID Mappings", "completed")
        return True

    except Exception as e:
        logger.error(f"Failed to build ID mappings: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "ID Mappings", "failed")
        return False


def _run_loader_phase(
    logger, loaders: list[LoaderConfig], dry_run: bool, warning_message: str | None = None
) -> dict:
    """Run a phase of data loaders.

    Args:
        logger: Logger instance
        loaders: List of LoaderConfig objects
        dry_run: If True, don't actually load data
        warning_message: Optional warning message to display before loading

    Returns:
        Dictionary with stats about the phase
    """
    stats = {"tables": [], "rows": 0}

    if warning_message:
        logger.info(warning_message)

    total_steps = len(loaders)

    for idx, config in enumerate(loaders, 1):
        log_step(logger, idx, total_steps, f"Loading {config.name}")
        logger.debug(f"Loading from {config.file_path}")

        if not dry_run:
            try:
                loader = config.create_loader()
                loader.load()
            except Exception as e:
                logger.error(f"Failed to load {config.name}: {e}")
                raise

        stats["tables"].append(config.table_name)
        logger.info(f"  [OK] {config.name} loaded")

    return stats


def run_phase_1_reference_data(conn, dry_run: bool = False) -> dict:
    """Load reference data (teams, players)."""
    log_stage(logger, "Phase 1: Loading Reference Data", "started")

    try:
        stats = _run_loader_phase(logger, REFERENCE_LOADERS, dry_run)

        # Add virtual tables for tracking
        stats["tables"].extend(["player_demographics", "player_season_info"])

        log_stage(logger, "Phase 1: Loading Reference Data", "completed")
        return stats

    except Exception as e:
        logger.error(f"Phase 1 failed: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "Phase 1: Loading Reference Data", "failed")
        return {"tables": [], "rows": 0}


def run_phase_2_games_data(conn, dry_run: bool = False) -> dict:
    """Load game-level transaction data."""
    log_stage(logger, "Phase 2: Loading Game Data", "started")

    try:
        stats = _run_loader_phase(
            logger,
            GAME_LOADERS,
            dry_run,
            warning_message="This may take a while due to large file size...",
        )

        log_stage(logger, "Phase 2: Loading Game Data", "completed")
        return stats

    except Exception as e:
        logger.error(f"Phase 2 failed: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "Phase 2: Loading Game Data", "failed")
        return {"tables": [], "rows": 0}


def run_phase_3_season_stats(conn, dry_run: bool = False) -> dict:
    """Load aggregated season statistics."""
    log_stage(logger, "Phase 3: Loading Season Statistics", "started")

    try:
        stats = _run_loader_phase(logger, SEASON_STAT_LOADERS, dry_run)

        log_stage(logger, "Phase 3: Loading Season Statistics", "completed")
        return stats

    except Exception as e:
        logger.error(f"Phase 3 failed: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "Phase 3: Loading Season Statistics", "failed")
        return {"tables": [], "rows": 0}


def run_phase_4_awards_data(conn, dry_run: bool = False) -> dict:
    """Load awards and draft data."""
    log_stage(logger, "Phase 4: Loading Awards and Draft Data", "started")

    try:
        stats = _run_loader_phase(logger, AWARD_LOADERS, dry_run)

        log_stage(logger, "Phase 4: Loading Awards and Draft Data", "completed")
        return stats

    except Exception as e:
        logger.error(f"Phase 4 failed: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "Phase 4: Loading Awards and Draft Data", "failed")
        return {"tables": [], "rows": 0}


def run_phase_5_parquet_supplemental(conn, dry_run: bool = False) -> dict:
    """Load supplemental data from parquet files."""
    log_stage(logger, "Phase 5: Loading Parquet Supplemental Data", "started")

    try:
        stats = _run_loader_phase(logger, PARQUET_LOADERS, dry_run)

        # Note about other parquet files
        logger.info("  (Other parquet files are subsets of CSV data)")

        log_stage(logger, "Phase 5: Loading Parquet Supplemental Data", "completed")
        return stats

    except Exception as e:
        logger.error(f"Phase 5 failed: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "Phase 5: Loading Parquet Supplemental Data", "failed")
        return {"tables": [], "rows": 0}


def run_validation(conn, full: bool = True) -> bool:
    """Run data validation."""
    log_stage(logger, "Validation", "started")

    try:
        report = ValidationReport("Historical NBA Data Validation")

        # Run data validator
        log_step(logger, 1, 2 if full else 1, "Running data validations")
        logger.debug("Initializing DataValidator...")
        validator = DataValidator(conn)
        validation_results = validator.run_all_validations()
        logger.debug(f"Completed {len(validation_results)} validation checks")

        for validation in validation_results:
            report.add_section(
                validation.check_name,
                [{"severity": i.severity.value, "message": i.message} for i in validation.issues],
                "failed" if validation.has_errors() else "passed",
            )

        # Run consistency checks
        if full:
            log_step(logger, 2, 2, "Running consistency checks")
            logger.debug("Initializing ConsistencyChecker...")
            checker = ConsistencyChecker(conn)
            checker.run_all_checks()
            logger.debug(f"Completed {len(checker.results)} consistency checks")

            for result in checker.results:
                report.add_section(
                    f"Consistency: {result.check_name}",
                    result.discrepancies,
                    "passed" if result.passed else "failed",
                )

        # Print summary
        logger.info("Generating validation summary...")
        report.print_summary()

        # Save reports
        logger.debug("Saving validation reports...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = Path("validation_reports")
        report_dir.mkdir(exist_ok=True)

        report.generate_html_report(report_dir / f"validation_{timestamp}.html")
        report.generate_markdown_report(report_dir / f"validation_{timestamp}.md")
        report.save_json(report_dir / f"validation_{timestamp}.json")

        summary = report.generate_summary()
        if summary["status"] == "failed":
            logger.warning(f"Validation found {summary['total_issues']} issues")
            log_stage(logger, "Validation", "failed")
            return False
        else:
            logger.info("Validation passed!")
            log_stage(logger, "Validation", "completed")
            return True

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "Validation", "failed")
        return False


# Phase registry for dynamic execution
PHASE_REGISTRY: dict[str, Callable] = {
    "schema": create_schema,
    "mapping": build_id_mappings,
    "reference": run_phase_1_reference_data,
    "games": run_phase_2_games_data,
    "stats": run_phase_3_season_stats,
    "awards": run_phase_4_awards_data,
    "parquet": run_phase_5_parquet_supplemental,
}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest historical NBA data into database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full ingestion
  python scripts/run_historical_ingestion.py --full

  # Run specific phase only
  python scripts/run_historical_ingestion.py --phase reference

  # Validate existing data only
  python scripts/run_historical_ingestion.py --validate-only

  # Dry run (don't actually load data)
  python scripts/run_historical_ingestion.py --full --dry-run

  # Verbose logging with detailed progress
  python scripts/run_historical_ingestion.py --full --verbose
        """,
    )

    parser.add_argument("--full", action="store_true", help="Run complete ingestion pipeline")

    parser.add_argument(
        "--phase",
        choices=list(PHASE_REGISTRY.keys()),
        help="Run only specific phase",
    )

    parser.add_argument(
        "--validate-only", action="store_true", help="Only run validation on existing data"
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Enable verbose logging if requested (before anything else)
    if args.verbose:
        enable_verbose_logging()
    else:
        configure_root_logger("INFO")

    logger.debug(f"Command line args: {args}")

    # Validate-only mode
    if args.validate_only:
        logger.info("Running validation only...")
        conn = get_ingestion_connection()
        try:
            success = run_validation(conn, full=True)
            sys.exit(0 if success else 1)
        finally:
            close_ingestion_connection()
        return

    # Determine which phases to run
    if args.full:
        phases = list(PHASE_REGISTRY.keys())
    elif args.phase:
        phases = [args.phase]
    else:
        parser.print_help()
        sys.exit(1)

    logger.debug(f"Phases to run: {phases}")

    # Run ingestion
    start_time = time.time()
    conn = get_ingestion_connection()

    try:
        all_stats = []

        for phase in phases:
            logger.debug(f"Starting {phase} phase")

            phase_func = PHASE_REGISTRY[phase]

            # Schema and mapping phases return bool, data phases return dict
            if phase in ("schema", "mapping"):
                success = phase_func(conn)
                if not success:
                    logger.error(f"{phase} failed, aborting")
                    sys.exit(1)
            else:
                stats = phase_func(conn, args.dry_run)
                all_stats.append((phase.replace("_", " ").title(), stats))

            logger.debug(f"{phase} phase completed")

        # Summary
        elapsed = time.time() - start_time
        log_stage(logger, "INGESTION COMPLETE", "completed")
        logger.info(f"Total time: {elapsed:.1f} seconds")
        logger.debug(f"Completed {len(all_stats)} data loading phases")

        for name, stats in all_stats:
            logger.info(f"\n{name}:")
            logger.info(f"  Tables: {', '.join(stats['tables'])}")
            logger.debug(f"  Tables loaded for {name}: {len(stats['tables'])}")

        # Run validation if full ingestion
        if args.full and not args.dry_run:
            logger.debug("Running post-ingestion validation...")
            run_validation(conn)

        logger.info("\n[SUCCESS] Ingestion completed successfully!")

    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        logger.debug("Closing database connection...")
        close_ingestion_connection()


if __name__ == "__main__":
    main()
