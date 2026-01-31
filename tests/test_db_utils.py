"""Tests for database utility functions."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.db_utils import QueryBuilder, entity_exists, paginate_query


class TestEntityExists:
    """Tests for entity_exists function."""

    @pytest.fixture
    def mock_execute_query(self):
        """Mock execute_query function."""
        with patch("app.utils.db_utils.execute_query") as mock:
            yield mock

    def test_entity_exists_player_true(self, mock_execute_query):
        """Test checking if a player exists - exists."""
        mock_execute_query.return_value = [(1,)]

        result = entity_exists("player", 2544)

        assert result is True
        mock_execute_query.assert_called_once()
        call_args = mock_execute_query.call_args
        assert "players" in call_args[0][0]
        assert "player_id" in call_args[0][0]
        assert call_args[0][1] == [2544]

    def test_entity_exists_player_false(self, mock_execute_query):
        """Test checking if a player exists - does not exist."""
        mock_execute_query.return_value = []

        result = entity_exists("player", 999999)

        assert result is False

    def test_entity_exists_team(self, mock_execute_query):
        """Test checking if a team exists."""
        mock_execute_query.return_value = [(1,)]

        result = entity_exists("team", 1610612738)

        assert result is True
        call_args = mock_execute_query.call_args
        assert "teams" in call_args[0][0]
        assert "team_id" in call_args[0][0]

    def test_entity_exists_game(self, mock_execute_query):
        """Test checking if a game exists."""
        mock_execute_query.return_value = [(1,)]

        result = entity_exists("game", "0022400001")

        assert result is True
        call_args = mock_execute_query.call_args
        assert "games" in call_args[0][0]
        assert "game_id" in call_args[0][0]

    def test_entity_exists_invalid_type(self):
        """Test checking with invalid entity type raises error."""
        with pytest.raises(ValueError) as exc_info:
            entity_exists("invalid_type", 123)

        assert "Invalid entity_type" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)


class TestPaginateQuery:
    """Tests for paginate_query function."""

    @pytest.fixture
    def mock_execute_query(self):
        """Mock execute_query function."""
        with patch("app.utils.db_utils.execute_query") as mock:
            yield mock

    def test_paginate_query_basic(self, mock_execute_query):
        """Test basic pagination."""
        mock_execute_query.return_value = [
            (1, "LeBron", 5),
            (2, "Stephen", 5),
        ]

        rows, total = paginate_query("SELECT id, name FROM players", [], page=1, page_size=2)

        assert len(rows) == 2
        assert total == 5
        # Check that the query was wrapped with window function
        call_args = mock_execute_query.call_args
        assert "COUNT(*) OVER()" in call_args[0][0]
        assert "LIMIT" in call_args[0][0]
        assert "OFFSET" in call_args[0][0]

    def test_paginate_query_with_params(self, mock_execute_query):
        """Test pagination with query parameters."""
        mock_execute_query.return_value = [(1, "LeBron", 1)]

        rows, total = paginate_query(
            "SELECT id, name FROM players WHERE team_id = ?",
            [1610612747],
            page=2,
            page_size=10,
        )

        call_args = mock_execute_query.call_args
        # Check params include original + limit + offset
        assert call_args[0][1] == [1610612747, 10, 10]  # team_id, limit, offset

    def test_paginate_query_empty_result(self, mock_execute_query):
        """Test pagination with empty result."""
        mock_execute_query.return_value = []

        rows, total = paginate_query("SELECT id FROM players WHERE 1=0", [], page=1, page_size=10)

        assert len(rows) == 0
        assert total == 0

    def test_paginate_query_default_params(self, mock_execute_query):
        """Test pagination with default params."""
        mock_execute_query.return_value = [(1, 100)]

        rows, total = paginate_query("SELECT id FROM players")

        assert total == 100
        call_args = mock_execute_query.call_args
        assert call_args[0][1] == [20, 0]  # default page_size=20, offset=0


class TestQueryBuilder:
    """Tests for QueryBuilder class."""

    def test_query_builder_initialization(self):
        """Test QueryBuilder initialization."""
        qb = QueryBuilder()

        assert qb._select_columns == []
        assert qb._from_table == ""
        assert qb._where_clauses == []
        assert qb._where_params == []
        assert qb._order_by == ""
        assert qb._limit is None
        assert qb._offset is None

    def test_query_builder_select(self):
        """Test select method."""
        qb = QueryBuilder()
        result = qb.select("players", ["id", "name", "team_id"])

        assert result is qb  # Returns self for chaining
        assert qb._from_table == "players"
        assert qb._select_columns == ["id", "name", "team_id"]

    def test_query_builder_select_all(self):
        """Test select method with no columns (select *)."""
        qb = QueryBuilder()
        qb.select("players")

        assert qb._select_columns == ["*"]

    def test_query_builder_add_where(self):
        """Test add_where method."""
        qb = QueryBuilder()
        result = qb.add_where("team_id = ?", [1610612747])

        assert result is qb
        assert qb._where_clauses == ["team_id = ?"]
        assert qb._where_params == [1610612747]

    def test_query_builder_add_where_no_params(self):
        """Test add_where method without params."""
        qb = QueryBuilder()
        qb.add_where("active = 1")

        assert qb._where_clauses == ["active = 1"]
        assert qb._where_params == []

    def test_query_builder_add_where_multiple(self):
        """Test multiple add_where calls."""
        qb = QueryBuilder()
        qb.add_where("team_id = ?", [1610612747]).add_where("position = ?", ["PG"])

        assert qb._where_clauses == ["team_id = ?", "position = ?"]
        assert qb._where_params == [1610612747, "PG"]

    def test_query_builder_add_ilike(self):
        """Test add_ilike method."""
        qb = QueryBuilder()
        result = qb.add_ilike("name", "%james%")

        assert result is qb
        assert qb._where_clauses == ["name ILIKE ?"]
        assert qb._where_params == ["%james%"]

    def test_query_builder_set_order_by(self):
        """Test set_order_by method."""
        qb = QueryBuilder()
        result = qb.set_order_by("last_name ASC, first_name DESC")

        assert result is qb
        assert qb._order_by == "last_name ASC, first_name DESC"

    def test_query_builder_set_pagination(self):
        """Test set_pagination method."""
        qb = QueryBuilder()
        result = qb.set_pagination(page=3, page_size=25)

        assert result is qb
        assert qb._limit == 25
        assert qb._offset == 50  # (3-1) * 25

    def test_query_builder_build_basic(self):
        """Test build method with basic query."""
        qb = QueryBuilder()
        qb.select("players", ["id", "name"])

        query, params = qb.build()

        assert query == "SELECT id, name FROM players"
        assert params == []

    def test_query_builder_build_with_where(self):
        """Test build method with WHERE clause."""
        qb = QueryBuilder()
        qb.select("players", ["id", "name"]).add_where("team_id = ?", [1610612747])

        query, params = qb.build()

        assert "SELECT id, name FROM players" in query
        assert "WHERE team_id = ?" in query
        assert params == [1610612747]

    def test_query_builder_build_with_order_by(self):
        """Test build method with ORDER BY."""
        qb = QueryBuilder()
        qb.select("players", ["id"]).set_order_by("name ASC")

        query, params = qb.build()

        assert "ORDER BY name ASC" in query

    def test_query_builder_build_with_pagination(self):
        """Test build method with pagination."""
        qb = QueryBuilder()
        qb.select("players", ["id"]).set_pagination(page=2, page_size=10)

        query, params = qb.build()

        assert "LIMIT 10" in query
        assert "OFFSET 10" in query

    def test_query_builder_build_complete(self):
        """Test build method with all clauses."""
        qb = QueryBuilder()
        qb.select("players", ["id", "name", "position"])
        qb.add_where("team_id = ?", [1610612747])
        qb.add_where("active = ?", [True])
        qb.set_order_by("name ASC")
        qb.set_pagination(page=1, page_size=20)

        query, params = qb.build()

        assert "SELECT id, name, position FROM players" in query
        assert "WHERE team_id = ? AND active = ?" in query
        assert "ORDER BY name ASC" in query
        assert "LIMIT 20" in query
        assert "OFFSET 0" in query
        assert params == [1610612747, True]

    def test_query_builder_build_no_table_raises(self):
        """Test build method raises error if no table specified."""
        qb = QueryBuilder()

        with pytest.raises(ValueError) as exc_info:
            qb.build()

        assert "Table must be specified" in str(exc_info.value)

    def test_query_builder_build_with_count(self):
        """Test build_with_count method."""
        qb = QueryBuilder()
        qb.select("players", ["id", "name"])
        qb.add_where("team_id = ?", [1610612747])

        query, params = qb.build_with_count()

        assert "COUNT(*) OVER() as _total_count" in query
        assert "SELECT id, name," in query
        assert params == [1610612747]

    def test_query_builder_reset(self):
        """Test reset method."""
        qb = QueryBuilder()
        qb.select("players", ["id"])
        qb.add_where("team_id = ?", [1610612747])
        qb.set_order_by("name ASC")
        qb.set_pagination(page=1, page_size=10)

        result = qb.reset()

        assert result is qb
        assert qb._select_columns == []
        assert qb._from_table == ""
        assert qb._where_clauses == []
        assert qb._where_params == []
        assert qb._order_by == ""
        assert qb._limit is None
        assert qb._offset is None

    def test_query_builder_chaining(self):
        """Test method chaining."""
        qb = QueryBuilder()
        query, params = (
            qb.select("players", ["id", "name"])
            .add_where("team_id = ?", [1610612747])
            .add_ilike("name", "%james%")
            .set_order_by("name ASC")
            .set_pagination(page=1, page_size=10)
            .build()
        )

        assert "SELECT id, name FROM players" in query
        assert "WHERE team_id = ? AND name ILIKE ?" in query
        assert "ORDER BY name ASC" in query
        assert "LIMIT 10" in query
        assert params == [1610612747, "%james%"]
