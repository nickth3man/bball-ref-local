-- ============================================================================
-- 02_game_tables.sql
-- Tables for game-level data ingestion
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Games Historical
-- Historical game information from Basketball Reference
-- Source: Games.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS games_historical (
    game_id BIGINT PRIMARY KEY,
    game_datetime_est TIMESTAMP,
    home_team_city VARCHAR(100) NOT NULL,
    home_team_name VARCHAR(100) NOT NULL,
    home_team_id INTEGER NOT NULL,
    away_team_city VARCHAR(100) NOT NULL,
    away_team_name VARCHAR(100) NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    winner VARCHAR(10),
    game_type VARCHAR(20) NOT NULL,
    attendance INTEGER,
    arena_id INTEGER,
    game_label VARCHAR(200),
    game_sub_label VARCHAR(200),
    series_game_number INTEGER,
    data_source VARCHAR(100) DEFAULT 'Games.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_home_score_valid CHECK (home_score IS NULL OR home_score >= 0),
    CONSTRAINT chk_away_score_valid CHECK (away_score IS NULL OR away_score >= 0),
    CONSTRAINT chk_attendance_valid CHECK (attendance IS NULL OR attendance >= 0),
    CONSTRAINT chk_winner_valid CHECK (winner IS NULL OR winner IN ('home', 'away', 'tie'))
);

COMMENT ON TABLE games_historical IS 'Historical game data from Basketball Reference';
COMMENT ON COLUMN games_historical.game_id IS 'Unique game identifier (NBA API format)';
COMMENT ON COLUMN games_historical.game_datetime_est IS 'Game date and time (Eastern)';
COMMENT ON COLUMN games_historical.home_team_id IS 'Home team ID';
COMMENT ON COLUMN games_historical.away_team_id IS 'Away team ID';
COMMENT ON COLUMN games_historical.home_score IS 'Home team final score';
COMMENT ON COLUMN games_historical.away_score IS 'Away team final score';
COMMENT ON COLUMN games_historical.winner IS 'Game winner (home/away/tie)';
COMMENT ON COLUMN games_historical.game_type IS 'Game type (Regular Season, Playoffs, etc.)';
COMMENT ON COLUMN games_historical.attendance IS 'Game attendance';
COMMENT ON COLUMN games_historical.arena_id IS 'Arena identifier';
COMMENT ON COLUMN games_historical.game_label IS 'Game label/description';
COMMENT ON COLUMN games_historical.series_game_number IS 'Playoff series game number';

-- ----------------------------------------------------------------------------
-- Player Game Statistics
-- Individual player statistics per game
-- Source: PlayerStatistics.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_game_statistics (
    stat_id BIGINT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    person_id INTEGER NOT NULL,
    game_id BIGINT NOT NULL,
    game_datetime_est TIMESTAMP,
    player_team_city VARCHAR(100) NOT NULL,
    player_team_name VARCHAR(100) NOT NULL,
    opponent_team_city VARCHAR(100) NOT NULL,
    opponent_team_name VARCHAR(100) NOT NULL,
    game_type VARCHAR(20) NOT NULL,
    game_label VARCHAR(200),
    game_sub_label VARCHAR(200),
    series_game_number INTEGER,
    is_win BOOLEAN,
    is_home BOOLEAN,
    minutes_played DOUBLE,
    points INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    blocks INTEGER DEFAULT 0,
    steals INTEGER DEFAULT 0,
    field_goals_attempted INTEGER DEFAULT 0,
    field_goals_made INTEGER DEFAULT 0,
    field_goal_pct FLOAT,
    three_pointers_attempted INTEGER DEFAULT 0,
    three_pointers_made INTEGER DEFAULT 0,
    three_point_pct FLOAT,
    free_throws_attempted INTEGER DEFAULT 0,
    free_throws_made INTEGER DEFAULT 0,
    free_throw_pct FLOAT,
    rebounds_defensive INTEGER DEFAULT 0,
    rebounds_offensive INTEGER DEFAULT 0,
    rebounds_total INTEGER DEFAULT 0,
    fouls_personal INTEGER DEFAULT 0,
    turnovers INTEGER DEFAULT 0,
    plus_minus INTEGER,
    data_source VARCHAR(100) DEFAULT 'PlayerStatistics.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games_historical(game_id),
    CONSTRAINT chk_minutes_valid CHECK (minutes_played IS NULL OR minutes_played >= 0),
    CONSTRAINT chk_points_valid CHECK (points >= 0),
    CONSTRAINT chk_fg_pct_valid CHECK (field_goal_pct IS NULL OR (field_goal_pct >= 0 AND field_goal_pct <= 1)),
    CONSTRAINT chk_3p_pct_valid CHECK (three_point_pct IS NULL OR (three_point_pct >= 0 AND three_point_pct <= 1)),
    CONSTRAINT chk_ft_pct_valid CHECK (free_throw_pct IS NULL OR (free_throw_pct >= 0 AND free_throw_pct <= 1))
);

COMMENT ON TABLE player_game_statistics IS 'Individual player statistics per game';
COMMENT ON COLUMN player_game_statistics.stat_id IS 'Unique stat record identifier';
COMMENT ON COLUMN player_game_statistics.person_id IS 'NBA API person ID';
COMMENT ON COLUMN player_game_statistics.game_id IS 'Game identifier';
COMMENT ON COLUMN player_game_statistics.minutes_played IS 'Minutes played (can include seconds as decimal)';
COMMENT ON COLUMN player_game_statistics.points IS 'Points scored';
COMMENT ON COLUMN player_game_statistics.plus_minus IS 'Plus/minus rating';

-- ----------------------------------------------------------------------------
-- Team Game Statistics
-- Team-level statistics per game
-- Source: TeamStatistics.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS team_game_statistics (
    stat_id BIGINT PRIMARY KEY,
    game_id BIGINT NOT NULL,
    game_datetime_est TIMESTAMP,
    team_city VARCHAR(100) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    team_id INTEGER NOT NULL,
    opponent_team_city VARCHAR(100) NOT NULL,
    opponent_team_name VARCHAR(100) NOT NULL,
    opponent_team_id INTEGER NOT NULL,
    is_home BOOLEAN NOT NULL,
    is_win BOOLEAN,
    team_score INTEGER,
    opponent_score INTEGER,
    assists INTEGER DEFAULT 0,
    blocks INTEGER DEFAULT 0,
    steals INTEGER DEFAULT 0,
    field_goals_attempted INTEGER DEFAULT 0,
    field_goals_made INTEGER DEFAULT 0,
    field_goal_pct FLOAT,
    three_pointers_attempted INTEGER DEFAULT 0,
    three_pointers_made INTEGER DEFAULT 0,
    three_point_pct FLOAT,
    free_throws_attempted INTEGER DEFAULT 0,
    free_throws_made INTEGER DEFAULT 0,
    free_throw_pct FLOAT,
    rebounds_defensive INTEGER DEFAULT 0,
    rebounds_offensive INTEGER DEFAULT 0,
    rebounds_total INTEGER DEFAULT 0,
    fouls_personal INTEGER DEFAULT 0,
    turnovers INTEGER DEFAULT 0,
    plus_minus INTEGER,
    minutes_played INTEGER,
    q1_points INTEGER,
    q2_points INTEGER,
    q3_points INTEGER,
    q4_points INTEGER,
    bench_points INTEGER,
    biggest_lead INTEGER,
    biggest_scoring_run INTEGER,
    lead_changes INTEGER,
    points_fast_break INTEGER,
    points_from_turnovers INTEGER,
    points_in_paint INTEGER,
    points_second_chance INTEGER,
    times_tied INTEGER,
    timeouts_remaining INTEGER,
    season_wins INTEGER,
    season_losses INTEGER,
    coach_id INTEGER,
    data_source VARCHAR(100) DEFAULT 'TeamStatistics.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games_historical(game_id),
    CONSTRAINT chk_score_valid CHECK (team_score IS NULL OR team_score >= 0),
    CONSTRAINT chk_qtr_points_valid CHECK (q1_points IS NULL OR q1_points >= 0)
);

COMMENT ON TABLE team_game_statistics IS 'Team-level statistics per game';
COMMENT ON COLUMN team_game_statistics.team_id IS 'Team identifier';
COMMENT ON COLUMN team_game_statistics.opponent_team_id IS 'Opponent team identifier';
COMMENT ON COLUMN team_game_statistics.bench_points IS 'Points scored by bench players';
COMMENT ON COLUMN team_game_statistics.points_fast_break IS 'Fast break points';
COMMENT ON COLUMN team_game_statistics.points_in_paint IS 'Points in the paint';
COMMENT ON COLUMN team_game_statistics.biggest_lead IS 'Largest lead during game';
COMMENT ON COLUMN team_game_statistics.coach_id IS 'Coach identifier';
