"""Tests for Stats API endpoints."""

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
    with patch("app.routers.stats.execute_query") as mock:
        yield mock


@pytest.fixture
def sample_leader_row():
    """Sample league leader database row."""
    return (
        "2544",  # player_id
        "LeBron",  # first_name
        "James",  # last_name
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
        "1610612747",  # team_team_id
        "Los Angeles Lakers",  # team_full_name
        "LAL",  # team_abbreviation
        "Lakers",  # team_nickname
        "Los Angeles",  # team_city
        "California",  # team_state
        1947,  # team_year_founded
        "Crypto.com Arena",  # team_arena
        "Jeanie Buss",  # team_owner
        "Rob Pelinka",  # team_general_manager
        "JJ Redick",  # team_head_coach
        "Western",  # team_conference
        "Pacific",  # team_division
        28.5,  # avg_value (points)
        15,  # games_played
    )


@pytest.fixture
def sample_standings_row():
    """Sample standings database row."""
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
        50,  # wins
        20,  # losses
        30,  # home_wins
        10,  # home_losses
        20,  # away_wins
        10,  # away_losses
    )


class TestGetLeagueLeaders:
    """Tests for GET /api/v1/stats/leaders endpoint."""

    def test_get_league_leaders(self, client, mock_execute_query, sample_leader_row):
        """Test GET /api/v1/stats/leaders returns league leaders."""
        mock_execute_query.return_value = [sample_leader_row]

        response = client.get("/api/v1/stats/leaders?category=points&season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "points"
        assert data["season"] == 2024
        assert "leaders" in data
        assert len(data["leaders"]) == 1
        assert data["leaders"][0]["rank"] == 1
        assert data["leaders"][0]["player"]["first_name"] == "LeBron"
        assert data["leaders"][0]["value"] == 28.5

    def test_get_league_leaders_points(self, client, mock_execute_query, sample_leader_row):
        """Test points category."""
        mock_execute_query.return_value = [sample_leader_row]

        response = client.get("/api/v1/stats/leaders?category=points&season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "points"

    def test_get_league_leaders_rebounds(self, client, mock_execute_query, sample_leader_row):
        """Test rebounds category."""
        mock_execute_query.return_value = [sample_leader_row]

        response = client.get("/api/v1/stats/leaders?category=rebounds&season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "rebounds"

    def test_get_league_leaders_assists(self, client, mock_execute_query, sample_leader_row):
        """Test assists category."""
        mock_execute_query.return_value = [sample_leader_row]

        response = client.get("/api/v1/stats/leaders?category=assists&season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "assists"

    def test_get_league_leaders_steals(self, client, mock_execute_query, sample_leader_row):
        """Test steals category."""
        mock_execute_query.return_value = [sample_leader_row]

        response = client.get("/api/v1/stats/leaders?category=steals&season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "steals"

    def test_get_league_leaders_blocks(self, client, mock_execute_query, sample_leader_row):
        """Test blocks category."""
        mock_execute_query.return_value = [sample_leader_row]

        response = client.get("/api/v1/stats/leaders?category=blocks&season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "blocks"

    def test_get_league_leaders_fg_pct(self, client, mock_execute_query, sample_leader_row):
        """Test field goal percentage category."""
        mock_execute_query.return_value = [sample_leader_row]

        response = client.get("/api/v1/stats/leaders?category=fg_pct&season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "fg_pct"

    def test_get_league_leaders_fg3_pct(self, client, mock_execute_query, sample_leader_row):
        """Test three point percentage category."""
        mock_execute_query.return_value = [sample_leader_row]

        response = client.get("/api/v1/stats/leaders?category=fg3_pct&season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "fg3_pct"

    def test_get_league_leaders_ft_pct(self, client, mock_execute_query, sample_leader_row):
        """Test free throw percentage category."""
        mock_execute_query.return_value = [sample_leader_row]

        response = client.get("/api/v1/stats/leaders?category=ft_pct&season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "ft_pct"

    def test_get_league_leaders_with_limit(self, client, mock_execute_query, sample_leader_row):
        """Test limit parameter."""
        mock_execute_query.return_value = [sample_leader_row] * 5

        response = client.get("/api/v1/stats/leaders?category=points&season=2024&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["leaders"]) == 5

    def test_get_league_leaders_empty(self, client, mock_execute_query):
        """Test when no leaders found."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/stats/leaders?category=points&season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["leaders"] == []


class TestGetLeagueLeadersInvalidCategory:
    """Tests for invalid category handling."""

    def test_get_league_leaders_invalid_category(self, client):
        """Test 400 response for invalid category."""
        response = client.get("/api/v1/stats/leaders?category=invalid_category&season=2024")

        assert response.status_code == 400
        assert "Invalid category" in response.json()["detail"]

    def test_get_league_leaders_missing_category(self, client):
        """Test 422 response when category is missing."""
        response = client.get("/api/v1/stats/leaders?season=2024")

        assert response.status_code == 422

    def test_get_league_leaders_missing_season(self, client):
        """Test 422 response when season is missing."""
        response = client.get("/api/v1/stats/leaders?category=points")

        assert response.status_code == 422


class TestGetStandings:
    """Tests for GET /api/v1/stats/standings endpoint."""

    def test_get_standings(self, client, mock_execute_query, sample_standings_row):
        """Test GET /api/v1/stats/standings returns team standings."""
        mock_execute_query.return_value = [sample_standings_row]

        response = client.get("/api/v1/stats/standings?season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["season"] == 2024
        assert "standings" in data
        assert len(data["standings"]) == 1
        assert data["standings"][0]["team"]["team_id"] == "1610612738"
        assert data["standings"][0]["wins"] == 50
        assert data["standings"][0]["losses"] == 20

    def test_get_standings_structure(self, client, mock_execute_query, sample_standings_row):
        """Test standings response structure."""
        mock_execute_query.return_value = [sample_standings_row]

        response = client.get("/api/v1/stats/standings?season=2024")

        assert response.status_code == 200
        data = response.json()
        standing = data["standings"][0]

        # Check team info
        assert "team" in standing
        assert "team_id" in standing["team"]
        assert "full_name" in standing["team"]

        # Check stats
        assert "wins" in standing
        assert "losses" in standing
        assert "win_pct" in standing
        assert "home_record" in standing
        assert "away_record" in standing
        assert "conference_rank" in standing
        assert "division_rank" in standing

    def test_get_standings_multiple_teams(self, client, mock_execute_query, sample_standings_row):
        """Test standings with multiple teams."""
        row2 = list(sample_standings_row)
        row2[0] = "1610612747"  # Different team_id
        row2[1] = "Los Angeles Lakers"
        row2[2] = "LAL"
        row2[11] = "Western"  # Different conference
        row2[12] = "Pacific"  # Different division

        mock_execute_query.return_value = [sample_standings_row, tuple(row2)]

        response = client.get("/api/v1/stats/standings?season=2024")

        assert response.status_code == 200
        data = response.json()
        assert len(data["standings"]) == 2

    def test_get_standings_empty(self, client, mock_execute_query):
        """Test when no standings data available."""
        mock_execute_query.return_value = []

        response = client.get("/api/v1/stats/standings?season=2024")

        assert response.status_code == 200
        data = response.json()
        assert data["standings"] == []


class TestGetStandingsByConference:
    """Tests for conference filter on standings."""

    def test_get_standings_eastern_conference(
        self, client, mock_execute_query, sample_standings_row
    ):
        """Test Eastern conference filter."""
        mock_execute_query.return_value = [sample_standings_row]

        response = client.get("/api/v1/stats/standings?season=2024&conference=Eastern")

        assert response.status_code == 200
        data = response.json()
        assert data["conference"] == "Eastern"
        assert all(s["team"]["conference"] == "Eastern" for s in data["standings"])

    def test_get_standings_western_conference(self, client, mock_execute_query):
        """Test Western conference filter."""
        row = (
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
            45,
            25,
            28,
            12,
            17,
            13,
        )
        mock_execute_query.return_value = [row]

        response = client.get("/api/v1/stats/standings?season=2024&conference=Western")

        assert response.status_code == 200
        data = response.json()
        assert data["conference"] == "Western"
        assert all(s["team"]["conference"] == "Western" for s in data["standings"])

    def test_get_standings_invalid_conference(self, client):
        """Test 400 response for invalid conference."""
        response = client.get("/api/v1/stats/standings?season=2024&conference=Invalid")

        assert response.status_code == 400
        assert "Invalid conference" in response.json()["detail"]

    def test_get_standings_missing_season(self, client):
        """Test 422 response when season is missing."""
        response = client.get("/api/v1/stats/standings")

        assert response.status_code == 422
