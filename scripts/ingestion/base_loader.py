"""Abstract base class for data loaders."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from scripts.ingestion.config import BATCH_SIZE
from scripts.ingestion.exceptions import FileError
from scripts.ingestion.logger import get_logger


class BaseLoader(ABC):
    """Abstract base class for all data loaders."""

    def __init__(self, file_path, table_name, batch_size=BATCH_SIZE):
        """Initialize the base loader."""
        self.file_path = Path(file_path)
        self.table_name = table_name
        self.batch_size = batch_size
        self.logger = get_logger(self.__class__.__name__)
        self.logger.debug(
            f"Initialized {self.__class__.__name__} for {self.file_path} -> {self.table_name}"
        )

    @abstractmethod
    def load(self):
        """Load data from file to database."""
        pass

    @abstractmethod
    def transform(self, df):
        """Transform DataFrame before loading."""
        pass

    def validate(self, df, context="pre-load"):
        """Validate data before loading."""
        if df.empty:
            self.logger.warning(f"Validation ({context}): DataFrame is empty")
            return False
        self.logger.debug(f"Validation ({context}): {len(df)} rows")
        return True

    def read_file(self, **kwargs):
        """Read data from source file."""
        if not self.file_path.exists():
            raise FileError(
                "Source file not found",
                file_path=str(self.file_path),
                operation="read",
            )
        try:
            suffix = self.file_path.suffix.lower()
            if suffix == ".csv":
                self.logger.debug(f"Reading CSV file: {self.file_path}")
                return pd.read_csv(self.file_path, **kwargs)
            elif suffix in (".parquet", ".parq"):
                self.logger.debug(f"Reading Parquet file: {self.file_path}")
                return pd.read_parquet(self.file_path, **kwargs)
            else:
                raise FileError(
                    f"Unsupported file format: {suffix}",
                    file_path=str(self.file_path),
                    operation="read",
                )
        except Exception as e:
            raise FileError(
                f"Failed to read file: {e}",
                file_path=str(self.file_path),
                operation="read",
            ) from e

    def get_row_count(self):
        """Get expected row count from file."""
        try:
            suffix = self.file_path.suffix.lower()
            if suffix == ".csv":
                with open(self.file_path, encoding="utf-8") as f:
                    return sum(1 for _ in f) - 1
            elif suffix in (".parquet", ".parq"):
                import pyarrow.parquet as pq

                parquet_file = pq.ParquetFile(self.file_path)
                return parquet_file.metadata.num_rows
            else:
                df = self.read_file()
                return len(df)
        except Exception as e:
            raise FileError(
                f"Failed to get row count: {e}",
                file_path=str(self.file_path),
                operation="count",
            ) from e

    def get_file_size(self):
        """Get the size of the source file in bytes."""
        try:
            return self.file_path.stat().st_size
        except Exception as e:
            raise FileError(
                f"Failed to get file size: {e}",
                file_path=str(self.file_path),
                operation="stat",
            ) from e

    def _validate_files_exist(self, files: list) -> bool:
        """Validate that all files in the list exist.

        Args:
            files: List of file paths (strings or Path objects) to validate.

        Returns:
            True if all files exist.

        Raises:
            FileNotFoundError: If any file does not exist.
        """
        self.logger.debug(f"Validating {len(files)} file(s) exist...")
        missing_files = []
        for i, file_path in enumerate(files, 1):
            path = Path(file_path)
            exists = path.exists()
            self.logger.debug(f"  [{i}/{len(files)}] {path} - {'EXISTS' if exists else 'MISSING'}")
            if not exists:
                missing_files.append(str(path))

        if missing_files:
            raise FileNotFoundError(f"Missing required file(s): {', '.join(missing_files)}")

        self.logger.debug(f"All {len(files)} file(s) validated successfully")
        return True

    def _clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert DataFrame column names from camelCase to snake_case.

        Args:
            df: DataFrame with columns to clean.

        Returns:
            DataFrame with snake_case column names.
        """
        import re

        original_cols = list(df.columns)
        self.logger.debug(f"Cleaning {len(original_cols)} column names...")

        def to_snake_case(name: str) -> str:
            # Insert underscore before uppercase letters (except first char) and lowercase everything
            s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
            return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        df.columns = [to_snake_case(col) for col in df.columns]

        if self.logger.isEnabledFor(logging.DEBUG):
            for orig, new in zip(original_cols, df.columns, strict=True):
                if orig != new:
                    self.logger.debug(f"  {orig} -> {new}")

        return df

    def _load_csv(self, file_path) -> pd.DataFrame:
        """Load a CSV file with validation and column name cleaning.

        Args:
            file_path: Path to the CSV file (string or Path object).

        Returns:
            DataFrame with snake_case column names.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        path = Path(file_path)
        self.logger.debug(f"Loading CSV: {path.name}")
        self._validate_files_exist([file_path])

        # Get file size for progress indication
        file_size = path.stat().st_size
        self.logger.debug(f"  File size: {file_size:,} bytes")

        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        self.logger.debug(f"  Raw load: {len(df)} rows, {len(df.columns)} columns")

        df = self._clean_column_names(df)
        self.logger.debug(f"  Columns converted to snake_case: {len(df.columns)} columns")

        return df

    def __repr__(self):
        """Return string representation of the loader."""
        return (
            f"{self.__class__.__name__}("
            f"file_path={self.file_path}, "
            f"table_name={self.table_name}, "
            f"batch_size={self.batch_size}"
            f")"
        )
