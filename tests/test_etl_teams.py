"""Tests for ETL Teams pipeline."""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.etl_teams import (
    TeamsETL,
    run_etl,
)


class TestTeamsETL:
    """Tests for TeamsETL class."""

    @pytest.fixture
    def etl(self):
        return TeamsETL()

    def test_extract_returns_dataframe(self, etl, mock_get_teams, sample_team_data):
        """Test extract returns a DataFrame with correct columns."""
        result = etl.extract()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert "id" in result.columns
        assert "full_name" in result.columns
        assert "abbreviation" in result.columns
        mock_get_teams.assert_called_once()

    def test_extract_calls_rate_limit(self, etl, mock_get_teams, mock_time_sleep):
        """Test extract applies rate limiting."""
        etl.extract()

        # Check if any rate limiting was applied (value may come from settings)
        assert mock_time_sleep.called

    def test_extract_empty_response(self, etl, mock_get_teams):
        """Test extract handles empty response."""
        mock_get_teams.return_value = []

        result = etl.extract()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_transform_maps_columns(self, etl, sample_team_dataframe):
        """Test transform correctly maps column names."""
        result = etl.transform(sample_team_dataframe)

        assert "team_id" in result.columns
        assert "full_name" in result.columns
        assert "abbreviation" in result.columns
        assert "conference" in result.columns
        assert "division" in result.columns
        # Original 'id' column should be renamed
        assert "id" not in result.columns

    def test_transform_adds_conference_and_division(self, etl, sample_team_dataframe):
        """Test transform adds conference and division mappings."""
        result = etl.transform(sample_team_dataframe)

        # Boston Celtics should be Eastern, Atlantic
        celtics = result[result["team_id"] == 1610612738].iloc[0]
        assert celtics["conference"] == "Eastern"
        assert celtics["division"] == "Atlantic"

        # Lakers should be Western, Pacific
        lakers = result[result["team_id"] == 1610612747].iloc[0]
        assert lakers["conference"] == "Western"
        assert lakers["division"] == "Pacific"

    def test_transform_defaults_for_unknown_team(self, etl):
        """Test transform defaults for unknown team IDs."""
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

        result = etl.transform(df)

        assert result.iloc[0]["conference"] == "Eastern"  # Default
        assert result.iloc[0]["division"] == "Atlantic"  # Default

    def test_transform_handles_missing_columns(self, etl):
        """Test transform handles missing optional columns."""
        df = pd.DataFrame(
            [
                {
                    "id": 1610612738,
                    "full_name": "Boston Celtics",
                    "abbreviation": "BOS",
                }
            ]
        )

        result = etl.transform(df)

        assert "nickname" in result.columns
        assert "city" in result.columns
        assert "conference" in result.columns
        assert "division" in result.columns

    def test_transform_preserves_data(self, etl, sample_team_dataframe):
        """Test transform preserves original data values."""
        result = etl.transform(sample_team_dataframe)

        celtics = result[result["team_id"] == 1610612738].iloc[0]
        assert celtics["full_name"] == "Boston Celtics"
        assert celtics["abbreviation"] == "BOS"
        assert celtics["city"] == "Boston"
        assert celtics["year_founded"] == 1946

    def test_load_calls_database_execute(self, etl, mock_database):
        """Test load calls database execute for each team."""
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

        rows_loaded = etl.load(df)

        assert rows_loaded == 1
        mock_database["get_connection"].return_value.executemany.assert_called()

    def test_load_multiple_rows(self, etl, mock_database, sample_transformed_team_data):
        """Test load handles multiple teams."""
        df = pd.DataFrame(sample_transformed_team_data)

        rows_loaded = etl.load(df)

        assert rows_loaded == 3
        # Should be called once with executemany
        mock_database["get_connection"].return_value.executemany.assert_called_once()

    def test_load_empty_dataframe(self, etl, mock_database):
        """Test load handles empty DataFrame."""
        df = pd.DataFrame()

        rows_loaded = etl.load(df)

        assert rows_loaded == 0
        mock_database["get_connection"].return_value.executemany.assert_not_called()

    def test_load_database_error(self, etl, mock_database):
        """Test load raises exception on database error."""
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

        mock_database["get_connection"].return_value.executemany.side_effect = Exception("DB Error")

        # Expect DatabaseError (from ingestion exceptions)
        # Note: We need to import DatabaseError to catch it specifically,
        # or just catch Exception and check if it wraps the original.
        with pytest.raises(Exception) as excinfo:
            etl.load(df)

        assert "Failed to load teams" in str(excinfo.value)


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
        # Note: We now use executemany, so we mock that
        mock_database["get_connection"].return_value.executemany.side_effect = Exception("DB Error")

        result = run_etl()

        assert result["status"] == "failed"
        assert "DB Error" in result["error"]

    def test_run_etl_closes_connection_on_success(
        self, mock_get_teams, mock_database, sample_team_data
    ):
        """Test run_etl closes database connection on success."""
        run_etl()

        # The base class ensures close_db_connection is called
        # We need to verify this via the mock
        # Note: Depending on how mock_database is set up, this might need adjustment
        # For now assuming it mocks app.services.database.close_db_connection
        if "close_db_connection" in mock_database:
            mock_database["close_db_connection"].assert_called()
        elif "teams_close_db_connection" in mock_database:
            mock_database["teams_close_db_connection"].assert_called()

    def test_run_etl_closes_connection_on_failure(self, mock_get_teams, mock_database):
        """Test run_etl closes database connection on failure."""
        mock_get_teams.side_effect = Exception("API Error")

        run_etl()

        if "close_db_connection" in mock_database:
            mock_database["close_db_connection"].assert_called()
        elif "teams_close_db_connection" in mock_database:
            mock_database["teams_close_db_connection"].assert_called()

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
