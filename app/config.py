"""Configuration management with Pydantic Settings."""

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
    """

    app_name: str = "BBall Ref Local"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    database_path: str = "./data/bball_ref.db"
    log_level: str = "info"
    nba_api_delay: float = 0.6

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
