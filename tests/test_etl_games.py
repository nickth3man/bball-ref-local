"""Tests for ETL Games pipeline."""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.etl_games import (
    GamesETL,
    parse_game_date,
    run_etl,
)


class TestParseGameDate:
    """Tests for parse_game_date helper function."""

    def test_parse_game_date_iso_format(self):
        """Test parsing ISO format date."""
        result = parse_game_date("2024-10-22")
        assert result.year == 2024
        assert result.month == 10
        assert result.day == 22

    def test_parse_game_date_us_format(self):
        """Test parsing US format date."""
        result = parse_game_date("10/22/2024")
        assert result.year == 2024
        assert result.month == 10
        assert result.day == 22

    def test_parse_game_date_none(self):
        """Test parsing None returns None."""
        assert parse_game_date(None) is None
        assert parse_game_date("") is None

    def test_parse_game_date_invalid(self):
        """Test parsing invalid date returns None."""
        assert parse_game_date("not-a-date") is None


class TestGamesETL:
    """Tests for GamesETL class."""

    @pytest.fixture
    def etl(self):
        return GamesETL()

    def test_extract_with_season(self, etl, mock_league_game_finder):
        """Test extract with specific season."""
        result = etl.extract(season="2024-25", season_type="Regular Season")

        mock_league_game_finder.assert_called_once_with(
            season_nullable="2024-25",
            season_type_nullable="Regular Season",
            league_id_nullable="00",
        )
        assert isinstance(result, pd.DataFrame)

    def test_extract_playoffs(self, etl, mock_league_game_finder):
        """Test extract with playoffs season type."""
        etl.extract(season="2024-25", season_type="Playoffs")

        mock_league_game_finder.assert_called_once_with(
            season_nullable="2024-25",
            season_type_nullable="Playoffs",
            league_id_nullable="00",
        )

    def test_extract_applies_rate_limit(self, etl, mock_league_game_finder, mock_time_sleep):
        """Test extract applies rate limiting."""
        etl.extract(season="2024-25")

        # Check if any rate limiting was applied
        assert mock_time_sleep.called

    def test_extract_returns_team_game_records(
        self, etl, mock_league_game_finder, sample_game_dataframe
    ):
        """Test extract returns team-game records (2 per game)."""
        result = etl.extract(season="2024-25")

        # Sample data has 4 records (2 games x 2 teams each)
        assert len(result) == 4
        assert "GAME_ID" in result.columns
        assert "TEAM_ID" in result.columns
        assert "MATCHUP" in result.columns

    def test_transform_deduplicates(self, etl, sample_game_dataframe):
        """Test transform deduplicates team-game records to games."""
        etl.season = "2024-25"
        etl.season_type = "Regular Season"
        result = etl.transform(sample_game_dataframe)

        # 4 team-game records should become 2 games
        assert len(result) == 2

    def test_transform_identifies_home_away(self, etl, sample_game_dataframe):
        """Test transform correctly identifies home and away teams."""
        etl.season = "2024-25"
        etl.season_type = "Regular Season"
        result = etl.transform(sample_game_dataframe)

        # First game: BOS vs. NYK - BOS is home
        game1 = result[result["game_id"] == "0022400001"].iloc[0]
        assert game1["home_team_id"] == 1610612738  # Boston
        assert game1["away_team_id"] == 1610612752  # New York

    def test_transform_calculates_scores(self, etl, sample_game_dataframe):
        """Test transform extracts scores correctly."""
        etl.season = "2024-25"
        etl.season_type = "Regular Season"
        result = etl.transform(sample_game_dataframe)

        game1 = result[result["game_id"] == "0022400001"].iloc[0]
        assert game1["home_score"] == 132
        assert game1["away_score"] == 109

    def test_transform_determines_winner(self, etl, sample_game_dataframe):
        """Test transform determines winner correctly."""
        etl.season = "2024-25"
        etl.season_type = "Regular Season"
        result = etl.transform(sample_game_dataframe)

        # Game 1: Boston 132, New York 109 -> Boston wins
        game1 = result[result["game_id"] == "0022400001"].iloc[0]
        assert game1["winner_team_id"] == 1610612738

        # Game 2: Philadelphia 117, Milwaukee 118 -> Milwaukee wins
        game2 = result[result["game_id"] == "0022400002"].iloc[0]
        assert game2["winner_team_id"] == 1610612749

    def test_transform_sets_season(self, etl, sample_game_dataframe):
        """Test transform sets season correctly."""
        etl.season = "2024-25"
        etl.season_type = "Regular Season"
        result = etl.transform(sample_game_dataframe)

        assert all(result["season"] == 2024)

    def test_transform_sets_season_type(self, etl, sample_game_dataframe):
        """Test transform sets season type correctly."""
        etl.season = "2024-25"
        etl.season_type = "Playoffs"
        result = etl.transform(sample_game_dataframe)

        assert all(result["season_type"] == "Playoffs")

    def test_transform_sets_game_date(self, etl, sample_game_dataframe):
        """Test transform parses game date."""
        etl.season = "2024-25"
        etl.season_type = "Regular Season"
        result = etl.transform(sample_game_dataframe)

        assert result.iloc[0]["game_date"].year == 2024
        assert result.iloc[0]["game_date"].month == 10
        assert result.iloc[0]["game_date"].day == 22

    def test_transform_determines_status_final(self, etl, sample_game_dataframe):
        """Test transform determines final status for completed games."""
        etl.season = "2024-25"
        etl.season_type = "Regular Season"
        result = etl.transform(sample_game_dataframe)

        assert all(result["status"] == "Final")

    def test_transform_determines_status_scheduled(self, etl):
        """Test transform determines scheduled status for future games."""
        # Create data for a future game
        future_date = pd.Timestamp.now() + pd.Timedelta(days=7)
        df = pd.DataFrame(
            [
                {
                    "GAME_ID": "0022400100",
                    "GAME_DATE": future_date.strftime("%Y-%m-%d"),
                    "TEAM_ID": 1610612738,
                    "TEAM_ABBREVIATION": "BOS",
                    "MATCHUP": "BOS vs. NYK",
                    "PTS": None,
                    "WL": None,
                },
                {
                    "GAME_ID": "0022400100",
                    "GAME_DATE": future_date.strftime("%Y-%m-%d"),
                    "TEAM_ID": 1610612752,
                    "TEAM_ABBREVIATION": "NYK",
                    "MATCHUP": "NYK @ BOS",
                    "PTS": None,
                    "WL": None,
                },
            ]
        )

        etl.season = "2024-25"
        etl.season_type = "Regular Season"
        result = etl.transform(df)

        assert all(result["status"] == "Scheduled")

    def test_transform_handles_unmatched_records(self, etl):
        """Test transform handles unmatched home/away records."""
        # Create data with unmatched records
        df = pd.DataFrame(
            [
                {
                    "GAME_ID": "0022400001",
                    "GAME_DATE": "2024-10-22",
                    "TEAM_ID": 1610612738,
                    "TEAM_ABBREVIATION": "BOS",
                    "MATCHUP": "BOS vs. NYK",
                    "PTS": 132,
                    "WL": "W",
                }
            ]
        )  # Only home team, no away team

        etl.season = "2024-25"
        etl.season_type = "Regular Season"
        result = etl.transform(df)

        # Should have 0 games since no matching away record
        assert len(result) == 0

    def test_transform_selects_db_columns(self, etl, sample_game_dataframe):
        """Test transform selects only database columns."""
        etl.season = "2024-25"
        etl.season_type = "Regular Season"
        # Clear attendance data to ensure consistent columns
        etl.attendance_df = pd.DataFrame(columns=["game_id", "attendance"])
        result = etl.transform(sample_game_dataframe)

        expected_columns = [
            "game_id",
            "season_id",
            "season",
            "season_type",
            "game_date",
            "home_team_id",
            "away_team_id",
            "home_score",
            "away_score",
            "winner_team_id",
            "is_playoff",
            "is_overtime",
            "status",
        ]

        # Check core columns are present (attendance may or may not be present)
        for col in expected_columns:
            assert col in result.columns, f"Expected column {col} not found"
        # Verify no unexpected extra columns besides attendance
        assert all(col in expected_columns or col == "attendance" for col in result.columns)

    def test_load_calls_database(self, etl, mock_database):
        """Test load calls database execute for each game."""
        df = pd.DataFrame(
            [
                {
                    "game_id": "0022400001",
                    "season_id": "2024-25",
                    "season": 2024,
                    "season_type": "Regular Season",
                    "game_date": date(2024, 10, 22),
                    "home_team_id": 1610612738,
                    "away_team_id": 1610612752,
                    "home_score": 132,
                    "away_score": 109,
                    "winner_team_id": 1610612738,
                    "is_playoff": False,
                    "is_overtime": False,
                    "status": "Final",
                }
            ]
        )

        rows_loaded = etl.load(df)

        assert rows_loaded == 1
        mock_database["get_connection"].return_value.executemany.assert_called_once()

    def test_load_multiple_rows(self, etl, mock_database, sample_transformed_game_data):
        """Test load handles multiple games."""
        df = pd.DataFrame(sample_transformed_game_data)

        rows_loaded = etl.load(df)

        assert rows_loaded == 2
        assert mock_database["get_connection"].return_value.executemany.call_count == 1

    def test_load_empty_dataframe(self, etl, mock_database):
        """Test load handles empty DataFrame."""
        df = pd.DataFrame()

        rows_loaded = etl.load(df)

        assert rows_loaded == 0
        mock_database["get_connection"].return_value.executemany.assert_not_called()

    def test_load_converts_game_id_to_string(self, etl, mock_database):
        """Test load converts game_id to string."""
        df = pd.DataFrame(
            [
                {
                    "game_id": 22400001,  # Numeric game ID
                    "season_id": "2024-25",
                    "season": 2024,
                    "season_type": "Regular Season",
                    "game_date": date(2024, 10, 22),
                    "home_team_id": 1610612738,
                    "away_team_id": 1610612752,
                    "home_score": 132,
                    "away_score": 109,
                    "winner_team_id": 1610612738,
                    "is_playoff": False,
                    "is_overtime": False,
                    "status": "Final",
                }
            ]
        )

        etl.load(df)

        # Check that execute was called with string game_id
        # executemany call args: (query, data)
        call_args = mock_database["get_connection"].return_value.executemany.call_args
        data = call_args[0][1]
        assert isinstance(data[0][0], str)


class TestRunETL:
    """Tests for run_etl function."""

    def test_run_etl_success(self, mock_league_game_finder, mock_database):
        """Test run_etl successful execution."""
        result = run_etl(season="2024-25", season_type="Regular Season")

        assert result["status"] == "success"
        assert result["extracted"] == 4  # 4 team-game records
        assert result["loaded"] == 2  # 2 games
        assert result["season"] == "2024-25"
        assert result["season_type"] == "Regular Season"
        assert result["error"] is None

    def test_run_etl_uses_current_season(self, mock_league_game_finder, mock_database):
        """Test run_etl uses current season when not specified."""
        with patch("scripts.etl_games.get_current_season") as mock_get_season:
            mock_get_season.return_value = "2024-25"
            result = run_etl()

        assert result["season"] == "2024-25"

    def test_run_etl_extract_failure(self, mock_league_game_finder, mock_database):
        """Test run_etl handles extract failure."""
        mock_league_game_finder.side_effect = Exception("API Error")

        result = run_etl(season="2024-25")

        assert result["status"] == "failed"
        assert "API Error" in result["error"]

    def test_run_etl_load_failure(self, mock_league_game_finder, mock_database):
        """Test run_etl handles load failure."""
        mock_database["get_connection"].return_value.executemany.side_effect = Exception("DB Error")

        result = run_etl(season="2024-25")

        assert result["status"] == "failed"
        assert "DB Error" in result["error"]

    def test_run_etl_closes_connection(self, mock_league_game_finder, mock_database):
        """Test run_etl closes database connection."""
        run_etl(season="2024-25")

        mock_database["games_close_db_connection"].assert_called_once()

    def test_run_etl_empty_response(self, mock_league_game_finder, mock_database):
        """Test run_etl handles empty API response."""
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [pd.DataFrame()]
        mock_league_game_finder.return_value = mock_instance

        result = run_etl(season="2024-25")

        assert result["status"] == "success"
        assert result["extracted"] == 0
        assert result["loaded"] == 0
