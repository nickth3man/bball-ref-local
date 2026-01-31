"""Parquet data loaders for supplemental data."""

from pathlib import Path

import pandas as pd

from scripts.ingestion.base_loader import BaseLoader
from scripts.ingestion.config import PLANNING_PARQ_DIR
from scripts.ingestion.exceptions import ValidationError
from scripts.ingestion.logger import get_logger

logger = get_logger(__name__)


class ParquetLoader(BaseLoader):
    """Load parquet files for supplemental data enrichment."""

    PARQUET_FILES = {
        "totals": "totals.parq",
        "per_game": "per_game.parq",
        "advanced": "advanced.parq",
        "shooting": "shooting.parq",
        "roster": "roster.parq",
    }

    def __init__(
        self,
        file_path,
        table_name,
        parquet_file: str,
        columns: list[str] | None = None,
        parq_dir: Path | None = None,
    ):
        super().__init__(file_path, table_name)
        self.parq_dir = parq_dir or PLANNING_PARQ_DIR
        if parquet_file in self.PARQUET_FILES:
            self.parquet_file = self.parq_dir / self.PARQUET_FILES[parquet_file]
        else:
            self.parquet_file = self.parq_dir / parquet_file
        self.columns = columns

    def load(self):
        logger.info(f"Loading parquet file: {self.parquet_file.name}...")
        if not self.parquet_file.exists():
            raise FileNotFoundError(f"Parquet file not found: {self.parquet_file}")
        if self.columns:
            df = pd.read_parquet(self.parquet_file, columns=self.columns)
        else:
            df = pd.read_parquet(self.parquet_file)
        logger.info(f"Loaded {len(df)} records from {self.parquet_file.name}")
        df = self.transform(df)
        return df

    def transform(self, df):
        """Normalize season format from "2025/2026" to 2026."""
        df = df.copy()
        df = self._clean_column_names(df)
        if "season" in df.columns:
            df["season"] = df["season"].apply(self._normalize_season)
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].replace("", pd.NA)
        return df

    def _normalize_season(self, season):
        """Convert season format from "2025/2026" to 2026."""
        if pd.isna(season):
            return pd.NA
        if isinstance(season, str) and "/" in season:
            return int(season.split("/")[1])
        return int(season)

    def validate(self, df, context="pre-load"):
        if len(df) == 0:
            raise ValidationError("Parquet file is empty")
        return True
