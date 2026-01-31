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

# Run single test function
uv run pytest tests/test_api_games.py::test_get_games -v

# Run with coverage (if configured)
uv run pytest --cov=app --cov-report=term-missing

# Lint code
uv run ruff check .

# Lint with auto-fix
uv run ruff check . --fix

# Format code
uv run ruff format .

# Type check (using ty - optional but recommended)
uv run ty

# Run ETL scripts
uv run python scripts/run_all_etl.py
uv run python scripts/etl_games.py
uv run python scripts/etl_players.py
uv run python scripts/etl_teams.py
uv run python scripts/etl_stats.py
```

## Code Style Guidelines

### Imports (ruff-enforced)

```python
# 1. Standard library (alphabetical)
from collections.abc import AsyncGenerator
from datetime import date
from pathlib import Path

# 2. Third-party (alphabetical)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# 3. First-party app imports (alphabetical)
from app.models import Game, Player
from app.services.database import execute_query
```

### Formatting (ruff-enforced)

- Target Python version: 3.12+
- Line length: 100 characters
- Quote style: double quotes
- Indent: 4 spaces
- Use trailing commas in multi-line structures

### Naming Conventions

- **Modules**: snake_case (e.g., `game_service.py`)
- **Classes**: PascalCase (e.g., `Game`, `PlayerStats`)
- **Functions/Methods**: snake_case (e.g., `get_games`, `calculate_stats`)
- **Constants**: UPPER_CASE (e.g., `MAX_RESULTS`, `DEFAULT_SEASON`)
- **Private**: leading underscore (e.g., `_internal_helper`)

### Type Annotations

- Use type hints for all function parameters and return types
- Use `from __future__ import annotations` when needed for forward references
- Use `Annotated` for FastAPI dependency injection: `param: Annotated[str, Query(...)]`
- Complex return types: `-> list[Game]` or `-> dict[str, Any]`

### Error Handling

```python
# Prefer specific exceptions over generic ones
from fastapi import HTTPException

# Guard clause pattern (preferred)
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

## Development General Guidelines

- Avoid nested if statements - use guard clauses
- Follow single responsibility principle
- Keep functions small and focused (ideally under 30 lines)
- Document complex logic with docstrings
- Use f-strings for string formatting
- Prefer `pathlib.Path` over `os.path`
- Use available MCP tools (context7, gh_grep) for library docs

## Project Structure

```
bball-ref-local/
├── app/                    # FastAPI application
│   ├── main.py            # App entry point
│   ├── routers/           # API routes (games, players, teams, etc.)
│   ├── models/            # Pydantic models
│   ├── services/          # Business logic (database, export, htmx)
│   ├── templates/         # Jinja2 HTML templates
│   └── static/            # CSS/JS assets
├── scripts/               # ETL and utility scripts
├── tests/                 # pytest test files
├── data/                  # DuckDB database files
└── docs/                  # Documentation
```

## Testing Guidelines

- Test files: `test_*.py` naming convention
- Use fixtures in `conftest.py` for shared setup
- Mock external calls (NBA API, database where appropriate)
- Test both success and error cases
- Use descriptive test names: `test_get_games_returns_list`

## Dependencies

- **Core**: FastAPI, DuckDB, Pydantic, pandas, nba-api
- **Dev**: pytest, ruff, httpx, ty (type checker)
- **Add dependency**: `uv add <package>`
- **Add dev dependency**: `uv add --dev <package>`

## Environment

- Python 3.12+ required
- Use `.env` file for configuration (copy from `.env.example`)
- Virtual environment managed by `uv`
