"""Tests for ETL Games pipeline."""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.etl_games import (
    extract_games,
    load_games,
    parse_game_date,
    run_etl,
    transform_games,
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


class TestExtractGames:
    """Tests for extract_games function."""

    def test_extract_games_with_season(self, mock_league_game_finder):
        """Test extract_games with specific season."""
        result = extract_games(season="2024-25", season_type="Regular Season")

        mock_league_game_finder.assert_called_once_with(
            season_nullable="2024-25",
            season_type_nullable="Regular Season",
            player_or_team_abbreviation="T",
        )
        assert isinstance(result, pd.DataFrame)

    def test_extract_games_playoffs(self, mock_league_game_finder):
        """Test extract_games with playoffs season type."""
        extract_games(season="2024-25", season_type="Playoffs")

        mock_league_game_finder.assert_called_once_with(
            season_nullable="2024-25",
            season_type_nullable="Playoffs",
            player_or_team_abbreviation="T",
        )

    def test_extract_games_applies_rate_limit(self, mock_league_game_finder, mock_time_sleep):
        """Test extract_games applies rate limiting."""
        extract_games(season="2024-25")

        mock_time_sleep.assert_called_once_with(0.6)

    def test_extract_games_returns_team_game_records(
        self, mock_league_game_finder, sample_game_dataframe
    ):
        """Test extract_games returns team-game records (2 per game)."""
        result = extract_games(season="2024-25")

        # Sample data has 4 records (2 games x 2 teams each)
        assert len(result) == 4
        assert "GAME_ID" in result.columns
        assert "TEAM_ID" in result.columns
        assert "MATCHUP" in result.columns


class TestTransformGames:
    """Tests for transform_games function."""

    def test_transform_games_deduplicates(self, sample_game_dataframe):
        """Test transform_games deduplicates team-game records to games."""
        result = transform_games(
            sample_game_dataframe, season="2024-25", season_type="Regular Season"
        )

        # 4 team-game records should become 2 games
        assert len(result) == 2

    def test_transform_games_identifies_home_away(self, sample_game_dataframe):
        """Test transform_games correctly identifies home and away teams."""
        result = transform_games(
            sample_game_dataframe, season="2024-25", season_type="Regular Season"
        )

        # First game: BOS vs. NYK - BOS is home
        game1 = result[result["game_id"] == "0022400001"].iloc[0]
        assert game1["home_team_id"] == 1610612738  # Boston
        assert game1["away_team_id"] == 1610612752  # New York

    def test_transform_games_calculates_scores(self, sample_game_dataframe):
        """Test transform_games extracts scores correctly."""
        result = transform_games(
            sample_game_dataframe, season="2024-25", season_type="Regular Season"
        )

        game1 = result[result["game_id"] == "0022400001"].iloc[0]
        assert game1["home_score"] == 132
        assert game1["away_score"] == 109

    def test_transform_games_determines_winner(self, sample_game_dataframe):
        """Test transform_games determines winner correctly."""
        result = transform_games(
            sample_game_dataframe, season="2024-25", season_type="Regular Season"
        )

        # Game 1: Boston 132, New York 109 -> Boston wins
        game1 = result[result["game_id"] == "0022400001"].iloc[0]
        assert game1["winner_team_id"] == 1610612738

        # Game 2: Philadelphia 117, Milwaukee 118 -> Milwaukee wins
        game2 = result[result["game_id"] == "0022400002"].iloc[0]
        assert game2["winner_team_id"] == 1610612749

    def test_transform_games_sets_season(self, sample_game_dataframe):
        """Test transform_games sets season correctly."""
        result = transform_games(
            sample_game_dataframe, season="2024-25", season_type="Regular Season"
        )

        assert all(result["season"] == 2024)

    def test_transform_games_sets_season_type(self, sample_game_dataframe):
        """Test transform_games sets season type correctly."""
        result = transform_games(sample_game_dataframe, season="2024-25", season_type="Playoffs")

        assert all(result["season_type"] == "Playoffs")

    def test_transform_games_sets_game_date(self, sample_game_dataframe):
        """Test transform_games parses game date."""
        result = transform_games(
            sample_game_dataframe, season="2024-25", season_type="Regular Season"
        )

        assert result.iloc[0]["game_date"].year == 2024
        assert result.iloc[0]["game_date"].month == 10
        assert result.iloc[0]["game_date"].day == 22

    def test_transform_games_determines_status_final(self, sample_game_dataframe):
        """Test transform_games determines final status for completed games."""
        result = transform_games(
            sample_game_dataframe, season="2024-25", season_type="Regular Season"
        )

        assert all(result["status"] == "final")

    def test_transform_games_determines_status_scheduled(self):
        """Test transform_games determines scheduled status for future games."""
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

        result = transform_games(df, season="2024-25", season_type="Regular Season")

        assert all(result["status"] == "scheduled")

    def test_transform_games_handles_unmatched_records(self):
        """Test transform_games handles unmatched home/away records."""
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

        result = transform_games(df, season="2024-25", season_type="Regular Season")

        # Should have 0 games since no matching away record
        assert len(result) == 0

    def test_transform_games_selects_db_columns(self, sample_game_dataframe):
        """Test transform_games selects only database columns."""
        result = transform_games(
            sample_game_dataframe, season="2024-25", season_type="Regular Season"
        )

        expected_columns = [
            "game_id",
            "season",
            "season_type",
            "game_date",
            "home_team_id",
            "away_team_id",
            "home_score",
            "away_score",
            "winner_team_id",
            "status",
        ]

        assert list(result.columns) == expected_columns


class TestLoadGames:
    """Tests for load_games function."""

    def test_load_games_calls_database(self, mock_database):
        """Test load_games calls database execute for each game."""
        df = pd.DataFrame(
            [
                {
                    "game_id": "0022400001",
                    "season": 2024,
                    "season_type": "Regular Season",
                    "game_date": date(2024, 10, 22),
                    "home_team_id": 1610612738,
                    "away_team_id": 1610612752,
                    "home_score": 132,
                    "away_score": 109,
                    "winner_team_id": 1610612738,
                    "status": "final",
                }
            ]
        )

        rows_loaded = load_games(df)

        assert rows_loaded == 1
        mock_database["get_connection"].return_value.execute.assert_called_once()

    def test_load_games_multiple_rows(self, mock_database, sample_transformed_game_data):
        """Test load_games handles multiple games."""
        df = pd.DataFrame(sample_transformed_game_data)

        rows_loaded = load_games(df)

        assert rows_loaded == 2
        assert mock_database["get_connection"].return_value.execute.call_count == 2

    def test_load_games_empty_dataframe(self, mock_database):
        """Test load_games handles empty DataFrame."""
        df = pd.DataFrame()

        rows_loaded = load_games(df)

        assert rows_loaded == 0
        mock_database["get_connection"].return_value.execute.assert_not_called()

    def test_load_games_converts_game_id_to_string(self, mock_database):
        """Test load_games converts game_id to string."""
        df = pd.DataFrame(
            [
                {
                    "game_id": 22400001,  # Numeric game ID
                    "season": 2024,
                    "season_type": "Regular Season",
                    "game_date": date(2024, 10, 22),
                    "home_team_id": 1610612738,
                    "away_team_id": 1610612752,
                    "home_score": 132,
                    "away_score": 109,
                    "winner_team_id": 1610612738,
                    "status": "final",
                }
            ]
        )

        load_games(df)

        # Check that execute was called with string game_id
        call_args = mock_database["get_connection"].return_value.execute.call_args
        params = call_args[0][1]
        assert isinstance(params[0], str)


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
        mock_database["get_connection"].return_value.execute.side_effect = Exception("DB Error")

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
