"""Awards and recognition data loaders."""

from pathlib import Path

import pandas as pd

from scripts.ingestion.base_loader import BaseLoader
from scripts.ingestion.config import PLANNING_CSV_DIR
from scripts.ingestion.exceptions import ValidationError
from scripts.ingestion.logger import get_logger

logger = get_logger(__name__)


class AwardsLoader(BaseLoader):
    """Load awards and recognition data from multiple sources."""

    AWARD_FILES = {
        "all_star": "All-Star Selections.csv",
        "end_of_season_teams": "End_of_Season_Teams.csv",
        "end_of_season_voting": "End_of_Season_Teams_(Voting).csv",
        "award_shares": "Player_Award_Shares.csv",
    }

    def __init__(self, file_path, table_name, award_type: str, csv_dir: Path | None = None):
        super().__init__(file_path, table_name)
        if award_type not in self.AWARD_FILES:
            raise ValueError(f"Invalid award_type: {award_type}")
        self.award_type = award_type
        self.csv_dir = csv_dir or PLANNING_CSV_DIR
        self.award_file = self.csv_dir / self.AWARD_FILES[award_type]

    def load(self):
        logger.info(f"Loading {self.award_type} awards data...")
        self._validate_files_exist([self.award_file])
        df = self._load_csv(self.award_file)
        logger.info(f"Loaded {len(df)} {self.award_type} records")
        df = self.transform(df)
        df["award_type"] = self.award_type
        return df

    def transform(self, df):
        df = df.copy()
        df = self._clean_column_names(df)
        if "player_id" in df.columns:
            df["player_id"] = df["player_id"].astype(str)
        if "season" in df.columns:
            df["season"] = pd.to_numeric(df["season"], errors="coerce")
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].replace("", pd.NA)
        return df

    def validate(self, df, context="pre-load"):
        if "season" not in df.columns:
            raise ValidationError("Missing season column")
        return True


class DraftLoader(BaseLoader):
    """Load draft pick history data."""

    def __init__(self, file_path, table_name, csv_dir: Path | None = None):
        super().__init__(file_path, table_name)
        self.csv_dir = csv_dir or PLANNING_CSV_DIR
        self.draft_file = self.csv_dir / "Draft_Pick_History.csv"

    def load(self):
        logger.info("Loading draft pick history...")
        self._validate_files_exist([self.draft_file])
        df = self._load_csv(self.draft_file)
        logger.info(f"Loaded {len(df)} draft picks")
        df = self.transform(df)
        return df

    def transform(self, df):
        df = df.copy()
        df = self._clean_column_names(df)
        if "player_id" in df.columns:
            df["player_id"] = df["player_id"].astype(str)
        if "season" in df.columns:
            df["season"] = pd.to_numeric(df["season"], errors="coerce")
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].replace("", pd.NA)
        return df

    def validate(self, df, context="pre-load"):
        required_cols = ["season", "overall_pick"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValidationError(f"Missing required columns: {missing}")
        return True
