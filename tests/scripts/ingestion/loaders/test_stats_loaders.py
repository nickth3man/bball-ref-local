"""Tests for stats data loaders."""

import pandas as pd
import pytest

from scripts.ingestion.exceptions import ValidationError
from scripts.ingestion.loaders.stats_loaders import PlayerSeasonStatsLoader, TeamSeasonStatsLoader


class TestPlayerSeasonStatsLoader:
    """Tests for PlayerSeasonStatsLoader class."""

    @pytest.fixture
    def mock_csv_dir(self, tmp_path):
        """Fixture for CSV directory."""
        d = tmp_path / "csv"
        d.mkdir()
        return d

    @pytest.fixture
    def player_totals_file(self, mock_csv_dir):
        """Fixture for player totals CSV file."""
        f = mock_csv_dir / "Player_Totals.csv"
        df = pd.DataFrame({
            "player_id": [2544, 201939],
            "player": ["LeBron James", "Stephen Curry"],
            "season": [2024, 2024],
            "pts": [1500, 1800],
            "reb": [500, 300],
            "ast": [400, 350],
        })
        df.to_csv(f, index=False)
        return f

    def test_initialization(self, mock_csv_dir):
        """Test loader initialization."""
        loader = PlayerSeasonStatsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="player_season_stats",
            stat_type="totals",
            csv_dir=mock_csv_dir,
        )
        assert loader.stats_file == mock_csv_dir / "Player_Totals.csv"
        assert loader.stat_type == "totals"

    def test_initialization_invalid_stat_type(self, mock_csv_dir):
        """Test loader initialization with invalid stat type."""
        with pytest.raises(ValueError, match="Invalid stat_type"):
            PlayerSeasonStatsLoader(
                file_path=mock_csv_dir / "test.csv",
                table_name="player_season_stats",
                stat_type="invalid",
                csv_dir=mock_csv_dir,
            )

    def test_load(self, mock_csv_dir, player_totals_file):
        """Test loading player stats data."""
        loader = PlayerSeasonStatsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="player_season_stats",
            stat_type="totals",
            csv_dir=mock_csv_dir,
        )

        df = loader.load()

        assert len(df) == 2
        assert "player_id" in df.columns
        assert "stat_type" in df.columns
        assert df["stat_type"].iloc[0] == "totals"

    def test_transform(self, mock_csv_dir, player_totals_file):
        """Test transform method."""
        loader = PlayerSeasonStatsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="player_season_stats",
            stat_type="totals",
            csv_dir=mock_csv_dir,
        )
        df = pd.DataFrame({
            "player_id": [2544],
            "season": ["2024"],
            "pts": [1500],
        })

        result = loader.transform(df)

        assert "player_id" in result.columns
        assert result["player_id"].iloc[0] == "2544"
        assert result["season"].iloc[0] == 2024

    def test_validate_success(self, mock_csv_dir):
        """Test successful validation."""
        loader = PlayerSeasonStatsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="player_season_stats",
            stat_type="totals",
            csv_dir=mock_csv_dir,
        )
        df = pd.DataFrame({
            "player_id": ["2544"],
            "season": [2024],
        })
        assert loader.validate(df) is True

    def test_validate_missing_player_id(self, mock_csv_dir):
        """Test validation with missing player_id."""
        loader = PlayerSeasonStatsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="player_season_stats",
            stat_type="totals",
            csv_dir=mock_csv_dir,
        )
        df = pd.DataFrame({"season": [2024]})
        with pytest.raises(ValidationError, match="Missing player_id"):
            loader.validate(df)

    def test_validate_missing_season(self, mock_csv_dir):
        """Test validation with missing season."""
        loader = PlayerSeasonStatsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="player_season_stats",
            stat_type="totals",
            csv_dir=mock_csv_dir,
        )
        df = pd.DataFrame({"player_id": ["2544"]})
        with pytest.raises(ValidationError, match="Missing season"):
            loader.validate(df)


class TestTeamSeasonStatsLoader:
    """Tests for TeamSeasonStatsLoader class."""

    @pytest.fixture
    def mock_csv_dir(self, tmp_path):
        """Fixture for CSV directory."""
        d = tmp_path / "csv"
        d.mkdir()
        return d

    @pytest.fixture
    def team_totals_file(self, mock_csv_dir):
        """Fixture for team totals CSV file."""
        f = mock_csv_dir / "Team_Totals.csv"
        df = pd.DataFrame({
            "team_id": [1, 2],
            "team": ["Boston Celtics", "LA Lakers"],
            "season": [2024, 2024],
            "wins": [60, 50],
            "losses": [22, 32],
        })
        df.to_csv(f, index=False)
        return f

    def test_initialization(self, mock_csv_dir):
        """Test loader initialization."""
        loader = TeamSeasonStatsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="team_season_stats",
            stat_type="totals",
            csv_dir=mock_csv_dir,
        )
        assert loader.stats_file == mock_csv_dir / "Team_Totals.csv"

    def test_initialization_invalid_stat_type(self, mock_csv_dir):
        """Test loader initialization with invalid stat type."""
        with pytest.raises(ValueError, match="Invalid stat_type"):
            TeamSeasonStatsLoader(
                file_path=mock_csv_dir / "test.csv",
                table_name="team_season_stats",
                stat_type="invalid",
                csv_dir=mock_csv_dir,
            )

    def test_load(self, mock_csv_dir, team_totals_file):
        """Test loading team stats data."""
        loader = TeamSeasonStatsLoader(
            file_path=mock_csv_dir / "test.csv",
            table_name="team_season_stats",
            stat_type="totals",
            csv_dir=mock_csv_dir,
        )

        df = loader.load()

        assert len(df) == 2
        assert "team_id" in df.columns
        assert "stat_type" in df.columns
