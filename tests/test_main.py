"""Tests for main application module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "database" in data


class TestHTMLPages:
    """Tests for HTML page routes."""

    def test_root_page(self, client):
        """Test root page returns HTML."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_players_page(self, client):
        """Test players page returns HTML."""
        response = client.get("/players")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_teams_page(self, client):
        """Test teams page returns HTML."""
        response = client.get("/teams")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_games_page(self, client):
        """Test games page returns HTML."""
        response = client.get("/games")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_stats_page(self, client):
        """Test stats page returns HTML."""
        response = client.get("/stats")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestRequestLoggingMiddleware:
    """Tests for request logging middleware."""

    def test_middleware_logs_requests(self, client):
        """Test that requests are logged."""
        # Just make a request - if middleware is active it should not error
        response = client.get("/health")

        assert response.status_code == 200


class TestAppConfiguration:
    """Tests for app configuration."""

    def test_app_title(self):
        """Test app has correct title."""
        from app.main import app

        assert app.title == "BBall Ref Local"

    def test_app_version(self):
        """Test app has version."""
        from app.main import app

        assert app.version is not None

    def test_routes_exist(self):
        """Test that expected routes are registered."""
        from app.main import app

        routes = [route.path for route in app.routes]

        # Check main pages exist
        assert "/" in routes
        assert "/health" in routes
        assert "/players" in routes
        assert "/teams" in routes
        assert "/games" in routes
        assert "/stats" in routes
