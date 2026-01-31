"""Database utilities for the data ingestion pipeline.

This module provides backward-compatible imports from app.services.database.
New code should import directly from app.services.database.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from app.services.database import (
    close_db_connection,
    create_temp_table,
    execute_command,
    execute_many,
    execute_query,
    execute_sql_file,
    get_db_connection,
    get_row_count,
    get_optimized_connection as get_ingestion_connection,
    insert_dataframe,
    set_app_metadata,
    swap_tables,
    table_exists,
    transaction as ingestion_transaction,
    truncate_table,
)

if TYPE_CHECKING:
    import pandas as pd

# Re-export with aliases for backward compatibility
__all__ = [
    "get_ingestion_connection",
    "ingestion_transaction",
    "execute_many",
    "insert_dataframe",
    "create_temp_table",
    "swap_tables",
    "truncate_table",
    "table_exists",
    "get_row_count",
    "execute_sql_file",
    "close_ingestion_connection",
]


def close_ingestion_connection() -> None:
    """Close the database connection (delegates to close_db_connection)."""
    close_db_connection()
