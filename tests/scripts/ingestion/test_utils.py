"""Tests for ingestion utility functions."""

import numpy as np
import pandas as pd
import pytest

from scripts.ingestion.utils import (
    chunk_dataframe,
    clean_column_names,
    clean_string,
    normalize_team_name,
    parse_boolean,
    parse_season,
    safe_float,
    safe_int,
)


class TestCleanColumnNames:
    """Tests for clean_column_names function."""

    def test_clean_column_names_basic(self):
        """Test basic snake_case conversion."""
        cols = ["Player Name", "Team ID", "Points"]
        result = clean_column_names(cols)
        assert result == ["player_name", "team_id", "points"]

    def test_clean_column_names_special_chars(self):
        """Test handling of special characters."""
        cols = ["FG%", "3P%", "FT%", "+/-", "W/L"]
        result = clean_column_names(cols)
        assert result == ["fg_pct", "3p_pct", "ft_pct", "plus_minus", "w_per_l"]

    def test_clean_column_names_numeric_prefix(self):
        """Test handling of numeric prefixes."""
        cols = ["3P Attempted", "2P Made"]
        result = clean_column_names(cols)
        assert result == ["3p_attempted", "2p_made"]

    def test_clean_column_names_empty_strings(self):
        """Test handling of empty or whitespace strings."""
        cols = ["", "   ", "Valid"]
        result = clean_column_names(cols)
        assert result == ["unnamed_column", "unnamed_column", "valid"]


class TestParseSeason:
    """Tests for parse_season function."""

    def test_parse_season_valid_int(self):
        """Test parsing valid integer season."""
        assert parse_season(2023) == 2023

    def test_parse_season_valid_string(self):
        """Test parsing valid string season."""
        assert parse_season("2023") == 2023

    def test_parse_season_out_of_range(self):
        """Test parsing out of range season."""
        assert parse_season(1900) is None
        assert parse_season(2100) is None

    def test_parse_season_invalid_format(self):
        """Test parsing invalid format."""
        assert parse_season("not-a-year") is None
        assert parse_season("2023-24") is None  # Should be single year
        assert parse_season(None) is None


class TestNormalizeTeamName:
    """Tests for normalize_team_name function."""

    def test_normalize_team_name_standard(self):
        """Test standard normalization."""
        assert normalize_team_name("Boston Celtics") == "Boston Celtics"

    def test_normalize_team_name_mappings(self):
        """Test mapped team names."""
        assert normalize_team_name("LAL") == "Los Angeles Lakers"
        assert normalize_team_name("GSW") == "Golden State Warriors"
        assert normalize_team_name("Warriors") == "Golden State Warriors"

    def test_normalize_team_name_none(self):
        """Test handling of None."""
        assert normalize_team_name(None) is None


class TestSafeInt:
    """Tests for safe_int function."""

    def test_safe_int_valid(self):
        """Test valid integer conversion."""
        assert safe_int(10) == 10
        assert safe_int("10") == 10
        assert safe_int(10.0) == 10
        assert safe_int("1,000") == 1000

    def test_safe_int_none_values(self):
        """Test handling of null-like values."""
        assert safe_int(None) is None
        assert safe_int("") is None
        assert safe_int("NA") is None
        assert safe_int("n/a") is None
        assert safe_int(np.nan) is None

    def test_safe_int_invalid(self):
        """Test handling of invalid values."""
        assert safe_int("abc") is None
        assert safe_int("10.5") == 10  # Truncates float string


class TestSafeFloat:
    """Tests for safe_float function."""

    def test_safe_float_valid(self):
        """Test valid float conversion."""
        assert safe_float(10.5) == 10.5
        assert safe_float("10.5") == 10.5
        assert safe_float(10) == 10.0
        assert safe_float("1,000.5") == 1000.5

    def test_safe_float_percentages(self):
        """Test handling of percentage strings."""
        assert safe_float("50%") == 0.5
        assert safe_float("100%") == 1.0
        assert safe_float("0.5%") == 0.005

    def test_safe_float_none_values(self):
        """Test handling of null-like values."""
        assert safe_float(None) is None
        assert safe_float("") is None
        assert safe_float("NA") is None
        assert safe_float(np.nan) is None


class TestChunkDataframe:
    """Tests for chunk_dataframe function."""

    def test_chunk_dataframe_exact_split(self):
        """Test chunking with exact division."""
        df = pd.DataFrame({"A": range(10)})
        chunks = list(chunk_dataframe(df, 5))
        assert len(chunks) == 2
        assert len(chunks[0]) == 5
        assert len(chunks[1]) == 5

    def test_chunk_dataframe_remainder(self):
        """Test chunking with remainder."""
        df = pd.DataFrame({"A": range(10)})
        chunks = list(chunk_dataframe(df, 3))
        assert len(chunks) == 4
        assert len(chunks[0]) == 3
        assert len(chunks[3]) == 1

    def test_chunk_dataframe_empty(self):
        """Test chunking empty dataframe."""
        df = pd.DataFrame()
        chunks = list(chunk_dataframe(df, 5))
        assert len(chunks) == 0

    def test_chunk_dataframe_invalid_size(self):
        """Test invalid chunk size."""
        df = pd.DataFrame({"A": range(10)})
        with pytest.raises(ValueError):
            list(chunk_dataframe(df, 0))


class TestCleanString:
    """Tests for clean_string function."""

    def test_clean_string_valid(self):
        """Test valid string cleaning."""
        assert clean_string(" hello ") == "hello"
        assert clean_string(123) == "123"

    def test_clean_string_none(self):
        """Test handling of None/empty."""
        assert clean_string(None) is None
        assert clean_string("") is None
        assert clean_string("   ") is None


class TestParseBoolean:
    """Tests for parse_boolean function."""

    def test_parse_boolean_valid(self):
        """Test valid boolean parsing."""
        assert parse_boolean(True) is True
        assert parse_boolean("True") is True
        assert parse_boolean("yes") is True
        assert parse_boolean("1") is True

    def test_parse_boolean_false(self):
        """Test false values."""
        assert parse_boolean(False) is False
        assert parse_boolean("False") is False
        assert parse_boolean("no") is False
        assert parse_boolean("0") is False

    def test_parse_boolean_none(self):
        """Test handling of None/invalid."""
        assert parse_boolean(None) is None
        assert parse_boolean("maybe") is None
