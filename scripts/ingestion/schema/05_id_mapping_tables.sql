-- ============================================================================
-- 05_id_mapping_tables.sql
-- Tables for ID mapping and resolution between data sources
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Player ID Mapping
-- Maps NBA API personId to Basketball Reference player_id
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_id_mapping (
    mapping_id INTEGER PRIMARY KEY,
    person_id INTEGER NOT NULL,
    player_id VARCHAR(20) NOT NULL,
    player_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_verified BOOLEAN DEFAULT FALSE,
    verification_method VARCHAR(50),
    confidence_score FLOAT,
    notes VARCHAR(500),
    data_source VARCHAR(100) DEFAULT 'ID_Mapping',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (person_id, player_id),
    FOREIGN KEY (player_id) REFERENCES player_master(player_id),
    CONSTRAINT chk_confidence_valid CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1))
);

COMMENT ON TABLE player_id_mapping IS 'Mapping between NBA API personId and Basketball Reference player_id';
COMMENT ON COLUMN player_id_mapping.person_id IS 'NBA API person identifier';
COMMENT ON COLUMN player_id_mapping.player_id IS 'Basketball Reference player identifier';
COMMENT ON COLUMN player_id_mapping.is_verified IS 'Whether mapping has been manually verified';
COMMENT ON COLUMN player_id_mapping.confidence_score IS 'Automated matching confidence (0-1)';
COMMENT ON COLUMN player_id_mapping.verification_method IS 'Method used for verification';

-- ----------------------------------------------------------------------------
-- Team ID Mapping
-- Maps team names/abbreviations to team IDs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS team_id_mapping (
    mapping_id INTEGER PRIMARY KEY,
    team_id INTEGER NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    team_abbrev VARCHAR(10) NOT NULL,
    season INTEGER NOT NULL,
    league VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    notes VARCHAR(500),
    data_source VARCHAR(100) DEFAULT 'ID_Mapping',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (team_id, season),
    CONSTRAINT chk_season_valid CHECK (season >= 1940 AND season <= 2100)
);

COMMENT ON TABLE team_id_mapping IS 'Mapping between team identifiers across data sources';
COMMENT ON COLUMN team_id_mapping.team_id IS 'NBA API team identifier';
COMMENT ON COLUMN team_id_mapping.team_name IS 'Team name';
COMMENT ON COLUMN team_id_mapping.team_abbrev IS 'Team abbreviation';
COMMENT ON COLUMN team_id_mapping.season IS 'Season this mapping applies to';

-- ----------------------------------------------------------------------------
-- Data Source Tracking
-- Tracks which file each record came from
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_source_tracking (
    tracking_id BIGINT PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_key VARCHAR(200) NOT NULL,
    source_file VARCHAR(200) NOT NULL,
    source_path VARCHAR(500),
    file_hash VARCHAR(64),
    file_size_bytes BIGINT,
    row_number INTEGER,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ingestion_batch_id VARCHAR(50),
    validation_status VARCHAR(20) DEFAULT 'pending',
    validation_errors VARCHAR(1000),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (table_name, record_key, source_file)
);

COMMENT ON TABLE data_source_tracking IS 'Tracks the source of each ingested record';
COMMENT ON COLUMN data_source_tracking.table_name IS 'Destination table name';
COMMENT ON COLUMN data_source_tracking.record_key IS 'Primary key of the record';
COMMENT ON COLUMN data_source_tracking.source_file IS 'Source file name';
COMMENT ON COLUMN data_source_tracking.file_hash IS 'MD5/SHA256 hash of source file';
COMMENT ON COLUMN data_source_tracking.ingestion_batch_id IS 'Batch identifier for ingestion run';
COMMENT ON COLUMN data_source_tracking.validation_status IS 'Validation status (pending, valid, invalid)';

-- ----------------------------------------------------------------------------
-- Ingestion Log
-- Log of all data ingestion operations
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ingestion_log (
    log_id BIGINT PRIMARY KEY,
    batch_id VARCHAR(50) NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    source_file VARCHAR(500),
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message VARCHAR(2000),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ingestion_log IS 'Log of data ingestion operations';
COMMENT ON COLUMN ingestion_log.batch_id IS 'Unique batch identifier';
COMMENT ON COLUMN ingestion_log.operation_type IS 'Type of operation (full_load, incremental, etc.)';
COMMENT ON COLUMN ingestion_log.records_processed IS 'Total records processed';
COMMENT ON COLUMN ingestion_log.records_inserted IS 'Records successfully inserted';
COMMENT ON COLUMN ingestion_log.records_failed IS 'Records that failed validation';
