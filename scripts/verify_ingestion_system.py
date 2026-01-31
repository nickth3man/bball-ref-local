#!/usr/bin/env python3
"""
Verification script for the ingestion system.

This script verifies that all components are properly installed and configured.
"""

import sys
from importlib import import_module
from pathlib import Path


def check_file(path, description):
    """Check if a file exists."""
    if path.exists():
        print(f"  [OK] {description}")
        return True
    else:
        print(f"  [MISSING] {description}")
        return False


def check_module(module_path, description):
    """Check if a module can be imported."""
    try:
        import_module(module_path)
        print(f"  [OK] {description}")
        return True
    except Exception as e:
        print(f"  [ERROR] {description}: {e}")
        return False


def main():
    print("=" * 60)
    print("INGESTION SYSTEM VERIFICATION")
    print("=" * 60)

    all_passed = True

    # Check directory structure
    print("\n1. Directory Structure:")
    dirs = [
        ("scripts/ingestion", "Main ingestion directory"),
        ("scripts/ingestion/schema", "SQL schema directory"),
        ("scripts/ingestion/loaders", "Data loaders directory"),
        ("scripts/ingestion/mapping", "ID mapping directory"),
        ("scripts/ingestion/validation", "Validation directory"),
    ]
    for dir_path, desc in dirs:
        if not check_file(Path(dir_path), desc):
            all_passed = False

    # Check SQL schema files
    print("\n2. SQL Schema Files:")
    sql_files = [
        ("scripts/ingestion/schema/01_planning_tables.sql", "Planning tables"),
        ("scripts/ingestion/schema/02_game_tables.sql", "Game tables"),
        ("scripts/ingestion/schema/03_season_stats_tables.sql", "Season stats tables"),
        ("scripts/ingestion/schema/04_awards_tables.sql", "Awards tables"),
        ("scripts/ingestion/schema/05_id_mapping_tables.sql", "ID mapping tables"),
        ("scripts/ingestion/schema/06_indexes.sql", "Indexes"),
    ]
    for file_path, desc in sql_files:
        if not check_file(Path(file_path), desc):
            all_passed = False

    # Check core Python files
    print("\n3. Core Infrastructure:")
    core_files = [
        ("scripts/ingestion/__init__.py", "Package init"),
        ("scripts/ingestion/config.py", "Configuration"),
        ("scripts/ingestion/database.py", "Database utilities"),
        ("scripts/ingestion/logger.py", "Logging"),
        ("scripts/ingestion/exceptions.py", "Exceptions"),
        ("scripts/ingestion/orchestrator.py", "Orchestrator"),
        ("scripts/ingestion/base_loader.py", "Base loader"),
        ("scripts/ingestion/utils.py", "Utilities"),
    ]
    for file_path, desc in core_files:
        if not check_file(Path(file_path), desc):
            all_passed = False

    # Check loader files
    print("\n4. Data Loaders:")
    loader_files = [
        ("scripts/ingestion/loaders/__init__.py", "Loaders package"),
        ("scripts/ingestion/loaders/reference_loaders.py", "Reference loaders"),
        ("scripts/ingestion/loaders/game_loaders.py", "Game loaders"),
        ("scripts/ingestion/loaders/stats_loaders.py", "Stats loaders"),
        ("scripts/ingestion/loaders/awards_loaders.py", "Awards loaders"),
        ("scripts/ingestion/loaders/parquet_loaders.py", "Parquet loaders"),
    ]
    for file_path, desc in loader_files:
        if not check_file(Path(file_path), desc):
            all_passed = False

    # Check mapping files
    print("\n5. ID Mapping:")
    mapping_files = [
        ("scripts/ingestion/mapping/__init__.py", "Mapping package"),
        ("scripts/ingestion/mapping/player_mapper.py", "Player mapper"),
        ("scripts/ingestion/mapping/team_mapper.py", "Team mapper"),
        ("scripts/ingestion/mapping/id_resolver.py", "ID resolver"),
        ("scripts/ingestion/mapping/fuzzy_matcher.py", "Fuzzy matcher"),
        ("scripts/ingestion/mapping/manual_mappings.py", "Manual mappings"),
        ("scripts/ingestion/mapping/mapping_validator.py", "Mapping validator"),
    ]
    for file_path, desc in mapping_files:
        if not check_file(Path(file_path), desc):
            all_passed = False

    # Check validation files
    print("\n6. Validation Framework:")
    validation_files = [
        ("scripts/ingestion/validation/__init__.py", "Validation package"),
        ("scripts/ingestion/validation/validators.py", "Core validators"),
        ("scripts/ingestion/validation/consistency_checks.py", "Consistency checks"),
        ("scripts/ingestion/validation/sql_validators.py", "SQL validators"),
        ("scripts/ingestion/validation/report_generator.py", "Report generator"),
        ("scripts/ingestion/validation/validation_cli.py", "Validation CLI"),
    ]
    for file_path, desc in validation_files:
        if not check_file(Path(file_path), desc):
            all_passed = False

    # Check main scripts
    print("\n7. Main Scripts:")
    main_scripts = [
        ("scripts/run_historical_ingestion.py", "Main ingestion script"),
        ("scripts/ingestion/README.md", "Documentation"),
    ]
    for file_path, desc in main_scripts:
        if not check_file(Path(file_path), desc):
            all_passed = False

    # Check data files
    print("\n8. Data Files:")
    data_files = [
        ("planning/csv_data/Players.csv", "Players CSV"),
        ("planning/csv_data/Games.csv", "Games CSV"),
        ("planning/csv_data/PlayerStatistics.csv", "Player Statistics CSV"),
        ("planning/parq_data/roster.parq", "Roster Parquet"),
    ]
    for file_path, desc in data_files:
        if not check_file(Path(file_path), desc):
            all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL CHECKS PASSED")
        print("\nThe ingestion system is fully configured and ready to use.")
        print("\nQuick start:")
        print("  python scripts/run_historical_ingestion.py --full")
    else:
        print("SOME CHECKS FAILED")
        print("\nPlease review the missing components above.")
        return 1
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
