"""Data ingestion pipeline for basketball reference data.

This package provides the core infrastructure for ingesting data from CSV and Parquet
files into the DuckDB database. It includes base classes, utilities, and orchestration
for managing the entire ingestion pipeline.

Example:
    from scripts.ingestion import IngestionOrchestrator, BaseLoader
    from scripts.ingestion.config import PLANNING_CSV_DIR

    orchestrator = IngestionOrchestrator()
    orchestrator.run_ingestion(phases=["reference", "transaction", "stats"])
"""

__version__ = "1.0.0"
__author__ = "Basketball Reference ETL"

# Core exports
from scripts.ingestion.base_loader import BaseLoader
from scripts.ingestion.database import (
    create_temp_table,
    execute_many,
    get_ingestion_connection,
    swap_tables,
    truncate_table,
)
from scripts.ingestion.exceptions import IngestionError, MappingError, ValidationError
from scripts.ingestion.logger import get_logger
from scripts.ingestion.orchestrator import IngestionOrchestrator
from scripts.ingestion.utils import (
    chunk_dataframe,
    clean_column_names,
    normalize_team_name,
    parse_season,
    safe_float,
    safe_int,
)

__all__ = [
    # Version
    "__version__",
    # Core classes
    "BaseLoader",
    "IngestionOrchestrator",
    # Exceptions
    "IngestionError",
    "ValidationError",
    "MappingError",
    # Utilities
    "get_logger",
    "clean_column_names",
    "parse_season",
    "normalize_team_name",
    "safe_int",
    "safe_float",
    "chunk_dataframe",
    # Database
    "get_ingestion_connection",
    "execute_many",
    "create_temp_table",
    "swap_tables",
    "truncate_table",
]
