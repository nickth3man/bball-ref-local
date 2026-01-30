"""Reference data loaders for teams and players."""

from pathlib import Path

import pandas as pd

from scripts.ingestion.base_loader import BaseLoader
from scripts.ingestion.config import PLANNING_CSV_DIR
from scripts.ingestion.exceptions import ValidationError
from scripts.ingestion.logger import get_logger

logger = get_logger(__name__)


class TeamLoader(BaseLoader):
    """Load and merge team reference data from multiple sources."""

    def __init__(
        self,
        file_path: str | Path,
        table_name: str,
        column_mapping: dict[str, str] | None = None,
        csv_dir: Path | None = None,
    ):
        super().__init__(file_path, table_name)
        self.column_mapping = column_mapping or {}
        self.csv_dir = csv_dir or PLANNING_CSV_DIR
        self.abbrev_file = self.csv_dir / "Team_Abbrev.csv"
        self.history_file = self.csv_dir / "TeamHistories.csv"

    def load(self) -> pd.DataFrame:
        logger.info("Loading team reference data...")
        self._validate_files_exist([self.abbrev_file, self.history_file])
        abbrev_df = self._load_csv(self.abbrev_file)
        history_df = self._load_csv(self.history_file)
        logger.info(
            f"Loaded {len(abbrev_df)} team abbreviations, {len(history_df)} historical records"
        )
        abbrev_df = self.transform(abbrev_df, source="abbrev")
        history_df = self.transform(history_df, source="history")
        merged_df = self._merge_team_data(abbrev_df, history_df)
        if self.column_mapping:
            merged_df = merged_df.rename(columns=self.column_mapping)
        logger.info(f"Successfully loaded {len(merged_df)} team records")
        return merged_df

    def transform(self, df, source="abbrev"):
        df = df.copy()
        if source == "abbrev":
            df = self._clean_column_names(df)
            if "playoffs" in df.columns:
                df["playoffs"] = df["playoffs"].astype(bool)
        elif source == "history":
            df = self._clean_column_names(df)
            if "team_abbrev" in df.columns:
                df["team_abbrev"] = df["team_abbrev"].str.strip()
            if "season_active_till" in df.columns:
                df["is_active"] = df["season_active_till"] >= 2024
        return df

    def _merge_team_data(self, abbrev_df, history_df):
        id_to_abbrev = (
            abbrev_df.drop_duplicates(subset=["team"]).set_index("team")["abbreviation"].to_dict()
        )
        history_df["current_abbreviation"] = history_df.apply(
            lambda row: id_to_abbrev.get(
                f"{row['team_city']} {row['team_name']}", row["team_abbrev"].strip()
            ),
            axis=1,
        )
        return history_df

    def validate(self, df, context="pre-load"):
        required_cols = ["team_id", "team_city", "team_name", "team_abbrev"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValidationError(f"Missing required columns: {missing}")
        null_ids = df["team_id"].isnull().sum()
        if null_ids > 0:
            raise ValidationError(f"Found {null_ids} rows with null team_id")
        return True


class PlayerLoader(BaseLoader):
    """Load and merge player master data from multiple sources."""

    def __init__(
        self,
        file_path: str | Path,
        table_name: str,
        column_mapping: dict[str, str] | None = None,
        csv_dir: Path | None = None,
    ):
        super().__init__(file_path, table_name)
        self.column_mapping = column_mapping or {}
        self.csv_dir = csv_dir or PLANNING_CSV_DIR
        self.career_file = self.csv_dir / "Player_Career_Info.csv"
        self.players_file = self.csv_dir / "Players.csv"

    def load(self) -> pd.DataFrame:
        logger.info("Loading player master data...")
        self._validate_files_exist([self.career_file, self.players_file])
        career_df = self._load_csv(self.career_file)
        players_df = self._load_csv(self.players_file)
        logger.info(f"Loaded {len(career_df)} career records, {len(players_df)} player records")
        players_df = self._handle_duplicates(players_df)
        career_df = self.transform(career_df, source="career")
        players_df = self.transform(players_df, source="players")
        merged_df = self._merge_player_data(career_df, players_df)
        if self.column_mapping:
            merged_df = merged_df.rename(columns=self.column_mapping)
        logger.info(f"Successfully loaded {len(merged_df)} player records")
        return merged_df

    def transform(self, df, source="career"):
        df = df.copy()
        df = self._clean_column_names(df)
        if source == "career":
            if "pos" in df.columns:
                df["pos"] = df["pos"].apply(self._normalize_position)
            if "birth_date" in df.columns:
                df["birth_date"] = pd.to_datetime(df["birth_date"], errors="coerce")
            if "debut" in df.columns:
                df["debut"] = pd.to_datetime(df["debut"], errors="coerce")
            if "ht_in_in" in df.columns:
                df["height_inches"] = pd.to_numeric(df["ht_in_in"], errors="coerce")
                df["height"] = df["height_inches"].apply(self._inches_to_height_str)
            if "wt" in df.columns:
                df["weight"] = pd.to_numeric(df["wt"], errors="coerce")
            if "hof" in df.columns:
                df["hof"] = df["hof"].astype(bool)
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].replace("", pd.NA)
        elif source == "players":
            if "person_id" in df.columns:
                df["person_id"] = df["person_id"].astype(str)
            if "birthdate" in df.columns:
                df["birthdate"] = pd.to_datetime(df["birthdate"], errors="coerce")
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].replace("", pd.NA)
        return df

    def _handle_duplicates(self, df):
        name_counts = df.groupby(["firstName", "lastName"]).size()
        duplicates = name_counts[name_counts > 1].index.tolist()
        if duplicates:
            logger.warning(f"Found {len(duplicates)} duplicate player names")

            def select_best_record(group):
                non_null_counts = group.notnull().sum(axis=1)
                return group.loc[non_null_counts.idxmax()]

            df = df.groupby(["firstName", "lastName"], group_keys=False).apply(select_best_record)
            logger.info(f"After deduplication: {len(df)} unique player records")
        return df

    def _merge_player_data(self, career_df, players_df):
        career_df["name_key"] = career_df["player"].str.lower().str.replace(" ", "")
        players_df["name_key"] = (
            players_df["firstName"].fillna("") + players_df["lastName"].fillna("")
        ).str.lower()
        merged = career_df.merge(
            players_df[
                ["name_key", "birthdate", "country", "height", "body_weight", "last_attended"]
            ],
            on="name_key",
            how="left",
            suffixes=("", "_supplemental"),
        )
        merged = merged.drop(columns=["name_key"])
        if "birthdate" in merged.columns and "birth_date" in merged.columns:
            merged["birth_date"] = merged["birth_date"].fillna(merged["birthdate"])
        return merged

    def _normalize_position(self, pos):
        if pd.isna(pos) or pos == "":
            return pd.NA
        positions = pos.split("-")
        positions.sort()
        return "-".join(positions)

    def _inches_to_height_str(self, inches):
        if pd.isna(inches):
            return pd.NA
        feet = int(inches // 12)
        remaining_inches = int(inches % 12)
        return f"{feet}-{remaining_inches}"

    def validate(self, df, context="pre-load"):
        required_cols = ["player_id", "player"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValidationError(f"Missing required columns: {missing}")
        null_ids = df["player_id"].isnull().sum()
        if null_ids > 0:
            raise ValidationError(f"Found {null_ids} rows with null player_id")
        if "from" in df.columns and "to" in df.columns:
            invalid_years = df[df["from"] > df["to"]]
            if len(invalid_years) > 0:
                raise ValidationError(
                    f"Found {len(invalid_years)} players with invalid career years"
                )
        return True
