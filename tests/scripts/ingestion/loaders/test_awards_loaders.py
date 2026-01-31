"""Tests for awards data loaders."""

import pandas as pd
import pytest

from scripts.ingestion.exceptions import ValidationError
from scripts.ingestion.loaders.awards_loaders import AwardsLoader, DraftLoader


class TestAwardsLoader:
    """Tests for AwardsLoader class."""

    @pytest.fixture
    def mock_csv_dir(self, tmp_path):
        """Fixture for CSV directory."""
        d = tmp_path / "csv"
        d.mkdir()
        return d

    @pytest.fixture
    def all_star_file(self, mock_csv_dir):
        """Fixture for all-star selections CSV file."""
        f = mock_csv_dir / "All-Star Selections.csv"
        df = pd.DataFrame({
            "player_id": [2544, 201939],
            "player": ["LeBron James", "Stephen Curry"],
            "season": [2024, 2024],
            "team": ["West", "West"],
        })
        df.to_csv(f, index=False)
        return f

    def test_initialization(self, mock_csv_dir):
        """Test loader initialization."""
        loader = AwardsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="awards",
            award_type="all_star",
            csv_dir=mock_csv_dir,
        )
        assert loader.award_file == mock_csv_dir / "All-Star Selections.csv"
        assert loader.award_type == "all_star"

    def test_initialization_invalid_type(self, mock_csv_dir):
        """Test loader initialization with invalid award type."""
        with pytest.raises(ValueError, match="Invalid award_type"):
            AwardsLoader(
                file_path=mock_csv_dir / "test.csv",
                table_name="awards",
                award_type="invalid",
                csv_dir=mock_csv_dir,
            )

    def test_load(self, mock_csv_dir, all_star_file):
        """Test loading awards data."""
        loader = AwardsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="awards",
            award_type="all_star",
            csv_dir=mock_csv_dir,
        )

        df = loader.load()

        assert len(df) == 2
        assert "player_id" in df.columns
        assert "award_type" in df.columns
        assert df["award_type"].iloc[0] == "all_star"

    def test_transform(self, mock_csv_dir, all_star_file):
        """Test transform method."""
        loader = AwardsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="awards",
            award_type="all_star",
            csv_dir=mock_csv_dir,
        )
        df = pd.DataFrame({
            "player_id": [2544],
            "season": ["2024"],
            "award": ["All-Star"],
        })

        result = loader.transform(df)

        assert "player_id" in result.columns
        assert result["player_id"].iloc[0] == "2544"
        assert result["season"].iloc[0] == 2024

    def test_validate_success(self, mock_csv_dir):
        """Test successful validation."""
        loader = AwardsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="awards",
            award_type="all_star",
            csv_dir=mock_csv_dir,
        )
        df = pd.DataFrame({
            "season": [2024],
            "player": ["LeBron James"],
        })
        assert loader.validate(df) is True

    def test_validate_missing_season(self, mock_csv_dir):
        """Test validation with missing season."""
        loader = AwardsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="awards",
            award_type="all_star",
            csv_dir=mock_csv_dir,
        )
        df = pd.DataFrame({"other": [1]})
        with pytest.raises(ValidationError, match="Missing season column"):
            loader.validate(df)


class TestDraftLoader:
    """Tests for DraftLoader class."""

    @pytest.fixture
    def mock_csv_dir(self, tmp_path):
        """Fixture for CSV directory."""
        d = tmp_path / "csv"
        d.mkdir()
        return d

    @pytest.fixture
    def draft_file(self, mock_csv_dir):
        """Fixture for draft history CSV file."""
        f = mock_csv_dir / "Draft_Pick_History.csv"
        df = pd.DataFrame({
            "player_id": [2544, 201939],
            "player": ["LeBron James", "Stephen Curry"],
            "season": [2003, 2009],
            "round": [1, 1],
            "pick": [1, 7],
        })
        df.to_csv(f, index=False)
        return f

    def test_initialization(self, mock_csv_dir):
        """Test loader initialization."""
        loader = DraftLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="draft_picks",
            csv_dir=mock_csv_dir,
        )
        assert loader.draft_file == mock_csv_dir / "Draft_Pick_History.csv"

    def test_load(self, mock_csv_dir, draft_file):
        """Test loading draft data."""
        loader = DraftLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="draft_picks",
            csv_dir=mock_csv_dir,
        )

        df = loader.load()

        assert len(df) == 2
        assert "player_id" in df.columns
