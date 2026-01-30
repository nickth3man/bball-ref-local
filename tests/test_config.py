"""Tests for configuration."""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import Settings, settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_settings_default_values(self):
        s = Settings()
        assert s.app_name == "BBall Ref Local"
        assert s.app_version == "0.1.0"
        assert s.debug is False
        assert s.host == "0.0.0.0"
        assert s.port == 8000
        assert s.database_path == "./data/bball_ref.db"
        assert s.log_level == "info"
        assert s.nba_api_delay == 0.6

    def test_settings_database_path_is_string(self):
        s = Settings()
        assert isinstance(s.database_path, str)

    def test_settings_port_is_int(self):
        s = Settings()
        assert isinstance(s.port, int)

    def test_settings_debug_is_bool(self):
        s = Settings()
        assert isinstance(s.debug, bool)

    def test_settings_nba_api_delay_is_float(self):
        s = Settings()
        assert isinstance(s.nba_api_delay, float)

    def test_settings_custom_values(self):
        s = Settings(app_name="Test App", port=9000, debug=True)
        assert s.app_name == "Test App"
        assert s.port == 9000
        assert s.debug is True


class TestGlobalSettings:
    """Tests for global settings instance."""

    def test_global_settings_exists(self):
        assert settings is not None

    def test_global_settings_is_settings_instance(self):
        assert isinstance(settings, Settings)

    def test_global_settings_has_required_attributes(self):
        assert hasattr(settings, "app_name")
        assert hasattr(settings, "database_path")
        assert hasattr(settings, "port")
        assert hasattr(settings, "debug")
