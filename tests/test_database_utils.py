"""Tests for database utility functions in database.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.database import (
    create_temp_table,
    execute_many,
    execute_sql_file,
    get_optimized_connection,
    get_row_count,
    insert_dataframe,
    swap_tables,
    table_exists,
    transaction,
    truncate_table,
)


class TestGetOptimizedConnection:
    """Tests for get_optimized_connection function."""

    def test_get_optimized_connection(self):
        """Test connection optimization."""
        mock_conn = MagicMock()

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            result = get_optimized_connection(threads=8, memory_limit="4GB")

        assert result is mock_conn
        mock_conn.execute.assert_any_call("SET threads=8")
        mock_conn.execute.assert_any_call("SET memory_limit = '4GB'")


class TestTransaction:
    """Tests for transaction context manager."""

    def test_transaction_success(self):
        """Test successful transaction."""
        mock_conn = MagicMock()

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            with transaction() as conn:
                conn.execute("INSERT INTO test VALUES (1)")

        mock_conn.execute.assert_any_call("BEGIN TRANSACTION")
        mock_conn.execute.assert_any_call("COMMIT")

    def test_transaction_rollback_on_error(self):
        """Test transaction rollback on error."""
        mock_conn = MagicMock()

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            with pytest.raises(ValueError):
                with transaction() as conn:
                    conn.execute("INSERT INTO test VALUES (1)")
                    raise ValueError("Test error")

        mock_conn.execute.assert_any_call("BEGIN TRANSACTION")
        mock_conn.execute.assert_any_call("ROLLBACK")


class TestExecuteMany:
    """Tests for execute_many function."""

    def test_execute_many_basic(self):
        """Test basic batch insert."""
        mock_conn = MagicMock()

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            values = [(1, "a"), (2, "b"), (3, "c")]
            result = execute_many("INSERT INTO test VALUES (?, ?)", values, batch_size=2)

        assert result == 3
        assert mock_conn.executemany.call_count == 2  # 3 items / batch_size 2 = 2 batches

    def test_execute_many_empty_values(self):
        """Test execute_many with empty values."""
        result = execute_many("INSERT INTO test VALUES (?, ?)", [])
        assert result == 0

    def test_execute_many_error(self):
        """Test execute_many with database error."""
        mock_conn = MagicMock()
        mock_conn.executemany.side_effect = Exception("DB Error")

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            with pytest.raises(RuntimeError) as exc_info:
                execute_many("INSERT INTO test VALUES (?, ?)", [(1, "a")])

        assert "Bulk insert failed" in str(exc_info.value)


class TestInsertDataframe:
    """Tests for insert_dataframe function."""

    def test_insert_dataframe_small(self):
        """Test inserting small DataFrame."""
        mock_conn = MagicMock()
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            result = insert_dataframe(df, "test_table")

        assert result == 3
        mock_conn.execute.assert_called_once()

    def test_insert_dataframe_batching(self):
        """Test inserting large DataFrame with batching."""
        mock_conn = MagicMock()
        df = pd.DataFrame({"id": range(10), "name": ["x"] * 10})

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            result = insert_dataframe(df, "test_table", batch_size=3)

        assert result == 10
        # 10 rows / batch_size 3 = 4 batches (3+3+3+1)
        assert mock_conn.execute.call_count == 4

    def test_insert_dataframe_empty(self):
        """Test inserting empty DataFrame."""
        df = pd.DataFrame({"id": [], "name": []})

        result = insert_dataframe(df, "test_table")

        assert result == 0

    def test_insert_dataframe_error(self):
        """Test insert_dataframe with error."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("Insert error")
        df = pd.DataFrame({"id": [1]})

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            with pytest.raises(RuntimeError) as exc_info:
                insert_dataframe(df, "test_table")

        assert "Failed to insert DataFrame" in str(exc_info.value)


class TestTableExists:
    """Tests for table_exists function."""

    def test_table_exists_true(self):
        """Test table that exists."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (1,)

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            result = table_exists("players")

        assert result is True

    def test_table_exists_false(self):
        """Test table that doesn't exist."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (0,)

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            result = table_exists("nonexistent")

        assert result is False

    def test_table_exists_error(self):
        """Test table_exists with database error."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB error")

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            result = table_exists("players")

        assert result is False


class TestGetRowCount:
    """Tests for get_row_count function."""

    def test_get_row_count_success(self):
        """Test getting row count."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (150,)

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            result = get_row_count("players")

        assert result == 150
        mock_conn.execute.assert_called_with("SELECT COUNT(*) FROM players")

    def test_get_row_count_error(self):
        """Test get_row_count with error."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB error")

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            with pytest.raises(RuntimeError) as exc_info:
                get_row_count("players")

        assert "Failed to get row count" in str(exc_info.value)


class TestTruncateTable:
    """Tests for truncate_table function."""

    def test_truncate_table_success(self):
        """Test truncating a table."""
        mock_conn = MagicMock()

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            truncate_table("test_table")

        mock_conn.execute.assert_called_with("DELETE FROM test_table")

    def test_truncate_table_error(self):
        """Test truncate_table with error."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB error")

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            with pytest.raises(RuntimeError) as exc_info:
                truncate_table("test_table")

        assert "Failed to truncate table" in str(exc_info.value)


class TestCreateTempTable:
    """Tests for create_temp_table function."""

    def test_create_temp_table_success(self):
        """Test creating temp table."""
        mock_conn = MagicMock()

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            result = create_temp_table("my_table", "id INTEGER, name VARCHAR")

        assert result == "my_table_temp"
        mock_conn.execute.assert_any_call("DROP TABLE IF EXISTS my_table_temp")
        mock_conn.execute.assert_any_call("CREATE TABLE my_table_temp (id INTEGER, name VARCHAR)")

    def test_create_temp_table_error(self):
        """Test create_temp_table with error."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB error")

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            with pytest.raises(RuntimeError) as exc_info:
                create_temp_table("my_table", "id INTEGER")

        assert "Failed to create temporary table" in str(exc_info.value)


class TestSwapTables:
    """Tests for swap_tables function."""

    def test_swap_tables_success(self):
        """Test swapping tables."""
        mock_conn = MagicMock()

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            swap_tables("new_table_temp", "production_table")

        mock_conn.execute.assert_any_call("BEGIN TRANSACTION")
        mock_conn.execute.assert_any_call("DROP TABLE IF EXISTS production_table_backup")
        mock_conn.execute.assert_any_call("ALTER TABLE production_table RENAME TO production_table_backup")
        mock_conn.execute.assert_any_call("ALTER TABLE new_table_temp RENAME TO production_table")
        mock_conn.execute.assert_any_call("COMMIT")

    def test_swap_tables_rollback_on_error(self):
        """Test swap_tables rollback on error."""
        mock_conn = MagicMock()
        # Provide enough side effects: BEGIN, DROP, ALTER (fails), ROLLBACK
        mock_conn.execute.side_effect = [None, None, Exception("Rename failed"), None]

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            with pytest.raises(RuntimeError) as exc_info:
                swap_tables("new_table_temp", "production_table")

        mock_conn.execute.assert_any_call("ROLLBACK")
        assert "Failed to swap tables" in str(exc_info.value)


class TestExecuteSqlFile:
    """Tests for execute_sql_file function."""

    def test_execute_sql_file_success(self, tmp_path):
        """Test executing SQL from file."""
        mock_conn = MagicMock()
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE test (id INTEGER);")

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            execute_sql_file(sql_file)

        mock_conn.execute.assert_called_with("CREATE TABLE test (id INTEGER);")

    def test_execute_sql_file_error(self, tmp_path):
        """Test execute_sql_file with error."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("SQL error")
        sql_file = tmp_path / "test.sql"
        sql_file.write_text("INVALID SQL;")

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            with pytest.raises(RuntimeError) as exc_info:
                execute_sql_file(sql_file)

        assert "Failed to execute SQL file" in str(exc_info.value)

    def test_execute_sql_file_not_found(self):
        """Test execute_sql_file with non-existent file."""
        mock_conn = MagicMock()

        with patch("app.services.database.get_db_connection", return_value=mock_conn):
            with pytest.raises((RuntimeError, FileNotFoundError)):
                execute_sql_file("/nonexistent/file.sql")
