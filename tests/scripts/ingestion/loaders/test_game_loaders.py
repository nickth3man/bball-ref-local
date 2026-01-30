"""Tests for GamesLoader."""


import pandas as pd
import pytest

from scripts.ingestion.exceptions import ValidationError
from scripts.ingestion.loaders.game_loaders import GamesLoader


class TestGamesLoader:
    """Tests for GamesLoader class."""

    @pytest.fixture
    def mock_csv_dir(self, tmp_path):
        """Fixture for CSV directory."""
        d = tmp_path / "csv"
        d.mkdir()
        return d

    @pytest.fixture
    def games_file(self, mock_csv_dir):
        """Fixture for games CSV file."""
        f = mock_csv_dir / "Games.csv"
        df = pd.DataFrame(
            {
                "GAME_ID": ["001", "002"],
                "GAME_DATE_EST": ["2023-10-24T00:00:00", "2023-10-25T00:00:00"],
                "GAME_STATUS_TEXT": ["Final", "Final"],
                "HOME_TEAM_ID": [1, 2],
                "VISITOR_TEAM_ID": [2, 1],
                "SEASON": [2023, 2023],
                "TEAM_ID_home": [1, 2],
                "PTS_home": [100, 110],
                "FG_PCT_home": [0.5, 0.45],
            }
        )
        df.to_csv(f, index=False)
        return f

    def test_initialization(self, mock_csv_dir):
        """Test loader initialization."""
        loader = GamesLoader(
            file_path=mock_csv_dir / "Games.csv",
            table_name="games_historical",
            csv_dir=mock_csv_dir,
        )
        assert loader.games_file == mock_csv_dir / "Games.csv"

    def test_load(self, mock_csv_dir, games_file):
        """Test loading games data."""
        loader = GamesLoader(
            file_path=games_file, table_name="games_historical", csv_dir=mock_csv_dir
        )

        df = loader.load()

        assert len(df) == 2
        assert "game_id" in df.columns
        assert "home_team_id" in df.columns

    def test_transform_dates(self, mock_csv_dir):
        """Test date transformation."""
        f = mock_csv_dir / "Games.csv"
        df = pd.DataFrame(
            {
                "GAME_DATE_TIME_EST": ["2023-10-24T12:00:00"],
                "GAME_ID": ["1"],
                "HOME_TEAM_ID": [1],
            }
        )
        df.to_csv(f, index=False)

        loader = GamesLoader(file_path=f, table_name="test", csv_dir=mock_csv_dir)
        # Manually call transform since we want to test that specific logic
        # But load() calls transform() internally, so we can check the result of load()
        # Note: GamesLoader.load() calls _load_csv which calls _clean_column_names
        # then calls transform().

        # We need to ensure transform handles the snake_case conversion done by _clean_column_names
        # The GamesLoader.transform implementation looks for "game_date_time_est" (snake case)

        result = loader.load()
        assert "game_date" in result.columns
        # pd.to_datetime returns Timestamp, .dt.date returns python date object
        assert str(result["game_date"].iloc[0]) == "2023-10-24"

    def test_validate_success(self, mock_csv_dir):
        """Test successful validation."""
        loader = GamesLoader(
            file_path=mock_csv_dir / "Games.csv",
            table_name="test",
            csv_dir=mock_csv_dir,
        )
        df = pd.DataFrame({"game_id": ["1"], "game_date": ["2023-01-01"]})
        assert loader.validate(df) is True

    def test_validate_missing_columns(self, mock_csv_dir):
        """Test validation with missing columns."""
        loader = GamesLoader(
            file_path=mock_csv_dir / "Games.csv",
            table_name="test",
            csv_dir=mock_csv_dir,
        )
        df = pd.DataFrame({"other": [1]})
        with pytest.raises(ValidationError, match="Missing required columns"):
            loader.validate(df)
