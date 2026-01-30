"""Command-line interface for validation framework."""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.ingestion.database import close_ingestion_connection, get_ingestion_connection
from scripts.ingestion.logger import get_logger
from scripts.ingestion.validation.consistency_checks import ConsistencyChecker
from scripts.ingestion.validation.report_generator import ValidationReport
from scripts.ingestion.validation.validators import DataValidator

logger = get_logger("validation_cli")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Validate ingested NBA data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scripts.ingestion.validation.validation_cli --full
  python -m scripts.ingestion.validation.validation_cli --table players
  python -m scripts.ingestion.validation.validation_cli --quick --report validation.html
        """,
    )

    parser.add_argument(
        "--full", action="store_true", help="Run full validation suite (all checks)"
    )

    parser.add_argument(
        "--table", type=str, metavar="TABLE_NAME", help="Validate specific table only"
    )

    parser.add_argument(
        "--quick", action="store_true", help="Run quick checks only (skip consistency checks)"
    )

    parser.add_argument(
        "--fix", action="store_true", help="Attempt to auto-fix minor issues (use with caution)"
    )

    parser.add_argument(
        "--report", type=str, metavar="PATH", help="Generate HTML report at specified path"
    )

    parser.add_argument(
        "--json", type=str, metavar="PATH", help="Generate JSON report at specified path"
    )

    parser.add_argument(
        "--markdown", type=str, metavar="PATH", help="Generate Markdown report at specified path"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    return parser


def run_validation(args: argparse.Namespace) -> int:
    """Run validation based on arguments."""

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting validation...")

    try:
        conn = get_ingestion_connection()
        report = ValidationReport("NBA Data Validation Report")

        # Add metadata
        report.add_metadata("mode", "full" if args.full else "quick" if args.quick else "standard")
        report.add_metadata("auto_fix", args.fix)

        # Run data validator
        validator = DataValidator(conn)

        if args.table:
            # Validate specific table
            logger.info(f"Validating table: {args.table}")
            if args.table == "players":
                results = validator.validate_players()
            elif args.table == "games":
                results = validator.validate_games()
            elif args.table == "stats":
                results = validator.validate_stats()
            elif args.table == "seasons":
                results = validator.validate_seasons()
            elif args.table == "references":
                results = validator.validate_references()
            else:
                logger.error(f"Unknown table: {args.table}")
                return 1

            report.add_section(f"Table: {args.table}", results)
        else:
            # Run all validations
            logger.info("Running all data validations...")
            validation_results = validator.run_all_validations()

            for validation in validation_results:
                report.add_section(
                    validation.check_name,
                    [
                        {"severity": i.severity.value, "message": i.message, "context": i.context}
                        for i in validation.issues
                    ],
                    "failed" if validation.has_errors() else "passed",
                )

        # Run consistency checks (unless quick mode)
        if not args.quick and not args.table:
            logger.info("Running consistency checks...")
            checker = ConsistencyChecker(conn)
            consistency_results = checker.run_all_checks()

            for result in consistency_results:
                report.add_section(
                    f"Consistency: {result.check_name}",
                    result.discrepancies,
                    "passed" if result.passed else "failed",
                )

        # Print summary
        print("\n" + "=" * 60)
        report.print_summary()
        print("=" * 60 + "\n")

        # Generate reports
        if args.report:
            report.generate_html_report(args.report)
            print(f"HTML report saved to: {args.report}")

        if args.json:
            report.save_json(args.json)
            print(f"JSON report saved to: {args.json}")

        if args.markdown:
            report.generate_markdown_report(args.markdown)
            print(f"Markdown report saved to: {args.markdown}")

        # Return exit code based on results
        summary = report.generate_summary()
        if summary["status"] == "failed":
            logger.error(f"Validation failed with {summary['total_issues']} issues")
            return 1
        else:
            logger.info("Validation passed!")
            return 0

    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 2
    finally:
        close_ingestion_connection()


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Default to full validation if no specific option given
    if not any([args.full, args.table, args.quick]):
        args.full = True

    exit_code = run_validation(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
