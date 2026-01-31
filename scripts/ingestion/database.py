"""Database utilities for the data ingestion pipeline."""

from contextlib import contextmanager

from app.services.database import get_db_connection
from scripts.ingestion.config import INSERT_BATCH_SIZE, TEMP_TABLE_SUFFIX
from scripts.ingestion.exceptions import DatabaseError
from scripts.ingestion.logger import get_logger

logger = get_logger(__name__)


def get_ingestion_connection():
    """Get database connection optimized for bulk inserts."""
    try:
        conn = get_db_connection()
        conn.execute("SET threads=4")
        conn.execute("SET memory_limit = '1GB'")
        return conn
    except Exception as e:
        raise DatabaseError(
            "Failed to establish database connection",
            operation="connect",
            original_error=e,
        ) from e


@contextmanager
def ingestion_transaction():
    """Context manager for database transactions."""
    conn = get_ingestion_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        yield conn
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        raise DatabaseError(
            "Transaction failed and was rolled back",
            operation="transaction",
            original_error=e,
        ) from e


def execute_many(query, values, batch_size=INSERT_BATCH_SIZE):
    """Execute INSERT with batching for large datasets."""
    if not values:
        logger.warning("No values provided for execute_many")
        return 0
    conn = get_ingestion_connection()
    total_inserted = 0
    try:
        for i in range(0, len(values), batch_size):
            batch = values[i : i + batch_size]
            conn.executemany(query, batch)
            total_inserted += len(batch)
        return total_inserted
    except Exception as e:
        raise DatabaseError(
            f"Bulk insert failed after {total_inserted} rows",
            operation="execute_many",
            original_error=e,
        ) from e


def insert_dataframe(df, table_name, if_exists="append", batch_size=INSERT_BATCH_SIZE):
    """Insert a DataFrame into a database table."""
    if df.empty:
        logger.warning(f"Empty DataFrame provided for table {table_name}")
        return 0
    conn = get_ingestion_connection()
    try:
        if len(df) <= batch_size:
            conn.execute(f"INSERT INTO {table_name} SELECT * FROM df")
            return len(df)
        total_inserted = 0
        for i in range(0, len(df), batch_size):
            chunk = df.iloc[i : i + batch_size]
            conn.execute(f"INSERT INTO {table_name} SELECT * FROM chunk")
            total_inserted += len(chunk)
        return total_inserted
    except Exception as e:
        raise DatabaseError(
            f"Failed to insert DataFrame into {table_name}",
            operation="insert_dataframe",
            original_error=e,
        ) from e


def create_temp_table(table_name, schema):
    """Create temporary table for staging data."""
    temp_table_name = f"{table_name}{TEMP_TABLE_SUFFIX}"
    conn = get_ingestion_connection()
    try:
        conn.execute(f"DROP TABLE IF EXISTS {temp_table_name}")
        create_sql = f"CREATE TABLE {temp_table_name} ({schema})"
        conn.execute(create_sql)
        return temp_table_name
    except Exception as e:
        raise DatabaseError(
            f"Failed to create temporary table {temp_table_name}",
            operation="create_temp_table",
            original_error=e,
        ) from e


def swap_tables(temp_table, production_table):
    """Atomic swap for zero-downtime updates."""
    conn = get_ingestion_connection()
    backup_table = f"{production_table}_backup"
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(f"DROP TABLE IF EXISTS {backup_table}")
        conn.execute(f"ALTER TABLE {production_table} RENAME TO {backup_table}")
        conn.execute(f"ALTER TABLE {temp_table} RENAME TO {production_table}")
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        raise DatabaseError(
            f"Failed to swap tables {temp_table} -> {production_table}",
            operation="swap_tables",
            original_error=e,
        ) from e


def truncate_table(table_name):
    """Safely truncate a table."""
    conn = get_ingestion_connection()
    try:
        conn.execute(f"DELETE FROM {table_name}")
    except Exception as e:
        raise DatabaseError(
            f"Failed to truncate table {table_name}",
            operation="truncate_table",
            original_error=e,
        ) from e


def table_exists(table_name):
    """Check if a table exists in the database."""
    conn = get_ingestion_connection()
    try:
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()
        return result[0] > 0 if result else False
    except Exception as e:
        logger.warning(f"Error checking table existence: {e}")
        return False


def get_row_count(table_name):
    """Get the row count of a table."""
    conn = get_ingestion_connection()
    try:
        result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0
    except Exception as e:
        raise DatabaseError(
            f"Failed to get row count for {table_name}",
            operation="get_row_count",
            original_error=e,
        ) from e


def execute_sql_file(file_path):
    """Execute SQL from a file."""
    conn = get_ingestion_connection()
    try:
        with open(file_path) as f:
            sql = f.read()
        conn.execute(sql)
    except Exception as e:
        raise DatabaseError(
            f"Failed to execute SQL file {file_path}",
            operation="execute_sql_file",
            original_error=e,
        ) from e


def close_ingestion_connection():
    """Close the database connection (no-op since we're using connection pooling)."""
    pass
