"""Database utility functions and classes for HoopsDB.

Provides shared utilities to eliminate code duplication across routers,
including entity existence checks, query building, and pagination helpers.
"""

from typing import Any

from app.services.database import execute_query

# Valid entity types for existence checks
VALID_ENTITY_TYPES = {"player", "team", "game"}

# Entity configuration mapping
_ENTITY_CONFIG = {
    "player": {"table": "players", "id_column": "player_id"},
    "team": {"table": "teams", "id_column": "team_id"},
    "game": {"table": "games", "id_column": "game_id"},
}


def entity_exists(entity_type: str, entity_id: int | str) -> bool:
    """Check if an entity exists in the database.

    Args:
        entity_type: Type of entity ('player', 'team', or 'game').
        entity_id: The unique identifier for the entity.

    Returns:
        True if the entity exists, False otherwise.

    Raises:
        ValueError: If entity_type is not a valid entity type.

    Examples:
        >>> entity_exists("player", 2544)
        True
        >>> entity_exists("team", 999999)
        False
    """
    if entity_type not in VALID_ENTITY_TYPES:
        valid_types = ", ".join(sorted(VALID_ENTITY_TYPES))
        raise ValueError(f"Invalid entity_type '{entity_type}'. Must be one of: {valid_types}")

    config = _ENTITY_CONFIG[entity_type]
    query = f"SELECT 1 FROM {config['table']} WHERE {config['id_column']} = ?"

    result = execute_query(query, [entity_id])
    return bool(result)


def paginate_query(
    base_query: str,
    params: list[Any] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[Any, ...]], int]:
    """Execute a paginated query with total count using window function.

    Wraps the base query to add COUNT(*) OVER() for efficient pagination.
    The base query should NOT include LIMIT/OFFSET clauses.

    Args:
        base_query: The SQL query to execute (without LIMIT/OFFSET).
        params: Query parameters.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        Tuple of (rows, total_count). Each row includes the total count as the last column.

    Example:
        >>> query = "SELECT player_id, first_name FROM players WHERE team_id = ?"
        >>> rows, total = paginate_query(query, [1], page=1, page_size=10)
        >>> # rows contains tuples like (player_id, first_name, total_count)
    """
    if params is None:
        params = []

    offset = (page - 1) * page_size

    # Wrap the base query to add window function for count
    wrapped_query = f"""
        SELECT *, COUNT(*) OVER() as _total_count
        FROM ({base_query}) as _inner
        LIMIT ? OFFSET ?
    """

    query_params = list(params) + [page_size, offset]
    rows = execute_query(wrapped_query, query_params)

    total = rows[0][-1] if rows else 0
    return rows, total


class QueryBuilder:
    """Builder class for constructing dynamic SQL queries safely.

    Helps construct queries with dynamic WHERE clauses, preventing SQL injection
    by using parameterized queries throughout.

    Example:
        >>> qb = QueryBuilder()
        >>> qb.select("players", ["player_id", "first_name", "last_name"])
        >>> qb.add_where("team_id = ?", [1])
        >>> qb.add_where("position = ?", ["PG"])
        >>> query, params = qb.build()
        >>> # query: "SELECT player_id, first_name, last_name FROM players WHERE team_id = ? AND position = ?"
        >>> # params: [1, "PG"]
    """

    def __init__(self) -> None:
        """Initialize a new QueryBuilder instance."""
        self._select_columns: list[str] = []
        self._from_table: str = ""
        self._where_clauses: list[str] = []
        self._where_params: list[Any] = []
        self._order_by: str = ""
        self._limit: int | None = None
        self._offset: int | None = None

    def select(self, table: str, columns: list[str] | None = None) -> "QueryBuilder":
        """Set the SELECT clause.

        Args:
            table: Table name to select from.
            columns: List of column names to select. If None, selects all (*).

        Returns:
            Self for method chaining.
        """
        self._from_table = table
        self._select_columns = columns if columns else ["*"]
        return self

    def add_where(self, clause: str, params: list[Any] | None = None) -> "QueryBuilder":
        """Add a WHERE clause condition.

        Args:
            clause: SQL condition (e.g., "team_id = ?" or "age > ?").
            params: Parameters for the condition.

        Returns:
            Self for method chaining.
        """
        self._where_clauses.append(clause)
        if params:
            self._where_params.extend(params)
        return self

    def add_ilike(self, column: str, pattern: str) -> "QueryBuilder":
        """Add a case-insensitive LIKE condition.

        Args:
            column: Column name to search.
            pattern: Search pattern (e.g., "%jordan%").

        Returns:
            Self for method chaining.
        """
        self._where_clauses.append(f"{column} ILIKE ?")
        self._where_params.append(pattern)
        return self

    def set_order_by(self, order_by: str) -> "QueryBuilder":
        """Set the ORDER BY clause.

        Args:
            order_by: Column(s) to order by (e.g., "last_name ASC, first_name DESC").

        Returns:
            Self for method chaining.
        """
        self._order_by = order_by
        return self

    def set_pagination(self, page: int, page_size: int) -> "QueryBuilder":
        """Set pagination parameters.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Self for method chaining.
        """
        self._limit = page_size
        self._offset = (page - 1) * page_size
        return self

    def build(self) -> tuple[str, list[Any]]:
        """Build and return the final SQL query and parameters.

        Returns:
            Tuple of (query_string, parameters).

        Raises:
            ValueError: If SELECT or FROM clause is not set.
        """
        if not self._from_table:
            raise ValueError("Table must be specified using select()")

        columns_str = ", ".join(self._select_columns)
        query = f"SELECT {columns_str} FROM {self._from_table}"

        if self._where_clauses:
            where_sql = " AND ".join(self._where_clauses)
            query += f" WHERE {where_sql}"

        if self._order_by:
            query += f" ORDER BY {self._order_by}"

        if self._limit is not None:
            query += f" LIMIT {self._limit}"

        if self._offset is not None:
            query += f" OFFSET {self._offset}"

        return query, list(self._where_params)

    def build_with_count(self) -> tuple[str, list[Any]]:
        """Build query with COUNT(*) OVER() window function for pagination.

        Returns:
            Tuple of (query_string, parameters). The result rows will include
            total_count as the last column.
        """
        if not self._from_table:
            raise ValueError("Table must be specified using select()")

        columns_str = ", ".join(self._select_columns)

        # Add window function for count
        select_with_count = f"{columns_str}, COUNT(*) OVER() as _total_count"

        query = f"SELECT {select_with_count} FROM {self._from_table}"

        if self._where_clauses:
            where_sql = " AND ".join(self._where_clauses)
            query += f" WHERE {where_sql}"

        if self._order_by:
            query += f" ORDER BY {self._order_by}"

        if self._limit is not None:
            query += f" LIMIT {self._limit}"

        if self._offset is not None:
            query += f" OFFSET {self._offset}"

        return query, list(self._where_params)

    def reset(self) -> "QueryBuilder":
        """Reset the builder to initial state.

        Returns:
            Self for method chaining.
        """
        self._select_columns = []
        self._from_table = ""
        self._where_clauses = []
        self._where_params = []
        self._order_by = ""
        self._limit = None
        self._offset = None
        return self
