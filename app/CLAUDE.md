## FastAPI Application Layer

This directory contains the web application: API routers, Pydantic models, service layer, templates, and static assets.

## Entry Point

`main.py` is the FastAPI application entry point:

- **Lifespan manager** (`lifespan()`) handles startup (`init_db()`, set version metadata) and shutdown (`close_db_connection()`)
- **Static files** mounted at `/static` from `app/static/`
- **Templates** loaded from `app/templates/` via Jinja2Templates
- **HTML page routes**: `/`, `/players`, `/teams`, `/games`, `/stats` render full-page templates
- **Health/status**: `GET /health` (DB connectivity check), `GET /api/v1/status`

## Configuration (`config.py`)

- `Settings` class extends `pydantic_settings.BaseSettings`, loads from `.env`
- `settings` is a global singleton used throughout the app
- Legacy `Final` constants (`DB_PATH`, `BATCH_SIZE`, etc.) provide backward compatibility for scripts

## Routers (`routers/`)

Each router file defines an `APIRouter` with a prefix and handles both JSON and HTMX HTML responses.

### Pattern for all routers

```python
router = APIRouter(prefix="/api/v1/<resource>", tags=["<resource>"])

# Private helpers
def _row_to_model(row: tuple) -> Model:
    """Map a SQL result tuple to a Pydantic model by positional index."""

# Route handlers
@router.get("/")
async def list_items(request: Request, ...filters, page, page_size) -> dict | HTMLResponse:
    # 1. Build WHERE clauses dynamically
    # 2. Execute parameterized SQL with COUNT(*) OVER() for pagination
    # 3. Map rows to Pydantic models via _row_to_*()
    # 4. Check is_htmx_request(request) -> return HTML partial or JSON
```

### Router files

| File | Prefix | Key Endpoints |
|------|--------|---------------|
| `games.py` | `/api/v1/games` | List, today, box score (with JOINed team + player stats), export |
| `players.py` | `/api/v1/players` | List, index (A-Z), detail, stats (career+season), game log, enhanced game log, export |
| `teams.py` | `/api/v1/teams` | List, detail, roster, season stats, games, export |
| `stats.py` | `/api/v1/stats` | Leaders (by category+season), standings (by season+conference) |
| `search.py` | `/api/v1/search` | Global search across players/teams/games (LIKE queries with sanitized input) |

### Router-specific models

Some routers define response models inline (not in `models/`):
- `players.py`: `PlayerSeasonStats`, `PlayerStatsResponse`, `PlayerGameLogResponse`
- `stats.py`: `LeaderEntry`, `LeadersResponse`, `StandingsEntry`, `StandingsResponse`
- `search.py`: `SearchResult`, `SearchResponse`

## Models (`models/`)

Pydantic v2 models with `ConfigDict(from_attributes=True)`. Key patterns:

- **Field validation**: `ge=`, `le=` constraints, `Field(description=...)`
- **Computed fields**: `@computed_field` for derived stats (e.g., `fg_pct`, `rebounds_total`, `effective_fg_pct`, `true_shooting_pct`)
- **Display properties**: `@property` for formatted display (e.g., `height_display`, `weight_display`, `display_name`)
- **Optional fields**: `| None` with defaults for nullable database columns

| File | Models | Purpose |
|------|--------|---------|
| `game.py` | `Game` | Game data with computed `is_completed`, `point_differential`, `winning_team_name` |
| `player.py` | `Player` | Player bio with all physical/draft fields, `height_display`, `weight_display` |
| `team.py` | `Team` | Team info with `display_name` property ("City Nickname") |
| `stats.py` | `PlayerGameStats` | Box score with computed `fg_pct`, `fg3_pct`, `ft_pct`, `effective_fg_pct`, `true_shooting_pct` |
| `responses.py` | `PaginatedResponse[T]`, `PaginationParams`, `APIErrorResponse` | Generic pagination wrapper, typed aliases |

### Generic pagination

```python
PaginatedResponse[T]  # items: list[T], total, page, page_size, pages (computed)
PlayerListResponse = PaginatedResponse[Player]
GameListResponse = PaginatedResponse[Game]
```

## Services (`services/`)

### `database.py` - DuckDB connection and query execution

- **Connection**: Global singleton `_conn`, created on first `get_db_connection()` call
- **Schema**: `init_db()` creates all tables in dependency order + indexes
- **Queries**: `execute_query(sql, params)` returns `list[tuple]`
- **Commands**: `execute_command(sql, params)` returns affected row count
- **Batch ops**: `execute_many()` for bulk inserts, `insert_dataframe()` for pandas DataFrames
- **Transactions**: `with transaction() as conn:` context manager (BEGIN/COMMIT/ROLLBACK)
- **Table ops**: `table_exists()`, `get_row_count()`, `truncate_table()`, `create_temp_table()`, `swap_tables()` (atomic rename)
- **Metadata**: `set_app_metadata(key, value)` / `get_app_metadata(key)` for app state tracking
- **SQL files**: `execute_sql_file(path)` for running schema definitions
- **Optimization**: `get_optimized_connection(threads, memory_limit)` for bulk operations

### `htmx_utils.py` - HTMX request detection

- `is_htmx_request(request)` checks for `HX-Request: true` header
- `get_templates()` returns singleton `Jinja2Templates` instance

### `export_service.py` - CSV/JSON data export

- Generic: `export_to_csv(data, filename)`, `export_to_json(data, filename)`
- Domain-specific: `export_player_stats()`, `export_team_stats()`, `export_game_logs()`, `export_box_score()`
- CSV includes UTF-8 BOM for Excel compatibility
- Filenames are sanitized to prevent header injection

## Templates (`templates/`)

### Hierarchy

```
base.html                  # Layout with blocks: content, scripts, styles
├── index.html             # Home page
├── games/list.html        # Games listing
├── players/
│   ├── index.html         # A-Z player index
│   ├── list.html          # Player search/list
│   └── detail.html        # Player profile
├── teams/
│   ├── list.html          # Teams grid
│   └── detail.html        # Team page
├── stats/
│   └── leaders.html       # Stats leaders
└── partials/              # HTMX swap targets (no base template)
    ├── box_score.html
    ├── game_list.html, games_list_by_date.html
    ├── player_list.html, player_card.html, player_game_log.html
    ├── player_stats_table.html, game_log_pagination.html
    ├── team_list.html, team_roster.html
    ├── leaders_table.html, standings_table.html
    ├── search_results.html
    └── export_button.html
```

### HTMX integration

Routes detect HTMX via `is_htmx_request()` and return partial HTML (from `partials/`) instead of JSON. Full-page templates extend `base.html` and include HTMX attributes for dynamic loading.

## Adding a New Endpoint

1. Define Pydantic model in `models/` (or inline in router if response-only)
2. Add route function to appropriate router in `routers/`
3. Use `_row_to_model()` helper for SQL row mapping
4. Support HTMX: check `is_htmx_request(request)` and return partial template
5. Add export support if needed via `export_service.py`
6. Write tests in `tests/test_api_<resource>.py`
