"""Season statistics loaders for aggregated player and team stats."""

from pathlib import Path

import pandas as pd

from scripts.ingestion.base_loader import BaseLoader
from scripts.ingestion.config import PLANNING_CSV_DIR
from scripts.ingestion.exceptions import ValidationError
from scripts.ingestion.logger import get_logger

logger = get_logger(__name__)


class PlayerSeasonStatsLoader(BaseLoader):
    """Load player season statistics from various stat type files."""

    STAT_TYPE_FILES = {
        "totals": "Player_Totals.csv",
        "per_game": "Player_Per_Game.csv",
        "per_100_poss": "Per_100_Poss.csv",
        "per_36_minutes": "Per_36_Minutes.csv",
        "advanced": "Advanced.csv",
        "shooting": "Player_Shooting.csv",
        "play_by_play": "Player_Play_By_Play.csv",
    }

    def __init__(self, file_path, table_name, stat_type: str, csv_dir: Path | None = None):
        super().__init__(file_path, table_name)
        if stat_type not in self.STAT_TYPE_FILES:
            raise ValueError(
                f"Invalid stat_type: {stat_type}. Must be one of {list(self.STAT_TYPE_FILES.keys())}"
            )
        self.stat_type = stat_type
        self.csv_dir = csv_dir or PLANNING_CSV_DIR
        self.stats_file = self.csv_dir / self.STAT_TYPE_FILES[stat_type]

    def load(self):
        logger.info(f"Loading player {self.stat_type} statistics...")
        self._validate_files_exist([self.stats_file])
        df = self._load_csv(self.stats_file)
        logger.info(f"Loaded {len(df)} player {self.stat_type} records")
        df = self.transform(df)
        df["stat_type"] = self.stat_type
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
        if "player_id" not in df.columns:
            raise ValidationError("Missing player_id column")
        if "season" not in df.columns:
            raise ValidationError("Missing season column")
        return True


class TeamSeasonStatsLoader(BaseLoader):
    """Load team season statistics from various stat type files."""

    STAT_TYPE_FILES = {
        "totals": "Team_Totals.csv",
        "per_game": "Team_Stats_Per_Game.csv",
        "per_100_poss": "Team_Stats_Per_100_Poss.csv",
        "summaries": "Team_Summaries.csv",
        "opponent_totals": "Opponent_Totals.csv",
        "opponent_per_game": "Opponent_Stats_Per_Game.csv",
        "opponent_per_100_poss": "Opponent_Stats_Per_100_Poss.csv",
    }

    def __init__(self, file_path, table_name, stat_type: str, csv_dir: Path | None = None):
        super().__init__(file_path, table_name)
        if stat_type not in self.STAT_TYPE_FILES:
            raise ValueError(f"Invalid stat_type: {stat_type}")
        self.stat_type = stat_type
        self.csv_dir = csv_dir or PLANNING_CSV_DIR
        self.stats_file = self.csv_dir / self.STAT_TYPE_FILES[stat_type]

    def load(self):
        logger.info(f"Loading team {self.stat_type} statistics...")
        self._validate_files_exist([self.stats_file])
        df = self._load_csv(self.stats_file)
        logger.info(f"Loaded {len(df)} team {self.stat_type} records")
        df = self.transform(df)
        df["stat_type"] = self.stat_type
        return df

    def transform(self, df):
        df = df.copy()
        df = self._clean_column_names(df)
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
