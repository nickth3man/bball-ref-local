"""Tests for BaseLoader abstract base class."""


import pandas as pd
import pytest

from scripts.ingestion.base_loader import BaseLoader
from scripts.ingestion.exceptions import FileError


class ConcreteLoader(BaseLoader):
    """Concrete implementation of BaseLoader for testing."""

    def load(self):
        """Mock implementation of load."""
        return 0

    def transform(self, df):
        """Mock implementation of transform."""
        return df


class TestBaseLoader:
    """Tests for BaseLoader class."""

    @pytest.fixture
    def loader(self, tmp_path):
        """Fixture for concrete loader instance."""
        file_path = tmp_path / "test.csv"
        file_path.touch()
        return ConcreteLoader(file_path, "test_table")

    def test_initialization(self, tmp_path):
        """Test basic initialization."""
        file_path = tmp_path / "test.csv"
        loader = ConcreteLoader(file_path, "test_table")

        assert loader.file_path == file_path
        assert loader.table_name == "test_table"
        assert loader.batch_size > 0

    def test_validate_success(self, loader):
        """Test successful validation."""
        df = pd.DataFrame({"col": [1, 2, 3]})
        assert loader.validate(df) is True

    def test_validate_empty(self, loader):
        """Test validation with empty dataframe."""
        df = pd.DataFrame()
        assert loader.validate(df) is False

    def test_read_file_csv(self, tmp_path):
        """Test reading CSV file."""
        file_path = tmp_path / "data.csv"
        df = pd.DataFrame({"col": [1, 2, 3]})
        df.to_csv(file_path, index=False)

        loader = ConcreteLoader(file_path, "test_table")
        result = loader.read_file()

        assert len(result) == 3
        assert list(result.columns) == ["col"]

    def test_read_file_parquet(self, tmp_path):
        """Test reading Parquet file."""
        file_path = tmp_path / "data.parquet"
        df = pd.DataFrame({"col": [1, 2, 3]})
        df.to_parquet(file_path)

        loader = ConcreteLoader(file_path, "test_table")
        result = loader.read_file()

        assert len(result) == 3

    def test_read_file_not_found(self, tmp_path):
        """Test reading non-existent file."""
        file_path = tmp_path / "missing.csv"
        loader = ConcreteLoader(file_path, "test_table")

        with pytest.raises(FileError, match="Source file not found"):
            loader.read_file()

    def test_read_file_unsupported(self, tmp_path):
        """Test reading unsupported file format."""
        file_path = tmp_path / "data.txt"
        file_path.touch()
        loader = ConcreteLoader(file_path, "test_table")

        with pytest.raises(FileError, match="Unsupported file format"):
            loader.read_file()

    def test_get_row_count_csv(self, tmp_path):
        """Test getting row count for CSV."""
        file_path = tmp_path / "data.csv"
        df = pd.DataFrame({"col": [1, 2, 3]})
        df.to_csv(file_path, index=False)

        loader = ConcreteLoader(file_path, "test_table")
        assert loader.get_row_count() == 3

    def test_get_file_size(self, tmp_path):
        """Test getting file size."""
        file_path = tmp_path / "data.csv"
        file_path.write_text("test")

        loader = ConcreteLoader(file_path, "test_table")
        assert loader.get_file_size() == 4

    def test_clean_column_names(self, loader):
        """Test internal column name cleaning."""
        df = pd.DataFrame({"PlayerName": [1], "TeamID": [2], "FG%": [0.5]})
        result = loader._clean_column_names(df)

        assert "player_name" in result.columns
        assert "team_id" in result.columns
        assert "fg%" in result.columns  # BaseLoader uses basic camel->snake conversion

    def test_validate_files_exist_success(self, tmp_path):
        """Test checking existing files."""
        f1 = tmp_path / "f1.txt"
        f1.touch()
        f2 = tmp_path / "f2.txt"
        f2.touch()

        loader = ConcreteLoader(f1, "t")
        assert loader._validate_files_exist([f1, f2]) is True

    def test_validate_files_exist_failure(self, tmp_path):
        """Test checking missing files."""
        f1 = tmp_path / "exists.txt"
        f1.touch()
        f2 = tmp_path / "missing.txt"

        loader = ConcreteLoader(f1, "t")
        with pytest.raises(FileNotFoundError, match="Missing required file"):
            loader._validate_files_exist([f1, f2])
