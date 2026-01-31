"""Configuration management with Pydantic Settings.

This module provides unified configuration for both the web application and
data ingestion pipeline, replacing multiple separate configuration files.
"""

from pathlib import Path
from typing import Final

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        app_name: Application name.
        app_version: Application version.
        debug: Debug mode flag.
        host: Server host address.
        port: Server port number.
        database_path: Path to the DuckDB database file.
        log_level: Logging level.
        nba_api_delay: Delay between NBA API requests in seconds.

        Data ingestion paths
        planning_csv_dir: Directory for planning CSV data.
        planning_parquet_dir: Directory for planning Parquet data.

        Data ingestion thresholds
        min_season: Minimum NBA season year.
        max_season: Maximum NBA season year.

        Data ingestion batch sizes
        batch_size: Batch size for large CSV files.
        insert_batch_size: Batch size for database INSERT operations.
    """

    app_name: str = "BBall Ref Local"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    database_path: str = "./data/bball_ref.db"
    log_level: str = "info"
    nba_api_delay: float = 0.6

    # Data ingestion paths
    planning_csv_dir: Path = Path("./planning/csv_data")
    planning_parquet_dir: Path = Path("./planning/parq_data")

    # Data ingestion thresholds
    min_season: int = 1946
    max_season: int = 2026

    # Data ingestion batch sizes
    batch_size: int = 10000
    insert_batch_size: int = 1000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


# Legacy constants for backward compatibility
DATA_DIR: Final[Path] = settings.database_path.replace("./data/", "")
DB_PATH: Final[Path] = Path(settings.database_path)
MIN_SEASON: Final[int] = settings.min_season
MAX_SEASON: Final[int] = settings.max_season
BATCH_SIZE: Final[int] = settings.batch_size
INSERT_BATCH_SIZE: Final[int] = settings.insert_batch_size
PLANNING_CSV_DIR: Final[Path] = settings.planning_csv_dir
PLANNING_PARQ_DIR: Final[Path] = settings.planning_parquet_dir
BULK_INSERT_OPTIMIZATIONS: Final[dict[str, str]] = {
    "memory_limit": "1GB",
    "threads": "4",
}
TEMP_TABLE_SUFFIX: Final[str] = "_temp"
BACKUP_TABLE_SUFFIX: Final[str] = "_backup"
DATA_SOURCE_CSV: Final[str] = "planning_csv"
DATA_SOURCE_PARQUET: Final[str] = "planning_parquet"
LOG_LEVEL: Final[str] = settings.log_level.upper()
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
