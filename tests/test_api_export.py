"""Tests for export API endpoints.

This module tests the export endpoints for players, teams, and games.
"""

import csv
import json
from io import StringIO
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient


class TestPlayerExport:
    """Tests for player export endpoint."""

    @patch("app.routers.players.export_player_stats")
    def test_export_player_csv(self, mock_export: Mock, client: TestClient) -> None:
        """Test exporting player data in CSV format."""
        from fastapi.responses import Response

        # Create a proper CSV response
        csv_content = "season,games_played,points\n2024,82,1500\n"
        response = Response(
            content=csv_content.encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=player_123_stats.csv"},
        )
        mock_export.return_value = response

        response = client.get("/api/v1/players/123/export?format=csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        mock_export.assert_called_once_with("123", "csv")

    @patch("app.routers.players.export_game_logs")
    def test_export_player_games(self, mock_export: Mock, client: TestClient) -> None:
        """Test exporting player game logs."""
        from fastapi.responses import Response

        csv_content = "game_date,points\n2024-01-15,30\n"
        response = Response(
            content=csv_content.encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=player_123_gamelog.csv"},
        )
        mock_export.return_value = response

        response = client.get("/api/v1/players/123/export?format=csv&type=games&season=2024")

        assert response.status_code == 200
        mock_export.assert_called_once_with("123", 2024, "csv")

    @patch("app.routers.players.export_player_stats")
    def test_export_player_invalid_format(self, mock_export: Mock, client: TestClient) -> None:
        """Test export with invalid format defaults to CSV."""
        from fastapi.responses import Response

        csv_content = "season,games_played,points\n2024,10,250\n"
        response_mock = Response(content=csv_content, media_type="text/csv")
        mock_export.return_value = response_mock

        response = client.get("/api/v1/players/123/export?format=xml")

        # Should default to CSV, not error
        assert response.status_code == 200
        # Verify export was called (with format defaulting to csv)
        mock_export.assert_called_once()


class TestTeamExport:
    """Tests for team export endpoint."""

    @patch("app.routers.teams.export_team_stats")
    def test_export_team_csv(self, mock_export: Mock, client: TestClient) -> None:
        """Test exporting team data in CSV format."""
        from fastapi.responses import Response

        csv_content = "season,wins,losses\n2024,50,32\n"
        response = Response(
            content=csv_content.encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=team_1610612738_stats.csv"},
        )
        mock_export.return_value = response

        response = client.get("/api/v1/teams/1610612738/export?format=csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        mock_export.assert_called_once_with("1610612738", "csv")

    @patch("app.routers.teams.export_team_stats")
    def test_export_team_json(self, mock_export: Mock, client: TestClient) -> None:
        """Test exporting team data in JSON format."""
        from fastapi.responses import Response

        json_content = json.dumps([{"season": 2024, "wins": 50, "losses": 32}])
        response = Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=team_1610612738_stats.json"},
        )
        mock_export.return_value = response

        response = client.get("/api/v1/teams/1610612738/export?format=json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        data = json.loads(response.content)
        assert len(data) == 1
        assert data[0]["wins"] == 50


class TestGameExport:
    """Tests for game export endpoint."""

    @patch("app.routers.games.export_box_score")
    def test_export_game_csv(self, mock_export: Mock, client: TestClient) -> None:
        """Test exporting game box score in CSV format."""
        from fastapi.responses import Response

        csv_content = "player_name,team,points\nLeBron James,LAL,30\n"
        response = Response(
            content=csv_content.encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=game_0022400001_boxscore.csv"},
        )
        mock_export.return_value = response

        response = client.get("/api/v1/games/0022400001/export?format=csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        mock_export.assert_called_once_with("0022400001", "csv")

    @patch("app.routers.games.export_box_score")
    def test_export_game_json(self, mock_export: Mock, client: TestClient) -> None:
        """Test exporting game box score in JSON format."""
        from fastapi.responses import Response

        json_content = json.dumps([{"player_name": "LeBron James", "points": 30}])
        response = Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=game_0022400001_boxscore.json"},
        )
        mock_export.return_value = response

        response = client.get("/api/v1/games/0022400001/export?format=json")

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data[0]["player_name"] == "LeBron James"


class TestExportFormats:
    """Tests for export format handling."""

    @patch("app.routers.players.export_player_stats")
    def test_default_format_is_csv(self, mock_export: Mock, client: TestClient) -> None:
        """Test that default format is CSV."""
        from fastapi.responses import Response

        csv_content = "season,games_played\n2024,82\n"
        response = Response(
            content=csv_content.encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=player_123_stats.csv"},
        )
        mock_export.return_value = response

        response = client.get("/api/v1/players/123/export")

        assert response.status_code == 200
        mock_export.assert_called_once_with("123", "csv")

    @patch("app.routers.players.export_player_stats")
    def test_case_insensitive_format(self, mock_export: Mock, client: TestClient) -> None:
        """Test that format parameter is case insensitive."""
        from fastapi.responses import Response

        response = Response(
            content=b"test",
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=test.csv"},
        )
        mock_export.return_value = response

        # Test uppercase CSV
        client.get("/api/v1/players/123/export?format=CSV")
        mock_export.assert_called_with("123", "csv")

        # Reset mock and test mixed case
        mock_export.reset_mock()
        client.get("/api/v1/players/123/export?format=Csv")
        mock_export.assert_called_with("123", "csv")


class TestExportContent:
    """Tests for export content validation."""

    @patch("app.services.export_service.execute_query")
    def test_csv_utf8_bom(self, mock_execute: Mock, client: TestClient) -> None:
        """Test that CSV exports include UTF-8 BOM for Excel compatibility."""
        from app.services.export_service import export_player_stats

        mock_execute.return_value = [
            (
                2024,
                82,
                2460.5,
                1500,
                400,
                300,
                100,
                50,
                600,
                1200,
                0.5,
                150,
                400,
                0.375,
                200,
                250,
                0.8,
                150,
                200,
            ),
        ]

        response = export_player_stats("123", "csv")
        content = response.body

        # Check for UTF-8 BOM
        assert content.startswith(b"\xef\xbb\xbf")

    @patch("app.services.export_service.execute_query")
    def test_csv_headers(self, mock_execute: Mock, client: TestClient) -> None:
        """Test that CSV exports have proper headers."""
        from app.services.export_service import export_player_stats

        mock_execute.return_value = [
            (
                2024,
                82,
                2460.5,
                1500,
                400,
                300,
                100,
                50,
                600,
                1200,
                0.5,
                150,
                400,
                0.375,
                200,
                250,
                0.8,
                150,
                200,
            ),
        ]

        response = export_player_stats("123", "csv")
        content = response.body.decode("utf-8-sig")

        reader = csv.reader(StringIO(content))
        headers = next(reader)

        expected_headers = [
            "season",
            "games_played",
            "minutes",
            "points",
            "rebounds",
            "assists",
            "steals",
            "blocks",
            "fg_made",
            "fg_attempted",
            "fg_pct",
            "fg3_made",
            "fg3_attempted",
            "fg3_pct",
            "ft_made",
            "ft_attempted",
            "ft_pct",
            "turnovers",
            "personal_fouls",
        ]

        assert headers == expected_headers
