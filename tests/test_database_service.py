"""Comprehensive unit tests for the database service layer.

Tests all database operations including connection management, query execution,
schema initialization, and metadata operations with proper mocking.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services import database as db_module


@pytest.fixture
def mock_duckdb_connection():
    """Create a mock DuckDB connection for testing."""
    mock_conn = MagicMock()
    mock_conn.execute = MagicMock()
    mock_conn.close = MagicMock()
    mock_conn.rowcount = 1
    return mock_conn


@pytest.fixture
def reset_database_state():
    """Reset the global database connection state before each test."""
    # Store original state
    original_conn = db_module._conn

    # Reset to None for clean test state
    db_module._conn = None

    yield

    # Restore original state after test
    db_module._conn = original_conn


class TestGetDbConnection:
    """Test suite for get_db_connection function."""

    def test_returns_existing_connection(self, mock_duckdb_connection, reset_database_state):
        """Test that existing connection is returned without creating new one."""
        # Arrange
        db_module._conn = mock_duckdb_connection

        # Act
        result = db_module.get_db_connection()

        # Assert
        assert result is mock_duckdb_connection

    @patch("app.services.database.duckdb.connect")
    def test_creates_new_connection_when_none_exists(
        self, mock_connect, mock_duckdb_connection, reset_database_state
    ):
        """Test that new connection is created when _conn is None."""
        # Arrange
        mock_connect.return_value = mock_duckdb_connection
        db_module._conn = None

        # Act
        result = db_module.get_db_connection()

        # Assert
        mock_connect.assert_called_once()
        assert result is mock_duckdb_connection
        assert db_module._conn is mock_duckdb_connection

    @patch("app.services.database.duckdb.connect")
    def test_raises_runtime_error_on_connection_failure(self, mock_connect, reset_database_state):
        """Test that RuntimeError is raised when connection fails."""
        # Arrange
        mock_connect.side_effect = Exception("Connection failed")
        db_module._conn = None

        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to connect to database"):
            db_module.get_db_connection()


class TestCloseDbConnection:
    """Test suite for close_db_connection function."""

    def test_closes_connection_when_exists(self, mock_duckdb_connection, reset_database_state):
        """Test that connection is closed and reset to None."""
        # Arrange
        db_module._conn = mock_duckdb_connection

        # Act
        db_module.close_db_connection()

        # Assert
        mock_duckdb_connection.close.assert_called_once()
        assert db_module._conn is None

    def test_handles_none_connection_gracefully(self, reset_database_state):
        """Test that no error occurs when closing None connection."""
        # Arrange
        db_module._conn = None

        # Act & Assert (should not raise)
        db_module.close_db_connection()
        assert db_module._conn is None


class TestExecuteQuery:
    """Test suite for execute_query function."""

    def test_executes_query_with_params(self, mock_duckdb_connection, reset_database_state):
        """Test query execution with parameters."""
        # Arrange
        db_module._conn = mock_duckdb_connection
        expected_results = [(1, "John", "Doe"), (2, "Jane", "Smith")]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = expected_results
        mock_duckdb_connection.execute.return_value = mock_cursor

        query = "SELECT * FROM players WHERE team_id = ?"
        params = [123]

        # Act
        result = db_module.execute_query(query, params)

        # Assert
        mock_duckdb_connection.execute.assert_called_once_with(query, params)
        assert result == expected_results

    def test_executes_query_without_params(self, mock_duckdb_connection, reset_database_state):
        """Test query execution without parameters."""
        # Arrange
        db_module._conn = mock_duckdb_connection
        expected_results = [(1,), (2,), (3,)]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = expected_results
        mock_duckdb_connection.execute.return_value = mock_cursor

        query = "SELECT COUNT(*) FROM teams"

        # Act
        result = db_module.execute_query(query, None)

        # Assert
        mock_duckdb_connection.execute.assert_called_once_with(query)
        assert result == expected_results

    def test_raises_runtime_error_on_query_failure(
        self, mock_duckdb_connection, reset_database_state
    ):
        """Test that RuntimeError is raised on query failure."""
        # Arrange
        db_module._conn = mock_duckdb_connection
        mock_duckdb_connection.execute.side_effect = Exception("Syntax error")

        # Act & Assert
        with pytest.raises(RuntimeError, match="Query execution failed"):
            db_module.execute_query("INVALID SQL", None)


class TestExecuteCommand:
    """Test suite for execute_command function."""

    def test_executes_insert_with_params(self, mock_duckdb_connection, reset_database_state):
        """Test INSERT command execution with parameters."""
        # Arrange
        db_module._conn = mock_duckdb_connection
        mock_duckdb_connection.rowcount = 5

        command = "INSERT INTO players (name) VALUES (?)"
        params = ["John"]

        # Act
        result = db_module.execute_command(command, params)

        # Assert
        mock_duckdb_connection.execute.assert_called_once_with(command, params)
        assert result == 5

    def test_executes_update_without_params(self, mock_duckdb_connection, reset_database_state):
        """Test UPDATE command execution without parameters."""
        # Arrange
        db_module._conn = mock_duckdb_connection
        mock_duckdb_connection.rowcount = 10

        command = "UPDATE teams SET city = 'New York'"

        # Act
        result = db_module.execute_command(command, None)

        # Assert
        mock_duckdb_connection.execute.assert_called_once_with(command)
        assert result == 10

    def test_handles_none_rowcount(self, mock_duckdb_connection, reset_database_state):
        """Test handling of None rowcount."""
        # Arrange
        db_module._conn = mock_duckdb_connection
        mock_duckdb_connection.rowcount = None

        # Act
        result = db_module.execute_command("DELETE FROM players WHERE id = 1", None)

        # Assert
        assert result == 0

    def test_raises_runtime_error_on_command_failure(
        self, mock_duckdb_connection, reset_database_state
    ):
        """Test that RuntimeError is raised on command failure."""
        # Arrange
        db_module._conn = mock_duckdb_connection
        mock_duckdb_connection.execute.side_effect = Exception("Constraint violation")

        # Act & Assert
        with pytest.raises(RuntimeError, match="Command execution failed"):
            db_module.execute_command("INSERT INTO invalid_table VALUES (1)", None)


class TestAppMetadata:
    """Test suite for application metadata operations."""

    def test_set_app_metadata(self, mock_duckdb_connection, reset_database_state):
        """Test setting application metadata."""
        # Arrange
        db_module._conn = mock_duckdb_connection

        # Act
        db_module.set_app_metadata("version", "1.0.0")

        # Assert
        mock_duckdb_connection.execute.assert_called_once()
        call_args = mock_duckdb_connection.execute.call_args
        assert "INSERT OR REPLACE INTO app_metadata" in call_args[0][0]
        assert call_args[0][1] == ["version", "1.0.0"]

    def test_get_app_metadata_found(self, mock_duckdb_connection, reset_database_state):
        """Test retrieving existing metadata value."""
        # Arrange
        db_module._conn = mock_duckdb_connection
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("1.0.0",)
        mock_duckdb_connection.execute.return_value = mock_cursor

        # Act
        result = db_module.get_app_metadata("version")

        # Assert
        assert result == "1.0.0"
        mock_duckdb_connection.execute.assert_called_once_with(
            "SELECT value FROM app_metadata WHERE key = ?", ["version"]
        )

    def test_get_app_metadata_not_found(self, mock_duckdb_connection, reset_database_state):
        """Test retrieving non-existent metadata returns None."""
        # Arrange
        db_module._conn = mock_duckdb_connection
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_duckdb_connection.execute.return_value = mock_cursor

        # Act
        result = db_module.get_app_metadata("nonexistent")

        # Assert
        assert result is None


class TestInitDb:
    """Test suite for database initialization."""

    @patch("app.services.database._create_indexes")
    def test_creates_all_tables(
        self, mock_create_indexes, mock_duckdb_connection, reset_database_state
    ):
        """Test that all required tables are created during initialization."""
        # Arrange
        db_module._conn = mock_duckdb_connection

        # Act
        db_module.init_db()

        # Assert
        execute_calls = mock_duckdb_connection.execute.call_args_list

        # Check that tables are created
        created_tables = []
        for call_args in execute_calls:
            sql = call_args[0][0] if call_args[0] else call_args[1].get("command", "")
            if "CREATE TABLE" in sql:
                # Extract table name
                if "teams" in sql.lower():
                    created_tables.append("teams")
                elif "players" in sql.lower():
                    created_tables.append("players")
                elif "games" in sql.lower():
                    created_tables.append("games")
                elif "player_game_stats" in sql.lower():
                    created_tables.append("player_game_stats")
                elif "seasons" in sql.lower():
                    created_tables.append("seasons")

        # Verify _create_indexes was called
        mock_create_indexes.assert_called_once_with(mock_duckdb_connection)

        # Verify app_metadata table is created
        metadata_calls = [c for c in execute_calls if "app_metadata" in str(c)]
        assert len(metadata_calls) > 0


class TestCreateIndexes:
    """Test suite for index creation."""

    def test_creates_all_indexes(self, mock_duckdb_connection, reset_database_state):
        """Test that all required indexes are created."""
        # Act
        db_module._create_indexes(mock_duckdb_connection)

        # Assert
        execute_calls = mock_duckdb_connection.execute.call_args_list

        # Check for specific indexes
        index_names = []
        for call_args in execute_calls:
            sql = call_args[0][0]
            if "CREATE INDEX" in sql:
                index_names.append(sql)

        # Verify key indexes are created
        assert any("idx_teams_abbreviation" in idx for idx in index_names)
        assert any("idx_players_team_id" in idx for idx in index_names)
        assert any("idx_games_date" in idx for idx in index_names)
        assert any("idx_stats_player_id" in idx for idx in index_names)


class TestDatabaseConfiguration:
    """Test suite for database configuration constants."""

    def test_data_dir_is_path_object(self):
        """Test that DATA_DIR is a Path object."""
        assert isinstance(db_module.DATA_DIR, Path)

    def test_db_path_is_path_object(self):
        """Test that DB_PATH is a Path object."""
        assert isinstance(db_module.DB_PATH, Path)

    def test_db_path_in_data_dir(self):
        """Test that DB_PATH is within DATA_DIR."""
        assert db_module.DB_PATH.parent == db_module.DATA_DIR

    def test_db_path_has_correct_name(self):
        """Test that DB_PATH has correct filename."""
        assert db_module.DB_PATH.name == "bball_ref.db"


class TestDatabaseIntegration:
    """Integration-style tests with mocked DuckDB."""

    @patch("app.services.database.duckdb.connect")
    def test_full_query_lifecycle(self, mock_connect, reset_database_state):
        """Test complete lifecycle: connect -> query -> close."""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, "Test")]
        mock_conn.execute.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Act - Get connection and execute query
        result = db_module.execute_query("SELECT * FROM test", None)

        # Close connection
        db_module.close_db_connection()

        # Assert
        mock_connect.assert_called_once()
        assert result == [(1, "Test")]
        mock_conn.close.assert_called_once()
        assert db_module._conn is None

    @patch("app.services.database.duckdb.connect")
    def test_multiple_queries_same_connection(self, mock_connect, reset_database_state):
        """Test that multiple queries reuse the same connection."""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [[(1,)], [(2,)], [(3,)]]
        mock_conn.execute.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Act
        db_module.get_db_connection()
        result1 = db_module.execute_query("SELECT 1", None)
        result2 = db_module.execute_query("SELECT 2", None)
        result3 = db_module.execute_query("SELECT 3", None)

        # Assert
        assert mock_connect.call_count == 1  # Only one connection created
        assert result1 == [(1,)]
        assert result2 == [(2,)]
        assert result3 == [(3,)]
        assert mock_conn.execute.call_count == 3
