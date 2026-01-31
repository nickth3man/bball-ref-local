"""Tests for Parquet loaders."""

import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.ingestion.exceptions import ValidationError
from scripts.ingestion.loaders.parquet_loaders import ParquetLoader


class TestParquetLoader:
    """Tests for ParquetLoader class."""

    @pytest.fixture
    def mock_parquet_dir(self, tmp_path):
        """Fixture for parquet directory."""
        d = tmp_path / "parquet"
        d.mkdir()
        return d

    @pytest.fixture
    def sample_parquet(self, mock_parquet_dir):
        """Create a sample parquet file."""
        f = mock_parquet_dir / "totals.parq"
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "value": [10.5, 20.5, 30.5],
        })
        df.to_parquet(f, index=False)
        return f

    def test_initialization_with_preset(self, mock_parquet_dir):
        """Test loader initialization with preset file."""
        loader = ParquetLoader(
            file_path=mock_parquet_dir / "test.parquet",
            table_name="test_table",
            parquet_file="totals",
            parq_dir=mock_parquet_dir,
        )
        assert loader.parquet_file == mock_parquet_dir / "totals.parq"

    def test_initialization_with_custom(self, mock_parquet_dir):
        """Test loader initialization with custom file."""
        loader = ParquetLoader(
            file_path=mock_parquet_dir / "test.parquet",
            table_name="test_table",
            parquet_file="custom.parq",
            parq_dir=mock_parquet_dir,
        )
        assert loader.parquet_file == mock_parquet_dir / "custom.parq"

    def test_load_parquet(self, mock_parquet_dir, sample_parquet):
        """Test loading parquet file."""
        loader = ParquetLoader(
            file_path=mock_parquet_dir / "test.parquet",
            table_name="test_table",
            parquet_file="totals",
            parq_dir=mock_parquet_dir,
        )

        df = loader.load()

        assert len(df) == 3
        assert list(df.columns) == ["id", "name", "value"]
        assert df["id"].tolist() == [1, 2, 3]

    def test_transform(self, mock_parquet_dir, sample_parquet):
        """Test transform method."""
        loader = ParquetLoader(
            file_path=mock_parquet_dir / "test.parquet",
            table_name="test_table",
            parquet_file="totals",
            parq_dir=mock_parquet_dir,
        )
        df = pd.DataFrame({
            "id": [1, 2],
            "name": ["Test", "Data"],
        })

        result = loader.transform(df)

        # Transform should just return the dataframe (clean_column_names)
        assert len(result) == 2
        assert "id" in result.columns

    def test_normalize_season(self, mock_parquet_dir, sample_parquet):
        """Test season normalization."""
        loader = ParquetLoader(
            file_path=mock_parquet_dir / "test.parquet",
            table_name="test_table",
            parquet_file="totals",
            parq_dir=mock_parquet_dir,
        )

        # Test string format "2025/2026"
        assert loader._normalize_season("2025/2026") == 2026
        # Test integer
        assert loader._normalize_season(2024) == 2024
        # Test NaN
        assert pd.isna(loader._normalize_season(pd.NA))

    def test_validate_success(self, mock_parquet_dir):
        """Test successful validation."""
        loader = ParquetLoader(
            file_path=mock_parquet_dir / "test.parquet",
            table_name="test_table",
            parquet_file="totals",
            parq_dir=mock_parquet_dir,
        )
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["a", "b", "c"],
        })
        assert loader.validate(df) is True

    def test_validate_empty(self, mock_parquet_dir):
        """Test validation with empty dataframe."""
        loader = ParquetLoader(
            file_path=mock_parquet_dir / "test.parquet",
            table_name="test_table",
            parquet_file="totals",
            parq_dir=mock_parquet_dir,
        )
        df = pd.DataFrame()
        with pytest.raises(ValidationError, match="Parquet file is empty"):
            loader.validate(df)

    def test_file_not_found(self, mock_parquet_dir):
        """Test loading non-existent file."""
        loader = ParquetLoader(
            file_path=mock_parquet_dir / "test.parquet",
            table_name="test_table",
            parquet_file="nonexistent",
            parq_dir=mock_parquet_dir,
        )
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_get_row_count(self, mock_parquet_dir, sample_parquet):
        """Test get_row_count method."""
        loader = ParquetLoader(
            file_path=sample_parquet,  # Use the actual parquet file as file_path
            table_name="test_table",
            parquet_file="totals",
            parq_dir=mock_parquet_dir,
        )

        count = loader.get_row_count()

        assert count == 3

    def test_get_file_size(self, mock_parquet_dir, sample_parquet):
        """Test get_file_size method."""
        loader = ParquetLoader(
            file_path=sample_parquet,  # Use the actual parquet file as file_path
            table_name="test_table",
            parquet_file="totals",
            parq_dir=mock_parquet_dir,
        )

        size = loader.get_file_size()

        assert size > 0
