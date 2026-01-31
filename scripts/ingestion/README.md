# Historical NBA Data Ingestion System

This directory contains a comprehensive data ingestion pipeline for loading historical NBA data from the `planning/` directory into the DuckDB database.

## Overview

The ingestion system is designed to:
- Load 34 data files (29 CSV + 5 Parquet) covering NBA data from 1946-2026
- Handle ID mapping between different data sources
- Validate data integrity and consistency
- Support incremental and full loads
- Generate comprehensive reports

## Architecture

```
scripts/ingestion/
├── schema/                    # SQL DDL files
│   ├── 01_planning_tables.sql
│   ├── 02_game_tables.sql
│   ├── 03_season_stats_tables.sql
│   ├── 04_awards_tables.sql
│   ├── 05_id_mapping_tables.sql
│   └── 06_indexes.sql
├── loaders/                   # Data loader modules
│   ├── reference_loaders.py   # Teams, players
│   ├── game_loaders.py        # Games, box scores
│   ├── stats_loaders.py       # Season statistics
│   ├── awards_loaders.py      # Awards, draft
│   └── parquet_loaders.py     # Parquet files
├── mapping/                   # ID resolution
│   ├── player_mapper.py       # Player ID mapping
│   ├── team_mapper.py         # Team ID mapping
│   ├── id_resolver.py         # Main resolver
│   ├── fuzzy_matcher.py       # Fuzzy name matching
│   └── manual_mappings.py     # Known mappings
├── validation/                # Data validation
│   ├── validators.py          # Core validators
│   ├── consistency_checks.py  # Cross-source checks
│   ├── report_generator.py    # Report generation
│   └── validation_cli.py      # CLI interface
├── config.py                  # Configuration
├── database.py                # Database utilities
├── orchestrator.py            # Main orchestrator
├── base_loader.py             # Abstract base class
├── logger.py                  # Logging setup
├── exceptions.py              # Custom exceptions
└── utils.py                   # Utility functions
```

## Quick Start

### 1. Create Database Schema

```bash
python scripts/run_historical_ingestion.py --phase schema
```

### 2. Build ID Mappings

```bash
python scripts/run_historical_ingestion.py --phase mapping
```

### 3. Run Full Ingestion

```bash
python scripts/run_historical_ingestion.py --full
```

### 4. Validate Data

```bash
python scripts/run_historical_ingestion.py --validate-only
```

Or use the validation CLI directly:

```bash
python -m scripts.ingestion.validation.validation_cli --full --report validation.html
```

## Phases

### Phase 1: Reference Data
Loads master data tables:
- `team_abbreviations` - Team name mappings by season
- `team_histories` - Franchise history and relocations
- `player_master` - Primary player registry
- `player_demographics` - Player biographical data
- `player_season_info` - Season-by-season player info

**Source Files:**
- `Team_Abbrev.csv` (1,819 rows)
- `TeamHistories.csv` (141 rows)
- `Players.csv` (6,682 rows)
- `Player_Career_Info.csv` (5,385 rows)
- `Player_Season_Info.csv` (33,120 rows)

### Phase 2: Game Data
Loads transaction-level data:
- `games_historical` - Game schedule and results
- `player_game_statistics` - Player box scores (1.6M rows!)
- `team_game_statistics` - Team box scores (145K rows)

**Source Files:**
- `Games.csv` (72,668 rows)
- `PlayerStatistics.csv` (1,648,657 rows) ⚠️ Large file
- `TeamStatistics.csv` (145,337 rows)

**Note:** PlayerStatistics.csv is loaded in chunks of 10,000 rows to manage memory.

### Phase 3: Season Statistics
Loads aggregated statistics:

**Player Stats:**
- `player_season_totals` - Cumulative season totals
- `player_season_per_game` - Per-game averages
- `player_season_advanced` - Advanced metrics (PER, WS, VORP)
- `player_season_per_100` - Per 100 possessions
- `player_season_per_36` - Per 36 minutes
- `player_season_shooting` - Shooting breakdowns
- `player_season_play_by_play` - Play-by-play stats

**Team Stats:**
- `team_season_totals` - Team season totals
- `team_season_summaries` - Team summaries with advanced stats
- `team_season_per_game` - Per-game averages
- `opponent_season_totals` - Opponent statistics

**Source Files:**
- `Player_Totals.csv`, `Player_Per_Game.csv`, `Advanced.csv`, etc.
- `Team_Totals.csv`, `Team_Summaries.csv`, etc.

### Phase 4: Awards and Draft
Loads recognition data:
- `all_star_selections` - All-Star selections
- `end_of_season_teams` - All-NBA, All-Defense, All-Rookie
- `end_of_season_teams_voting` - Voting details
- `player_award_shares` - MVP, ROY, DPOY awards
- `draft_pick_history` - Complete draft history

**Source Files:**
- `All-Star Selections.csv` (2,005 rows)
- `End_of_Season_Teams.csv` (2,188 rows)
- `End_of_Season_Teams_(Voting).csv` (4,414 rows)
- `Player_Award_Shares.csv` (3,399 rows)
- `Draft_Pick_History.csv` (8,384 rows)

### Phase 5: Parquet Supplemental
Loads additional biographical data:
- Height, weight, birth dates, college from `roster.parq`

**Note:** Other parquet files are subsets of CSV data and are skipped.

## ID Mapping

The system handles two different player ID systems:

1. **personId** (numeric) - From Players.csv (6,681 players)
2. **player_id** (string) - From Basketball Reference format like "jamesle01" (5,384 players)

### Mapping Strategy

1. **Exact Name Match** - Match by first_name + last_name
2. **Fuzzy Matching** - Use difflib.SequenceMatcher for near-matches
3. **Manual Overrides** - Known mappings for edge cases
4. **Unresolved Tracking** - Flag players that couldn't be matched

### Key Findings

- **4,633 players** successfully mapped between systems
- **1,717 players** in Players.csv have no match in Player_Career_Info.csv
- These are primarily international players or players with limited NBA experience

## Data Validation

The system performs multiple types of validation:

### 1. Schema Validation
- Column names and data types
- Required fields present
- Foreign key relationships

### 2. Business Rule Validation
- Points calculation: `PTS = (FG * 2) + 3P + FT`
- Percentages between 0 and 1
- No negative statistics
- Valid date ranges

### 3. Consistency Checks
- Player season totals match sum of game stats
- Game scores match team statistics
- All foreign keys reference valid records
- No duplicate primary keys

### 4. Cross-Source Validation
- CSV data matches parquet data (where overlapping)
- All awards reference valid players
- Draft picks reference valid players

## Configuration

Edit `scripts/ingestion/config.py` to customize:

```python
# Batch sizes for large files
BATCH_SIZE = 10000

# Data sources
DATA_SOURCE_CSV = "planning_csv"
DATA_SOURCE_PARQUET = "planning_parquet"

# Validation thresholds
MIN_SEASON = 1946
MAX_SEASON = 2026
```

## Usage Examples

### Run Specific Phase

```bash
# Only load reference data
python scripts/run_historical_ingestion.py --phase reference

# Only load game data
python scripts/run_historical_ingestion.py --phase games
```

### Dry Run

```bash
# Show what would be loaded without making changes
python scripts/run_historical_ingestion.py --full --dry-run
```

### Validate Specific Table

```bash
python -m scripts.ingestion.validation.validation_cli --table players
```

### Generate Reports

```bash
# HTML report
python -m scripts.ingestion.validation.validation_cli --full --report validation.html

# JSON report
python -m scripts.ingestion.validation.validation_cli --full --json validation.json

# Markdown report
python -m scripts.ingestion.validation.validation_cli --full --markdown validation.md
```

## Data Quality

### Known Issues

1. **Duplicate Players** - Some players appear twice in Players.csv (e.g., Olivinha)
2. **Missing Biographical Data** - Many older/international players lack birthdates
3. **Position Data** - Older seasons use "NA" for position
4. **Traded Players** - Multiple rows per season for traded players

### Handling Missing Data

- **NULL values** - Used for truly missing data (e.g., pre-1974 steals/blocks)
- **Empty strings** - Converted to NULL during ingestion
- **Special values** - -1 for undrafted players, etc.

## Performance

### Optimization Strategies

1. **Chunked Loading** - Large files loaded in batches
2. **Batch Inserts** - Multiple rows inserted per transaction
3. **Indexes** - 80+ indexes for fast queries
4. **Temp Tables** - Staging tables for atomic swaps
5. **Caching** - ID mappings cached in memory

### Expected Load Times

- **Reference Data** - ~5 seconds
- **Game Data** - ~2-3 minutes (1.6M player game records)
- **Season Stats** - ~30 seconds
- **Awards** - ~5 seconds
- **Total** - ~5-10 minutes for full load

## Troubleshooting

### Memory Issues

If you encounter memory errors with large files:

```python
# Reduce batch size in config.py
BATCH_SIZE = 5000  # Instead of 10000
```

### ID Mapping Failures

To see unresolved IDs:

```python
from scripts.ingestion.mapping.id_resolver import IDResolver

resolver = IDResolver(conn)
resolver.generate_unresolved_report()
```

### Validation Failures

Run with verbose logging:

```bash
python scripts/run_historical_ingestion.py --full -v
```

## Database Schema

See SQL files in `scripts/ingestion/schema/` for complete schema definitions.

### Key Tables

| Table | Rows | Description |
|-------|------|-------------|
| player_master | 5,384 | Primary player registry |
| games_historical | 72,668 | Game schedule and results |
| player_game_statistics | 1,648,657 | Player box scores |
| player_season_totals | 33,119 | Season cumulative stats |
| team_season_summaries | 1,907 | Team season summaries |

## Testing

Run validation tests:

```bash
# Run all validations
python -m scripts.ingestion.validation.validation_cli --full

# Check specific consistency
python -c "
from scripts.ingestion.database import get_ingestion_connection
from scripts.ingestion.validation.consistency_checks import ConsistencyChecker

conn = get_ingestion_connection()
checker = ConsistencyChecker(conn)
result = checker.check_player_totals_consistency()
print(f'Passed: {result.passed}')
print(f'Discrepancies: {len(result.discrepancies)}')
"
```

## Contributing

When adding new loaders:

1. Extend `BaseLoader` class
2. Implement `load()` and `transform()` methods
3. Add validation in `validate()` method
4. Register in `orchestrator.py`
5. Add tests in `validation/test_validators.py`

## License

Same as the main project.

## Support

For issues or questions:
1. Check validation reports in `validation_reports/`
2. Review logs for specific error messages
3. Run with `--verbose` flag for detailed output
