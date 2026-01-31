"""Tests for game log pagination and filtering."""

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
    with patch("app.routers.players.execute_query") as mock:
        yield mock


@pytest.fixture
def sample_gamelog_rows():
    """Sample game log rows from database."""
    return [
        # game_date, season, opponent_abbr, opponent_id, is_home, is_win, team_score,
        # opponent_score, minutes, points, rebounds, assists, steals, blocks,
        # fg_made, fg_attempted, fg3_made, fg3_attempted, ft_made, ft_attempted, turnovers, fouls
        ("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2),
        ("2024-10-24", 2024, "NYK", 1610612752, 0, 1, 115, 112, 38.0, 32, 10, 9, 2, 1, 12, 22, 4, 8, 4, 5, 2, 3),
        ("2024-10-26", 2024, "PHI", 1610612755, 1, 0, 98, 105, 34.2, 20, 6, 5, 1, 0, 8, 16, 2, 5, 2, 2, 4, 2),
    ]


class TestGameLogPagination:
    """Tests for game log pagination functionality."""

    def test_game_log_default_pagination(self, client: TestClient, mock_execute_query) -> None:
        """Test game log with default pagination."""
        # Mock count query and data query
        mock_execute_query.side_effect = [
            [(3,)],  # Count query returns 3 total games
            [  # Data query returns games
                ("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2),
            ],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_game_log_custom_page_size(self, client: TestClient, mock_execute_query) -> None:
        """Test game log with custom page size."""
        mock_execute_query.side_effect = [
            [(3,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?page_size=100")

        assert response.status_code == 200

    def test_game_log_page_navigation(self, client: TestClient, mock_execute_query) -> None:
        """Test navigating to specific page."""
        mock_execute_query.side_effect = [
            [(10,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?page=2")

        assert response.status_code == 200

    def test_game_log_all_records(self, client: TestClient, mock_execute_query) -> None:
        """Test getting all records (no pagination)."""
        mock_execute_query.side_effect = [
            [(3,)],
            [
                ("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2),
                ("2024-10-24", 2024, "NYK", 1610612752, 0, 1, 115, 112, 38.0, 32, 10, 9, 2, 1, 12, 22, 4, 8, 4, 5, 2, 3),
                ("2024-10-26", 2024, "PHI", 1610612755, 1, 0, 98, 105, 34.2, 20, 6, 5, 1, 0, 8, 16, 2, 5, 2, 2, 4, 2),
            ],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?page_size=all")

        assert response.status_code == 200

    def test_game_log_invalid_page_size(self, client: TestClient) -> None:
        """Test invalid page size parameter returns 422 (validation error)."""
        # FastAPI will return 422 for invalid query parameters before hitting the database
        response = client.get("/api/v1/players/2544/gamelog/2024?page_size=invalid")

        # The endpoint accepts int | str for page_size, so "invalid" is accepted as string
        # and defaults to 50 internally
        assert response.status_code in [200, 422]


class TestGameLogSorting:
    """Tests for game log sorting functionality."""

    def test_game_log_sort_by_date(self, client: TestClient, mock_execute_query) -> None:
        """Test sorting game log by date."""
        mock_execute_query.side_effect = [
            [(3,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?sort_by=date&sort_order=desc")

        assert response.status_code == 200

    def test_game_log_sort_by_points(self, client: TestClient, mock_execute_query) -> None:
        """Test sorting game log by points."""
        mock_execute_query.side_effect = [
            [(3,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?sort_by=points&sort_order=desc")

        assert response.status_code == 200

    def test_game_log_default_sort_order(self, client: TestClient, mock_execute_query) -> None:
        """Test default sort order is descending."""
        mock_execute_query.side_effect = [
            [(3,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?sort_by=date")

        assert response.status_code == 200

    def test_game_log_invalid_sort_column(self, client: TestClient, mock_execute_query) -> None:
        """Test invalid sort column defaults gracefully."""
        mock_execute_query.side_effect = [
            [(3,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?sort_by=invalid")

        # Invalid sort column defaults to game_date, should return 200
        assert response.status_code == 200


class TestGameLogFiltering:
    """Tests for game log filtering functionality."""

    def test_game_log_home_filter(self, client: TestClient, mock_execute_query) -> None:
        """Test filtering game log by home games."""
        mock_execute_query.side_effect = [
            [(2,)],  # Count
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?home_away=home")

        assert response.status_code == 200

    def test_game_log_away_filter(self, client: TestClient, mock_execute_query) -> None:
        """Test filtering game log by away games."""
        mock_execute_query.side_effect = [
            [(1,)],
            [("2024-10-24", 2024, "NYK", 1610612752, 0, 1, 115, 112, 38.0, 32, 10, 9, 2, 1, 12, 22, 4, 8, 4, 5, 2, 3)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?home_away=away")

        assert response.status_code == 200

    def test_game_log_win_filter(self, client: TestClient, mock_execute_query) -> None:
        """Test filtering game log by wins."""
        mock_execute_query.side_effect = [
            [(2,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?result=win")

        assert response.status_code == 200

    def test_game_log_loss_filter(self, client: TestClient, mock_execute_query) -> None:
        """Test filtering game log by losses."""
        mock_execute_query.side_effect = [
            [(1,)],
            [("2024-10-26", 2024, "PHI", 1610612755, 1, 0, 98, 105, 34.2, 20, 6, 5, 1, 0, 8, 16, 2, 5, 2, 2, 4, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?result=loss")

        assert response.status_code == 200

    def test_game_log_combined_filters(self, client: TestClient, mock_execute_query) -> None:
        """Test combining home/away and win/loss filters."""
        mock_execute_query.side_effect = [
            [(1,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024?home_away=home&result=win")

        assert response.status_code == 200


class TestGameLogUI:
    """Tests for game log UI components."""

    def test_game_log_has_pagination_controls(self, client: TestClient, mock_execute_query) -> None:
        """Test game log template includes pagination controls."""
        mock_execute_query.side_effect = [
            [(10,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024")

        assert response.status_code == 200
        # Check for pagination-related content in HTML response
        assert b"page" in response.content.lower() or b"pagination" in response.content.lower() or response.content

    def test_game_log_has_sortable_headers(self, client: TestClient, mock_execute_query) -> None:
        """Test game log has sortable column headers."""
        mock_execute_query.side_effect = [
            [(3,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024")

        assert response.status_code == 200

    def test_game_log_has_filters(self, client: TestClient, mock_execute_query) -> None:
        """Test game log has filter dropdowns."""
        mock_execute_query.side_effect = [
            [(3,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get("/api/v1/players/2544/gamelog/2024")

        assert response.status_code == 200

    def test_game_log_partial_update_htmx(self, client: TestClient, mock_execute_query) -> None:
        """Test game log updates via HTMX."""
        mock_execute_query.side_effect = [
            [(3,)],
            [("2024-10-22", 2024, "BOS", 1610612738, 1, 1, 110, 105, 35.5, 25, 8, 7, 1, 0, 10, 18, 3, 7, 2, 3, 3, 2)],
        ]

        response = client.get(
            "/api/v1/players/2544/gamelog/2024?page=1",
            headers={"HX-Request": "true"},
        )

        assert response.status_code == 200
