"""Base ETL class for standardized Extract-Transform-Load operations.

This module provides a base class that implements the standard ETL pattern used
across the application, including:
- Standardized logging and timing
- Error handling and result reporting
- Rate limiting management
- Database connection management
"""

import time
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from app.config import settings
from app.services.database import close_db_connection
from scripts.ingestion.exceptions import ETLError
from scripts.logging_utils import ETLLogger, setup_etl_logging

logger = setup_etl_logging(__name__)


class BaseETL(ABC):
    """Abstract base class for ETL operations."""

    def __init__(self, operation_name: str):
        """Initialize the ETL process.

        Args:
            operation_name: Name of the operation for logging (e.g., "games_etl").
        """
        self.operation_name = operation_name
        self.logger = setup_etl_logging(operation_name)
        self.rate_limit_delay = settings.nba_api_delay

    @abstractmethod
    def extract(self, *args, **kwargs) -> pd.DataFrame:
        """Extract data from source.

        Returns:
            DataFrame containing extracted raw data.
        """
        pass

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform raw data into target schema.

        Args:
            df: Raw DataFrame from extract step.

        Returns:
            Transformed DataFrame ready for loading.
        """
        pass

    @abstractmethod
    def load(self, df: pd.DataFrame) -> int:
        """Load transformed data into database.

        Args:
            df: Transformed DataFrame.

        Returns:
            Number of records loaded.
        """
        pass

    def run(self, *args, **kwargs) -> dict[str, Any]:
        """Run the complete ETL pipeline.

        Returns:
            Dictionary containing execution results and stats.
        """
        result = {
            "status": "success",
            "extracted": 0,
            "loaded": 0,
            "error": None,
        }

        with ETLLogger(self.logger, self.operation_name) as etl_log:
            try:
                # 1. Extract
                self.logger.info("Starting extraction...")
                df_raw = self.extract(*args, **kwargs)
                extracted_count = len(df_raw) if df_raw is not None else 0
                result["extracted"] = extracted_count

                if extracted_count == 0:
                    self.logger.warning("No data extracted. Stopping.")
                    etl_log.set_result(result)
                    return result

                # 2. Transform
                self.logger.info(f"Transforming {extracted_count} records...")
                df_transformed = self.transform(df_raw)

                # 3. Load
                self.logger.info("Loading data into database...")
                loaded_count = self.load(df_transformed)
                result["loaded"] = loaded_count

                etl_log.set_result(result)

            except Exception as e:
                self.logger.exception(f"ETL failed: {e}")
                result["status"] = "failed"
                result["error"] = str(e)
                # Re-raise generic ETLError to be caught by orchestrator if needed
                # or just return the failure result (design choice: returning result dict for now)
            finally:
                close_db_connection()

        return result

    def _apply_rate_limit(self):
        """Apply rate limiting sleep."""
        time.sleep(self.rate_limit_delay)
