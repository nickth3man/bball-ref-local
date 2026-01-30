-- ============================================================================
-- 01_planning_tables.sql
-- Tables for planning data ingestion from Basketball Reference historical data
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Team Abbreviations
-- Maps team names to abbreviations by season
-- Source: Team_Abbrev.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS team_abbreviations (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(10) NOT NULL,
    is_playoff BOOLEAN DEFAULT FALSE,
    data_source VARCHAR(100) DEFAULT 'Team_Abbrev.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, team_name, is_playoff),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100)
);

COMMENT ON TABLE team_abbreviations IS 'Team name to abbreviation mappings by season';
COMMENT ON COLUMN team_abbreviations.season IS 'NBA season year (e.g., 2026 for 2025-26 season)';
COMMENT ON COLUMN team_abbreviations.league IS 'League identifier (NBA, ABA, etc.)';
COMMENT ON COLUMN team_abbreviations.team_name IS 'Full team name';
COMMENT ON COLUMN team_abbreviations.abbreviation IS 'Team abbreviation code';
COMMENT ON COLUMN team_abbreviations.is_playoff IS 'Whether this is playoff data';

-- ----------------------------------------------------------------------------
-- Team Histories
-- Historical team information including franchise history
-- Source: TeamHistories.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS team_histories (
    team_id INTEGER NOT NULL,
    team_city VARCHAR(100) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    team_abbrev VARCHAR(10) NOT NULL,
    season_founded INTEGER NOT NULL,
    season_active_till INTEGER,
    league VARCHAR(10) NOT NULL,
    data_source VARCHAR(100) DEFAULT 'TeamHistories.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, season_founded),
    CONSTRAINT chk_season_founded_valid CHECK (season_founded >= 1940 AND season_founded <= 2100),
    CONSTRAINT chk_season_active_valid CHECK (season_active_till IS NULL OR (season_active_till >= 1940 AND season_active_till <= 2100))
);

COMMENT ON TABLE team_histories IS 'Historical team franchise information';
COMMENT ON COLUMN team_histories.team_id IS 'Unique team identifier';
COMMENT ON COLUMN team_histories.team_city IS 'Team city';
COMMENT ON COLUMN team_histories.team_name IS 'Team name';
COMMENT ON COLUMN team_histories.team_abbrev IS 'Team abbreviation';
COMMENT ON COLUMN team_histories.season_founded IS 'First season of franchise';
COMMENT ON COLUMN team_histories.season_active_till IS 'Last season of franchise (NULL if active)';
COMMENT ON COLUMN team_histories.league IS 'League (NBA, ABA, BAA)';

-- ----------------------------------------------------------------------------
-- Player Master
-- PRIMARY player table - core player career information
-- Source: Player_Career_Info.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_master (
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) PRIMARY KEY,
    position VARCHAR(10),
    height_inches INTEGER,
    weight_lbs INTEGER,
    birth_date DATE,
    colleges VARCHAR(500),
    career_start INTEGER,
    career_end INTEGER,
    debut_date DATE,
    hall_of_fame BOOLEAN DEFAULT FALSE,
    data_source VARCHAR(100) DEFAULT 'Player_Career_Info.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_height_valid CHECK (height_inches IS NULL OR (height_inches >= 60 AND height_inches <= 100)),
    CONSTRAINT chk_weight_valid CHECK (weight_lbs IS NULL OR (weight_lbs >= 100 AND weight_lbs <= 400)),
    CONSTRAINT chk_career_start_valid CHECK (career_start >= 1940 AND career_start <= 2100),
    CONSTRAINT chk_career_end_valid CHECK (career_end IS NULL OR (career_end >= 1940 AND career_end <= 2100))
);

COMMENT ON TABLE player_master IS 'Primary player reference table with career information';
COMMENT ON COLUMN player_master.player_name IS 'Player full name';
COMMENT ON COLUMN player_master.player_id IS 'Unique player identifier (e.g., jamesle01)';
COMMENT ON COLUMN player_master.position IS 'Primary position (G, F, C, G-F, F-C, etc.)';
COMMENT ON COLUMN player_master.height_inches IS 'Height in inches';
COMMENT ON COLUMN player_master.weight_lbs IS 'Weight in pounds';
COMMENT ON COLUMN player_master.birth_date IS 'Player birth date';
COMMENT ON COLUMN player_master.colleges IS 'College(s) attended';
COMMENT ON COLUMN player_master.career_start IS 'First season in league';
COMMENT ON COLUMN player_master.career_end IS 'Last season in league (NULL if active)';
COMMENT ON COLUMN player_master.debut_date IS 'NBA debut date';
COMMENT ON COLUMN player_master.hall_of_fame IS 'Hall of Fame inductee';

-- ----------------------------------------------------------------------------
-- Player Demographics
-- Supplemental player data from NBA API
-- Source: Players.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_demographics (
    person_id INTEGER PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    birth_date DATE,
    last_attended VARCHAR(200),
    country VARCHAR(100),
    height VARCHAR(10),
    body_weight VARCHAR(20),
    is_guard BOOLEAN DEFAULT FALSE,
    is_forward BOOLEAN DEFAULT FALSE,
    is_center BOOLEAN DEFAULT FALSE,
    draft_year INTEGER,
    draft_round INTEGER,
    draft_number INTEGER,
    data_source VARCHAR(100) DEFAULT 'Players.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_draft_year_valid CHECK (draft_year IS NULL OR (draft_year >= 1940 AND draft_year <= 2100)),
    CONSTRAINT chk_draft_round_valid CHECK (draft_round IS NULL OR (draft_round >= 1 AND draft_round <= 10)),
    CONSTRAINT chk_draft_number_valid CHECK (draft_number IS NULL OR (draft_number >= 1 AND draft_number <= 100))
);

COMMENT ON TABLE player_demographics IS 'Supplemental player demographic data from NBA API';
COMMENT ON COLUMN player_demographics.person_id IS 'NBA API person ID';
COMMENT ON COLUMN player_demographics.first_name IS 'Player first name';
COMMENT ON COLUMN player_demographics.last_name IS 'Player last name';
COMMENT ON COLUMN player_demographics.birth_date IS 'Player birth date';
COMMENT ON COLUMN player_demographics.last_attended IS 'Last school attended';
COMMENT ON COLUMN player_demographics.country IS 'Country of origin';
COMMENT ON COLUMN player_demographics.height IS 'Height as string (e.g., 6-9)';
COMMENT ON COLUMN player_demographics.body_weight IS 'Weight as string';
COMMENT ON COLUMN player_demographics.is_guard IS 'Can play guard position';
COMMENT ON COLUMN player_demographics.is_forward IS 'Can play forward position';
COMMENT ON COLUMN player_demographics.is_center IS 'Can play center position';
COMMENT ON COLUMN player_demographics.draft_year IS 'NBA draft year';
COMMENT ON COLUMN player_demographics.draft_round IS 'Draft round';
COMMENT ON COLUMN player_demographics.draft_number IS 'Overall draft pick number';

-- ----------------------------------------------------------------------------
-- Player Season Info
-- Season-by-season player information
-- Source: Player_Season_Info.csv
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_season_info (
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    age INTEGER,
    team VARCHAR(10) NOT NULL,
    position VARCHAR(10),
    experience INTEGER,
    data_source VARCHAR(100) DEFAULT 'Player_Season_Info.csv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season, player_id, team),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100),
    CONSTRAINT chk_age_valid CHECK (age IS NULL OR (age >= 15 AND age <= 50)),
    CONSTRAINT chk_experience_valid CHECK (experience IS NULL OR experience >= 0)
);

COMMENT ON TABLE player_season_info IS 'Player information for each season';
COMMENT ON COLUMN player_season_info.season IS 'NBA season year';
COMMENT ON COLUMN player_season_info.league IS 'League identifier';
COMMENT ON COLUMN player_season_info.player_name IS 'Player full name';
COMMENT ON COLUMN player_season_info.player_id IS 'Player identifier';
COMMENT ON COLUMN player_season_info.age IS 'Player age during season';
COMMENT ON COLUMN player_season_info.team IS 'Team abbreviation';
COMMENT ON COLUMN player_season_info.position IS 'Position played';
COMMENT ON COLUMN player_season_info.experience IS 'Years of experience (0 for rookie)';

