"""Tests for HTMX utilities."""

import sys
from pathlib import Path

from fastapi import Request

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.htmx_utils import get_templates, is_htmx_request


class MockRequest:
    """Mock request for testing."""

    def __init__(self, headers=None):
        self.headers = headers or {}


class TestHtmxUtils:
    """Tests for HTMX utilities."""

    def test_is_htmx_request_true(self):
        request = MockRequest(headers={"HX-Request": "true"})
        assert is_htmx_request(request) is True

    def test_is_htmx_request_false(self):
        request = MockRequest(headers={})
        assert is_htmx_request(request) is False

    def test_is_htmx_request_false_when_wrong_value(self):
        request = MockRequest(headers={"HX-Request": "false"})
        assert is_htmx_request(request) is False

    def test_get_templates_returns_jinja2(self):
        templates = get_templates()
        assert templates is not None

    def test_get_templates_consistent_instance(self):
        templates1 = get_templates()
        templates2 = get_templates()
        assert templates1 is templates2


class TestHtmxIntegration:
    """Integration tests for HTMX functionality."""

    def test_is_htmx_request_with_real_headers(self):
        scope = {
            "type": "http",
            "method": "GET",
            "headers": [(b"hx-request", b"true")],
        }
        request = Request(scope)
        assert is_htmx_request(request) is True

    def test_is_htmx_request_false_real_headers(self):
        scope = {
            "type": "http",
            "method": "GET",
            "headers": [],
        }
        request = Request(scope)
        assert is_htmx_request(request) is False
