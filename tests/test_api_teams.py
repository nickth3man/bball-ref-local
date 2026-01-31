"""Tests for Teams API endpoints."""

import sys
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
    with patch("app.routers.teams.execute_query") as mock:
        yield mock


@pytest.fixture
def sample_team_row():
    """Sample team database row."""
    return (
        "1610612738",  # team_id
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
def sample_team_rows():
    """Sample list of team database rows."""
    return [
        (
            "1610612738",
            "Boston Celtics",
            "BOS",
            "Celtics",
            "Boston",
            "Massachusetts",
            1946,
            "TD Garden",
            "Wyc Grousbeck",
            "Danny Ainge",
            "Joe Mazzulla",
            "Eastern",
            "Atlantic",
        ),
        (
            "1610612747",
            "Los Angeles Lakers",
            "LAL",
            "Lakers",
            "Los Angeles",
            "California",
            1947,
            "Crypto.com Arena",
            "Jeanie Buss",
            "Rob Pelinka",
            "JJ Redick",
            "Western",
            "Pacific",
        ),
        (
            "1610612741",
            "Chicago Bulls",
            "CHI",
            "Bulls",
            "Chicago",
            "Illinois",
            1966,
            "United Center",
            "Jerry Reinsdorf",
            "Marc Eversley",
            "Billy Donovan",
            "Eastern",
            "Central",
        ),
    ]


@pytest.fixture
def sample_roster_row():
    """Sample roster player database row."""
    return (
        "2544",  # player_id
        "LeBron",  # first_name
        "James",  # last_name
        "LeBron James",  # full_name
        "1610612747",  # team_id
        "SF",  # position
        23,  # jersey_number
        "6'8",  # height
        250,  # weight
        "1984-12-30",  # birth_date
        "USA",  # country
        2003,  # draft_year
        1,  # draft_round
        1,  # draft_number
    )


@pytest.fixture
def sample_team_stats_row():
    """Sample team stats database row."""
    return (
        50,  # wins
        20,  # losses
        30,  # home_wins
        10,  # home_losses
        20,  # away_wins
        10,  # away_losses
    )


@pytest.fixture
def sample_game_row():
    """Sample game database row."""
    return (
        "0022400001",  # game_id
        2024,  # season
        "Regular Season",  # season_type
        "2024-10-22",  # game_date
        "1610612738",  # home_team_id
        "1610612747",  # away_team_id
        132,  # home_score
        109,  # away_score
        "1610612738",  # winner_team_id
        "final",  # status
    )


class TestListTeams:
    """Tests for GET /api/v1/teams/ endpoint."""

    def test_list_teams(self, client, mock_execute_query, sample_team_rows):
        """Test GET /api/v1/teams/ returns list of all teams."""
        mock_execute_query.return_value = sample_team_rows

        response = client.get("/api/v1/teams/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["team_id"] == "1610612738"
        assert data[0]["full_name"] == "Boston Celtics"
        assert data[0]["abbreviation"] == "BOS"

    def test_list_teams_empty(self, client, mock_execute_query):
        """Test team list with no teams."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/teams/")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_teams_database_error(self, client, mock_execute_query):
        """Test handling of database errors."""
        mock_execute_query.side_effect = Exception("Database error")

        response = client.get("/api/v1/teams/")

        assert response.status_code == 500


class TestListTeamsWithFilters:
    """Tests for team list filtering."""

    def test_list_teams_with_conference_filter(self, client, mock_execute_query, sample_team_rows):
        """Test filtering teams by conference."""
        eastern_teams = [row for row in sample_team_rows if row[11] == "Eastern"]
        mock_execute_query.return_value = eastern_teams

        response = client.get("/api/v1/teams/?conference=Eastern")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(team["conference"] == "Eastern" for team in data)

    def test_list_teams_with_division_filter(self, client, mock_execute_query, sample_team_rows):
        """Test filtering teams by division."""
        atlantic_teams = [row for row in sample_team_rows if row[12] == "Atlantic"]
        mock_execute_query.return_value = atlantic_teams

        response = client.get("/api/v1/teams/?division=Atlantic")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["division"] == "Atlantic"

    def test_list_teams_with_conference_and_division(
        self, client, mock_execute_query, sample_team_rows
    ):
        """Test filtering by both conference and division."""
        eastern_atlantic = [
            row for row in sample_team_rows if row[11] == "Eastern" and row[12] == "Atlantic"
        ]
        mock_execute_query.return_value = eastern_atlantic

        response = client.get("/api/v1/teams/?conference=Eastern&division=Atlantic")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["conference"] == "Eastern"
        assert data[0]["division"] == "Atlantic"


class TestGetTeamById:
    """Tests for GET /api/v1/teams/{id} endpoint."""

    def test_get_team_by_id(self, client, mock_execute_query, sample_team_row):
        """Test GET /api/v1/teams/{id} returns team details."""
        mock_execute_query.return_value = [sample_team_row]

        response = client.get("/api/v1/teams/1610612738")

        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == "1610612738"
        assert data["full_name"] == "Boston Celtics"
        assert data["abbreviation"] == "BOS"
        assert data["conference"] == "Eastern"
        assert data["division"] == "Atlantic"

    def test_get_team_not_found(self, client, mock_execute_query):
        """Test 404 response for non-existent team."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/teams/999999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetTeamRoster:
    """Tests for GET /api/v1/teams/{id}/roster endpoint."""

    def test_get_team_roster(self, client, mock_execute_query, sample_roster_row):
        """Test GET /api/v1/teams/{id}/roster returns team roster."""
        # Endpoint only makes one query for roster, no team check
        mock_execute_query.return_value = [sample_roster_row]

        response = client.get("/api/v1/teams/1610612738/roster")

        assert response.status_code == 200
        data = response.json()
        # Endpoint returns list[Player], not a dict with team/roster
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["first_name"] == "LeBron"

    def test_get_team_roster_not_found(self, client, mock_execute_query):
        """Test empty roster when team has no players (endpoint doesn't check team existence)."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/teams/999999/roster")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_team_roster_empty(self, client, mock_execute_query):
        """Test roster for team with no players."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/teams/1610612738/roster")

        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestGetTeamStats:
    """Tests for GET /api/v1/teams/{id}/stats endpoint."""

    def test_get_team_stats(self, client, mock_execute_query):
        """Test GET /api/v1/teams/{id}/stats returns team statistics."""
        # Stats endpoint requires season parameter and makes single query
        # Query returns 17 columns: games_played, wins, losses, avg_points_for, total_points_for,
        # total_fg_made, total_fg_attempted, total_fg3_made, total_fg3_attempted,
        # total_ft_made, total_ft_attempted, total_offensive_rebounds, total_defensive_rebounds,
        # total_assists, total_steals, total_blocks, total_turnovers, total_personal_fouls
        mock_execute_query.return_value = [
            (70, 50, 20, 115.5, 8085, 3000, 6000, 800, 2200, 1200, 1500, 800, 2400, 1800, 500, 400, 900, 1400)
        ]

        response = client.get("/api/v1/teams/1610612738/stats?season=2024")

        assert response.status_code == 200
        data = response.json()
        # Endpoint returns stats dict directly, not wrapped in team/stats structure
        assert "team_id" in data
        assert "wins" in data
        assert data["wins"] == 50
        assert data["losses"] == 20
        assert data["win_pct"] == 0.714

    def test_get_team_stats_not_found(self, client, mock_execute_query):
        """Test empty stats when no games found (endpoint doesn't check team existence)."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/teams/999999/stats?season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["wins"] == 0
        assert data["losses"] == 0
        assert data["games_played"] == 0


class TestGetTeamGames:
    """Tests for GET /api/v1/teams/{id}/games endpoint."""

    def test_get_team_games(self, client, mock_execute_query, sample_game_row):
        """Test GET /api/v1/teams/{id}/games returns team games."""
        # Endpoint makes single query with window function (11 columns + total_count)
        game_with_count = sample_game_row + (20,)  # Add total_count
        mock_execute_query.return_value = [game_with_count]

        response = client.get("/api/v1/teams/1610612738/games")

        assert response.status_code == 200
        data = response.json()
        # Endpoint returns GameListResponse with items, total, page, page_size, pages
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert data["total"] == 20
        assert len(data["items"]) == 1
        assert data["items"][0]["home_team_id"] == "1610612738"

    def test_get_team_games_not_found(self, client, mock_execute_query):
        """Test empty games list when team has no games (endpoint doesn't check team existence)."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/teams/999999/games")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_team_games_with_season_filter(self, client, mock_execute_query, sample_game_row):
        """Test team games with season filter."""
        game_with_count = sample_game_row + (10,)
        mock_execute_query.return_value = [game_with_count]

        response = client.get("/api/v1/teams/1610612738/games?season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["season"] == 2024

    def test_get_team_games_with_pagination(self, client, mock_execute_query, sample_game_row):
        """Test team games with pagination."""
        game_with_count = sample_game_row + (50,)
        mock_execute_query.return_value = [game_with_count]

        response = client.get("/api/v1/teams/1610612738/games?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total"] == 50


class TestGetTeamNotFound:
    """Tests for 404 responses on team endpoints."""

    def test_get_team_stats_not_found(self, client, mock_execute_query):
        """Test empty stats when team has no games (endpoint doesn't check team existence)."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/teams/999999/stats?season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["games_played"] == 0
        assert data["wins"] == 0

    def test_get_team_games_not_found(self, client, mock_execute_query):
        """Test empty games list when team has no games (endpoint doesn't check team existence)."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/teams/999999/games")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
