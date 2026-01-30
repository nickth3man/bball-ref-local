"""Tests for Games API endpoints."""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_execute_query():
    """Mock the execute_query function."""
    with patch("app.routers.games.execute_query") as mock:
        yield mock


@pytest.fixture
def sample_game_row():
    """Sample game database row."""
    return (
        "0022400001",  # game_id
        2024,  # season
        "Regular Season",  # season_type
        date(2024, 10, 22),  # game_date
        1610612738,  # home_team_id
        1610612752,  # away_team_id
        132,  # home_score
        109,  # away_score
        1610612738,  # winner_team_id
        "final",  # status
    )


@pytest.fixture
def sample_game_rows():
    """Sample list of game database rows."""
    return [
        (
            "0022400001",
            2024,
            "Regular Season",
            date(2024, 10, 22),
            1610612738,
            1610612752,
            132,
            109,
            1610612738,
            "final",
        ),
        (
            "0022400002",
            2024,
            "Regular Season",
            date(2024, 10, 22),
            1610612755,
            1610612749,
            117,
            118,
            1610612749,
            "final",
        ),
        (
            "0022400003",
            2024,
            "Regular Season",
            date(2024, 10, 23),
            1610612761,
            1610612766,
            110,
            105,
            1610612761,
            "final",
        ),
    ]


@pytest.fixture
def sample_team_row():
    """Sample team database row."""
    return (
        1610612738,  # team_id
        "Boston Celtics",  # full_name
        "BOS",  # abbreviation
        "Celtics",  # nickname
        "Boston",  # city
        "Massachusetts",  # state
        1946,  # year_founded
        "TD Garden",  # arena
        "Wyc Grousbeck",  # owner
        "Danny Ainge",  # general_manager
        "Joe Mazzulla",  # head_coach
        "Eastern",  # conference
        "Atlantic",  # division
    )


@pytest.fixture
def sample_player_stats_row():
    """Sample player stats database row."""
    return (
        12345,  # stat_id
        "0022400001",  # game_id
        2544,  # player_id
        1610612738,  # team_id
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


class TestListGames:
    """Tests for GET /api/v1/games/ endpoint."""

    def test_list_games(self, client, mock_execute_query, sample_game_rows):
        """Test GET /api/v1/games/ returns paginated game list."""
        mock_execute_query.side_effect = [
            [(3,)],  # Count
            sample_game_rows,  # Games data
        ]

        response = client.get("/api/v1/games/")

        assert response.status_code == 200
        data = response.json()
        assert "games" in data
        assert "pagination" in data
        assert data["pagination"]["total_count"] == 3
        assert len(data["games"]) == 3
        assert data["games"][0]["game_id"] == "0022400001"

    def test_list_games_empty(self, client, mock_execute_query):
        """Test game list with no games."""
        mock_execute_query.side_effect = [
            [(0,)],  # Count
            [],  # No games
        ]

        response = client.get("/api/v1/games/")

        assert response.status_code == 200
        data = response.json()
        assert data["games"] == []
        assert data["pagination"]["total_count"] == 0

    def test_list_games_pagination(self, client, mock_execute_query, sample_game_rows):
        """Test game list pagination."""
        mock_execute_query.side_effect = [
            [(100,)],  # Count
            sample_game_rows[:1],  # First page with 1 item
        ]

        response = client.get("/api/v1/games/?page=1&page_size=1")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 1
        assert data["pagination"]["total_pages"] == 100
        assert len(data["games"]) == 1


class TestListGamesWithDateFilter:
    """Tests for game list date filtering."""

    def test_list_games_with_date_from(self, client, mock_execute_query, sample_game_rows):
        """Test date_from filter."""
        mock_execute_query.side_effect = [
            [(2,)],  # Count
            sample_game_rows[:2],  # Filtered games
        ]

        response = client.get("/api/v1/games/?date_from=2024-10-22")

        assert response.status_code == 200
        data = response.json()
        assert len(data["games"]) == 2

    def test_list_games_with_date_to(self, client, mock_execute_query, sample_game_rows):
        """Test date_to filter."""
        mock_execute_query.side_effect = [
            [(1,)],  # Count
            sample_game_rows[:1],  # Filtered games
        ]

        response = client.get("/api/v1/games/?date_to=2024-10-22")

        assert response.status_code == 200
        data = response.json()
        assert len(data["games"]) == 1

    def test_list_games_with_date_range(self, client, mock_execute_query, sample_game_rows):
        """Test both date_from and date_to filters."""
        mock_execute_query.side_effect = [
            [(2,)],  # Count
            sample_game_rows[:2],  # Filtered games
        ]

        response = client.get("/api/v1/games/?date_from=2024-10-22&date_to=2024-10-22")

        assert response.status_code == 200
        data = response.json()
        assert len(data["games"]) == 2


class TestListGamesWithTeamFilter:
    """Tests for game list team filtering."""

    def test_list_games_with_team_filter(self, client, mock_execute_query, sample_game_rows):
        """Test team_id filter."""
        mock_execute_query.side_effect = [
            [(1,)],  # Count
            [sample_game_rows[0]],  # Games for specific team
        ]

        response = client.get("/api/v1/games/?team_id=1610612738")

        assert response.status_code == 200
        data = response.json()
        assert len(data["games"]) == 1
        assert data["games"][0]["home_team_id"] == 1610612738

    def test_list_games_with_team_as_away(self, client, mock_execute_query, sample_game_rows):
        """Test team filter includes games where team is away."""
        mock_execute_query.side_effect = [
            [(1,)],  # Count
            [sample_game_rows[0]],  # Team is home
        ]

        response = client.get("/api/v1/games/?team_id=1610612752")

        assert response.status_code == 200
        data = response.json()
        assert data["games"][0]["away_team_id"] == 1610612752


class TestGetTodaysGames:
    """Tests for GET /api/v1/games/today endpoint."""

    def test_get_todays_games(self, client, mock_execute_query, sample_game_rows):
        """Test GET /api/v1/games/today returns today's games."""
        mock_execute_query.return_value = [sample_game_rows[0]]

        response = client.get("/api/v1/games/today")

        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "games" in data
        assert "count" in data
        assert data["count"] == 1

    def test_get_todays_games_empty(self, client, mock_execute_query):
        """Test today's games when no games scheduled."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/games/today")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["games"] == []


class TestGetGameById:
    """Tests for GET /api/v1/games/{id} endpoint."""

    def test_get_game_by_id(
        self, client, mock_execute_query, sample_game_row, sample_team_row, sample_player_stats_row
    ):
        """Test GET /api/v1/games/{id} returns game box score."""
        mock_execute_query.side_effect = [
            [sample_game_row],  # Game details
            [sample_team_row, sample_team_row],  # Home and away teams
            [sample_player_stats_row],  # Player stats
        ]

        response = client.get("/api/v1/games/0022400001")

        assert response.status_code == 200
        data = response.json()
        assert data["game"]["game_id"] == "0022400001"
        assert "home_team" in data
        assert "away_team" in data
        assert "home_players" in data
        assert "away_players" in data
        assert "home_totals" in data
        assert "away_totals" in data

    def test_get_game_not_found(self, client, mock_execute_query):
        """Test 404 response for non-existent game."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/games/99999999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetGameBoxScore:
    """Tests for game box score response structure."""

    def test_get_game_box_score_structure(
        self, client, mock_execute_query, sample_game_row, sample_team_row, sample_player_stats_row
    ):
        """Test box score has correct structure."""
        mock_execute_query.side_effect = [
            [sample_game_row],
            [sample_team_row, sample_team_row],
            [sample_player_stats_row],
        ]

        response = client.get("/api/v1/games/0022400001")

        assert response.status_code == 200
        data = response.json()

        # Check game structure
        assert "game_id" in data["game"]
        assert "season" in data["game"]
        assert "home_score" in data["game"]
        assert "away_score" in data["game"]

        # Check team structure
        assert "team_id" in data["home_team"]
        assert "full_name" in data["home_team"]

        # Check player stats structure
        if data["home_players"]:
            player = data["home_players"][0]
            assert "player_id" in player
            assert "points" in player
            assert "rebounds_offensive" in player
            assert "assists" in player

    def test_get_game_box_score_totals(
        self, client, mock_execute_query, sample_game_row, sample_team_row, sample_player_stats_row
    ):
        """Test box score includes team totals."""
        mock_execute_query.side_effect = [
            [sample_game_row],
            [sample_team_row, sample_team_row],
            [sample_player_stats_row],
        ]

        response = client.get("/api/v1/games/0022400001")

        assert response.status_code == 200
        data = response.json()

        # Check totals exist
        assert "home_totals" in data
        assert "away_totals" in data

        # Check totals structure
        totals = data["home_totals"]
        assert "points" in totals
        assert "rebounds_total" in totals
        assert "assists" in totals


class TestGetGameNotFound:
    """Tests for 404 responses on game endpoints."""

    def test_get_game_by_id_not_found(self, client, mock_execute_query):
        """Test 404 on get game endpoint."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/games/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_game_database_error(self, client, mock_execute_query):
        """Test handling of database errors."""
        mock_execute_query.side_effect = Exception("Database error")

        response = client.get("/api/v1/games/0022400001")

        assert response.status_code == 500
