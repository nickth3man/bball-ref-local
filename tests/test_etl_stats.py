"""Tests for ETL Stats pipeline."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.etl_stats import (
    extract_player_stats,
    generate_stat_id,
    load_player_stats,
    parse_minutes_played,
    run_etl,
    transform_player_stats,
)


class TestGenerateStatId:
    """Tests for generate_stat_id helper function."""

    def test_generate_stat_id_deterministic(self):
        """Test generate_stat_id returns deterministic value."""
        stat_id_1 = generate_stat_id(2544, "0022400001")
        stat_id_2 = generate_stat_id(2544, "0022400001")

        assert stat_id_1 == stat_id_2
        assert isinstance(stat_id_1, int)

    def test_generate_stat_id_different_inputs(self):
        """Test generate_stat_id produces different values for different inputs."""
        stat_id_1 = generate_stat_id(2544, "0022400001")
        stat_id_2 = generate_stat_id(2544, "0022400002")
        stat_id_3 = generate_stat_id(201939, "0022400001")

        assert stat_id_1 != stat_id_2
        assert stat_id_1 != stat_id_3
        assert stat_id_2 != stat_id_3

    def test_generate_stat_id_positive(self):
        """Test generate_stat_id always returns positive integer."""
        stat_id = generate_stat_id(2544, "0022400001")

        assert stat_id > 0


class TestParseMinutesPlayed:
    """Tests for parse_minutes_played helper function."""

    def test_parse_minutes_decimal(self):
        """Test parsing decimal minutes."""
        assert parse_minutes_played(34.5) == 34.5
        assert parse_minutes_played(36.0) == 36.0

    def test_parse_minutes_minutes_seconds(self):
        """Test parsing minutes:seconds format."""
        assert parse_minutes_played("35:42") == 35.7  # 35 + 42/60
        assert parse_minutes_played("40:00") == 40.0
        assert parse_minutes_played("25:30") == 25.5

    def test_parse_minutes_string_number(self):
        """Test parsing string number."""
        assert parse_minutes_played("34.5") == 34.5
        assert parse_minutes_played("36") == 36.0

    def test_parse_minutes_none(self):
        """Test parsing None returns None."""
        assert parse_minutes_played(None) is None
        assert parse_minutes_played("") is None

    def test_parse_minutes_invalid(self):
        """Test parsing invalid minutes returns None."""
        assert parse_minutes_played("invalid") is None
        assert parse_minutes_played("abc:def") is None

    def test_parse_minutes_negative(self):
        """Test parsing negative returns None for numeric, negative float for string."""
        assert parse_minutes_played(-5) is None
        # String "-10" gets converted to -10.0 (function doesn't validate negative strings)
        assert parse_minutes_played("-10") == -10.0


class TestExtractPlayerStats:
    """Tests for extract_player_stats function."""

    def test_extract_player_stats_with_season(self, mock_player_game_logs):
        """Test extract_player_stats with specific season."""
        result = extract_player_stats(season="2024-25", season_type="Regular Season")

        mock_player_game_logs.assert_called_once_with(
            season_nullable="2024-25",
            season_type_nullable="Regular Season",
        )
        assert isinstance(result, pd.DataFrame)

    def test_extract_player_stats_playoffs(self, mock_player_game_logs):
        """Test extract_player_stats with playoffs."""
        result = extract_player_stats(season="2024-25", season_type="Playoffs")

        mock_player_game_logs.assert_called_once_with(
            season_nullable="2024-25",
            season_type_nullable="Playoffs",
        )

    def test_extract_player_stats_applies_rate_limit(self, mock_player_game_logs, mock_time_sleep):
        """Test extract_player_stats applies rate limiting."""
        extract_player_stats(season="2024-25")

        mock_time_sleep.assert_called_once_with(0.6)

    def test_extract_player_stats_returns_data(
        self, mock_player_game_logs, sample_player_stats_dataframe
    ):
        """Test extract_player_stats returns player stats data."""
        result = extract_player_stats(season="2024-25")

        assert len(result) == 3
        assert "PLAYER_ID" in result.columns
        assert "GAME_ID" in result.columns
        assert "PTS" in result.columns

    def test_extract_player_stats_empty_response(self, mock_player_game_logs):
        """Test extract_player_stats handles empty response."""
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [pd.DataFrame()]
        mock_player_game_logs.return_value = mock_instance

        result = extract_player_stats(season="2024-25")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_extract_player_stats_error_handling(self, mock_player_game_logs):
        """Test extract_player_stats handles API errors."""
        mock_player_game_logs.side_effect = Exception("API Error")

        result = extract_player_stats(season="2024-25")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestTransformPlayerStats:
    """Tests for transform_player_stats function."""

    def test_transform_player_stats_maps_columns(self, sample_player_stats_dataframe):
        """Test transform_player_stats correctly maps columns."""
        result = transform_player_stats(sample_player_stats_dataframe)

        assert "player_id" in result.columns
        assert "team_id" in result.columns
        assert "game_id" in result.columns
        assert "points" in result.columns
        assert "assists" in result.columns
        assert "rebounds_offensive" in result.columns
        assert "rebounds_defensive" in result.columns

    def test_transform_player_stats_generates_stat_id(self, sample_player_stats_dataframe):
        """Test transform_player_stats generates stat_id."""
        result = transform_player_stats(sample_player_stats_dataframe)

        assert "stat_id" in result.columns
        assert all(result["stat_id"] > 0)
        # Same player + game should generate same stat_id
        lebron_stats = result[result["player_id"] == 2544]
        assert lebron_stats["stat_id"].nunique() == 2  # 2 different games

    def test_transform_player_stats_parses_minutes(self, sample_player_stats_dataframe):
        """Test transform_player_stats parses minutes played."""
        result = transform_player_stats(sample_player_stats_dataframe)

        assert "minutes_played" in result.columns
        # First row has MIN = 34.5
        assert result.iloc[0]["minutes_played"] == 34.5

    def test_transform_player_stats_numeric_columns(self, sample_player_stats_dataframe):
        """Test transform_player_stats converts stats to numeric."""
        result = transform_player_stats(sample_player_stats_dataframe)

        numeric_cols = [
            "points",
            "fg_made",
            "fg_attempted",
            "fg3_made",
            "fg3_attempted",
            "ft_made",
            "ft_attempted",
            "rebounds_offensive",
            "rebounds_defensive",
            "assists",
            "steals",
            "blocks",
            "turnovers",
            "personal_fouls",
        ]

        for col in numeric_cols:
            assert result[col].dtype in ["int64", "int32"], f"{col} should be integer"

    def test_transform_player_stats_preserves_values(self, sample_player_stats_dataframe):
        """Test transform_player_stats preserves original values."""
        result = transform_player_stats(sample_player_stats_dataframe)

        lebron_game1 = result[
            (result["player_id"] == 2544) & (result["game_id"] == "0022400001")
        ].iloc[0]

        assert lebron_game1["points"] == 25
        assert lebron_game1["fg_made"] == 10
        assert lebron_game1["fg_attempted"] == 18
        assert lebron_game1["assists"] == 8

    def test_transform_player_stats_handles_missing_columns(self):
        """Test transform_player_stats handles missing columns gracefully."""
        df = pd.DataFrame(
            {
                "PLAYER_ID": [2544],
                "GAME_ID": ["0022400001"],
                "TEAM_ID": [1610612747],
            }
        )

        result = transform_player_stats(df)

        # Should still work with default values
        assert "points" in result.columns
        assert "assists" in result.columns
        assert result.iloc[0]["points"] == 0  # Default value

    def test_transform_player_stats_removes_duplicates(self):
        """Test transform_player_stats removes duplicate stat records."""
        # Create duplicate data
        df = pd.DataFrame(
            {
                "PLAYER_ID": [2544, 2544],  # Same player
                "GAME_ID": ["0022400001", "0022400001"],  # Same game
                "TEAM_ID": [1610612747, 1610612747],
                "PTS": [25, 25],
            }
        )

        result = transform_player_stats(df)

        # Should deduplicate to 1 record
        assert len(result) == 1


class TestLoadPlayerStats:
    """Tests for load_player_stats function."""

    def test_load_player_stats_calls_database(self, mock_database):
        """Test load_player_stats calls database execute for each record."""
        df = pd.DataFrame(
            [
                {
                    "stat_id": 12345,
                    "game_id": "0022400001",
                    "player_id": 2544,
                    "team_id": 1610612747,
                    "minutes_played": 34.5,
                    "points": 25,
                    "rebounds_offensive": 1,
                    "rebounds_defensive": 8,
                    "assists": 8,
                    "steals": 1,
                    "blocks": 0,
                    "turnovers": 4,
                    "personal_fouls": 2,
                    "fg_made": 10,
                    "fg_attempted": 18,
                    "fg3_made": 3,
                    "fg3_attempted": 7,
                    "ft_made": 2,
                    "ft_attempted": 3,
                }
            ]
        )

        rows_loaded = load_player_stats(df)

        assert rows_loaded == 1
        mock_database["get_connection"].return_value.execute.assert_called_once()

    def test_load_player_stats_batch_processing(self, mock_database):
        """Test load_player_stats processes in batches."""
        # Create 5 stat records
        stats = [
            {
                "stat_id": 1000 + i,
                "game_id": f"002240000{i + 1}",
                "player_id": 2544,
                "team_id": 1610612747,
                "points": 20 + i,
                "minutes_played": 30.0,
            }
            for i in range(5)
        ]
        # Add required columns with defaults
        for stat in stats:
            stat.update(
                {
                    "rebounds_offensive": 0,
                    "rebounds_defensive": 0,
                    "assists": 0,
                    "steals": 0,
                    "blocks": 0,
                    "turnovers": 0,
                    "personal_fouls": 0,
                    "fg_made": 0,
                    "fg_attempted": 0,
                    "fg3_made": 0,
                    "fg3_attempted": 0,
                    "ft_made": 0,
                    "ft_attempted": 0,
                }
            )

        df = pd.DataFrame(stats)

        rows_loaded = load_player_stats(df, batch_size=2)

        assert rows_loaded == 5
        # Should be called 5 times (once per row, no executemany)
        assert mock_database["get_connection"].return_value.execute.call_count == 5

    def test_load_player_stats_empty_dataframe(self, mock_database):
        """Test load_player_stats handles empty DataFrame."""
        df = pd.DataFrame()

        rows_loaded = load_player_stats(df)

        assert rows_loaded == 0
        mock_database["get_connection"].return_value.execute.assert_not_called()

    def test_load_player_stats_converts_types(self, mock_database):
        """Test load_player_stats converts data types correctly."""
        df = pd.DataFrame(
            [
                {
                    "stat_id": 12345.7,  # Float stat_id
                    "game_id": "0022400001",
                    "player_id": 2544,
                    "team_id": 1610612747,
                    "minutes_played": 34.5,
                    "points": 25,
                    "rebounds_offensive": 1,
                    "rebounds_defensive": 8,
                    "assists": 8,
                    "steals": 1,
                    "blocks": 0,
                    "turnovers": 4,
                    "personal_fouls": 2,
                    "fg_made": 10,
                    "fg_attempted": 18,
                    "fg3_made": 3,
                    "fg3_attempted": 7,
                    "ft_made": 2,
                    "ft_attempted": 3,
                }
            ]
        )

        load_player_stats(df)

        # Check that execute was called with correct types
        call_args = mock_database["get_connection"].return_value.execute.call_args
        params = call_args[0][1]
        assert isinstance(params[0], int)  # stat_id
        assert isinstance(params[1], str)  # game_id
        assert isinstance(params[2], int)  # player_id


class TestRunETL:
    """Tests for run_etl function."""

    def test_run_etl_success(self, mock_player_game_logs, mock_database):
        """Test run_etl successful execution."""
        result = run_etl(season="2024-25", season_type="Regular Season")

        assert result["status"] == "success"
        assert result["extracted"] == 3
        assert result["loaded"] == 3
        assert result["season"] == "2024-25"
        assert result["season_type"] == "Regular Season"
        assert result["error"] is None

    def test_run_etl_uses_current_season(self, mock_player_game_logs, mock_database):
        """Test run_etl uses current season when not specified."""
        with patch("scripts.etl_stats.get_current_season") as mock_get_season:
            mock_get_season.return_value = "2024-25"
            result = run_etl()

        assert result["season"] == "2024-25"

    def test_run_etl_empty_response(self, mock_player_game_logs, mock_database):
        """Test run_etl handles empty API response."""
        mock_instance = MagicMock()
        mock_instance.get_data_frames.return_value = [pd.DataFrame()]
        mock_player_game_logs.return_value = mock_instance

        result = run_etl(season="2024-25")

        assert result["status"] == "success"
        assert result["extracted"] == 0
        assert result["loaded"] == 0

    def test_run_etl_extract_failure(self, mock_player_game_logs, mock_database):
        """Test run_etl handles extract failure."""
        mock_player_game_logs.side_effect = Exception("API Error")

        result = run_etl(season="2024-25")

        # Should handle error gracefully (returns empty DataFrame)
        assert result["status"] == "success"
        assert result["extracted"] == 0
        assert result["loaded"] == 0

    def test_run_etl_load_failure(self, mock_player_game_logs, mock_database):
        """Test run_etl handles load failure."""
        mock_database["get_connection"].return_value.execute.side_effect = Exception("DB Error")

        result = run_etl(season="2024-25")

        assert result["status"] == "failed"
        assert "DB Error" in result["error"]

    def test_run_etl_closes_connection(self, mock_player_game_logs, mock_database):
        """Test run_etl closes database connection."""
        run_etl(season="2024-25")

        mock_database["stats_close_db_connection"].assert_called_once()

    def test_run_etl_custom_batch_size(self, mock_player_game_logs, mock_database):
        """Test run_etl with custom batch size."""
        result = run_etl(season="2024-25", batch_size=500)

        assert result["status"] == "success"
