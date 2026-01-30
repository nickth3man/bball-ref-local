"""Tests for Players API endpoints."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.main import app
from app.models.player import Player
from app.models.stats import PlayerGameStats


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_execute_query():
    """Mock the execute_query function."""
    with patch("app.routers.players.execute_query") as mock:
        yield mock


@pytest.fixture
def sample_player_row():
    """Sample player database row."""
    return (
        2544,  # player_id
        "LeBron",  # first_name
        "James",  # last_name
        1610612747,  # team_id
        "SF",  # position
        23,  # jersey_number
        80,  # height (inches)
        250,  # weight
        "1984-12-30",  # birth_date
        "USA",  # country
        2003,  # draft_year
        1,  # draft_round
        1,  # draft_number
    )


@pytest.fixture
def sample_player_rows():
    """Sample list of player database rows."""
    return [
        (2544, "LeBron", "James", 1610612747, "SF", 23, 80, 250, "1984-12-30", "USA", 2003, 1, 1),
        (
            201939,
            "Stephen",
            "Curry",
            1610612744,
            "PG",
            30,
            75,
            185,
            "1988-03-14",
            "USA",
            2009,
            1,
            7,
        ),
        (
            1628983,
            "Shai",
            "Gilgeous-Alexander",
            1610612760,
            "SG",
            2,
            78,
            195,
            "1998-07-12",
            "Canada",
            2018,
            1,
            11,
        ),
    ]


@pytest.fixture
def sample_player_stats_row():
    """Sample player game stats database row."""
    return (
        12345,  # stat_id
        "0022400001",  # game_id
        2544,  # player_id
        1610612747,  # team_id
        34.5,  # minutes_played
        25,  # points
        1,  # rebounds_offensive
        8,  # rebounds_defensive
        8,  # assists
        1,  # steals
        0,  # blocks
        4,  # turnovers
        2,  # personal_fouls
        10,  # fg_made
        18,  # fg_attempted
        3,  # fg3_made
        7,  # fg3_attempted
        2,  # ft_made
        3,  # ft_attempted
    )


class TestListPlayers:
    """Tests for GET /api/v1/players/ endpoint."""

    def test_list_players(self, client, mock_execute_query, sample_player_rows):
        """Test GET /api/v1/players/ returns paginated player list."""
        # Mock count query
        mock_execute_query.side_effect = [
            [(3,)],  # Count result
            sample_player_rows,  # Player data
        ]

        response = client.get("/api/v1/players/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "pages" in data
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["items"][0]["first_name"] == "LeBron"
        assert data["items"][0]["last_name"] == "James"

    def test_list_players_with_search(self, client, mock_execute_query, sample_player_rows):
        """Test search filter on player list."""
        # Filter to just LeBron
        filtered_rows = [sample_player_rows[0]]
        mock_execute_query.side_effect = [
            [(1,)],  # Count result
            filtered_rows,  # Player data
        ]

        response = client.get("/api/v1/players/?search=LeBron")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["first_name"] == "LeBron"

    def test_list_players_with_pagination(self, client, mock_execute_query, sample_player_rows):
        """Test page and page_size parameters."""
        # Return only first player for page 1 with page_size 1
        mock_execute_query.side_effect = [
            [(3,)],  # Count result (3 total)
            [sample_player_rows[0]],  # First player only
        ]

        response = client.get("/api/v1/players/?page=1&page_size=1")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 1
        assert data["total"] == 3
        assert data["pages"] == 3
        assert len(data["items"]) == 1

    def test_list_players_empty_result(self, client, mock_execute_query):
        """Test player list with no results."""
        mock_execute_query.side_effect = [
            [(0,)],  # Count result
            [],  # No players
        ]

        response = client.get("/api/v1/players/?search=NonExistentPlayer")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
        assert data["pages"] == 0

    def test_list_players_with_team_filter(self, client, mock_execute_query, sample_player_rows):
        """Test filtering players by team_id."""
        lakers_players = [row for row in sample_player_rows if row[3] == 1610612747]
        mock_execute_query.side_effect = [
            [(len(lakers_players),)],
            lakers_players,
        ]

        response = client.get("/api/v1/players/?team_id=1610612747")

        assert response.status_code == 200
        data = response.json()
        assert all(player["team_id"] == 1610612747 for player in data["items"])

    def test_list_players_database_error(self, client, mock_execute_query):
        """Test handling of database errors."""
        mock_execute_query.side_effect = Exception("Database error")

        response = client.get("/api/v1/players/")

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]


class TestGetPlayerById:
    """Tests for GET /api/v1/players/{id} endpoint."""

    def test_get_player_by_id(self, client, mock_execute_query, sample_player_row):
        """Test GET /api/v1/players/{id} returns player details."""
        mock_execute_query.return_value = [sample_player_row]

        response = client.get("/api/v1/players/2544")

        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert data["first_name"] == "LeBron"
        assert data["last_name"] == "James"
        assert data["position"] == "SF"
        assert data["team_id"] == 1610612747

    def test_get_player_not_found(self, client, mock_execute_query):
        """Test 404 response for non-existent player."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/players/999999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_player_database_error(self, client, mock_execute_query):
        """Test handling of database errors."""
        mock_execute_query.side_effect = Exception("Database connection failed")

        response = client.get("/api/v1/players/2544")

        assert response.status_code == 500


class TestGetPlayerStats:
    """Tests for GET /api/v1/players/{id}/stats endpoint."""

    def test_get_player_stats(self, client, mock_execute_query, sample_player_stats_row):
        """Test GET /api/v1/players/{id}/stats returns player statistics."""
        # Mock player exists check
        # Mock career stats query
        # Mock season stats query
        # Mock recent games query
        mock_execute_query.side_effect = [
            [(2544,)],  # Player exists check
            [(10, 345.0, 250, 80, 60, 15, 5, 100, 200, 30, 80, 40, 50, 25, 40)],  # Career stats
            [],  # Season stats (empty for this test)
            [sample_player_stats_row],  # Recent games
        ]

        response = client.get("/api/v1/players/2544/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert "career_stats" in data
        assert "season_stats" in data
        assert "recent_games" in data
        assert data["career_stats"]["games_played"] == 10
        assert data["career_stats"]["points"] == 250

    def test_get_player_stats_not_found(self, client, mock_execute_query):
        """Test 404 when player doesn't exist."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/players/999999/stats")

        assert response.status_code == 404

    def test_get_player_stats_with_season_filter(
        self, client, mock_execute_query, sample_player_stats_row
    ):
        """Test stats endpoint with season filter."""
        mock_execute_query.side_effect = [
            [(2544,)],  # Player exists check
            [(5, 172.5, 125, 40, 30, 8, 3, 50, 100, 15, 40, 20, 25, 12, 20)],  # Season stats
            [],  # No season-by-season when filter applied
            [sample_player_stats_row],  # Recent games
        ]

        response = client.get("/api/v1/players/2544/stats?season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert data["career_stats"]["season"] == 2024


class TestGetPlayerGames:
    """Tests for GET /api/v1/players/{id}/games endpoint."""

    def test_get_player_games(self, client, mock_execute_query, sample_player_stats_row):
        """Test GET /api/v1/players/{id}/games returns player game log."""
        mock_execute_query.side_effect = [
            [(2544,)],  # Player exists check
            [(50,)],  # Total count
            [sample_player_stats_row],  # Game data
        ]

        response = client.get("/api/v1/players/2544/games")

        assert response.status_code == 200
        data = response.json()
        assert data["player_id"] == 2544
        assert "games" in data
        assert "total_count" in data
        assert data["total_count"] == 50
        assert len(data["games"]) == 1
        assert data["games"][0]["points"] == 25

    def test_get_player_games_not_found(self, client, mock_execute_query):
        """Test 404 when player doesn't exist."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/players/999999/games")

        assert response.status_code == 404

    def test_get_player_games_with_season_filter(
        self, client, mock_execute_query, sample_player_stats_row
    ):
        """Test games endpoint with season filter."""
        mock_execute_query.side_effect = [
            [(2544,)],  # Player exists check
            [(20,)],  # Count for season
            [sample_player_stats_row],  # Game data
        ]

        response = client.get("/api/v1/players/2544/games?season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["season"] == 2024
        assert data["total_count"] == 20


class TestListPlayersHtmx:
    """Tests for HTMX response format on player endpoints."""

    def test_list_players_htmx(self, client, mock_execute_query, sample_player_rows):
        """Test HTMX request returns HTML response."""
        mock_execute_query.side_effect = [
            [(3,)],
            sample_player_rows,
        ]

        response = client.get("/api/v1/players/", headers={"HX-Request": "true"})

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_get_player_htmx(self, client, mock_execute_query, sample_player_row):
        """Test HTMX request for single player returns HTML."""
        mock_execute_query.return_value = [sample_player_row]

        response = client.get("/api/v1/players/2544", headers={"HX-Request": "true"})

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_get_player_stats_htmx(self, client, mock_execute_query, sample_player_stats_row):
        """Test HTMX request for player stats returns HTML."""
        mock_execute_query.side_effect = [
            [(2544,)],
            [(10, 345.0, 250, 80, 60, 15, 5, 100, 200, 30, 80, 40, 50, 25, 40)],
            [],
            [sample_player_stats_row],
        ]

        response = client.get("/api/v1/players/2544/stats", headers={"HX-Request": "true"})

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
