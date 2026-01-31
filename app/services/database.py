"""Database service for DuckDB connection and schema management."""

from pathlib import Path
from typing import Any

import duckdb

# Database configuration
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "bball_ref.db"

# Global connection instance
_conn: duckdb.DuckDBPyConnection | None = None


def get_db_connection() -> duckdb.DuckDBPyConnection:
    """Get or create a DuckDB connection.

    Returns:
        duckdb.DuckDBPyConnection: Active database connection.

    Raises:
        RuntimeError: If connection cannot be established.
    """
    global _conn

    if _conn is None:
        try:
            _conn = duckdb.connect(str(DB_PATH))
        except Exception as e:
            raise RuntimeError(f"Failed to connect to database: {e}") from e

    return _conn


def close_db_connection() -> None:
    """Close the database connection."""
    global _conn

    if _conn is not None:
        _conn.close()
        _conn = None


# Index configuration for _create_indexes
INDEX_CONFIG: list[tuple[str, str, str]] = [
    # Team indexes
    ("idx_teams_abbreviation", "teams", "abbreviation"),
    ("idx_teams_conference", "teams", "conference"),
    ("idx_teams_division", "teams", "division"),
    # Player indexes
    ("idx_players_team_id", "players", "team_id"),
    ("idx_players_name", "players", "last_name, first_name"),
    ("idx_players_full_name", "players", "full_name"),
    ("idx_players_active", "players", "active"),
    ("idx_players_hall_of_fame", "players", "hall_of_fame"),
    # Game indexes
    ("idx_games_date", "games", "game_date"),
    ("idx_games_season", "games", "season"),
    ("idx_games_season_id", "games", "season_id"),
    ("idx_games_home_team", "games", "home_team_id"),
    ("idx_games_away_team", "games", "away_team_id"),
    ("idx_games_is_playoff", "games", "is_playoff"),
    # Player game stats indexes
    ("idx_stats_game_id", "player_game_stats", "game_id"),
    ("idx_stats_player_id", "player_game_stats", "player_id"),
    ("idx_stats_team_id", "player_game_stats", "team_id"),
    ("idx_stats_player_game", "player_game_stats", "player_id, game_id"),
    # Seasons indexes
    ("idx_seasons_year_start", "seasons", "year_start"),
    ("idx_seasons_year_end", "seasons", "year_end"),
    # Player season stats indexes
    ("idx_player_season_stats_player", "player_season_stats", "player_id"),
    ("idx_player_season_stats_season", "player_season_stats", "season_id"),
    # Player game logs indexes
    ("idx_player_game_logs_player", "player_game_logs", "player_id"),
    ("idx_player_game_logs_game", "player_game_logs", "game_id"),
    # Team season stats indexes
    ("idx_team_season_stats_team", "team_season_stats", "team_id"),
    ("idx_team_season_stats_season", "team_season_stats", "season_id"),
    # Awards indexes
    ("idx_awards_season", "awards", "season_id"),
    ("idx_awards_player", "awards", "player_id"),
    ("idx_awards_type", "awards", "award_type"),
    # Draft picks indexes
    ("idx_draft_picks_season", "draft_picks", "season_id"),
    ("idx_draft_picks_team", "draft_picks", "team_id"),
    ("idx_draft_picks_player", "draft_picks", "player_id"),
]


def _create_teams_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the teams table.

    TODO: MEDIUM - Add franchise tracking columns
    Missing columns per PRD:
      - franchise_id: For tracking team relocations (e.g., Seattle SuperSonics -> OKC Thunder)
      - current_abbrev: Current abbreviation if team relocated
    These fields enable proper franchise history tracking across team moves
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id VARCHAR PRIMARY KEY,
            full_name VARCHAR NOT NULL,
            abbreviation VARCHAR(3) NOT NULL,
            nickname VARCHAR NOT NULL,
            city VARCHAR NOT NULL,
            state VARCHAR,
            year_founded INTEGER,
            arena VARCHAR,
            owner VARCHAR,
            general_manager VARCHAR,
            head_coach VARCHAR,
            conference VARCHAR(8) NOT NULL,
            division VARCHAR(9) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _create_players_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the players table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id VARCHAR PRIMARY KEY,
            first_name VARCHAR NOT NULL,
            last_name VARCHAR NOT NULL,
            full_name VARCHAR NOT NULL,
            team_id VARCHAR NOT NULL,
            position VARCHAR,
            jersey_number INTEGER,
            height VARCHAR(5),
            height_cm INTEGER,
            weight INTEGER,
            weight_kg INTEGER,
            birth_date DATE,
            birth_place VARCHAR,
            birth_country VARCHAR,
            country VARCHAR,
            college VARCHAR,
            draft_year INTEGER,
            draft_round INTEGER,
            draft_number INTEGER,
            draft_team_id VARCHAR,
            shoots VARCHAR(1),
            active BOOLEAN DEFAULT TRUE,
            hall_of_fame BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (draft_team_id) REFERENCES teams(team_id)
        )
    """)


def _create_games_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the games table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id VARCHAR PRIMARY KEY,
            season_id VARCHAR NOT NULL,
            season INTEGER NOT NULL,
            season_type VARCHAR(14) NOT NULL,
            game_date DATE NOT NULL,
            home_team_id VARCHAR NOT NULL,
            away_team_id VARCHAR NOT NULL,
            home_score INTEGER,
            away_score INTEGER,
            home_q1 INTEGER,
            home_q2 INTEGER,
            home_q3 INTEGER,
            home_q4 INTEGER,
            home_ot INTEGER,
            away_q1 INTEGER,
            away_q2 INTEGER,
            away_q3 INTEGER,
            away_q4 INTEGER,
            away_ot INTEGER,
            winner_team_id VARCHAR,
            is_playoff BOOLEAN DEFAULT FALSE,
            is_overtime BOOLEAN DEFAULT FALSE,
            attendance INTEGER,
            arena VARCHAR,
            status VARCHAR(9) DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (season_id) REFERENCES seasons(season_id),
            FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
            FOREIGN KEY (away_team_id) REFERENCES teams(team_id),
            FOREIGN KEY (winner_team_id) REFERENCES teams(team_id)
        )
    """)


def _create_player_game_stats_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the player_game_stats table.

    TODO: LOW - Add foreign key constraints
    Currently no FK constraints on game_id, player_id, team_id
    Should reference:
      - game_id REFERENCES games(game_id)
      - player_id REFERENCES players(player_id)
      - team_id REFERENCES teams(team_id)
    This would improve data integrity but may impact bulk insert performance
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_game_stats (
            stat_id INTEGER PRIMARY KEY,
            game_id VARCHAR NOT NULL,
            player_id VARCHAR NOT NULL,
            team_id VARCHAR NOT NULL,
            minutes_played DOUBLE,
            points INTEGER DEFAULT 0,
            rebounds_offensive INTEGER DEFAULT 0,
            rebounds_defensive INTEGER DEFAULT 0,
            assists INTEGER DEFAULT 0,
            steals INTEGER DEFAULT 0,
            blocks INTEGER DEFAULT 0,
            turnovers INTEGER DEFAULT 0,
            personal_fouls INTEGER DEFAULT 0,
            fg_made INTEGER DEFAULT 0,
            fg_attempted INTEGER DEFAULT 0,
            fg3_made INTEGER DEFAULT 0,
            fg3_attempted INTEGER DEFAULT 0,
            ft_made INTEGER DEFAULT 0,
            ft_attempted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _create_seasons_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the seasons table.

    TODO: CRITICAL - Create ETL script to populate this table
    This table stores NBA season metadata but NO ETL populates it.

    Data to include:
      - All NBA seasons from 1946-47 to present
      - season_id (e.g., "2023-24")
      - year_start, year_end
      - display_name (e.g., "2023-24 NBA Season")

    Implementation approach:
      1. Create etl_seasons.py script
      2. Generate seasons programmatically (1946-47 to current)
      3. Insert into this table

    Note: This is a prerequisite for other ETLs that reference season_id

    File to create: scripts/etl_seasons.py
    Priority: CRITICAL - Required as foreign key reference for other tables
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seasons (
            season_id VARCHAR PRIMARY KEY,
            year_start INTEGER NOT NULL,
            year_end INTEGER NOT NULL,
            league VARCHAR DEFAULT 'NBA',
            display_name VARCHAR
        )
    """)


def _create_player_season_stats_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the player_season_stats table.

    TODO: CRITICAL - Create ETL script to populate this table
    This table has columns for advanced statistics but NO ETL populates it:
      - per: Player Efficiency Rating (complex formula requiring league averages)
      - ts_pct: True Shooting % (can calculate from basic stats)
      - usg_pct: Usage Rate (requires team totals)
      - ortg: Offensive Rating (requires team pace and league averages)
      - drtg: Defensive Rating (requires team defensive stats)
      - ws: Win Shares (complex calculation)
      - ws_per_48: Win Shares per 48 minutes
      - bpm: Box Plus/Minus (requires regression coefficients)
      - vorp: Value Over Replacement Player (derived from BPM)

    Advanced statistics formulas verified correct per basketball-reference.com:
      - TS% = PTS / (2 * (FGA + 0.44 * FTA))
      - USG% = 100 * ((FGA + 0.44 * FTA + TO) * (TmMP / 5)) / (MP * (TmFGA + 0.44 * TmFTA + TmTO))
      - PER: Complex formula (see basketball-reference.com/about/per.html)
      - WS: Based on Marginal Offensive/Defensive Contribution
      - BPM: Box Plus/Minus with team adjustment
      - VORP: (BPM - (-2.0)) * (% of minutes played)

    Implementation approach:
      1. Aggregate player_game_stats to season totals
      2. Calculate per-game averages
      3. Calculate advanced stats using league averages
      4. Insert into this table

    File to create: scripts/etl_player_season_stats.py
    Priority: CRITICAL - Required for player career stats and leaderboards
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_season_stats (
            stat_id BIGINT PRIMARY KEY,
            player_id VARCHAR,
            season_id VARCHAR,
            team_id VARCHAR,
            age INTEGER,
            games_played INTEGER,
            games_started INTEGER,
            minutes_played INTEGER,
            field_goals INTEGER,
            field_goal_attempts INTEGER,
            fg_pct FLOAT,
            three_pointers INTEGER,
            three_point_attempts INTEGER,
            fg3_pct FLOAT,
            two_pointers INTEGER,
            two_point_attempts INTEGER,
            fg2_pct FLOAT,
            effective_fg_pct FLOAT,
            free_throws INTEGER,
            free_throw_attempts INTEGER,
            ft_pct FLOAT,
            offensive_rebounds INTEGER,
            defensive_rebounds INTEGER,
            total_rebounds INTEGER,
            assists INTEGER,
            steals INTEGER,
            blocks INTEGER,
            turnovers INTEGER,
            personal_fouls INTEGER,
            points INTEGER,
            per FLOAT,
            ts_pct FLOAT,
            usg_pct FLOAT,
            ortg FLOAT,
            drtg FLOAT,
            ws FLOAT,
            ws_per_48 FLOAT,
            bpm FLOAT,
            vorp FLOAT,
            FOREIGN KEY (player_id) REFERENCES players(player_id),
            FOREIGN KEY (season_id) REFERENCES seasons(season_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id)
        )
    """)


def _create_player_game_logs_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the player_game_logs table.

    TODO: CRITICAL - Create ETL script to populate this table
    This table has columns but NO ETL populates it:
      - plus_minus: Net point differential while player was on court
      - ts_pct: True Shooting % per game
      - efg_pct: Effective FG% per game
      - is_home, is_win: Game context flags

    Data source: PlayerGameLogs endpoint from nba_api already provides PLUS_MINUS
    Other calculated fields can be derived from basic stats in player_game_stats

    Implementation approach:
      1. Query player_game_stats for game-by-game data
      2. Calculate ts_pct and efg_pct per game
      3. Join with games table for is_home, is_win, opponent_id
      4. Insert into this table

    File to create: scripts/etl_player_game_logs.py
    Priority: CRITICAL - Required for player game log display
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_game_logs (
            log_id BIGINT PRIMARY KEY,
            player_id VARCHAR,
            game_id VARCHAR,
            team_id VARCHAR,
            opponent_id VARCHAR,
            is_home BOOLEAN,
            is_win BOOLEAN,
            minutes_played INTEGER,
            field_goals INTEGER,
            field_goal_attempts INTEGER,
            fg_pct FLOAT,
            three_pointers INTEGER,
            three_point_attempts INTEGER,
            fg3_pct FLOAT,
            free_throws INTEGER,
            free_throw_attempts INTEGER,
            ft_pct FLOAT,
            offensive_rebounds INTEGER,
            defensive_rebounds INTEGER,
            total_rebounds INTEGER,
            assists INTEGER,
            steals INTEGER,
            blocks INTEGER,
            turnovers INTEGER,
            personal_fouls INTEGER,
            points INTEGER,
            plus_minus INTEGER,
            ts_pct FLOAT,
            efg_pct FLOAT,
            FOREIGN KEY (player_id) REFERENCES players(player_id),
            FOREIGN KEY (game_id) REFERENCES games(game_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (opponent_id) REFERENCES teams(team_id)
        )
    """)


def _create_team_season_stats_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the team_season_stats table.

    TODO: CRITICAL - Create ETL script to populate this table
    This table has columns for team advanced stats but NO ETL populates it:
      - pace: Team pace factor (possessions per game)
      - srs: Simple Rating System (point differential adjusted for SOS)
      - ortg: Offensive Rating (points per 100 possessions)
      - drtg: Defensive Rating (points allowed per 100 possessions)
      - nrtg: Net Rating (ortg - drtg)

    Advanced statistics formulas verified correct per basketball-reference.com:
      - Pace = 48 * ((Tm Poss + Opp Poss) / (2 * (Tm MP / 5)))
      - SRS: Requires solving system of equations for all teams
      - ORtg = (Points Scored / Possessions) * 100
      - DRtg = (Points Allowed / Possessions) * 100
      - NRtg = ORtg - DRtg

    Data source:
      1. Aggregate from player_game_stats for offensive stats
      2. Aggregate opponent stats from games table
      3. Calculate possessions using standard formula
      4. Calculate SRS via matrix algebra or iterative method

    Implementation approach:
      1. Aggregate team stats per season
      2. Calculate opponent stats per season
      3. Calculate possessions for pace
      4. Calculate SRS (Simple Rating System)
      5. Calculate ORtg, DRtg, NRtg
      6. Insert into this table

    File to create: scripts/etl_team_season_stats.py
    Priority: CRITICAL - Required for team standings and analytics
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_season_stats (
            stat_id BIGINT PRIMARY KEY,
            team_id VARCHAR,
            season_id VARCHAR,
            wins INTEGER,
            losses INTEGER,
            win_pct FLOAT,
            games_played INTEGER,
            minutes_played INTEGER,
            points_for INTEGER,
            pts_per_game FLOAT,
            field_goals INTEGER,
            field_goal_attempts INTEGER,
            fg_pct FLOAT,
            three_pointers INTEGER,
            three_point_attempts INTEGER,
            fg3_pct FLOAT,
            free_throws INTEGER,
            free_throw_attempts INTEGER,
            ft_pct FLOAT,
            offensive_rebounds INTEGER,
            defensive_rebounds INTEGER,
            total_rebounds INTEGER,
            assists INTEGER,
            steals INTEGER,
            blocks INTEGER,
            turnovers INTEGER,
            personal_fouls INTEGER,
            points_against INTEGER,
            opp_pts_per_game FLOAT,
            opp_field_goals INTEGER,
            opp_field_goal_attempts INTEGER,
            opp_fg_pct FLOAT,
            opp_three_pointers INTEGER,
            opp_three_point_attempts INTEGER,
            opp_fg3_pct FLOAT,
            opp_free_throws INTEGER,
            opp_free_throw_attempts INTEGER,
            opp_ft_pct FLOAT,
            opp_offensive_rebounds INTEGER,
            opp_defensive_rebounds INTEGER,
            opp_total_rebounds INTEGER,
            opp_assists INTEGER,
            opp_steals INTEGER,
            opp_blocks INTEGER,
            opp_turnovers INTEGER,
            opp_personal_fouls INTEGER,
            pace FLOAT,
            srs FLOAT,
            ortg FLOAT,
            drtg FLOAT,
            nrtg FLOAT,
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (season_id) REFERENCES seasons(season_id)
        )
    """)


def _create_awards_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the awards table.

    TODO: CRITICAL - Create ETL script to populate this table
    This table stores NBA awards but NO ETL populates it.

    Awards to track:
      - MVP (Most Valuable Player)
      - All-NBA First/Second/Third Team
      - ROY (Rookie of the Year)
      - DPOY (Defensive Player of the Year)
      - All-Defensive First/Second Team
      - All-Star selections
      - And more...

    Data sources:
      1. NBA API Awards endpoints (if available)
      2. Basketball Reference CSV exports (planning/csv_data/)
      3. Manual data entry for historical completeness

    Implementation approach:
      1. Create etl_awards.py script
      2. Load from CSV or API
      3. Map player/team IDs
      4. Insert into this table

    File to create: scripts/etl_awards.py
    Priority: CRITICAL - Required for awards tracking and player achievements
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS awards (
            award_id BIGINT PRIMARY KEY,
            award_name VARCHAR NOT NULL,
            award_type VARCHAR,
            season_id VARCHAR,
            player_id VARCHAR,
            team_id VARCHAR,
            rank INTEGER,
            points_won INTEGER,
            points_max INTEGER,
            share FLOAT,
            FOREIGN KEY (player_id) REFERENCES players(player_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (season_id) REFERENCES seasons(season_id)
        )
    """)


def _create_draft_picks_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the draft_picks table.

    TODO: CRITICAL - Create ETL script to populate this table
    This table stores NBA draft history but NO ETL populates it.

    Data to include:
      - All NBA draft picks from 1947 to present
      - Draft year, round, pick number
      - Team that made the selection
      - Player selected
      - College/nationality

    Data sources:
      1. Basketball Reference CSV exports (planning/csv_data/)
      2. NBA API Draft endpoints (limited historical data)
      3. Manual compilation for older drafts

    Implementation approach:
      1. Create etl_draft_picks.py script
      2. Load from CSV files
      3. Map team and player IDs
      4. Insert into this table

    File to create: scripts/etl_draft_picks.py
    Priority: CRITICAL - Required for draft history feature
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS draft_picks (
            draft_id BIGINT PRIMARY KEY,
            season_id VARCHAR,
            round INTEGER,
            pick_number INTEGER,
            team_id VARCHAR,
            player_id VARCHAR,
            college VARCHAR,
            nationality VARCHAR,
            FOREIGN KEY (season_id) REFERENCES seasons(season_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        )
    """)


def _create_app_metadata_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the app_metadata table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_metadata (
            key VARCHAR PRIMARY KEY,
            value VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _create_indexes(conn: duckdb.DuckDBPyConnection) -> None:
    """Create indexes for performance optimization.

    Args:
        conn: Active database connection.
    """
    for index_name, table, columns in INDEX_CONFIG:
        conn.execute(f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table}({columns})
        """)


def init_db() -> None:
    """Initialize database with all tables and indexes.

    Creates tables matching Pydantic models if they don't exist.
    """
    conn = get_db_connection()

    # Create tables in dependency order
    _create_teams_table(conn)
    _create_players_table(conn)
    _create_seasons_table(conn)
    _create_games_table(conn)
    _create_player_game_stats_table(conn)
    _create_player_season_stats_table(conn)
    _create_player_game_logs_table(conn)
    _create_team_season_stats_table(conn)
    _create_awards_table(conn)
    _create_draft_picks_table(conn)
    _create_app_metadata_table(conn)

    # Create indexes for common query patterns
    _create_indexes(conn)


def set_app_metadata(key: str, value: str) -> None:
    """Set or update application metadata.

    Args:
        key: Metadata key.
        value: Metadata value.
    """
    conn = get_db_connection()
    conn.execute(
        """
        INSERT OR REPLACE INTO app_metadata (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """,
        [key, value],
    )


def get_app_metadata(key: str) -> str | None:
    """Get application metadata value.

    Args:
        key: Metadata key.

    Returns:
        Metadata value or None if not found.
    """
    conn = get_db_connection()
    result = conn.execute("SELECT value FROM app_metadata WHERE key = ?", [key]).fetchone()

    return result[0] if result else None


def execute_query(query: str, params: list[Any] | None = None) -> list[tuple]:
    """Execute a SQL query and return results.

    Args:
        query: SQL query string.
        params: Optional query parameters.

    Returns:
        Query results as list of tuples.

    Raises:
        RuntimeError: If query execution fails.
    """
    conn = get_db_connection()

    try:
        if params:
            result = conn.execute(query, params).fetchall()
        else:
            result = conn.execute(query).fetchall()
        return result
    except Exception as e:
        raise RuntimeError(f"Query execution failed: {e}") from e


def execute_command(command: str, params: list[Any] | None = None) -> int:
    """Execute a SQL command (INSERT, UPDATE, DELETE).

    Args:
        command: SQL command string.
        params: Optional command parameters.

    Returns:
        Number of rows affected.

    Raises:
        RuntimeError: If command execution fails.
    """
    conn = get_db_connection()

    try:
        if params:
            conn.execute(command, params)
        else:
            conn.execute(command)
        return conn.rowcount if conn.rowcount is not None else 0
    except Exception as e:
        raise RuntimeError(f"Command execution failed: {e}") from e


# =============================================================================
# Batch Operations and Advanced Utilities
# =============================================================================

from contextlib import contextmanager


def get_optimized_connection(threads: int = 4, memory_limit: str = "1GB"):
    """Get database connection optimized for bulk operations.

    Args:
        threads: Number of threads for parallel operations.
        memory_limit: Memory limit for the connection.

    Returns:
        Optimized DuckDB connection.
    """
    conn = get_db_connection()
    conn.execute(f"SET threads={threads}")
    conn.execute(f"SET memory_limit = '{memory_limit}'")
    return conn


@contextmanager
def transaction():
    """Context manager for database transactions.

    Automatically handles BEGIN, COMMIT, and ROLLBACK.

    Example:
        >>> with transaction() as conn:
        ...     conn.execute("INSERT INTO table VALUES (?)", [value])
    """
    conn = get_db_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def execute_many(query: str, values: list[tuple], batch_size: int = 1000) -> int:
    """Execute INSERT with batching for large datasets.

    Args:
        query: SQL INSERT query with placeholders.
        values: List of tuples with values to insert.
        batch_size: Number of rows per batch.

    Returns:
        Total number of rows inserted.

    Raises:
        RuntimeError: If bulk insert fails.
    """
    if not values:
        return 0

    conn = get_db_connection()
    total_inserted = 0

    try:
        for i in range(0, len(values), batch_size):
            batch = values[i : i + batch_size]
            conn.executemany(query, batch)
            total_inserted += len(batch)
        return total_inserted
    except Exception as e:
        raise RuntimeError(f"Bulk insert failed after {total_inserted} rows: {e}") from e


def insert_dataframe(df: "pd.DataFrame", table_name: str, batch_size: int = 1000) -> int:
    """Insert a pandas DataFrame into a database table.

    Args:
        df: DataFrame to insert.
        table_name: Target table name.
        batch_size: Number of rows per batch for large DataFrames.

    Returns:
        Number of rows inserted.

    Raises:
        RuntimeError: If insert fails.
    """
    import pandas as pd

    if df.empty:
        return 0

    conn = get_db_connection()

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
        raise RuntimeError(f"Failed to insert DataFrame into {table_name}: {e}") from e


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database.

    Args:
        table_name: Name of the table to check.

    Returns:
        True if table exists, False otherwise.
    """
    conn = get_db_connection()
    try:
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()
        return result[0] > 0 if result else False
    except Exception:
        return False


def get_row_count(table_name: str) -> int:
    """Get the row count of a table.

    Args:
        table_name: Name of the table.

    Returns:
        Number of rows in the table.

    Raises:
        RuntimeError: If query fails.
    """
    conn = get_db_connection()
    try:
        result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0
    except Exception as e:
        raise RuntimeError(f"Failed to get row count for {table_name}: {e}") from e


def truncate_table(table_name: str) -> None:
    """Safely truncate a table (delete all rows).

    Args:
        table_name: Name of the table to truncate.

    Raises:
        RuntimeError: If truncate fails.
    """
    conn = get_db_connection()
    try:
        conn.execute(f"DELETE FROM {table_name}")
    except Exception as e:
        raise RuntimeError(f"Failed to truncate table {table_name}: {e}") from e


def create_temp_table(table_name: str, schema: str) -> str:
    """Create temporary table for staging data.

    Args:
        table_name: Base name for the temp table.
        schema: SQL schema definition (e.g., "id INTEGER, name VARCHAR").

    Returns:
        Name of the created temp table.

    Raises:
        RuntimeError: If creation fails.
    """
    temp_table_name = f"{table_name}_temp"
    conn = get_db_connection()

    try:
        conn.execute(f"DROP TABLE IF EXISTS {temp_table_name}")
        conn.execute(f"CREATE TABLE {temp_table_name} ({schema})")
        return temp_table_name
    except Exception as e:
        raise RuntimeError(f"Failed to create temporary table {temp_table_name}: {e}") from e


def swap_tables(temp_table: str, production_table: str) -> None:
    """Atomic swap for zero-downtime table updates.

    Args:
        temp_table: Temporary table with new data.
        production_table: Production table to replace.

    Raises:
        RuntimeError: If swap fails.
    """
    backup_table = f"{production_table}_backup"
    conn = get_db_connection()

    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(f"DROP TABLE IF EXISTS {backup_table}")
        conn.execute(f"ALTER TABLE {production_table} RENAME TO {backup_table}")
        conn.execute(f"ALTER TABLE {temp_table} RENAME TO {production_table}")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise RuntimeError(f"Failed to swap tables {temp_table} -> {production_table}")


def execute_sql_file(file_path: Path | str) -> None:
    """Execute SQL statements from a file.

    Args:
        file_path: Path to SQL file.

    Raises:
        RuntimeError: If execution fails.
    """
    conn = get_db_connection()
    file_path = Path(file_path)

    try:
        with open(file_path) as f:
            sql = f.read()
        conn.execute(sql)
    except Exception as e:
        raise RuntimeError(f"Failed to execute SQL file {file_path}: {e}") from e
