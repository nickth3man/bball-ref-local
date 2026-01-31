## ETL Pipeline and Data Ingestion

This directory contains two data pipeline systems for populating the DuckDB database:

1. **Simple ETL scripts** (`etl_*.py`) - Extract from NBA API, transform, load to DB
2. **Advanced ingestion framework** (`ingestion/`) - Load CSV/Parquet files from Basketball Reference with ID mapping and validation

## Simple ETL Pipeline

### Architecture

```
run_all_etl.py (orchestrator)
├── etl_teams.py   → nba_api.get_teams()        → teams table
├── etl_players.py → CommonAllPlayers endpoint   → players table
├── etl_games.py   → LeagueGameFinder endpoint   → games table
└── etl_stats.py   → PlayerGameLogs endpoint     → player_game_stats table
```

### BaseETL class (`etl_base.py`)

Abstract base class implementing the Template Method pattern:

```python
class BaseETL(ABC):
    def extract(self, *args, **kwargs) -> pd.DataFrame  # Fetch from source
    def transform(self, df: pd.DataFrame) -> pd.DataFrame  # Clean and reshape
    def load(self, df: pd.DataFrame) -> int  # Insert into DuckDB

    def run(self, *args, **kwargs) -> dict[str, Any]:
        # Calls extract -> transform -> load with logging, timing, error handling
        # Returns {"status": "success"|"failed", "extracted": N, "loaded": N, "error": ...}
```

- Rate limiting via `_apply_rate_limit()` using `settings.nba_api_delay` (0.6s default)
- Logging via `ETLLogger` context manager from `logging_utils.py`
- Database connection closed in `finally` block

### ETL execution order

`run_all_etl.py` runs in dependency order:
1. `run_teams_etl()` - Must run first (other tables FK to teams)
2. `run_players_etl()` - Depends on teams
3. `run_games_etl()` - Depends on teams + seasons
4. `run_stats_etl()` - Depends on games + players

Results stored via `set_app_metadata("last_etl_status", json_result)`.

### Return value format

All ETL functions return a consistent dict:
```python
{
    "status": "success" | "failed",
    "extracted": int,       # Rows from source
    "loaded": int,          # Rows inserted to DB
    "error": str | None,    # Error message if failed
    "season": str,          # Optional: "2024-25"
    "season_type": str,     # Optional: "Regular Season"
}
```

## Utility Scripts

| File | Purpose |
|------|---------|
| `retry_utils.py` | Retry decorator with exponential backoff for NBA API calls |
| `logging_utils.py` | `setup_etl_logging()` factory, `ETLLogger` context manager (timing + result tracking) |
| `etl_utils.py` | Shared ETL helper functions |
| `init_db.py` | Standalone database initialization script |
| `run_historical_ingestion.py` | Run full historical data ingestion |
| `verify_ingestion_system.py` | Validate data integrity after ingestion |

## Advanced Ingestion Framework (`ingestion/`)

For loading historical CSV/Parquet data from Basketball Reference.

### Framework Structure

```
ingestion/
├── base_loader.py          # Abstract BaseLoader class
├── orchestrator.py         # Coordinates loaders, manages dependencies
├── config.py               # Ingestion-specific settings (paths, batch sizes)
├── database.py             # Database operations for ingestion
├── exceptions.py           # Exception hierarchy (7 exception types)
├── logger.py               # get_logger() factory
├── utils.py                # Helper utilities
├── loaders/                # Concrete loader implementations
│   ├── game_loaders.py     # Historical game data loaders
│   ├── stats_loaders.py    # Player/team stats loaders
│   ├── awards_loaders.py   # Awards/draft loaders
│   ├── reference_loaders.py # Reference data loaders
│   └── parquet_loaders.py  # Parquet file loaders
├── mapping/                # ID resolution between data sources
│   ├── team_mapper.py      # NBA API team ID <-> Basketball Ref team ID
│   ├── player_mapper.py    # NBA API player ID <-> Basketball Ref player ID
│   ├── fuzzy_matcher.py    # Fuzzy name matching for unresolved IDs
│   ├── id_resolver.py      # Central resolution coordinator
│   ├── mapping_validator.py # Validates mapping completeness
│   └── manual_mappings.py  # Hardcoded mappings for edge cases
├── validation/             # Data quality checks
│   ├── validators.py       # Schema validation rules
│   ├── sql_validators.py   # SQL-based data checks
│   ├── consistency_checks.py # Cross-table referential integrity
│   ├── report_generator.py # HTML/JSON/MD validation reports
│   └── validation_cli.py   # CLI interface for running validations
└── schema/                 # SQL DDL files (executed in order)
    ├── 01_planning_tables.sql    # Reference/master tables
    ├── 02_game_tables.sql        # Game history + statistics
    ├── 03_season_stats_tables.sql # Player/team season stats (7 stat types)
    ├── 04_awards_tables.sql      # Awards and draft picks
    ├── 05_id_mapping_tables.sql  # Cross-source ID mappings
    └── 06_indexes.sql            # Indexes for all ingestion tables
```

### BaseLoader class (`base_loader.py`)

```python
class BaseLoader(ABC):
    def __init__(self, file_path, table_name, batch_size=BATCH_SIZE)
    def load(self)                          # Abstract: full load pipeline
    def transform(self, df)                 # Abstract: data transformation
    def validate(self, df, context)         # Basic row count validation
    def read_file(self, **kwargs)           # Auto-detects CSV/Parquet by extension
    def get_row_count(self)                 # File row count without full read
    def get_file_size(self)                 # File size in bytes
    def _validate_files_exist(self, files)  # Batch file existence check
    def _clean_column_names(self, df)       # camelCase -> snake_case conversion
    def _load_csv(self, file_path)          # CSV load with column cleaning
```

### Exception hierarchy (`exceptions.py`)

All exceptions extend `IngestionError` which carries a `details` dict:

```
IngestionError (base)
├── ValidationError    # field, value, constraint
├── MappingError       # entity_type, external_id, mapping_table
├── DatabaseError      # operation, query, original_error
├── FileError          # file_path, operation
├── ETLError           # etl_stage, entity_type, original_error
├── APIError           # endpoint, status_code, original_error
└── DataTransformationError  # field, value, transformation, original_error
```

### Schema files (`schema/`)

Numbered for execution order. Key tables created:

- **01**: `player_master`, `team_master` (reference tables)
- **02**: `games_historical`, `player_game_statistics`, `team_game_statistics`
- **03**: `player_season_totals`, `player_season_per_game`, `player_season_advanced`, `player_season_per_100`, `player_season_per_36`, `player_season_shooting`, `player_season_play_by_play`, `team_season_totals`, `team_season_summaries`, `opponent_season_totals`
- **04**: Awards tables
- **05**: `nba_player_mapping`, `nba_team_mapping`, `bbref_player_mapping`, `bbref_team_mapping`
- **06**: Indexes on all above tables

### ID Mapping (`mapping/`)

NBA API and Basketball Reference use different ID systems. The mapping layer resolves between them:

- **Exact matching**: Direct ID lookup in mapping tables
- **Fuzzy matching**: Levenshtein distance on player/team names for unresolved IDs
- **Manual mappings**: Hardcoded overrides in `manual_mappings.py` for known edge cases
- **Validation**: `mapping_validator.py` checks completeness and reports unmatched entities

### Data sources

| Source | Location | Format | Contains |
|--------|----------|--------|----------|
| NBA API | Network | JSON (via nba-api) | Current players, games, box scores |
| Basketball Ref CSVs | `planning/csv_data/` | CSV | Historical player/team stats (25+ files) |
| Basketball Ref Parquets | `planning/parq_data/` | Parquet | Roster, advanced stats, per-game |

## Adding a New ETL Module

1. Create `etl_<entity>.py` extending `BaseETL`
2. Implement `extract()`, `transform()`, `load()`
3. Add table schema to `app/services/database.py` (or `ingestion/schema/`)
4. Register in `run_all_etl.py` in correct dependency order
5. Add mock fixtures in `tests/conftest.py`
6. Write tests in `tests/test_etl_<entity>.py`

## Adding a New Ingestion Loader

1. Create loader class in `ingestion/loaders/` extending `BaseLoader`
2. Implement `load()` and `transform()` methods
3. Add table schema to appropriate `schema/*.sql` file
4. Register with orchestrator in `ingestion/orchestrator.py`
5. Add ID mappings if cross-referencing data sources
6. Write tests in `tests/scripts/ingestion/loaders/`
