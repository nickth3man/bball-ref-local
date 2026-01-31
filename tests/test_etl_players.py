"""Tests for ETL Players pipeline."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.etl_players import (
    extract_players,
    load_players,
    parse_birth_date,
    parse_height,
    run_etl,
    transform_players,
)


class TestParseHeight:
    """Tests for parse_height helper function."""

    def test_parse_height_valid(self):
        """Test parsing valid height string."""
        assert parse_height("6-9") == 81  # 6*12 + 9 = 81
        assert parse_height("7-0") == 84
        assert parse_height("5-11") == 71

    def test_parse_height_none(self):
        """Test parsing None returns None."""
        assert parse_height(None) is None
        assert parse_height("") is None

    def test_parse_height_invalid(self):
        """Test parsing invalid height strings."""
        assert parse_height("invalid") is None
        assert parse_height("6") is None  # Missing inches


class TestParseBirthDate:
    """Tests for parse_birth_date helper function."""

    def test_parse_birth_date_iso_format(self):
        """Test parsing ISO format date."""
        result = parse_birth_date("1984-12-30")
        assert result.year == 1984
        assert result.month == 12
        assert result.day == 30

    def test_parse_birth_date_us_format(self):
        """Test parsing US format date."""
        result = parse_birth_date("12/30/1984")
        assert result.year == 1984
        assert result.month == 12
        assert result.day == 30

    def test_parse_birth_date_none(self):
        """Test parsing None returns None."""
        assert parse_birth_date(None) is None
        assert parse_birth_date("") is None

    def test_parse_birth_date_invalid(self):
        """Test parsing invalid date returns None."""
        assert parse_birth_date("not-a-date") is None


class TestExtractPlayers:
    """Tests for extract_players function."""

    def test_extract_players_active_only(self, mock_common_all_players):
        """Test extract_players with active_only=True."""
        result = extract_players(active_only=True)

        mock_common_all_players.assert_called_once_with(is_only_current_season=1)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    def test_extract_players_all_players(self, mock_common_all_players):
        """Test extract_players with active_only=False."""
        result = extract_players(active_only=False)

        mock_common_all_players.assert_called_once_with(is_only_current_season=0)
        assert isinstance(result, pd.DataFrame)

    def test_extract_players_applies_rate_limit(self, mock_common_all_players, mock_time_sleep):
        """Test extract_players applies rate limiting."""
        extract_players(active_only=True)

        mock_time_sleep.assert_called_once_with(0.6)

    def test_extract_players_returns_correct_columns(self, mock_common_all_players):
        """Test extract_players returns DataFrame with expected columns."""
        result = extract_players(active_only=True)

        assert "PERSON_ID" in result.columns
        assert "DISPLAY_FIRST_LAST" in result.columns
        assert "TEAM_ID" in result.columns


class TestTransformPlayers:
    """Tests for transform_players function."""

    def test_transform_players_maps_columns(self, sample_player_dataframe):
        """Test transform_players correctly maps columns."""
        result = transform_players(sample_player_dataframe)

        assert "player_id" in result.columns
        assert "first_name" in result.columns
        assert "last_name" in result.columns
        assert "team_id" in result.columns

    def test_transform_players_extracts_names(self, sample_player_dataframe):
        """Test transform_players extracts first and last names."""
        result = transform_players(sample_player_dataframe)

        lebron = result[result["player_id"] == 2544].iloc[0]
        assert lebron["first_name"] == "LeBron"
        assert lebron["last_name"] == "James"

    def test_transform_players_handles_position_mapping(self, sample_player_with_all_fields_df):
        """Test transform_players maps positions correctly."""
        result = transform_players(sample_player_with_all_fields_df)

        # "F" should map to "SF"
        assert result.iloc[0]["position"] == "SF"

    def test_transform_players_parses_height(self, sample_player_with_all_fields_df):
        """Test transform_players parses height."""
        result = transform_players(sample_player_with_all_fields_df)

        # "6-9" = 81 inches
        assert result.iloc[0]["height"] == 81

    def test_transform_players_parses_weight(self, sample_player_with_all_fields_df):
        """Test transform_players parses weight."""
        result = transform_players(sample_player_with_all_fields_df)

        assert result.iloc[0]["weight"] == 250

    def test_transform_players_parses_birth_date(self, sample_player_with_all_fields_df):
        """Test transform_players parses birth date."""
        result = transform_players(sample_player_with_all_fields_df)

        birth_date = result.iloc[0]["birth_date"]
        assert birth_date.year == 1984
        assert birth_date.month == 12
        assert birth_date.day == 30

    def test_transform_players_parses_draft_info(self, sample_player_with_all_fields_df):
        """Test transform_players parses draft information."""
        result = transform_players(sample_player_with_all_fields_df)

        assert result.iloc[0]["draft_year"] == 2003
        assert result.iloc[0]["draft_round"] == 1
        assert result.iloc[0]["draft_number"] == 1

    def test_transform_players_parses_jersey_number(self, sample_player_with_all_fields_df):
        """Test transform_players parses jersey number."""
        result = transform_players(sample_player_with_all_fields_df)

        assert result.iloc[0]["jersey_number"] == 23

    def test_transform_players_drops_rows_without_player_id(self, sample_player_dataframe):
        """Test transform_players drops rows with missing player_id."""
        # Add a row with NaN player_id
        df_with_nan = pd.concat(
            [
                sample_player_dataframe,
                pd.DataFrame([{"PERSON_ID": None, "DISPLAY_FIRST_LAST": "Invalid Player"}]),
            ],
            ignore_index=True,
        )

        result = transform_players(df_with_nan)

        assert len(result) == 3  # Original 3, NaN row dropped

    def test_transform_players_ensures_numeric_team_id(self, sample_player_dataframe):
        """Test transform_players ensures team_id is numeric."""
        result = transform_players(sample_player_dataframe)

        assert result["team_id"].dtype in ["int64", "int32"]
        assert all(result["team_id"] > 0)

    def test_transform_players_position_default(self):
        """Test transform_players defaults position when not provided."""
        df = pd.DataFrame(
            [
                {
                    "PERSON_ID": 2544,
                    "DISPLAY_FIRST_LAST": "LeBron James",
                    "TEAM_ID": 1610612747,
                }
            ]
        )

        result = transform_players(df)

        assert result.iloc[0]["position"] == "PG"


class TestLoadPlayers:
    """Tests for load_players function."""

    def test_load_players_calls_database(self, mock_database):
        """Test load_players calls database executemany."""
        df = pd.DataFrame(
            [
                {
                    "player_id": 2544,
                    "first_name": "LeBron",
                    "last_name": "James",
                    "team_id": 1610612747,
                    "position": "SF",
                    "jersey_number": 23,
                    "height": 81,
                    "weight": 250,
                    "birth_date": pd.to_datetime("1984-12-30").date(),
                    "country": "USA",
                    "draft_year": 2003,
                    "draft_round": 1,
                    "draft_number": 1,
                }
            ]
        )

        rows_loaded = load_players(df, batch_size=500)

        assert rows_loaded == 1
        mock_database["get_connection"].return_value.executemany.assert_called_once()

    def test_load_players_batch_processing(self, mock_database):
        """Test load_players processes in batches."""
        # Create 10 players
        players = [
            {
                "player_id": 2544 + i,
                "first_name": f"Player{i}",
                "last_name": "Test",
                "team_id": 1610612747,
                "position": "PG",
            }
            for i in range(10)
        ]
        df = pd.DataFrame(players)

        rows_loaded = load_players(df, batch_size=3)

        assert rows_loaded == 10
        # Should be called 4 times (3+3+3+1 batches)
        assert mock_database["get_connection"].return_value.executemany.call_count == 4

    def test_load_players_empty_dataframe(self, mock_database):
        """Test load_players handles empty DataFrame."""
        df = pd.DataFrame()

        rows_loaded = load_players(df)

        assert rows_loaded == 0
        mock_database["get_connection"].return_value.executemany.assert_not_called()

    def test_load_players_database_error(self, mock_database):
        """Test load_players raises exception on database error."""
        df = pd.DataFrame(
            [
                {
                    "player_id": 2544,
                    "first_name": "LeBron",
                    "last_name": "James",
                    "team_id": 1610612747,
                    "position": "SF",
                }
            ]
        )

        mock_database["get_connection"].return_value.executemany.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            load_players(df)


class TestRunETL:
    """Tests for run_etl function."""

    def test_run_etl_success(self, mock_common_all_players, mock_database):
        """Test run_etl successful execution."""
        result = run_etl(active_only=True)

        assert result["status"] == "success"
        assert result["extracted"] == 3
        assert result["loaded"] == 3
        assert result["error"] is None

    def test_run_etl_with_active_only_false(self, mock_common_all_players, mock_database):
        """Test run_etl with active_only=False."""
        result = run_etl(active_only=False)

        mock_common_all_players.assert_called_once_with(is_only_current_season=0)
        assert result["status"] == "success"

    def test_run_etl_extract_failure(self, mock_common_all_players, mock_database):
        """Test run_etl handles extract failure."""
        mock_common_all_players.side_effect = Exception("API Timeout")

        result = run_etl(active_only=True)

        assert result["status"] == "failed"
        assert "API Timeout" in result["error"]

    def test_run_etl_load_failure(self, mock_common_all_players, mock_database):
        """Test run_etl handles load failure."""
        mock_database["get_connection"].return_value.executemany.side_effect = Exception("DB Error")

        result = run_etl(active_only=True)

        assert result["status"] == "failed"
        assert "DB Error" in result["error"]

    def test_run_etl_closes_connection(self, mock_common_all_players, mock_database):
        """Test run_etl closes database connection."""
        run_etl(active_only=True)

        mock_database["players_close_db_connection"].assert_called_once()

    def test_run_etl_custom_batch_size(self, mock_common_all_players, mock_database):
        """Test run_etl with custom batch size."""
        result = run_etl(active_only=True, batch_size=100)

        assert result["status"] == "success"

    def test_run_etl_empty_response(self, mock_common_all_players, mock_database):
        """Test run_etl handles empty API response."""
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [pd.DataFrame()]
        mock_common_all_players.return_value = mock_instance

        result = run_etl(active_only=True)

        assert result["status"] == "success"
        assert result["extracted"] == 0
        assert result["loaded"] == 0
