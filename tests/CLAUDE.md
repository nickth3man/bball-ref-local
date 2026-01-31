## Test Suite

pytest-based test suite. All tests run via `uv run pytest`.

## Configuration

Defined in `pyproject.toml`:
- **Test paths**: `tests/`
- **File patterns**: `test_*.py`, `*_test.py`
- **Class patterns**: `Test*`
- **Function patterns**: `test_*`
- **Default options**: `-v --tb=short`
- **Async mode**: `auto`

## Test Organization

```
tests/
├── conftest.py                    # All shared fixtures (500+ lines)
├── test_api_games.py              # Games router endpoints
├── test_api_players.py            # Players router endpoints
├── test_api_teams.py              # Teams router endpoints
├── test_api_stats.py              # Stats router (leaders, standings)
├── test_api_search.py             # Search endpoint
├── test_models.py                 # Pydantic model validation + computed fields
├── test_config.py                 # Settings/config tests
├── test_database_service.py       # Database service layer
├── test_htmx_utils.py            # HTMX request detection
├── test_export_service.py         # CSV/JSON export
├── test_etl_teams.py             # Teams ETL pipeline
├── test_etl_players.py           # Players ETL pipeline
├── test_etl_games.py             # Games ETL pipeline
├── test_etl_stats.py             # Stats ETL pipeline
├── test_run_all_etl.py           # ETL orchestrator
├── test_game_log_pagination.py   # Game log pagination logic
└── scripts/ingestion/            # Ingestion framework tests
    ├── test_base_loader.py       # BaseLoader abstract class
    ├── test_orchestrator.py      # Orchestrator coordination
    ├── test_utils.py             # Utility function tests
    └── loaders/
        └── test_game_loaders.py  # Game data loader tests
```

## Shared Fixtures (`conftest.py`)

### FastAPI Client

```python
@pytest.fixture
def client():
    """TestClient wrapping the FastAPI app."""
    return TestClient(app)
```

### Auto-use Fixtures

- `mock_time_sleep` (autouse=True) - Patches `time.sleep` globally to speed up all tests

### Database Mocks

| Fixture | Purpose |
|---------|---------|
| `mock_db_connection` | MagicMock with `.execute()`, `.executemany()`, `.rowcount`, `.close()` |
| `mock_get_db_connection` | Patches `get_db_connection` in all 4 ETL modules simultaneously |
| `mock_close_db_connection` | Patches `close_db_connection` in `etl_base` module |
| `mock_database` | Combined fixture with dict access to all connection mocks per module |

The `mock_database` fixture provides per-module mock access:
```python
def test_something(mock_database):
    mock_database["teams_get_db_connection"]  # teams module's mock
    mock_database["connection"]               # the underlying mock connection
```

### Sample Data Fixtures

**Teams**: `sample_team_data` (raw dicts), `sample_team_dataframe`, `sample_transformed_team_data`
**Players**: `sample_player` (LeBron), `sample_player_api_data`, `sample_player_dataframe`, `sample_player_with_all_fields`, `sample_player_with_all_fields_df`
**Games**: `sample_game_api_data` (duplicate rows per game), `sample_game_dataframe`, `sample_transformed_game_data`
**Stats**: `sample_player_stats_api_data`, `sample_player_stats_dataframe`, `sample_transformed_player_stats`

### NBA API Mocks

| Fixture | What It Patches | Returns |
|---------|-----------------|---------|
| `mock_common_all_players` | `scripts.etl_players.CommonAllPlayers` | Sample player DataFrame |
| `mock_league_game_finder` | `scripts.etl_games.LeagueGameFinder` | Sample game DataFrame |
| `mock_player_game_logs` | `scripts.etl_stats.PlayerGameLogs` | Sample stats DataFrame |
| `mock_get_teams` | `scripts.etl_teams.get_teams` | Sample team dicts |

### ETL Orchestrator Mocks

| Fixture | Purpose |
|---------|---------|
| `mock_etl_modules` | Patches all 4 `run_*_etl()` in `run_all_etl` with success returns |
| `mock_set_app_metadata` | Patches metadata storage |

## Test Patterns

### API endpoint tests

```python
def test_list_games_returns_paginated_response(client):
    response = client.get("/api/v1/games/?page=1&page_size=20")
    assert response.status_code == 200
    data = response.json()
    assert "games" in data
    assert "pagination" in data

def test_get_nonexistent_game_returns_404(client):
    response = client.get("/api/v1/games/invalid_id")
    assert response.status_code == 404
```

### HTMX response tests

```python
def test_list_games_returns_html_for_htmx(client):
    response = client.get("/api/v1/games/", headers={"HX-Request": "true"})
    assert "text/html" in response.headers["content-type"]
```

### ETL pipeline tests

```python
def test_teams_etl_success(mock_get_teams, mock_database):
    result = run_teams_etl()
    assert result["status"] == "success"
    assert result["loaded"] > 0
    mock_database["connection"].execute.assert_called()
```

### Model validation tests

```python
def test_game_computed_fields():
    game = Game(game_id="001", season=2024, ..., home_score=110, away_score=105)
    assert game.is_completed is True
    assert game.point_differential == 5
```

## Writing New Tests

1. **File naming**: `test_<module>.py` in appropriate directory
2. **Use existing fixtures**: Check `conftest.py` before creating new mocks
3. **Patch at usage site**: `patch("scripts.etl_teams.get_db_connection")` not `patch("app.services.database.get_db_connection")`
4. **Test both JSON and HTMX**: API endpoints should test both response types
5. **Test error cases**: 404s, 400s, empty results, database failures
6. **Descriptive names**: `test_<action>_<condition>_<expected_result>` (e.g., `test_list_games_with_date_filter_returns_filtered_results`)
7. **Fixture composition**: Use `mock_database` for ETL tests, `client` for API tests
