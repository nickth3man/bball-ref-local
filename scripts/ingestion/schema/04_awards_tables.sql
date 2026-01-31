-- ============================================================================
-- 04_awards_tables.sql
-- Tables for awards and recognition data
-- ============================================================================

-- ----------------------------------------------------------------------------
-- All-Star Selections
-- All-Star game selections
-- Source: All-Star Selections.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS all_star_selections (
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    team VARCHAR(10) NOT NULL,
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    replaced_player VARCHAR(100),
    data_source VARCHAR(100) DEFAULT 'All-Star Selections.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, player_id),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100)
);

COMMENT ON TABLE all_star_selections IS 'NBA All-Star game selections';
COMMENT ON COLUMN all_star_selections.replaced_player IS 'Player who was replaced (if injury)';

-- ----------------------------------------------------------------------------
-- End of Season Teams
-- All-NBA, All-Defensive, All-Rookie selections
-- Source: End_of_Season_Teams.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS end_of_season_teams (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    team_type VARCHAR(50) NOT NULL,
    team_number INTEGER NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    position VARCHAR(10),
    data_source VARCHAR(100) DEFAULT 'End_of_Season_Teams.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, team_type, team_number, player_id),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100),
    CONSTRAINT chk_team_number_valid CHECK (team_number >= 1 AND team_number <= 3)
);

COMMENT ON TABLE end_of_season_teams IS 'All-NBA, All-Defensive, All-Rookie team selections';
COMMENT ON COLUMN end_of_season_teams.team_type IS 'Type of team (All-NBA, All-Defensive, All-Rookie)';
COMMENT ON COLUMN end_of_season_teams.team_number IS 'Team number (1st, 2nd, 3rd)';

-- ----------------------------------------------------------------------------
-- End of Season Teams Voting
-- Voting details for end of season teams
-- Source: End_of_Season_Teams_(Voting).csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS end_of_season_teams_voting (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    team_type VARCHAR(50) NOT NULL,
    team_number INTEGER NOT NULL,
    position VARCHAR(10),
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    age INTEGER,
    points_won INTEGER DEFAULT 0,
    points_max INTEGER,
    share FLOAT,
    first_team_votes INTEGER DEFAULT 0,
    second_team_votes INTEGER DEFAULT 0,
    third_team_votes INTEGER DEFAULT 0,
    data_source VARCHAR(100) DEFAULT 'End_of_Season_Teams_(Voting).csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, team_type, player_id),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100),
    CONSTRAINT chk_points_valid CHECK (points_won >= 0),
    CONSTRAINT chk_share_valid CHECK (share IS NULL OR (share >= 0 AND share <= 1))
);

COMMENT ON TABLE end_of_season_teams_voting IS 'Voting results for end of season teams';
COMMENT ON COLUMN end_of_season_teams_voting.points_won IS 'Total voting points received';
COMMENT ON COLUMN end_of_season_teams_voting.points_max IS 'Maximum possible points';
COMMENT ON COLUMN end_of_season_teams_voting.share IS 'Share of maximum points (0-1)';
COMMENT ON COLUMN end_of_season_teams_voting.first_team_votes IS 'Number of first team votes';

-- ----------------------------------------------------------------------------
-- Player Award Shares
-- Award voting and shares for major awards
-- Source: Player_Award_Shares.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_award_shares (
    season INTEGER NOT NULL,
    award_name VARCHAR(100) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    age INTEGER,
    first_place_votes INTEGER DEFAULT 0,
    points_won INTEGER DEFAULT 0,
    points_max INTEGER,
    share FLOAT,
    is_winner BOOLEAN DEFAULT FALSE,
    data_source VARCHAR(100) DEFAULT 'Player_Award_Shares.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, award_name, player_id),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100),
    CONSTRAINT chk_share_valid CHECK (share IS NULL OR (share >= 0 AND share <= 1))
);

COMMENT ON TABLE player_award_shares IS 'Award voting shares (MVP, ROY, DPOY, etc.)';
COMMENT ON COLUMN player_award_shares.award_name IS 'Name of award (MVP, Rookie of the Year, etc.)';
COMMENT ON COLUMN player_award_shares.first_place_votes IS 'Number of first place votes';
COMMENT ON COLUMN player_award_shares.is_winner IS 'Whether player won the award';

-- ----------------------------------------------------------------------------
-- Draft Pick History
-- Historical NBA draft picks
-- Source: Draft_Pick_History.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS draft_pick_history (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    overall_pick INTEGER NOT NULL,
    round INTEGER NOT NULL,
    team VARCHAR(10) NOT NULL,
    player_name VARCHAR(100),
    player_id VARCHAR(20),
    college VARCHAR(200),
    data_source VARCHAR(100) DEFAULT 'Draft_Pick_History.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, overall_pick),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100),
    CONSTRAINT chk_overall_pick_valid CHECK (overall_pick > 0),
    CONSTRAINT chk_round_valid CHECK (round > 0)
);

COMMENT ON TABLE draft_pick_history IS 'Historical NBA draft picks';
COMMENT ON COLUMN draft_pick_history.overall_pick IS 'Overall pick number in draft';
COMMENT ON COLUMN draft_pick_history.round IS 'Draft round';
COMMENT ON COLUMN draft_pick_history.college IS 'College attended (if applicable)';
