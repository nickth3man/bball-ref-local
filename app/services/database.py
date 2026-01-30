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

    # Create teams table (VARCHAR IDs for NBA API compatibility)
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

    # Create players table (VARCHAR IDs for NBA API compatibility)
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
            FOREIGN KEY (draft_team_id) REFERENCES teams(team_id)
        )
    """)

    # Create games table
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
            FOREIGN KEY (season_id) REFERENCES seasons(season_id)
        )
    """)

    # Create player_game_stats table
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

    # Create seasons table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seasons (
            season_id VARCHAR PRIMARY KEY,
            year_start INTEGER NOT NULL,
            year_end INTEGER NOT NULL,
            league VARCHAR DEFAULT 'NBA',
            display_name VARCHAR
        )
    """)

    # Create player_season_stats table
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

    # Create player_game_logs table
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

    # Create team_season_stats table
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

    # Create awards table
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

    # Create draft_picks table
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
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_teams_division
        ON teams(division)
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
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_players_full_name
        ON players(full_name)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_players_active
        ON players(active)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_players_hall_of_fame
        ON players(hall_of_fame)
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
        CREATE INDEX IF NOT EXISTS idx_games_season_id
        ON games(season_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_games_home_team
        ON games(home_team_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_games_away_team
        ON games(away_team_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_games_is_playoff
        ON games(is_playoff)
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

    # Seasons indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_seasons_year_start
        ON seasons(year_start)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_seasons_year_end
        ON seasons(year_end)
    """)

    # Player season stats indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_season_stats_player
        ON player_season_stats(player_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_season_stats_season
        ON player_season_stats(season_id)
    """)

    # Player game logs indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_game_logs_player
        ON player_game_logs(player_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_player_game_logs_game
        ON player_game_logs(game_id)
    """)

    # Team season stats indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_team_season_stats_team
        ON team_season_stats(team_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_team_season_stats_season
        ON team_season_stats(season_id)
    """)

    # Awards indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_awards_season
        ON awards(season_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_awards_player
        ON awards(player_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_awards_type
        ON awards(award_type)
    """)

    # Draft picks indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_draft_picks_season
        ON draft_picks(season_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_draft_picks_team
        ON draft_picks(team_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_draft_picks_player
        ON draft_picks(player_id)
    """)


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
