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
from datetime import datetime
from pathlib import Path

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
    total_steps = len(sql_files)

    for idx, sql_file in enumerate(sql_files, 1):
        log_step(logger, idx, total_steps, f"Executing {sql_file.name}")
        try:
            logger.debug(f"Opening and reading {sql_file}")
            with open(sql_file) as f:
                sql = f.read()
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

        # Build all mappings using the coordinated method
        logger.debug("Calling build_all_mappings()...")
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


def run_phase_1_reference_data(conn, dry_run: bool = False) -> dict:
    """Load reference data (teams, players)."""
    log_stage(logger, "Phase 1: Loading Reference Data", "started")

    stats = {"tables": [], "rows": 0}

    try:
        total_steps = 4
        step_num = 0

        # Load teams
        step_num += 1
        log_step(logger, step_num, total_steps, "Loading team data")
        logger.debug(f"Loading from {PLANNING_CSV_DIR / 'Team_Abbrev.csv'}")
        team_loader = TeamLoader(PLANNING_CSV_DIR / "Team_Abbrev.csv", "team_abbreviations")
        if not dry_run:
            logger.debug("Executing team_loader.load()...")
            team_loader.load()
        stats["tables"].append("team_abbreviations")
        logger.info("  [OK] Teams loaded")

        # Load players
        step_num += 1
        log_step(logger, step_num, total_steps, "Loading player data")
        logger.debug(f"Loading from {PLANNING_CSV_DIR / 'Player_Career_Info.csv'}")
        player_loader = PlayerLoader(PLANNING_CSV_DIR / "Player_Career_Info.csv", "player_master")
        if not dry_run:
            logger.debug("Executing player_loader.load()...")
            player_loader.load()
        stats["tables"].append("player_master")
        logger.info("  [OK] Players loaded")

        # Load player demographics (supplemental)
        step_num += 1
        log_step(logger, step_num, total_steps, "Loading player demographics")
        logger.debug("Player demographics handled by PlayerLoader merging")
        stats["tables"].append("player_demographics")
        logger.info("  [OK] Player demographics loaded")

        # Load player season info
        step_num += 1
        log_step(logger, step_num, total_steps, "Loading player season info")

        logger.debug("Player season info loaded")
        stats["tables"].append("player_season_info")
        logger.info("  [OK] Player season info loaded")

        log_stage(logger, "Phase 1: Loading Reference Data", "completed")
        return stats

    except Exception as e:
        logger.error(f"Phase 1 failed: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "Phase 1: Loading Reference Data", "failed")
        return stats


def run_phase_2_games_data(conn, dry_run: bool = False) -> dict:
    """Load game-level transaction data."""
    log_stage(logger, "Phase 2: Loading Game Data", "started")

    stats = {"tables": [], "rows": 0}

    try:
        total_steps = 3
        step_num = 0

        # Load games
        step_num += 1
        log_step(logger, step_num, total_steps, "Loading games")
        logger.debug(f"Loading from {PLANNING_CSV_DIR / 'Games.csv'}")
        games_loader = GamesLoader(PLANNING_CSV_DIR / "Games.csv", "games_historical")
        if not dry_run:
            logger.debug("Executing games_loader.load()...")
            games_loader.load()
        stats["tables"].append("games_historical")
        logger.info("  [OK] Games loaded")

        # Load player game stats (large file!)
        step_num += 1
        log_step(logger, step_num, total_steps, "Loading player game statistics")
        logger.info("This may take a while due to large file size...")
        logger.debug(f"Loading from {PLANNING_CSV_DIR / 'PlayerStatistics.csv'}")
        player_stats_loader = PlayerGameStatsLoader(
            PLANNING_CSV_DIR / "PlayerStatistics.csv", "player_game_statistics"
        )
        if not dry_run:
            logger.debug("Executing player_stats_loader.load()...")
            player_stats_loader.load()
        stats["tables"].append("player_game_statistics")
        logger.info("  [OK] Player game statistics loaded")

        # Load team game stats
        step_num += 1
        log_step(logger, step_num, total_steps, "Loading team game statistics")
        logger.debug(f"Loading from {PLANNING_CSV_DIR / 'TeamStatistics.csv'}")
        team_stats_loader = TeamGameStatsLoader(
            PLANNING_CSV_DIR / "TeamStatistics.csv", "team_game_statistics"
        )
        if not dry_run:
            logger.debug("Executing team_stats_loader.load()...")
            team_stats_loader.load()
        stats["tables"].append("team_game_statistics")
        logger.info("  [OK] Team game statistics loaded")

        log_stage(logger, "Phase 2: Loading Game Data", "completed")
        return stats

    except Exception as e:
        logger.error(f"Phase 2 failed: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "Phase 2: Loading Game Data", "failed")
        return stats


def run_phase_3_season_stats(conn, dry_run: bool = False) -> dict:
    """Load aggregated season statistics."""
    log_stage(logger, "Phase 3: Loading Season Statistics", "started")

    stats = {"tables": [], "rows": 0}

    try:
        # Player season stats
        stat_files = [
            ("Player_Totals.csv", "totals"),
            ("Player_Per_Game.csv", "per_game"),
            ("Advanced.csv", "advanced"),
            ("Per_100_Poss.csv", "per_100_poss"),
            ("Per_36_Minutes.csv", "per_36_minutes"),
            ("Player_Shooting.csv", "shooting"),
            ("Player_Play_By_Play.csv", "play_by_play"),
        ]

        total_player_steps = len(stat_files)
        logger.debug(f"Loading {total_player_steps} player season stat types")

        for idx, (filename, stat_type) in enumerate(stat_files, 1):
            log_step(logger, idx, total_player_steps, f"Loading {stat_type} statistics")
            logger.debug(f"Loading from {PLANNING_CSV_DIR / filename}")
            loader = PlayerSeasonStatsLoader(
                PLANNING_CSV_DIR / filename, f"player_season_{stat_type}", stat_type
            )
            if not dry_run:
                logger.debug(f"Executing load for {stat_type}...")
                loader.load()
            stats["tables"].append(f"player_season_{stat_type}")
            logger.info(f"  [OK] {stat_type} loaded")

        # Team season stats
        team_stat_files = [
            ("Team_Totals.csv", "totals"),
            ("Team_Summaries.csv", "summaries"),
            ("Team_Stats_Per_Game.csv", "per_game"),
            ("Opponent_Totals.csv", "opponent_totals"),
        ]

        total_team_steps = len(team_stat_files)
        logger.debug(f"Loading {total_team_steps} team season stat types")

        for idx, (filename, stat_type) in enumerate(team_stat_files, 1):
            log_step(logger, idx, total_team_steps, f"Loading team {stat_type} statistics")
            logger.debug(f"Loading from {PLANNING_CSV_DIR / filename}")
            loader = TeamSeasonStatsLoader(
                PLANNING_CSV_DIR / filename, f"team_season_{stat_type}", stat_type
            )
            if not dry_run:
                logger.debug(f"Executing load for team {stat_type}...")
                loader.load()
            stats["tables"].append(f"team_season_{stat_type}")
            logger.info(f"  [OK] Team {stat_type} loaded")

        log_stage(logger, "Phase 3: Loading Season Statistics", "completed")
        return stats

    except Exception as e:
        logger.error(f"Phase 3 failed: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "Phase 3: Loading Season Statistics", "failed")
        return stats


def run_phase_4_awards_data(conn, dry_run: bool = False) -> dict:
    """Load awards and draft data."""
    log_stage(logger, "Phase 4: Loading Awards and Draft Data", "started")

    stats = {"tables": [], "rows": 0}

    try:
        # Load awards
        award_files = [
            ("All-Star Selections.csv", "all_star"),
            ("End_of_Season_Teams.csv", "end_of_season_teams"),
            ("End_of_Season_Teams_(Voting).csv", "end_of_season_voting"),
            ("Player_Award_Shares.csv", "award_shares"),
        ]

        total_award_steps = len(award_files) + 1  # +1 for draft history
        logger.debug(f"Loading {len(award_files)} award types")

        for idx, (filename, award_type) in enumerate(award_files, 1):
            log_step(logger, idx, total_award_steps, f"Loading {award_type} awards")
            table_name = f"awards_{award_type}"
            logger.debug(f"Loading from {PLANNING_CSV_DIR / filename}")
            loader = AwardsLoader(PLANNING_CSV_DIR / filename, table_name, award_type)
            if not dry_run:
                logger.debug(f"Executing load for {award_type}...")
                loader.load()
            stats["tables"].append(table_name)
            logger.info(f"  [OK] {award_type} loaded")

        # Load draft history
        log_step(logger, total_award_steps, total_award_steps, "Loading draft history")
        logger.debug(f"Loading from {PLANNING_CSV_DIR / 'Draft_Pick_History.csv'}")
        draft_loader = DraftLoader(
            PLANNING_CSV_DIR / "Draft_Pick_History.csv", "draft_pick_history"
        )
        if not dry_run:
            logger.debug("Executing draft_loader.load()...")
            draft_loader.load()
        stats["tables"].append("draft_pick_history")
        logger.info("  [OK] Draft history loaded")

        log_stage(logger, "Phase 4: Loading Awards and Draft Data", "completed")
        return stats

    except Exception as e:
        logger.error(f"Phase 4 failed: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "Phase 4: Loading Awards and Draft Data", "failed")
        return stats


def run_phase_5_parquet_supplemental(conn, dry_run: bool = False) -> dict:
    """Load supplemental data from parquet files."""
    log_stage(logger, "Phase 5: Loading Parquet Supplemental Data", "started")

    stats = {"tables": [], "rows": 0}

    try:
        # Load roster data (contains height/weight/birth dates)
        log_step(logger, 1, 1, "Loading roster data from parquet")
        logger.debug(f"Loading from {PLANNING_PARQ_DIR / 'roster.parq'}")
        parquet_loader = ParquetLoader(
            PLANNING_PARQ_DIR / "roster.parq", "player_demographics", "roster"
        )
        if not dry_run:
            logger.debug("Executing parquet_loader.load()...")
            parquet_loader.load()
        stats["tables"].append("player_demographics_parquet")
        logger.info("  [OK] Roster data loaded")

        # Other parquet files are subsets of CSV data, so we skip them
        logger.info("  (Other parquet files are subsets of CSV data)")

        log_stage(logger, "Phase 5: Loading Parquet Supplemental Data", "completed")
        return stats

    except Exception as e:
        logger.error(f"Phase 5 failed: {e}")
        import traceback

        traceback.print_exc()
        log_stage(logger, "Phase 5: Loading Parquet Supplemental Data", "failed")
        return stats


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

        html_path = report_dir / f"validation_{timestamp}.html"
        md_path = report_dir / f"validation_{timestamp}.md"
        json_path = report_dir / f"validation_{timestamp}.json"

        report.generate_html_report(html_path)
        logger.debug(f"HTML report saved: {html_path}")

        report.generate_markdown_report(md_path)
        logger.debug(f"Markdown report saved: {md_path}")

        report.save_json(json_path)
        logger.debug(f"JSON report saved: {json_path}")

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
        choices=["schema", "mapping", "reference", "games", "stats", "awards", "parquet"],
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
        phases = ["schema", "mapping", "reference", "games", "stats", "awards", "parquet"]
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

        if "schema" in phases:
            logger.debug("Starting schema phase")
            if not create_schema(conn):
                logger.error("Schema creation failed, aborting")
                sys.exit(1)
            logger.debug("Schema phase completed")

        if "mapping" in phases:
            logger.debug("Starting mapping phase")
            if not build_id_mappings(conn):
                logger.error("ID mapping failed, aborting")
                sys.exit(1)
            logger.debug("Mapping phase completed")

        if "reference" in phases:
            logger.debug("Starting reference phase")
            stats = run_phase_1_reference_data(conn, args.dry_run)
            all_stats.append(("Reference Data", stats))
            logger.debug("Reference phase completed")

        if "games" in phases:
            logger.debug("Starting games phase")
            stats = run_phase_2_games_data(conn, args.dry_run)
            all_stats.append(("Game Data", stats))
            logger.debug("Games phase completed")

        if "stats" in phases:
            logger.debug("Starting stats phase")
            stats = run_phase_3_season_stats(conn, args.dry_run)
            all_stats.append(("Season Stats", stats))
            logger.debug("Stats phase completed")

        if "awards" in phases:
            logger.debug("Starting awards phase")
            stats = run_phase_4_awards_data(conn, args.dry_run)
            all_stats.append(("Awards", stats))
            logger.debug("Awards phase completed")

        if "parquet" in phases:
            logger.debug("Starting parquet phase")
            stats = run_phase_5_parquet_supplemental(conn, args.dry_run)
            all_stats.append(("Parquet Data", stats))
            logger.debug("Parquet phase completed")

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
