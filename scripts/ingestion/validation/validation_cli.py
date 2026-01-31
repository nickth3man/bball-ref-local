"""Command-line interface for validation framework."""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.ingestion.database import close_ingestion_connection, get_ingestion_connection
from scripts.ingestion.logger import enable_verbose_logging, get_logger
from scripts.ingestion.validation.consistency_checks import ConsistencyChecker
from scripts.ingestion.validation.report_generator import ValidationReport
from scripts.ingestion.validation.validators import DataValidator

logger = get_logger("validation_cli")


class ValidationRunner:
    """Orchestrates the validation process based on CLI arguments."""

    def __init__(self, conn, report: ValidationReport):
        self.conn = conn
        self.report = report

    def run_table_validation(self, table_name: str) -> bool:
        """Run validation for a specific table.

        Args:
            table_name: Name of the table to validate

        Returns:
            True if validation was successful, False otherwise
        """
        logger.info(f"Validating table: {table_name}")
        validator = DataValidator(self.conn)

        # Map table names to validation methods
        table_validators = {
            "players": validator.validate_duplicate_players,
            "games": validator.validate_duplicate_games,
            "stats": validator.validate_points_calculation,
            "seasons": validator.validate_season_ranges,
            "references": validator.validate_foreign_keys_players,
        }

        if table_name not in table_validators:
            logger.error(f"Unknown table: {table_name}")
            return False

        result = table_validators[table_name]()
        self.report.add_section(
            f"Table: {table_name}",
            [{"severity": i.severity.value, "message": i.message} for i in result.issues],
            "failed" if result.has_errors() else "passed",
        )
        return True

    def run_all_validations(self) -> None:
        """Run all data validations and add results to report."""
        logger.info("Running all data validations...")
        validator = DataValidator(self.conn)
        validation_results = validator.run_all_validations()

        for validation in validation_results:
            self.report.add_section(
                validation.check_name,
                [
                    {"severity": i.severity.value, "message": i.message}
                    for i in validation.issues
                ],
                "failed" if validation.has_errors() else "passed",
            )

    def run_consistency_checks(self) -> None:
        """Run consistency checks and add results to report."""
        logger.info("Running consistency checks...")
        checker = ConsistencyChecker(self.conn)
        checker.run_all_checks()

        for result in checker.results:
            self.report.add_section(
                f"Consistency: {result.check_name}",
                result.discrepancies,
                "passed" if result.passed else "failed",
            )


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
        enable_verbose_logging()

    logger.info("Starting validation...")

    try:
        conn = get_ingestion_connection()
        report = ValidationReport("NBA Data Validation Report")

        # Add metadata
        report.add_metadata(
            "mode", "full" if args.full else "quick" if args.quick else "standard"
        )
        report.add_metadata("auto_fix", args.fix)

        runner = ValidationRunner(conn, report)

        if args.table:
            # Validate specific table
            if not runner.run_table_validation(args.table):
                return 1
        else:
            # Run all validations
            runner.run_all_validations()

        # Run consistency checks (unless quick mode)
        if not args.quick and not args.table:
            runner.run_consistency_checks()

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
