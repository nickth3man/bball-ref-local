"""Tests for export service functionality.

This module tests the CSV and JSON export functionality for players,
teams, and games data.
"""

import csv
import json
from datetime import date, datetime
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import Response

from app.services.export_service import (
    DecimalEncoder,
    _build_csv_response,
    _build_json_response,
    _format_value,
    export_box_score,
    export_game_logs,
    export_player_stats,
    export_team_stats,
    export_to_csv,
    export_to_json,
)


class TestDecimalEncoder:
    """Tests for DecimalEncoder JSON encoder."""

    def test_encode_date(self) -> None:
        """Test encoding date objects."""
        encoder = DecimalEncoder()
        test_date = date(2024, 1, 15)
        result = encoder.default(test_date)
        assert result == "2024-01-15"

    def test_encode_datetime(self) -> None:
        """Test encoding datetime objects."""
        encoder = DecimalEncoder()
        test_datetime = datetime(2024, 1, 15, 14, 30, 0)
        result = encoder.default(test_datetime)
        assert result == "2024-01-15T14:30:00"


class TestFormatValue:
    """Tests for _format_value helper function."""

    def test_format_none(self) -> None:
        """Test formatting None value."""
        assert _format_value(None) == ""

    def test_format_date(self) -> None:
        """Test formatting date value."""
        test_date = date(2024, 1, 15)
        assert _format_value(test_date) == "2024-01-15"

    def test_format_datetime(self) -> None:
        """Test formatting datetime value."""
        test_datetime = datetime(2024, 1, 15, 14, 30, 0)
        assert _format_value(test_datetime) == "2024-01-15"

    def test_format_float(self) -> None:
        """Test formatting float value."""
        assert _format_value(3.14159) == "3.14"
        assert _format_value(0.5) == "0.50"
        assert _format_value(100.0) == "100.00"

    def test_format_integer(self) -> None:
        """Test formatting integer value."""
        assert _format_value(42) == "42"
        assert _format_value(0) == "0"

    def test_format_string(self) -> None:
        """Test formatting string value."""
        assert _format_value("test") == "test"
        assert _format_value("") == ""


class TestBuildCsvResponse:
    """Tests for _build_csv_response function."""

    def test_empty_data_raises_error(self) -> None:
        """Test that empty data raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            _build_csv_response([], "test")
        assert exc_info.value.status_code == 404
        assert "No data to export" in exc_info.value.detail

    def test_csv_response_structure(self) -> None:
        """Test CSV response has correct structure."""
        data = [
            {"name": "John", "age": 30, "score": 95.5},
            {"name": "Jane", "age": 25, "score": 88.0},
        ]
        response = _build_csv_response(data, "players")

        assert isinstance(response, Response)
        assert response.media_type == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "players.csv" in response.headers["content-disposition"]

    def test_csv_content(self) -> None:
        """Test CSV content is correctly formatted."""
        data = [
            {"name": "John Doe", "points": 25, "fg_pct": 0.485},
        ]
        response = _build_csv_response(data, "test")

        # Parse the CSV content
        content = response.body.decode("utf-8-sig")
        reader = csv.reader(StringIO(content))
        rows = list(reader)

        assert len(rows) == 2  # Header + 1 data row
        assert rows[0] == ["name", "points", "fg_pct"]
        assert rows[1] == ["John Doe", "25", "0.48"]  # 0.485 rounds to 0.48 with 2 decimals

    def test_csv_with_date_values(self) -> None:
        """Test CSV with date values."""
        data = [
            {"player": "Test", "game_date": date(2024, 1, 15)},
        ]
        response = _build_csv_response(data, "test")

        content = response.body.decode("utf-8-sig")
        reader = csv.reader(StringIO(content))
        rows = list(reader)

        assert rows[1] == ["Test", "2024-01-15"]

    def test_csv_utf8_bom(self) -> None:
        """Test CSV includes UTF-8 BOM for Excel compatibility."""
        data = [{"name": "Test"}]
        response = _build_csv_response(data, "test")

        content_bytes = response.body
        # Check for UTF-8 BOM (EF BB BF)
        assert content_bytes.startswith(b"\xef\xbb\xbf")


class TestBuildJsonResponse:
    """Tests for _build_json_response function."""

    def test_empty_data_raises_error(self) -> None:
        """Test that empty data raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            _build_json_response([], "test")
        assert exc_info.value.status_code == 404

    def test_json_response_structure(self) -> None:
        """Test JSON response has correct structure."""
        data = [
            {"name": "John", "age": 30},
        ]
        response = _build_json_response(data, "players")

        assert isinstance(response, Response)
        assert response.media_type == "application/json"
        assert "attachment" in response.headers["content-disposition"]
        assert "players.json" in response.headers["content-disposition"]

    def test_json_content(self) -> None:
        """Test JSON content is correctly formatted."""
        data = [
            {"name": "John", "age": 30, "active": True},
        ]
        response = _build_json_response(data, "test")

        content = response.body.decode("utf-8")
        parsed = json.loads(content)

        assert len(parsed) == 1
        assert parsed[0]["name"] == "John"
        assert parsed[0]["age"] == 30

    def test_json_with_dates(self) -> None:
        """Test JSON encoding with date values."""
        data = [
            {"player": "Test", "game_date": date(2024, 1, 15)},
        ]
        response = _build_json_response(data, "test")

        content = response.body.decode("utf-8")
        parsed = json.loads(content)

        assert parsed[0]["game_date"] == "2024-01-15"


class TestExportToCsv:
    """Tests for export_to_csv function."""

    def test_export_to_csv(self) -> None:
        """Test generic CSV export function."""
        data = [
            {"id": 1, "value": "test"},
            {"id": 2, "value": "test2"},
        ]
        response = export_to_csv(data, "export")

        assert response.media_type == "text/csv; charset=utf-8"
        content = response.body.decode("utf-8-sig")
        assert "id,value" in content


class TestExportToJson:
    """Tests for export_to_json function."""

    def test_export_to_json(self) -> None:
        """Test generic JSON export function."""
        data = [
            {"id": 1, "value": "test"},
        ]
        response = export_to_json(data, "export")

        assert response.media_type == "application/json"
        content = json.loads(response.body.decode("utf-8"))
        assert len(content) == 1


class TestExportPlayerStats:
    """Tests for export_player_stats function."""

    @patch("app.services.export_service.execute_query")
    def test_export_player_stats_csv(self, mock_execute: Mock) -> None:
        """Test exporting player stats in CSV format."""
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

        assert response.media_type == "text/csv; charset=utf-8"
        assert "player_123_stats" in response.headers["content-disposition"]
        mock_execute.assert_called_once()

    @patch("app.services.export_service.execute_query")
    def test_export_player_stats_json(self, mock_execute: Mock) -> None:
        """Test exporting player stats in JSON format."""
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

        response = export_player_stats("123", "json")

        assert response.media_type == "application/json"
        content = json.loads(response.body.decode("utf-8"))
        assert len(content) == 1
        assert content[0]["season"] == 2024

    @patch("app.services.export_service.execute_query")
    def test_export_player_no_data(self, mock_execute: Mock) -> None:
        """Test exporting player with no stats."""
        mock_execute.return_value = []

        with pytest.raises(HTTPException) as exc_info:
            export_player_stats("999", "csv")
        assert exc_info.value.status_code == 404

    @patch("app.services.export_service.execute_query")
    def test_export_player_query_error(self, mock_execute: Mock) -> None:
        """Test handling database query error."""
        mock_execute.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            export_player_stats("123", "csv")
        assert exc_info.value.status_code == 500
        assert "Failed to fetch player stats" in exc_info.value.detail


class TestExportTeamStats:
    """Tests for export_team_stats function."""

    @patch("app.services.export_service.execute_query")
    def test_export_team_stats_csv(self, mock_execute: Mock) -> None:
        """Test exporting team stats in CSV format."""
        mock_execute.return_value = [
            (
                2024,
                82,
                50,
                32,
                9000,
                110.0,
                3000,
                6000,
                0.5,
                800,
                2200,
                0.364,
                1200,
                1600,
                3500,
                1800,
                400,
                300,
                500,
            ),
        ]

        response = export_team_stats("1610612738", "csv")

        assert response.media_type == "text/csv; charset=utf-8"
        assert "team_1610612738_stats" in response.headers["content-disposition"]

    @patch("app.services.export_service.execute_query")
    def test_export_team_stats_json(self, mock_execute: Mock) -> None:
        """Test exporting team stats in JSON format."""
        mock_execute.return_value = [
            (
                2024,
                82,
                50,
                32,
                9000,
                110.0,
                3000,
                6000,
                0.5,
                800,
                2200,
                0.364,
                1200,
                1600,
                3500,
                1800,
                400,
                300,
                500,
            ),
        ]

        response = export_team_stats("1610612738", "json")

        assert response.media_type == "application/json"
        content = json.loads(response.body.decode("utf-8"))
        assert content[0]["wins"] == 50
        assert content[0]["losses"] == 32

    @patch("app.services.export_service.execute_query")
    def test_export_team_no_data(self, mock_execute: Mock) -> None:
        """Test exporting team with no stats."""
        mock_execute.return_value = []

        with pytest.raises(HTTPException) as exc_info:
            export_team_stats("999", "csv")
        assert exc_info.value.status_code == 404


class TestExportGameLogs:
    """Tests for export_game_logs function."""

    @patch("app.services.export_service.execute_query")
    def test_export_game_logs_csv(self, mock_execute: Mock) -> None:
        """Test exporting game logs in CSV format."""
        mock_execute.return_value = [
            (
                date(2024, 1, 15),
                2024,
                "LAL",
                "Home",
                "Win",
                120,
                110,
                35.5,
                30,
                8,
                5,
                2,
                1,
                10,
                20,
                0.5,
                2,
                5,
                0.4,
                8,
                10,
                0.8,
                3,
                2,
            ),
        ]

        response = export_game_logs("123", season=2024, format_type="csv")

        assert response.media_type == "text/csv; charset=utf-8"
        assert "player_123_gamelog_2024" in response.headers["content-disposition"]

    @patch("app.services.export_service.execute_query")
    def test_export_game_logs_all_seasons(self, mock_execute: Mock) -> None:
        """Test exporting game logs without season filter."""
        mock_execute.return_value = [
            (
                date(2024, 1, 15),
                2024,
                "LAL",
                "Home",
                "Win",
                120,
                110,
                35.5,
                30,
                8,
                5,
                2,
                1,
                10,
                20,
                0.5,
                2,
                5,
                0.4,
                8,
                10,
                0.8,
                3,
                2,
            ),
        ]

        response = export_game_logs("123", season=None, format_type="csv")

        assert "player_123_gamelog" in response.headers["content-disposition"]
        assert "_2024" not in response.headers["content-disposition"]

    @patch("app.services.export_service.execute_query")
    def test_export_game_logs_json(self, mock_execute: Mock) -> None:
        """Test exporting game logs in JSON format."""
        mock_execute.return_value = [
            (
                date(2024, 1, 15),
                2024,
                "LAL",
                "Home",
                "Win",
                120,
                110,
                35.5,
                30,
                8,
                5,
                2,
                1,
                10,
                20,
                0.5,
                2,
                5,
                0.4,
                8,
                10,
                0.8,
                3,
                2,
            ),
        ]

        response = export_game_logs("123", season=2024, format_type="json")

        assert response.media_type == "application/json"
        content = json.loads(response.body.decode("utf-8"))
        assert len(content) == 1
        assert content[0]["points"] == 30


class TestExportBoxScore:
    """Tests for export_box_score function."""

    @patch("app.services.export_service.execute_query")
    def test_export_box_score_csv(self, mock_execute: Mock) -> None:
        """Test exporting box score in CSV format."""
        mock_execute.return_value = [
            ("LeBron James", "LAL", 35.5, 30, 8, 5, 2, 1, 10, 20, 0.5, 2, 5, 0.4, 8, 10, 0.8, 3, 2),
            (
                "Anthony Davis",
                "LAL",
                32.0,
                25,
                12,
                3,
                1,
                3,
                8,
                15,
                0.533,
                0,
                1,
                0.0,
                9,
                10,
                0.9,
                2,
                3,
            ),
        ]

        response = export_box_score("0022400001", "csv")

        assert response.media_type == "text/csv; charset=utf-8"
        assert "game_0022400001_boxscore" in response.headers["content-disposition"]

    @patch("app.services.export_service.execute_query")
    def test_export_box_score_json(self, mock_execute: Mock) -> None:
        """Test exporting box score in JSON format."""
        mock_execute.return_value = [
            ("LeBron James", "LAL", 35.5, 30, 8, 5, 2, 1, 10, 20, 0.5, 2, 5, 0.4, 8, 10, 0.8, 3, 2),
        ]

        response = export_box_score("0022400001", "json")

        assert response.media_type == "application/json"
        content = json.loads(response.body.decode("utf-8"))
        assert len(content) == 1
        assert content[0]["player_name"] == "LeBron James"
        assert content[0]["team"] == "LAL"

    @patch("app.services.export_service.execute_query")
    def test_export_box_score_no_data(self, mock_execute: Mock) -> None:
        """Test exporting box score with no data."""
        mock_execute.return_value = []

        with pytest.raises(HTTPException) as exc_info:
            export_box_score("INVALID", "csv")
        assert exc_info.value.status_code == 404


class TestExportIntegration:
    """Integration-style tests for export functionality."""

    @patch("app.services.export_service.execute_query")
    def test_player_export_formats_consistency(self, mock_execute: Mock) -> None:
        """Test that CSV and JSON exports contain the same data."""
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

        csv_response = export_player_stats("123", "csv")
        json_response = export_player_stats("123", "json")

        # Parse CSV
        csv_content = csv_response.body.decode("utf-8-sig")
        csv_reader = csv.DictReader(StringIO(csv_content))
        csv_data = list(csv_reader)

        # Parse JSON
        json_content = json.loads(json_response.body.decode("utf-8"))

        # Compare data
        assert len(csv_data) == len(json_content)
        assert csv_data[0]["season"] == str(json_content[0]["season"])
        assert csv_data[0]["games_played"] == str(json_content[0]["games_played"])

    def test_format_value_edge_cases(self) -> None:
        """Test format_value with various edge cases."""
        # Test various numeric formats
        assert _format_value(0.0) == "0.00"
        assert _format_value(1.0) == "1.00"
        assert _format_value(0.333) == "0.33"
        assert _format_value(100.999) == "101.00"

        # Test None handling in different contexts
        assert _format_value(None) == ""

        # Test date edge cases
        leap_year_date = date(2024, 2, 29)
        assert _format_value(leap_year_date) == "2024-02-29"
