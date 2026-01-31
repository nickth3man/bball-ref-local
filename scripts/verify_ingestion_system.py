#!/usr/bin/env python3
"""
Verification script for the ingestion system.

This script verifies that all components are properly installed and configured.
"""

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileCheck:
    """Represents a file/directory to check."""

    path: str
    description: str
    is_required: bool = True


class CheckGroup:
    """A group of related file checks."""

    def __init__(self, name: str, checks: list[FileCheck]):
        self.name = name
        self.checks = checks


# Define all check groups
CHECK_GROUPS = [
    CheckGroup(
        "Directory Structure",
        [
            FileCheck("scripts/ingestion", "Main ingestion directory"),
            FileCheck("scripts/ingestion/schema", "SQL schema directory"),
            FileCheck("scripts/ingestion/loaders", "Data loaders directory"),
            FileCheck("scripts/ingestion/mapping", "ID mapping directory"),
            FileCheck("scripts/ingestion/validation", "Validation directory"),
        ],
    ),
    CheckGroup(
        "SQL Schema Files",
        [
            FileCheck("scripts/ingestion/schema/01_planning_tables.sql", "Planning tables"),
            FileCheck("scripts/ingestion/schema/02_game_tables.sql", "Game tables"),
            FileCheck("scripts/ingestion/schema/03_season_stats_tables.sql", "Season stats tables"),
            FileCheck("scripts/ingestion/schema/04_awards_tables.sql", "Awards tables"),
            FileCheck("scripts/ingestion/schema/05_id_mapping_tables.sql", "ID mapping tables"),
            FileCheck("scripts/ingestion/schema/06_indexes.sql", "Indexes"),
        ],
    ),
    CheckGroup(
        "Core Infrastructure",
        [
            FileCheck("scripts/ingestion/__init__.py", "Package init"),
            FileCheck("scripts/ingestion/config.py", "Configuration"),
            FileCheck("scripts/ingestion/database.py", "Database utilities"),
            FileCheck("scripts/ingestion/logger.py", "Logging"),
            FileCheck("scripts/ingestion/exceptions.py", "Exceptions"),
            FileCheck("scripts/ingestion/orchestrator.py", "Orchestrator"),
            FileCheck("scripts/ingestion/base_loader.py", "Base loader"),
            FileCheck("scripts/ingestion/utils.py", "Utilities"),
        ],
    ),
    CheckGroup(
        "Data Loaders",
        [
            FileCheck("scripts/ingestion/loaders/__init__.py", "Loaders package"),
            FileCheck("scripts/ingestion/loaders/reference_loaders.py", "Reference loaders"),
            FileCheck("scripts/ingestion/loaders/game_loaders.py", "Game loaders"),
            FileCheck("scripts/ingestion/loaders/stats_loaders.py", "Stats loaders"),
            FileCheck("scripts/ingestion/loaders/awards_loaders.py", "Awards loaders"),
            FileCheck("scripts/ingestion/loaders/parquet_loaders.py", "Parquet loaders"),
        ],
    ),
    CheckGroup(
        "ID Mapping",
        [
            FileCheck("scripts/ingestion/mapping/__init__.py", "Mapping package"),
            FileCheck("scripts/ingestion/mapping/player_mapper.py", "Player mapper"),
            FileCheck("scripts/ingestion/mapping/team_mapper.py", "Team mapper"),
            FileCheck("scripts/ingestion/mapping/id_resolver.py", "ID resolver"),
            FileCheck("scripts/ingestion/mapping/fuzzy_matcher.py", "Fuzzy matcher"),
            FileCheck("scripts/ingestion/mapping/manual_mappings.py", "Manual mappings"),
            FileCheck("scripts/ingestion/mapping/mapping_validator.py", "Mapping validator"),
            FileCheck("scripts/ingestion/mapping/utils.py", "Mapping utilities"),
        ],
    ),
    CheckGroup(
        "Validation Framework",
        [
            FileCheck("scripts/ingestion/validation/__init__.py", "Validation package"),
            FileCheck("scripts/ingestion/validation/validators.py", "Core validators"),
            FileCheck("scripts/ingestion/validation/consistency_checks.py", "Consistency checks"),
            FileCheck("scripts/ingestion/validation/sql_validators.py", "SQL validators"),
            FileCheck("scripts/ingestion/validation/report_generator.py", "Report generator"),
            FileCheck("scripts/ingestion/validation/validation_cli.py", "Validation CLI"),
        ],
    ),
    CheckGroup(
        "Main Scripts",
        [
            FileCheck("scripts/run_historical_ingestion.py", "Main ingestion script"),
            FileCheck("scripts/ingestion/README.md", "Documentation"),
        ],
    ),
    CheckGroup(
        "Data Files",
        [
            FileCheck("planning/csv_data/Players.csv", "Players CSV", is_required=False),
            FileCheck("planning/csv_data/Games.csv", "Games CSV", is_required=False),
            FileCheck(
                "planning/csv_data/PlayerStatistics.csv", "Player Statistics CSV", is_required=False
            ),
            FileCheck("planning/parq_data/roster.parq", "Roster Parquet", is_required=False),
        ],
    ),
]


def check_file(path: Path, description: str, is_required: bool = True) -> bool:
    """Check if a file exists.

    Args:
        path: Path to check
        description: Description of the file for output
        is_required: Whether this file is required (affects output status)

    Returns:
        True if file exists or is not required, False if required and missing
    """
    if path.exists():
        print(f"  [OK] {description}")
        return True
    elif is_required:
        print(f"  [MISSING] {description}")
        return False
    else:
        print(f"  [OPTIONAL] {description} (not found)")
        return True


def run_checks(groups: list[CheckGroup]) -> bool:
    """Run all file checks.

    Args:
        groups: List of check groups to run

    Returns:
        True if all required checks passed
    """
    all_passed = True

    for i, group in enumerate(groups, 1):
        print(f"\n{i}. {group.name}:")
        for check in group.checks:
            if not check_file(Path(check.path), check.description, check.is_required):
                all_passed = False

    return all_passed


def print_summary(all_passed: bool) -> None:
    """Print the final summary."""
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL CHECKS PASSED")
        print("\nThe ingestion system is fully configured and ready to use.")
        print("\nQuick start:")
        print("  python scripts/run_historical_ingestion.py --full")
    else:
        print("SOME CHECKS FAILED")
        print("\nPlease review the missing components above.")
    print("=" * 60)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("=" * 60)
    print("INGESTION SYSTEM VERIFICATION")
    print("=" * 60)

    all_passed = run_checks(CHECK_GROUPS)
    print_summary(all_passed)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
