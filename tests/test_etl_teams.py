"""Tests for ETL Teams pipeline."""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.etl_teams import (
    extract_teams,
    load_teams,
    run_etl,
    transform_teams,
)


class TestExtractTeams:
    """Tests for extract_teams function."""

    def test_extract_teams_returns_dataframe(self, mock_get_teams, sample_team_data):
        """Test extract_teams returns a DataFrame with correct columns."""
        result = extract_teams()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert "id" in result.columns
        assert "full_name" in result.columns
        assert "abbreviation" in result.columns
        mock_get_teams.assert_called_once()

    def test_extract_teams_calls_rate_limit(self, mock_get_teams, mock_time_sleep):
        """Test extract_teams applies rate limiting."""
        extract_teams()

        mock_time_sleep.assert_called_once_with(0.6)

    def test_extract_teams_empty_response(self, mock_get_teams):
        """Test extract_teams handles empty response."""
        mock_get_teams.return_value = []

        result = extract_teams()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestTransformTeams:
    """Tests for transform_teams function."""

    def test_transform_teams_maps_columns(self, sample_team_dataframe):
        """Test transform_teams correctly maps column names."""
        result = transform_teams(sample_team_dataframe)

        assert "team_id" in result.columns
        assert "full_name" in result.columns
        assert "abbreviation" in result.columns
        assert "conference" in result.columns
        assert "division" in result.columns
        # Original 'id' column should be renamed
        assert "id" not in result.columns

    def test_transform_teams_adds_conference_and_division(self, sample_team_dataframe):
        """Test transform_teams adds conference and division mappings."""
        result = transform_teams(sample_team_dataframe)

        # Boston Celtics should be Eastern, Atlantic
        celtics = result[result["team_id"] == 1610612738].iloc[0]
        assert celtics["conference"] == "Eastern"
        assert celtics["division"] == "Atlantic"

        # Lakers should be Western, Pacific
        lakers = result[result["team_id"] == 1610612747].iloc[0]
        assert lakers["conference"] == "Western"
        assert lakers["division"] == "Pacific"

    def test_transform_teams_defaults_for_unknown_team(self):
        """Test transform_teams defaults for unknown team IDs."""
        df = pd.DataFrame(
            [
                {
                    "id": 999999,  # Unknown team ID
                    "full_name": "Unknown Team",
                    "abbreviation": "UNK",
                    "nickname": "Unknown",
                    "city": "Unknown",
                    "state": "Unknown",
                    "year_founded": 2024,
                }
            ]
        )

        result = transform_teams(df)

        assert result.iloc[0]["conference"] == "Eastern"  # Default
        assert result.iloc[0]["division"] == "Atlantic"  # Default

    def test_transform_teams_handles_missing_columns(self):
        """Test transform_teams handles missing optional columns."""
        df = pd.DataFrame(
            [
                {
                    "id": 1610612738,
                    "full_name": "Boston Celtics",
                    "abbreviation": "BOS",
                }
            ]
        )

        result = transform_teams(df)

        assert "nickname" in result.columns
        assert "city" in result.columns
        assert "conference" in result.columns
        assert "division" in result.columns

    def test_transform_teams_preserves_data(self, sample_team_dataframe):
        """Test transform_teams preserves original data values."""
        result = transform_teams(sample_team_dataframe)

        celtics = result[result["team_id"] == 1610612738].iloc[0]
        assert celtics["full_name"] == "Boston Celtics"
        assert celtics["abbreviation"] == "BOS"
        assert celtics["city"] == "Boston"
        assert celtics["year_founded"] == 1946


class TestLoadTeams:
    """Tests for load_teams function."""

    def test_load_teams_calls_database_execute(self, mock_database):
        """Test load_teams calls database execute for each team."""
        df = pd.DataFrame(
            [
                {
                    "team_id": 1610612738,
                    "full_name": "Boston Celtics",
                    "abbreviation": "BOS",
                    "nickname": "Celtics",
                    "city": "Boston",
                    "state": "Massachusetts",
                    "year_founded": 1946,
                    "conference": "Eastern",
                    "division": "Atlantic",
                }
            ]
        )

        rows_loaded = load_teams(df)

        assert rows_loaded == 1
        mock_database["get_connection"].return_value.execute.assert_called()

    def test_load_teams_multiple_rows(self, mock_database, sample_transformed_team_data):
        """Test load_teams handles multiple teams."""
        df = pd.DataFrame(sample_transformed_team_data)

        rows_loaded = load_teams(df)

        assert rows_loaded == 3
        assert mock_database["get_connection"].return_value.execute.call_count == 3

    def test_load_teams_empty_dataframe(self, mock_database):
        """Test load_teams handles empty DataFrame."""
        df = pd.DataFrame()

        rows_loaded = load_teams(df)

        assert rows_loaded == 0
        mock_database["get_connection"].return_value.execute.assert_not_called()

    def test_load_teams_database_error(self, mock_database):
        """Test load_teams raises exception on database error."""
        df = pd.DataFrame(
            [
                {
                    "team_id": 1610612738,
                    "full_name": "Boston Celtics",
                    "abbreviation": "BOS",
                    "conference": "Eastern",
                    "division": "Atlantic",
                }
            ]
        )

        mock_database["get_connection"].return_value.execute.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            load_teams(df)


class TestRunETL:
    """Tests for run_etl function."""

    def test_run_etl_success(self, mock_get_teams, mock_database, sample_team_data):
        """Test run_etl successful execution."""
        result = run_etl()

        assert result["status"] == "success"
        assert result["extracted"] == 3
        assert result["loaded"] == 3
        assert result["error"] is None

    def test_run_etl_extract_failure(self, mock_get_teams, mock_database):
        """Test run_etl handles extract failure."""
        mock_get_teams.side_effect = Exception("API Error")

        result = run_etl()

        assert result["status"] == "failed"
        assert "API Error" in result["error"]
        assert result["extracted"] == 0

    def test_run_etl_load_failure(self, mock_get_teams, mock_database, sample_team_data):
        """Test run_etl handles load failure."""
        mock_database["get_connection"].return_value.execute.side_effect = Exception("DB Error")

        result = run_etl()

        assert result["status"] == "failed"
        assert "DB Error" in result["error"]

    def test_run_etl_closes_connection_on_success(
        self, mock_get_teams, mock_database, sample_team_data
    ):
        """Test run_etl closes database connection on success."""
        run_etl()

        mock_database["teams_close_db_connection"].assert_called_once()

    def test_run_etl_closes_connection_on_failure(self, mock_get_teams, mock_database):
        """Test run_etl closes database connection on failure."""
        mock_get_teams.side_effect = Exception("API Error")

        run_etl()

        mock_database["teams_close_db_connection"].assert_called_once()

    def test_run_etl_result_structure(self, mock_get_teams, mock_database, sample_team_data):
        """Test run_etl returns properly structured result."""
        result = run_etl()

        assert "extracted" in result
        assert "loaded" in result
        assert "status" in result
        assert "error" in result
        assert isinstance(result["extracted"], int)
        assert isinstance(result["loaded"], int)
        assert result["status"] in ["success", "failed"]
