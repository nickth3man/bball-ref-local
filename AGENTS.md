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
```

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

## Development Guidelines

- Avoid nested if statements - use guard clauses
- Single responsibility principle
- Functions under 30 lines
- Document complex logic with docstrings
- Use f-strings
- Prefer `pathlib.Path` over `os.path`

## Project Structure

```
bball-ref-local/
├── app/                        # FastAPI application
│   ├── main.py                # App entry point, lifespan manager, HTML page routes
│   ├── config.py              # Pydantic Settings, legacy constants
│   ├── routers/               # API routes (games, players, teams, stats, search)
│   ├── models/                # Pydantic models (game, player, team, stats, responses)
│   ├── services/              # Business logic (database, export, htmx_utils)
│   ├── utils/                 # Utility functions (db_utils)
│   ├── templates/             # Jinja2 HTML templates + HTMX partials
│   └── static/                # CSS/JS assets
├── scripts/                   # ETL and ingestion scripts
│   ├── etl_base.py           # Abstract BaseETL class
│   ├── etl_*.py              # ETL pipeline scripts (games, players, stats, teams)
│   ├── run_all_etl.py        # Orchestrate all ETLs
│   ├── init_db.py            # Database initialization
│   ├── ingestion/            # Advanced ingestion framework
│   │   ├── base_loader.py    # Abstract BaseLoader (file -> DB)
│   │   ├── orchestrator.py   # Ingestion orchestrator
│   │   ├── exceptions.py     # Custom exception hierarchy
│   │   ├── loaders/          # CSV/Parquet loaders
│   │   ├── mapping/          # ID mapping, fuzzy matching
│   │   ├── validation/       # Data validation, consistency checks
│   │   └── schema/           # SQL schema definitions (01-06 numbered)
│   └── *.py                  # Utility scripts
├── tests/                     # pytest test suite
│   ├── conftest.py           # Shared fixtures
│   ├── test_api_*.py         # API endpoint tests
│   ├── test_etl_*.py         # ETL pipeline tests
│   ├── test_*_service.py     # Service layer tests
│   └── scripts/ingestion/    # Ingestion framework tests
├── data/                      # DuckDB database files (gitignored)
├── planning/                  # Source data (CSV/Parquet)
├── docs/                      # Documentation
└── validation_reports/        # Generated validation reports
```

## Testing Guidelines

- Test files: `test_*.py`
- Test classes: `Test*` (optional, for grouping)
- Test functions: `test_*`
- Fixtures in `conftest.py` for shared setup
- Mock external calls (NBA API, database)
- Test success and error cases
- Descriptive names: `test_list_games_returns_empty_list`
- `time.sleep` is auto-mocked via `autouse=True` fixture

## Dependencies

- **Core**: FastAPI, DuckDB, Pydantic, pydantic-settings, pandas, nba-api, uvicorn, jinja2
- **Dev**: pytest, pytest-cov, ruff, httpx, ty, pandas-stubs, pyarrow-stubs, types-requests
- **Add dependency**: `uv add <package>`
- **Add dev dependency**: `uv add --dev <package>`

## Environment

- Python 3.12+ required
- Use `.env` file (copy from `.env.example`)
- Virtual environment managed by `uv`
