-- ============================================================================
-- 03_season_stats_tables.sql
-- Tables for aggregated season statistics
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Player Season Totals
-- Aggregated season totals for players
-- Source: Player_Totals.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_season_totals (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    age INTEGER,
    team VARCHAR(10) NOT NULL,
    position VARCHAR(10),
    games_played INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,
    minutes_played INTEGER DEFAULT 0,
    field_goals INTEGER DEFAULT 0,
    field_goal_attempts INTEGER DEFAULT 0,
    fg_pct FLOAT,
    three_pointers INTEGER DEFAULT 0,
    three_point_attempts INTEGER DEFAULT 0,
    fg3_pct FLOAT,
    two_pointers INTEGER DEFAULT 0,
    two_point_attempts INTEGER DEFAULT 0,
    fg2_pct FLOAT,
    effective_fg_pct FLOAT,
    free_throws INTEGER DEFAULT 0,
    free_throw_attempts INTEGER DEFAULT 0,
    ft_pct FLOAT,
    offensive_rebounds INTEGER DEFAULT 0,
    defensive_rebounds INTEGER DEFAULT 0,
    total_rebounds INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    steals INTEGER DEFAULT 0,
    blocks INTEGER DEFAULT 0,
    turnovers INTEGER DEFAULT 0,
    personal_fouls INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    triple_doubles INTEGER DEFAULT 0,
    data_source VARCHAR(100) DEFAULT 'Player_Totals.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, player_id, team),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100),
    CONSTRAINT chk_games_valid CHECK (games_played >= 0 AND games_played <= 100),
    CONSTRAINT chk_pct_valid CHECK (fg_pct IS NULL OR (fg_pct >= 0 AND fg_pct <= 1))
);

COMMENT ON TABLE player_season_totals IS 'Player season total statistics';
COMMENT ON COLUMN player_season_totals.games_played IS 'Games played';
COMMENT ON COLUMN player_season_totals.minutes_played IS 'Total minutes played';
COMMENT ON COLUMN player_season_totals.triple_doubles IS 'Number of triple-doubles';

-- ----------------------------------------------------------------------------
-- Player Season Per Game
-- Per-game averages for players
-- Source: Player_Per_Game.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_season_per_game (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    age INTEGER,
    team VARCHAR(10) NOT NULL,
    position VARCHAR(10),
    games_played INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,
    minutes_per_game FLOAT,
    fg_per_game FLOAT,
    fga_per_game FLOAT,
    fg_pct FLOAT,
    fg3_per_game FLOAT,
    fg3a_per_game FLOAT,
    fg3_pct FLOAT,
    fg2_per_game FLOAT,
    fg2a_per_game FLOAT,
    fg2_pct FLOAT,
    effective_fg_pct FLOAT,
    ft_per_game FLOAT,
    fta_per_game FLOAT,
    ft_pct FLOAT,
    orb_per_game FLOAT,
    drb_per_game FLOAT,
    trb_per_game FLOAT,
    ast_per_game FLOAT,
    stl_per_game FLOAT,
    blk_per_game FLOAT,
    tov_per_game FLOAT,
    pf_per_game FLOAT,
    pts_per_game FLOAT,
    data_source VARCHAR(100) DEFAULT 'Player_Per_Game.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, player_id, team),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100)
);

COMMENT ON TABLE player_season_per_game IS 'Player per-game statistics';
COMMENT ON COLUMN player_season_per_game.pts_per_game IS 'Points per game';
COMMENT ON COLUMN player_season_per_game.ast_per_game IS 'Assists per game';
COMMENT ON COLUMN player_season_per_game.trb_per_game IS 'Total rebounds per game';

-- ----------------------------------------------------------------------------
-- Player Season Advanced
-- Advanced statistics for players
-- Source: Advanced.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_season_advanced (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    age INTEGER,
    team VARCHAR(10) NOT NULL,
    position VARCHAR(10),
    games_played INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,
    minutes_played INTEGER DEFAULT 0,
    per FLOAT,
    ts_pct FLOAT,
    three_point_ar FLOAT,
    ft_rate FLOAT,
    orb_pct FLOAT,
    drb_pct FLOAT,
    trb_pct FLOAT,
    ast_pct FLOAT,
    stl_pct FLOAT,
    blk_pct FLOAT,
    tov_pct FLOAT,
    usg_pct FLOAT,
    ows FLOAT,
    dws FLOAT,
    ws FLOAT,
    ws_per_48 FLOAT,
    obpm FLOAT,
    dbpm FLOAT,
    bpm FLOAT,
    vorp FLOAT,
    data_source VARCHAR(100) DEFAULT 'Advanced.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, player_id, team),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100)
);

COMMENT ON TABLE player_season_advanced IS 'Player advanced statistics';
COMMENT ON COLUMN player_season_advanced.per IS 'Player Efficiency Rating';
COMMENT ON COLUMN player_season_advanced.ts_pct IS 'True Shooting Percentage';
COMMENT ON COLUMN player_season_advanced.ws IS 'Win Shares';
COMMENT ON COLUMN player_season_advanced.ws_per_48 IS 'Win Shares per 48 minutes';
COMMENT ON COLUMN player_season_advanced.bpm IS 'Box Plus/Minus';
COMMENT ON COLUMN player_season_advanced.vorp IS 'Value Over Replacement Player';
COMMENT ON COLUMN player_season_advanced.usg_pct IS 'Usage Percentage';

-- ----------------------------------------------------------------------------
-- Player Season Per 100 Possessions
-- Statistics normalized per 100 possessions
-- Source: Per_100_Poss.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_season_per_100 (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    age INTEGER,
    team VARCHAR(10) NOT NULL,
    position VARCHAR(10),
    games_played INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,
    minutes_played INTEGER DEFAULT 0,
    fg_per_100 FLOAT,
    fga_per_100 FLOAT,
    fg_pct FLOAT,
    fg3_per_100 FLOAT,
    fg3a_per_100 FLOAT,
    fg3_pct FLOAT,
    fg2_per_100 FLOAT,
    fg2a_per_100 FLOAT,
    fg2_pct FLOAT,
    effective_fg_pct FLOAT,
    ft_per_100 FLOAT,
    fta_per_100 FLOAT,
    ft_pct FLOAT,
    orb_per_100 FLOAT,
    drb_per_100 FLOAT,
    trb_per_100 FLOAT,
    ast_per_100 FLOAT,
    stl_per_100 FLOAT,
    blk_per_100 FLOAT,
    tov_per_100 FLOAT,
    pf_per_100 FLOAT,
    pts_per_100 FLOAT,
    o_rtg INTEGER,
    d_rtg INTEGER,
    data_source VARCHAR(100) DEFAULT 'Per_100_Poss.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, player_id, team),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100)
);

COMMENT ON TABLE player_season_per_100 IS 'Player statistics per 100 possessions';
COMMENT ON COLUMN player_season_per_100.o_rtg IS 'Offensive Rating';
COMMENT ON COLUMN player_season_per_100.d_rtg IS 'Defensive Rating';

-- ----------------------------------------------------------------------------
-- Player Season Per 36 Minutes
-- Statistics normalized per 36 minutes
-- Source: Per_36_Minutes.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_season_per_36 (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    age INTEGER,
    team VARCHAR(10) NOT NULL,
    position VARCHAR(10),
    games_played INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,
    minutes_played INTEGER DEFAULT 0,
    fg_per_36 FLOAT,
    fga_per_36 FLOAT,
    fg_pct FLOAT,
    fg3_per_36 FLOAT,
    fg3a_per_36 FLOAT,
    fg3_pct FLOAT,
    fg2_per_36 FLOAT,
    fg2a_per_36 FLOAT,
    fg2_pct FLOAT,
    effective_fg_pct FLOAT,
    ft_per_36 FLOAT,
    fta_per_36 FLOAT,
    ft_pct FLOAT,
    orb_per_36 FLOAT,
    drb_per_36 FLOAT,
    trb_per_36 FLOAT,
    ast_per_36 FLOAT,
    stl_per_36 FLOAT,
    blk_per_36 FLOAT,
    tov_per_36 FLOAT,
    pf_per_36 FLOAT,
    pts_per_36 FLOAT,
    data_source VARCHAR(100) DEFAULT 'Per_36_Minutes.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, player_id, team),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100)
);

COMMENT ON TABLE player_season_per_36 IS 'Player statistics per 36 minutes';

-- ----------------------------------------------------------------------------
-- Player Season Shooting
-- Detailed shooting breakdowns
-- Source: Player_Shooting.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_season_shooting (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    age INTEGER,
    team VARCHAR(10) NOT NULL,
    position VARCHAR(10),
    games_played INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,
    minutes_played INTEGER DEFAULT 0,
    fg_pct FLOAT,
    avg_dist_fga FLOAT,
    pct_fga_from_x2p FLOAT,
    pct_fga_from_x0_3 FLOAT,
    pct_fga_from_x3_10 FLOAT,
    pct_fga_from_x10_16 FLOAT,
    pct_fga_from_x16_3p FLOAT,
    pct_fga_from_x3p FLOAT,
    fg_pct_from_x2p FLOAT,
    fg_pct_from_x0_3 FLOAT,
    fg_pct_from_x3_10 FLOAT,
    fg_pct_from_x10_16 FLOAT,
    fg_pct_from_x16_3p FLOAT,
    fg_pct_from_x3p FLOAT,
    pct_assisted_x2p FLOAT,
    pct_assisted_x3p FLOAT,
    pct_dunks_of_fga FLOAT,
    num_dunks INTEGER,
    pct_corner_3s_of_3pa FLOAT,
    corner_3_pct FLOAT,
    num_heaves_attempted INTEGER DEFAULT 0,
    num_heaves_made INTEGER DEFAULT 0,
    data_source VARCHAR(100) DEFAULT 'Player_Shooting.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, player_id, team),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100)
);

COMMENT ON TABLE player_season_shooting IS 'Player shooting breakdowns by distance';
COMMENT ON COLUMN player_season_shooting.avg_dist_fga IS 'Average distance of field goal attempts';
COMMENT ON COLUMN player_season_shooting.pct_fga_from_x0_3 IS 'Pct of FGA from 0-3 ft';
COMMENT ON COLUMN player_season_shooting.num_dunks IS 'Number of dunks';
COMMENT ON COLUMN player_season_shooting.num_heaves_attempted IS 'Number of heaves attempted';

-- ----------------------------------------------------------------------------
-- Player Season Play By Play
-- Play-by-play derived statistics
-- Source: Player_Play_By_Play.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_season_play_by_play (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    age INTEGER,
    team VARCHAR(10) NOT NULL,
    position VARCHAR(10),
    games_played INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,
    minutes_played INTEGER DEFAULT 0,
    pg_pct FLOAT,
    sg_pct FLOAT,
    sf_pct FLOAT,
    pf_pct FLOAT,
    c_pct FLOAT,
    on_court_plus_minus_per_100 FLOAT,
    net_plus_minus_per_100 FLOAT,
    bad_pass_turnover INTEGER DEFAULT 0,
    lost_ball_turnover INTEGER DEFAULT 0,
    shooting_foul_committed INTEGER DEFAULT 0,
    offensive_foul_committed INTEGER DEFAULT 0,
    shooting_foul_drawn INTEGER DEFAULT 0,
    offensive_foul_drawn INTEGER DEFAULT 0,
    points_generated_by_assists INTEGER DEFAULT 0,
    and1 INTEGER DEFAULT 0,
    fga_blocked INTEGER DEFAULT 0,
    data_source VARCHAR(100) DEFAULT 'Player_Play_By_Play.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, player_id, team),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100)
);

COMMENT ON TABLE player_season_play_by_play IS 'Play-by-play derived statistics';
COMMENT ON COLUMN player_season_play_by_play.pg_pct IS 'Percent of minutes at point guard';
COMMENT ON COLUMN player_season_play_by_play.on_court_plus_minus_per_100 IS 'On-court plus/minus per 100 possessions';
COMMENT ON COLUMN player_season_play_by_play.and1 IS 'And-1 opportunities';

-- ----------------------------------------------------------------------------
-- Team Season Totals
-- Aggregated season totals for teams
-- Source: Team_Totals.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS team_season_totals (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(10) NOT NULL,
    is_playoff BOOLEAN DEFAULT FALSE,
    games_played INTEGER DEFAULT 0,
    minutes_played INTEGER DEFAULT 0,
    field_goals INTEGER DEFAULT 0,
    field_goal_attempts INTEGER DEFAULT 0,
    fg_pct FLOAT,
    three_pointers INTEGER DEFAULT 0,
    three_point_attempts INTEGER DEFAULT 0,
    fg3_pct FLOAT,
    two_pointers INTEGER DEFAULT 0,
    two_point_attempts INTEGER DEFAULT 0,
    fg2_pct FLOAT,
    free_throws INTEGER DEFAULT 0,
    free_throw_attempts INTEGER DEFAULT 0,
    ft_pct FLOAT,
    offensive_rebounds INTEGER DEFAULT 0,
    defensive_rebounds INTEGER DEFAULT 0,
    total_rebounds INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    steals INTEGER DEFAULT 0,
    blocks INTEGER DEFAULT 0,
    turnovers INTEGER DEFAULT 0,
    personal_fouls INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    data_source VARCHAR(100) DEFAULT 'Team_Totals.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, abbreviation, is_playoff),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100)
);

COMMENT ON TABLE team_season_totals IS 'Team season total statistics';

-- ----------------------------------------------------------------------------
-- Team Season Summaries
-- Team season summary statistics
-- Source: Team_Summaries.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS team_season_summaries (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(10) NOT NULL,
    is_playoff BOOLEAN DEFAULT FALSE,
    age FLOAT,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    pythagorean_wins FLOAT,
    pythagorean_losses FLOAT,
    margin_of_victory FLOAT,
    strength_of_schedule FLOAT,
    simple_rating FLOAT,
    offensive_rating FLOAT,
    defensive_rating FLOAT,
    net_rating FLOAT,
    pace FLOAT,
    free_throw_rate FLOAT,
    three_point_attempt_rate FLOAT,
    true_shooting_pct FLOAT,
    effective_fg_pct FLOAT,
    turnover_pct FLOAT,
    offensive_rebound_pct FLOAT,
    ft_per_fga FLOAT,
    opp_effective_fg_pct FLOAT,
    opp_turnover_pct FLOAT,
    defensive_rebound_pct FLOAT,
    opp_ft_per_fga FLOAT,
    arena VARCHAR(200),
    attendance INTEGER,
    attendance_per_game INTEGER,
    data_source VARCHAR(100) DEFAULT 'Team_Summaries.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, abbreviation, is_playoff),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100),
    CONSTRAINT chk_wins_losses CHECK (wins >= 0 AND losses >= 0)
);

COMMENT ON TABLE team_season_summaries IS 'Team season summary and advanced stats';
COMMENT ON COLUMN team_season_summaries.pythagorean_wins IS 'Pythagorean expected wins';
COMMENT ON COLUMN team_season_summaries.margin_of_victory IS 'Average margin of victory';
COMMENT ON COLUMN team_season_summaries.simple_rating IS 'Simple Rating System';
COMMENT ON COLUMN team_season_summaries.net_rating IS 'Net rating (ORtg - DRtg)';

-- ----------------------------------------------------------------------------
-- Opponent Season Totals
-- Opponent statistics against each team
-- Source: Opponent_Totals.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS opponent_season_totals (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(10) NOT NULL,
    is_playoff BOOLEAN DEFAULT FALSE,
    games_played INTEGER DEFAULT 0,
    minutes_played INTEGER DEFAULT 0,
    opp_field_goals INTEGER DEFAULT 0,
    opp_field_goal_attempts INTEGER DEFAULT 0,
    opp_fg_pct FLOAT,
    opp_three_pointers INTEGER DEFAULT 0,
    opp_three_point_attempts INTEGER DEFAULT 0,
    opp_fg3_pct FLOAT,
    opp_two_pointers INTEGER DEFAULT 0,
    opp_two_point_attempts INTEGER DEFAULT 0,
    opp_fg2_pct FLOAT,
    opp_free_throws INTEGER DEFAULT 0,
    opp_free_throw_attempts INTEGER DEFAULT 0,
    opp_ft_pct FLOAT,
    opp_offensive_rebounds INTEGER DEFAULT 0,
    opp_defensive_rebounds INTEGER DEFAULT 0,
    opp_total_rebounds INTEGER DEFAULT 0,
    opp_assists INTEGER DEFAULT 0,
    opp_steals INTEGER DEFAULT 0,
    opp_blocks INTEGER DEFAULT 0,
    opp_turnovers INTEGER DEFAULT 0,
    opp_personal_fouls INTEGER DEFAULT 0,
    opp_points INTEGER DEFAULT 0,
    data_source VARCHAR(100) DEFAULT 'Opponent_Totals.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, abbreviation, is_playoff),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100)
);

COMMENT ON TABLE opponent_season_totals IS 'Opponent statistics against each team';
