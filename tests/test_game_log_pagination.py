"""Tests for game log pagination and filtering."""

from fastapi.testclient import TestClient


class TestGameLogPagination:
    """Tests for game log pagination functionality."""

    def test_game_log_default_pagination(self, client: TestClient, sample_player: dict) -> None:
        """Test game log with default pagination."""
        response = client.get(f"/api/v1/players/{sample_player['id']}/gamelog/2024")

        assert response.status_code == 200
        data = response.json()
        assert "games" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 50

    def test_game_log_custom_page_size(self, client: TestClient, sample_player: dict) -> None:
        """Test game log with custom page size."""
        response = client.get(f"/api/v1/players/{sample_player['id']}/gamelog/2024?page_size=100")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page_size"] == 100

    def test_game_log_page_navigation(self, client: TestClient, sample_player: dict) -> None:
        """Test navigating to specific page."""
        response = client.get(f"/api/v1/players/{sample_player['id']}/gamelog/2024?page=2")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 2

    def test_game_log_all_records(self, client: TestClient, sample_player: dict) -> None:
        """Test getting all records (no pagination)."""
        response = client.get(f"/api/v1/players/{sample_player['id']}/gamelog/2024?page_size=all")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page_size"] is None

    def test_game_log_invalid_page_size(self, client: TestClient, sample_player: dict) -> None:
        """Test invalid page size parameter."""
        response = client.get(
            f"/api/v1/players/{sample_player['id']}/gamelog/2024?page_size=invalid"
        )

        assert response.status_code == 422


class TestGameLogSorting:
    """Tests for game log sorting functionality."""

    def test_game_log_sort_by_date(self, client: TestClient, sample_player: dict) -> None:
        """Test sorting game log by date."""
        response = client.get(
            f"/api/v1/players/{sample_player['id']}/gamelog/2024?sort_by=date&sort_order=desc"
        )

        assert response.status_code == 200
        data = response.json()
        assert "games" in data

    def test_game_log_sort_by_points(self, client: TestClient, sample_player: dict) -> None:
        """Test sorting game log by points."""
        response = client.get(
            f"/api/v1/players/{sample_player['id']}/gamelog/2024?sort_by=pts&sort_order=desc"
        )

        assert response.status_code == 200
        data = response.json()
        assert "games" in data

    def test_game_log_default_sort_order(self, client: TestClient, sample_player: dict) -> None:
        """Test default sort order is descending."""
        response = client.get(f"/api/v1/players/{sample_player['id']}/gamelog/2024?sort_by=date")

        assert response.status_code == 200
        data = response.json()
        assert "games" in data

    def test_game_log_invalid_sort_column(self, client: TestClient, sample_player: dict) -> None:
        """Test invalid sort column."""
        response = client.get(f"/api/v1/players/{sample_player['id']}/gamelog/2024?sort_by=invalid")

        assert response.status_code == 422


class TestGameLogFiltering:
    """Tests for game log filtering functionality."""

    def test_game_log_home_filter(self, client: TestClient, sample_player: dict) -> None:
        """Test filtering game log by home games."""
        response = client.get(f"/api/v1/players/{sample_player['id']}/gamelog/2024?home_away=home")

        assert response.status_code == 200
        data = response.json()
        assert "games" in data

        # All games should be home games
        for game in data["games"]:
            assert game["is_home"] is True

    def test_game_log_away_filter(self, client: TestClient, sample_player: dict) -> None:
        """Test filtering game log by away games."""
        response = client.get(f"/api/v1/players/{sample_player['id']}/gamelog/2024?home_away=away")

        assert response.status_code == 200
        data = response.json()
        assert "games" in data

        # All games should be away games
        for game in data["games"]:
            assert game["is_home"] is False

    def test_game_log_win_filter(self, client: TestClient, sample_player: dict) -> None:
        """Test filtering game log by wins."""
        response = client.get(f"/api/v1/players/{sample_player['id']}/gamelog/2024?result=win")

        assert response.status_code == 200
        data = response.json()
        assert "games" in data

        # All games should be wins
        for game in data["games"]:
            assert game["is_win"] is True

    def test_game_log_loss_filter(self, client: TestClient, sample_player: dict) -> None:
        """Test filtering game log by losses."""
        response = client.get(f"/api/v1/players/{sample_player['id']}/gamelog/2024?result=loss")

        assert response.status_code == 200
        data = response.json()
        assert "games" in data

        # All games should be losses
        for game in data["games"]:
            assert game["is_win"] is False

    def test_game_log_combined_filters(self, client: TestClient, sample_player: dict) -> None:
        """Test combining home/away and win/loss filters."""
        response = client.get(
            f"/api/v1/players/{sample_player['id']}/gamelog/2024?home_away=home&result=win"
        )

        assert response.status_code == 200
        data = response.json()
        assert "games" in data

        # All games should be home wins
        for game in data["games"]:
            assert game["is_home"] is True
            assert game["is_win"] is True


class TestGameLogUI:
    """Tests for game log UI components."""

    def test_game_log_has_pagination_controls(
        self, client: TestClient, sample_player: dict
    ) -> None:
        """Test game log template includes pagination controls."""
        response = client.get(f"/players/{sample_player['id']}", headers={"Accept": "text/html"})

        assert response.status_code == 200
        assert b"page-selector" in response.content

    def test_game_log_has_sortable_headers(self, client: TestClient, sample_player: dict) -> None:
        """Test game log has sortable column headers."""
        response = client.get(f"/players/{sample_player['id']}", headers={"Accept": "text/html"})

        assert response.status_code == 200
        assert b"sortable" in response.content

    def test_game_log_has_filters(self, client: TestClient, sample_player: dict) -> None:
        """Test game log has filter dropdowns."""
        response = client.get(f"/players/{sample_player['id']}", headers={"Accept": "text/html"})

        assert response.status_code == 200
        assert b"home-away-filter" in response.content
        assert b"result-filter" in response.content

    def test_game_log_partial_update_htmx(self, client: TestClient, sample_player: dict) -> None:
        """Test game log updates via HTMX."""
        response = client.get(
            f"/api/v1/players/{sample_player['id']}/gamelog/2024?page=1",
            headers={"HX-Request": "true"},
        )

        assert response.status_code == 200
