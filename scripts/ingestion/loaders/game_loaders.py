"""Game data loaders for schedule, box scores, and team game stats."""

from pathlib import Path

import pandas as pd
from tqdm import tqdm

from scripts.ingestion.base_loader import BaseLoader
from scripts.ingestion.config import PLANNING_CSV_DIR
from scripts.ingestion.exceptions import ValidationError
from scripts.ingestion.logger import get_logger

logger = get_logger(__name__)


class GamesLoader(BaseLoader):
    """Load game schedule and results from Games.csv."""

    def __init__(self, file_path, table_name, csv_dir: Path | None = None):
        super().__init__(file_path, table_name)
        self.csv_dir = csv_dir or PLANNING_CSV_DIR
        self.games_file = self.csv_dir / "Games.csv"

    def load(self):
        logger.info("Loading games data...")
        self._validate_files_exist([self.games_file])
        df = self._load_csv(self.games_file)
        logger.info(f"Loaded {len(df)} games")
        df = self.transform(df)
        return df

    def transform(self, df):
        """Parse game_date, map team IDs, calculate winner."""
        df = df.copy()
        df = self._clean_column_names(df)
        if "game_date_time_est" in df.columns:
            df["game_date"] = pd.to_datetime(df["game_date_time_est"], errors="coerce")
            df["game_date"] = df["game_date"].dt.date
        if "winner" in df.columns:
            df["home_team_won"] = df["winner"] == df["hometeam_id"]
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].replace("", pd.NA)
        return df

    def validate(self, df, context="pre-load"):
        required_cols = ["game_id", "game_date"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValidationError(f"Missing required columns: {missing}")
        return True


class PlayerGameStatsLoader(BaseLoader):
    """Load player box scores with chunked reading for large file (1.6M rows)."""

    CHUNK_SIZE = 10000

    def __init__(self, file_path, table_name, csv_dir: Path | None = None):
        super().__init__(file_path, table_name)
        self.csv_dir = csv_dir or PLANNING_CSV_DIR
        self.stats_file = self.csv_dir / "PlayerStatistics.csv"

    def load(self):
        logger.info("Loading player game statistics (chunked)...")
        self._validate_files_exist([self.stats_file])
        chunks = []
        total_rows = 0
        for chunk in tqdm(
            pd.read_csv(self.stats_file, chunksize=self.CHUNK_SIZE), desc="Loading player stats"
        ):
            chunk = self.transform(chunk)
            chunks.append(chunk)
            total_rows += len(chunk)
        logger.info(f"Loaded {total_rows} player game statistics")
        return pd.concat(chunks, ignore_index=True)

    def transform(self, df):
        """Map personId to player_id, calculate shooting percentages, handle DNP."""
        df = df.copy()
        df = self._clean_column_names(df)
        if "person_id" in df.columns:
            df["person_id"] = df["person_id"].astype(str)
        if "game_date_time_est" in df.columns:
            df["game_date"] = pd.to_datetime(df["game_date_time_est"], errors="coerce")
        did_not_play = df["num_minutes"] == 0
        df["did_not_play"] = did_not_play
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].replace("", pd.NA)
        return df

    def validate(self, df, context="pre-load"):
        if "person_id" not in df.columns:
            raise ValidationError("Missing person_id column")
        if "game_id" not in df.columns:
            raise ValidationError("Missing game_id column")
        return True


class TeamGameStatsLoader(BaseLoader):
    """Load team game statistics with chunked reading (145K rows)."""

    CHUNK_SIZE = 5000

    def __init__(self, file_path, table_name, csv_dir: Path | None = None):
        super().__init__(file_path, table_name)
        self.csv_dir = csv_dir or PLANNING_CSV_DIR
        self.stats_file = self.csv_dir / "TeamStatistics.csv"

    def load(self):
        logger.info("Loading team game statistics (chunked)...")
        self._validate_files_exist([self.stats_file])
        chunks = []
        total_rows = 0
        for chunk in tqdm(
            pd.read_csv(self.stats_file, chunksize=self.CHUNK_SIZE), desc="Loading team stats"
        ):
            chunk = self.transform(chunk)
            chunks.append(chunk)
            total_rows += len(chunk)
        logger.info(f"Loaded {total_rows} team game statistics")
        return pd.concat(chunks, ignore_index=True)

    def transform(self, df):
        df = df.copy()
        df = self._clean_column_names(df)
        if "game_date_time_est" in df.columns:
            df["game_date"] = pd.to_datetime(df["game_date_time_est"], errors="coerce")
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].replace("", pd.NA)
        return df

    def validate(self, df, context="pre-load"):
        if "team_id" not in df.columns:
            raise ValidationError("Missing team_id column")
        if "game_id" not in df.columns:
            raise ValidationError("Missing game_id column")
        return True
