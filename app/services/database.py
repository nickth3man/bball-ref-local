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


def init_db() -> None:
    """Initialize database with all tables and indexes.
    
    Creates tables matching Pydantic models if they don't exist.
    """
    conn = get_db_connection()
    
    # Create teams table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY,
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
    
    # Create players table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY,
            first_name VARCHAR NOT NULL,
            last_name VARCHAR NOT NULL,
            team_id INTEGER NOT NULL,
            position VARCHAR(2) NOT NULL,
            jersey_number INTEGER,
            height INTEGER,
            weight INTEGER,
            birth_date DATE,
            country VARCHAR,
            draft_year INTEGER,
            draft_round INTEGER,
            draft_number INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create games table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id VARCHAR PRIMARY KEY,
            season INTEGER NOT NULL,
            season_type VARCHAR(14) NOT NULL,
            game_date DATE NOT NULL,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_score INTEGER,
            away_score INTEGER,
            winner_team_id INTEGER,
            status VARCHAR(9) DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create player_game_stats table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_game_stats (
            stat_id INTEGER PRIMARY KEY,
            game_id VARCHAR NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
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
    
    # Create indexes for common query patterns
    _create_indexes(conn)
    
    # Create app metadata table
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
    # Team indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_teams_abbreviation 
        ON teams(abbreviation)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_teams_conference 
        ON teams(conference)
    """)
    
    # Player indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_players_team_id 
        ON players(team_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_players_name 
        ON players(last_name, first_name)
    """)
    
    # Game indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_games_date 
        ON games(game_date)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_games_season 
        ON games(season)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_games_home_team 
        ON games(home_team_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_games_away_team 
        ON games(away_team_id)
    """)
    
    # Player game stats indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stats_game_id 
        ON player_game_stats(game_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stats_player_id 
        ON player_game_stats(player_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stats_team_id 
        ON player_game_stats(team_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stats_player_game 
        ON player_game_stats(player_id, game_id)
    """)


def set_app_metadata(key: str, value: str) -> None:
    """Set or update application metadata.
    
    Args:
        key: Metadata key.
        value: Metadata value.
    """
    conn = get_db_connection()
    conn.execute("""
        INSERT OR REPLACE INTO app_metadata (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, [key, value])


def get_app_metadata(key: str) -> str | None:
    """Get application metadata value.
    
    Args:
        key: Metadata key.
        
    Returns:
        Metadata value or None if not found.
    """
    conn = get_db_connection()
    result = conn.execute(
        "SELECT value FROM app_metadata WHERE key = ?",
        [key]
    ).fetchone()
    
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
