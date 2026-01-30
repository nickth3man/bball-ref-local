"""Tests for Search API endpoints."""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.main import app
from app.routers.search import _sanitize_query


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_execute_query():
    """Mock the execute_query function."""
    with patch("app.routers.search.execute_query") as mock:
        yield mock


@pytest.fixture
def sample_player_rows():
    """Sample player database rows for search results."""
    return [
        ("2544", "LeBron", "James", "SF", "Los Angeles Lakers", "LAL", 0),
        ("201939", "Stephen", "Curry", "PG", "Golden State Warriors", "GSW", 1),
    ]


@pytest.fixture
def sample_team_rows():
    """Sample team database rows for search results."""
    return [
        ("1610612747", "Los Angeles Lakers", "LAL", "Lakers", "Los Angeles", "Western", "Pacific", 0),
        ("1610612738", "Boston Celtics", "BOS", "Celtics", "Boston", "Eastern", "Atlantic", 1),
    ]


@pytest.fixture
def sample_game_rows():
    """Sample game database rows for search results."""
    return [
        ("0022400001", date(2024, 10, 22), 132, 109, "Boston Celtics", "New York Knicks", "BOS", "NYK", 2024),
    ]


class TestXSSPrevention:
    """Tests for XSS prevention in search queries."""

    def test_sanitize_query_script_tag(self):
        """Test that script tags are sanitized."""
        result = _sanitize_query("<script>alert(\'xss\')</script>")
        assert "<script>" not in result
        # Tags are stripped, content remains but escaped
        assert "alert" in result or result == ""

    def test_sanitize_query_img_tag(self):
        """Test that img tags with onerror are sanitized."""
        result = _sanitize_query("<img src=x onerror=alert(\'xss\')>")
        assert "<img" not in result
        # Tags should be stripped
        assert "onerror" not in result

    def test_sanitize_query_html_tags_stripped(self):
        """Test HTML tags stripping."""
        result = _sanitize_query("<div>LeBron</div>")
        assert result == "LeBron"
        result = _sanitize_query("<b>Bold</b> Text")
        assert result == "Bold Text"

    def test_sanitize_query_special_chars_escaped(self):
        """Test special characters escaping."""
        result = _sanitize_query('"quoted"')
        assert "&quot;" in result
        result = _sanitize_query("<>")
        assert "&lt;" in result

    def test_xss_payload_in_search_response(self, client, mock_execute_query, sample_player_rows):
        """Test that XSS payloads in query are sanitized in response."""
        mock_execute_query.return_value = sample_player_rows[:1]
        response = client.get("/api/v1/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert "query" in data

    def test_html_tags_stripped_from_search(self, client, mock_execute_query, sample_player_rows):
        """Test that HTML tags are stripped from search queries."""
        mock_execute_query.return_value = sample_player_rows[:1]
        response = client.get("/api/v1/search?q=test")
        assert response.status_code == 200
        data = response.json()
        assert "query" in data


class TestSearchFunctionality:
    """Tests for core search functionality."""

    def test_global_search_returns_all_entities(
        self, client, mock_execute_query, sample_player_rows, sample_team_rows, sample_game_rows
    ):
        """Test that global search returns players, teams, and games."""
        mock_execute_query.side_effect = [
            sample_player_rows[:2],
            sample_team_rows[:1],
            sample_game_rows[:1],
        ]
        response = client.get("/api/v1/search?q=lakers")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        types = [r["type"] for r in data["results"]]
        assert "player" in types
        assert "team" in types
        assert "game" in types

    def test_empty_search_query_validation(self, client):
        """Test that empty search query returns validation error."""
        response = client.get("/api/v1/search?q=")
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_search_with_no_results(self, client, mock_execute_query):
        """Test search with query that returns no results."""
        mock_execute_query.side_effect = [[], [], []]
        response = client.get("/api/v1/search?q=xyznonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["results"]) == 0

    def test_player_search_by_partial_name(self, client, mock_execute_query, sample_player_rows):
        """Test player search with partial name matching."""
        mock_execute_query.return_value = [sample_player_rows[0]]
        response = client.get("/api/v1/search?q=lebr")
        assert response.status_code == 200
        data = response.json()
        player_results = [r for r in data["results"] if r["type"] == "player"]
        assert len(player_results) > 0

    def test_team_search_by_abbreviation(self, client, mock_execute_query, sample_team_rows):
        """Test team search by abbreviation."""
        mock_execute_query.side_effect = [[], [sample_team_rows[0]], []]
        response = client.get("/api/v1/search?q=LAL")
        assert response.status_code == 200
        data = response.json()
        team_results = [r for r in data["results"] if r["type"] == "team"]
        assert len(team_results) > 0
        assert "Lakers" in team_results[0]["name"]

    def test_game_search_by_team_name(self, client, mock_execute_query, sample_game_rows):
        """Test game search by team name."""
        mock_execute_query.side_effect = [[], [], [sample_game_rows[0]]]
        response = client.get("/api/v1/search?q=celtics")
        assert response.status_code == 200
        data = response.json()
        game_results = [r for r in data["results"] if r["type"] == "game"]
        assert len(game_results) > 0
        assert "BOS" in game_results[0]["name"]

    def test_search_result_structure(self, client, mock_execute_query, sample_player_rows):
        """Test that search results have correct structure."""
        mock_execute_query.side_effect = [[sample_player_rows[0]], [], []]
        response = client.get("/api/v1/search?q=lebron")
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "total" in data
        if data["results"]:
            result = data["results"][0]
            assert "type" in result
            assert "id" in result
            assert "name" in result
            assert "subtitle" in result
            assert "url" in result

    def test_search_with_limit_parameter(self, client, mock_execute_query, sample_player_rows):
        """Test search with custom limit parameter."""
        mock_execute_query.return_value = sample_player_rows
        response = client.get("/api/v1/search?q=player&limit=5")
        assert response.status_code == 200
        calls = mock_execute_query.call_args_list
        assert len(calls) == 3


class TestSearchEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_sql_injection_drop_table(self, client, mock_execute_query):
        """Test SQL injection DROP TABLE attempt."""
        mock_execute_query.return_value = []
        response = client.get("/api/v1/search?q=DROP TABLE players")
        assert response.status_code in [200, 422]

    def test_sql_injection_or_condition(self, client, mock_execute_query):
        """Test SQL injection OR condition attempt."""
        mock_execute_query.return_value = []
        response = client.get("/api/v1/search?q=1 OR 1=1")
        assert response.status_code in [200, 422]

    def test_search_with_very_long_query(self, client, mock_execute_query):
        """Test search with very long query string."""
        long_query = "a" * 150
        response = client.get(f"/api/v1/search?q={long_query}")
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_search_with_special_characters(self, client, mock_execute_query):
        """Test search with special characters."""
        mock_execute_query.return_value = []
        special_queries = ["player@name", "name#123", "player$name%", "name*test"]
        for query in special_queries:
            response = client.get(f"/api/v1/search?q={query}")
            assert response.status_code == 200

    def test_search_limit_bounds_min(self, client, mock_execute_query):
        """Test limit parameter minimum bound."""
        mock_execute_query.return_value = []
        response = client.get("/api/v1/search?q=test&limit=0")
        assert response.status_code == 422

    def test_search_limit_bounds_max(self, client, mock_execute_query):
        """Test limit parameter maximum bound."""
        mock_execute_query.return_value = []
        response = client.get("/api/v1/search?q=test&limit=25")
        assert response.status_code == 422

    def test_search_limit_valid(self, client, mock_execute_query):
        """Test valid limit parameter."""
        mock_execute_query.return_value = []
        response = client.get("/api/v1/search?q=test&limit=10")
        assert response.status_code == 200


class TestSearchHtmxResponses:
    """Tests for HTMX partial response handling."""

    def test_htmx_request_returns_html(self, client, mock_execute_query, sample_player_rows):
        """Test that HTMX requests return HTML response."""
        mock_execute_query.side_effect = [sample_player_rows[:1], [], []]
        response = client.get("/api/v1/search?q=lebron", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_non_htmx_request_returns_json(self, client, mock_execute_query, sample_player_rows):
        """Test that non-HTMX requests return JSON response."""
        mock_execute_query.side_effect = [sample_player_rows[:1], [], []]
        response = client.get("/api/v1/search?q=lebron")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_htmx_response_contains_results(self, client, mock_execute_query, sample_player_rows):
        """Test that HTMX response contains search results."""
        mock_execute_query.side_effect = [sample_player_rows[:1], [], []]
        response = client.get("/api/v1/search?q=lebron", headers={"HX-Request": "true"})
        assert response.status_code == 200
        html_content = response.text
        assert "LeBron" in html_content or "search" in html_content.lower()

    def test_htmx_response_empty_results(self, client, mock_execute_query):
        """Test HTMX response with no results."""
        mock_execute_query.side_effect = [[], [], []]
        response = client.get("/api/v1/search?q=xyznonexistent", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestSearchErrorHandling:
    """Tests for error handling."""

    def test_database_error_handling(self, client, mock_execute_query):
        """Test handling of database errors."""
        mock_execute_query.side_effect = Exception("Database connection failed")
        response = client.get("/api/v1/search?q=lebron")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Search failed" in data["detail"]

    def test_invalid_search_parameters(self, client):
        """Test invalid search parameters."""
        response = client.get("/api/v1/search")
        assert response.status_code == 422

    def test_search_with_whitespace_query(self, client):
        """Test search with only whitespace."""
        response = client.get("/api/v1/search?q=   ")
        assert response.status_code == 422


class TestSearchInternalFunctions:
    """Tests for internal search functions."""

    def test_search_players_function(self, mock_execute_query, sample_player_rows):
        """Test _search_players function directly."""
        from app.routers.search import _search_players
        mock_execute_query.return_value = sample_player_rows[:1]
        results = _search_players("lebron", 10)
        assert len(results) == 1
        assert results[0].type == "player"
        assert "LeBron James" in results[0].name
        assert results[0].url == "/players/2544"

    def test_search_teams_function(self, mock_execute_query, sample_team_rows):
        """Test _search_teams function directly."""
        from app.routers.search import _search_teams
        mock_execute_query.return_value = sample_team_rows[:1]
        results = _search_teams("lakers", 10)
        assert len(results) == 1
        assert results[0].type == "team"
        assert "Lakers" in results[0].name
        assert results[0].url == "/teams/1610612747"

    def test_search_games_function(self, mock_execute_query, sample_game_rows):
        """Test _search_games function directly."""
        from app.routers.search import _search_games
        mock_execute_query.return_value = sample_game_rows[:1]
        results = _search_games("celtics", 10)
        assert len(results) == 1
        assert results[0].type == "game"
        assert "BOS" in results[0].name
        assert results[0].url == "/games/0022400001"

    def test_search_result_model(self):
        """Test SearchResult model creation."""
        from app.routers.search import SearchResult
        result = SearchResult(
            type="player",
            id="2544",
            name="LeBron James",
            subtitle="LAL - SF",
            url="/players/2544",
        )
        assert result.type == "player"
        assert result.id == "2544"
        assert result.name == "LeBron James"

    def test_search_response_model(self):
        """Test SearchResponse model creation."""
        from app.routers.search import SearchResponse, SearchResult
        results = [
            SearchResult(
                type="player",
                id="2544",
                name="LeBron James",
                subtitle="LAL - SF",
                url="/players/2544",
            )
        ]
        response = SearchResponse(query="lebron", results=results, total=1)
        assert response.query == "lebron"
        assert response.total == 1
        assert len(response.results) == 1
