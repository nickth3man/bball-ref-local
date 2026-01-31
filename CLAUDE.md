## Response Style

Use the pyramid method:

- Main message first - Lead with the core answer or conclusion
- Key details second - Provide supporting information and context
- Smart follow-up questions - Suggest 2-3 relevant next steps with estimated relevance:
  - [High probability] Question about immediate next action
  - [Medium probability] Question about alternative approaches
  - [Low probability] Question about edge cases or optimization

## Build / Lint / Test Commands

```bash
# Development server
uv run fastapi dev app/main.py

# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_api_games.py

# Run single test function (standalone)
uv run pytest tests/test_api_games.py::test_list_games -v

# Run single test method (in a class)
uv run pytest tests/test_api_games.py::TestGamesAPI::test_list_games -v

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Lint and format
uv run ruff check .
uv run ruff check . --fix
uv run ruff format .

# Type check (relaxed rules for scripts/)
uv run ty

# Run ETL pipeline
uv run python -m scripts.run_all_etl

# Initialize database only
uv run python -m scripts.init_db

# Run historical ingestion
uv run python -m scripts.run_historical_ingestion

# Validate ingestion data
uv run python -m scripts.verify_ingestion_system
```

## Architecture Overview

This is a **local basketball reference** application with a layered architecture:

```
Browser / API Client
    |
FastAPI Routers (app/routers/) ---- Jinja2 Templates + HTMX (app/templates/)
    |
Service Layer (app/services/)
    |
DuckDB (data/bball_ref.db) <---- ETL Pipeline (scripts/)
    |                                  |
    |                           NBA API (nba-api) + CSV/Parquet files (planning/)
    |
Pydantic Models (app/models/)
```

**Key architectural decisions:**
- **No ORM** - Direct SQL via DuckDB for query performance
- **Dual response format** - Routes return JSON by default, HTML partials for HTMX requests (detected via `HX-Request` header)
- **Computed fields** - Pydantic `@computed_field` for derived statistics (shooting percentages, totals)
- **Window functions** - SQL `COUNT(*) OVER()` for efficient paginated total counts
- **Two-level ETL** - Simple ETL scripts (`scripts/etl_*.py`) for NBA API data + advanced ingestion framework (`scripts/ingestion/`) for CSV/Parquet files
- **Global DuckDB connection** - Single connection instance managed via `get_db_connection()` with lifespan-based cleanup

## Code Style Guidelines

### Imports (ruff-enforced)

Order: stdlib (alphabetical) -> third-party (alphabetical) -> first-party (alphabetical)

```python
from collections.abc import AsyncGenerator
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.models import Game, Player
from app.services.database import execute_query
```

### Formatting

- Target: Python 3.12+
- Line length: 100
- Double quotes
- 4 spaces indent
- Trailing commas in multi-line structures

### Naming

- Modules: snake_case (`game_service.py`)
- Classes: PascalCase (`Game`, `PlayerStats`)
- Functions/Methods: snake_case (`get_games`, `calculate_stats`)
- Constants: UPPER_CASE (`MAX_RESULTS`)
- Private: leading underscore (`_internal_helper`)

### Type Annotations

- Use type hints for all parameters and return types
- Use `from __future__ import annotations` for forward references
- FastAPI injection: `param: Annotated[str, Query(...)]`
- Return types: `-> list[Game]`, `-> dict[str, Any]`

### Error Handling

```python
from fastapi import HTTPException

# Guard clause pattern (preferred - avoid nested if)
if not game_id:
    raise HTTPException(status_code=400, detail="Game ID is required")

# Database operations
try:
    result = execute_query(query, params)
except Exception as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### Pydantic Models

```python
from pydantic import BaseModel, ConfigDict, Field

class Game(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game_id: str = Field(description="Unique identifier")
    season: int = Field(description="NBA season year", ge=1946)
```

### SQL Patterns

- Parameterized queries (`?` placeholders) - never f-string interpolation for user input
- Dynamic WHERE clauses built from filter lists: `where_clauses.append("column = ?"); params.append(value)`
- Window functions for pagination counts: `COUNT(*) OVER() as total_count`
- `_row_to_model()` helper functions to map tuple rows to Pydantic models

## Development Guidelines

- Avoid nested if statements - use guard clauses
- Single responsibility principle
- Functions under 30 lines
- Document complex logic with docstrings
- Use f-strings
- Prefer `pathlib.Path` over `os.path`
- Use context7/gh_grep MCP tools for library docs

## Project Structure

```
bball-ref-local/
├── app/                        # FastAPI application (see app/CLAUDE.md)
│   ├── main.py                # App entry point, lifespan manager, HTML page routes
│   ├── config.py              # Pydantic Settings, legacy constants
│   ├── routers/               # API routes (games, players, teams, stats, search)
│   ├── models/                # Pydantic models (game, player, team, stats, responses)
│   ├── services/              # Business logic (database, export, htmx_utils)
│   ├── utils/                 # Utility functions (db_utils)
│   ├── templates/             # Jinja2 HTML templates + HTMX partials
│   └── static/                # CSS/JS assets
├── scripts/                   # ETL and ingestion (see scripts/CLAUDE.md)
│   ├── etl_base.py           # Abstract BaseETL class
│   ├── etl_*.py              # ETL pipeline scripts (games, players, stats, teams)
│   ├── run_all_etl.py        # Orchestrate all ETLs
│   ├── init_db.py            # Database initialization
│   ├── retry_utils.py        # Retry logic with backoff for NBA API
│   ├── logging_utils.py      # ETLLogger context manager, setup_etl_logging
│   ├── ingestion/            # Advanced ingestion framework
│   │   ├── base_loader.py    # Abstract BaseLoader (file -> DB)
│   │   ├── orchestrator.py   # Ingestion orchestrator
│   │   ├── exceptions.py     # Custom exception hierarchy
│   │   ├── loaders/          # CSV/Parquet loaders (games, stats, awards, reference)
│   │   ├── mapping/          # ID mapping, fuzzy matching (NBA API <-> Basketball Ref)
│   │   ├── validation/       # Data validation, consistency checks, report generation
│   │   └── schema/           # SQL schema definitions (01-06 numbered files)
│   └── *.py                  # Utility scripts
├── tests/                     # pytest test suite (see tests/CLAUDE.md)
│   ├── conftest.py           # Shared fixtures (client, mocks, sample data)
│   ├── test_api_*.py         # API endpoint tests
│   ├── test_etl_*.py         # ETL pipeline tests
│   ├── test_*_service.py     # Service layer tests
│   └── scripts/ingestion/    # Ingestion framework tests
├── data/                      # DuckDB database files (gitignored)
├── planning/                  # Source data for ingestion
│   ├── csv_data/             # 25+ CSV files from Basketball Reference
│   └── parq_data/            # 5 Parquet files
├── docs/                      # Documentation (PRD.md)
├── validation_reports/        # Generated validation reports (JSON/HTML/MD)
├── .env.example              # Environment variable template
├── pyproject.toml            # Project config, ruff, pytest, ty settings
└── uv.lock                   # Locked dependencies
```

## API Endpoints Summary

All API routes are prefixed with `/api/v1/`.

| Router | Endpoint | Description |
|--------|----------|-------------|
| games | `GET /games/` | List games (filters: date_from, date_to, team_id, season) |
| games | `GET /games/today` | Today's games |
| games | `GET /games/{game_id}` | Box score with player stats |
| games | `GET /games/{game_id}/export` | Export box score (csv/json) |
| players | `GET /players/` | List players (filters: search, team, position) |
| players | `GET /players/index` | Alphabetical player index |
| players | `GET /players/{player_id}` | Player bio |
| players | `GET /players/{player_id}/stats` | Career + season stats |
| players | `GET /players/{player_id}/games` | Game log with pagination |
| players | `GET /players/{player_id}/gamelog/{year}` | Enhanced game log (sort, W/L, home/away) |
| players | `GET /players/{player_id}/export` | Export player data (csv/json) |
| teams | `GET /teams/` | List teams (filters: conference, division) |
| teams | `GET /teams/{team_id}` | Team details |
| teams | `GET /teams/{team_id}/roster` | Team roster |
| teams | `GET /teams/{team_id}/stats` | Team season stats |
| teams | `GET /teams/{team_id}/games` | Team games (paginated) |
| teams | `GET /teams/{team_id}/export` | Export team data (csv/json) |
| stats | `GET /stats/leaders` | League leaders by category + season |
| stats | `GET /stats/standings` | Team standings by season (+ optional conference) |
| search | `GET /search?q=` | Global search across players, teams, games |

HTML page routes (non-API): `/`, `/players`, `/teams`, `/games`, `/stats`, `/health`

## Database Schema

**Core tables** (created in `app/services/database.py:init_db()`):

| Table | Primary Key | Key Foreign Keys | Purpose |
|-------|-------------|------------------|---------|
| `teams` | `team_id` | - | Team reference data (30 NBA teams) |
| `players` | `player_id` | `team_id`, `draft_team_id` -> teams | Player bios and metadata |
| `seasons` | `season_id` | - | Season reference (e.g., "2024-25") |
| `games` | `game_id` | `season_id`, `home_team_id`, `away_team_id`, `winner_team_id` | Game results with quarter scores |
| `player_game_stats` | `stat_id` | `game_id`, `player_id`, `team_id` | Box score statistics |
| `player_season_stats` | `stat_id` | `player_id`, `season_id`, `team_id` | Season totals + advanced (PER, WS, VORP, BPM) |
| `player_game_logs` | `log_id` | `player_id`, `game_id`, `team_id`, `opponent_id` | Per-game logs with plus/minus |
| `team_season_stats` | `stat_id` | `team_id`, `season_id` | Team season stats + opponent stats + pace/SRS/ratings |
| `awards` | `award_id` | `player_id`, `team_id`, `season_id` | MVP, All-Star, etc. |
| `draft_picks` | `draft_id` | `season_id`, `team_id`, `player_id` | Draft history |
| `app_metadata` | `key` | - | App state (version, ETL status) |

**Advanced tables** (created via `scripts/ingestion/schema/*.sql`):
`games_historical`, `player_game_statistics`, `team_game_statistics`, `player_season_totals`, `player_season_per_game`, `player_season_advanced`, `player_season_per_100`, `player_season_per_36`, `player_season_shooting`, `player_season_play_by_play`, `team_season_totals`, `team_season_summaries`, `opponent_season_totals`, `player_master`, `team_master`

**Table creation order matters** - foreign key dependencies require: teams -> players -> seasons -> games -> stats/logs/awards

## Environment Variables

Configured via `.env` file (copy from `.env.example`), loaded by Pydantic Settings:

```
APP_NAME=BBall Ref Local          # Display name
APP_VERSION=0.1.0                 # Semantic version
DEBUG=false                       # Debug mode
HOST=127.0.0.1                    # Server host
PORT=8000                         # Server port
DATABASE_PATH=./data/bball_ref.db # DuckDB file path
LOG_LEVEL=info                    # Logging level (debug|info|warning|error)
NBA_API_DELAY=0.6                 # Rate limiting delay in seconds between NBA API calls
```

Additional settings in `app/config.py` (not env-configurable defaults):
- `planning_csv_dir`: `./planning/csv_data`
- `planning_parquet_dir`: `./planning/parq_data`
- `min_season` / `max_season`: 1946-2026
- `batch_size`: 10000 (CSV processing)
- `insert_batch_size`: 1000 (DB inserts)

## Testing Guidelines

- Test files: `test_*.py`
- Test classes: `Test*` (optional, for grouping)
- Test functions: `test_*`
- Fixtures in `conftest.py` for shared setup
- Mock external calls (NBA API, database)
- Test success and error cases
- Descriptive names: `test_list_games_returns_empty_list`
- `time.sleep` is auto-mocked via `autouse=True` fixture to speed up tests
- HTMX tests: pass `headers={"HX-Request": "true"}` and check for `text/html` content-type

## Dependencies

- **Core**: FastAPI, DuckDB, Pydantic, pydantic-settings, pandas, nba-api, uvicorn, jinja2
- **Dev**: pytest, pytest-cov, ruff, httpx, ty, pandas-stubs, pyarrow-stubs, types-requests
- **Add dependency**: `uv add <package>`
- **Add dev dependency**: `uv add --dev <package>`

## Ruff Configuration

Defined in `pyproject.toml`:

- **Rules enabled**: E (pycodestyle errors), F (Pyflakes), I (isort), N (pep8-naming), W (pycodestyle warnings), UP (pyupgrade), B (flake8-bugbear), C4 (flake8-comprehensions), SIM (flake8-simplify)
- **Ignored**: E501 (line length - handled by formatter), E402 (module-level imports for sys.path), W291/W293 (whitespace in SQL strings)
- **First-party packages**: `["app"]`
- **Quote style**: double
- **Indent style**: space

## Type Checking (ty)

- Strict rules for `app/` code (errors for unresolved references, invalid types)
- Relaxed rules for `scripts/` (warnings for assignment/argument types, ignores unresolved attributes for pandas-heavy code)
- Tests are fully relaxed (most rules ignored)
- `error-on-warning = false` in terminal settings

## Environment

- Python 3.12+ required
- Use `.env` file (copy from `.env.example`)
- Virtual environment managed by `uv`
