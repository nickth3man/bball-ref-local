"""Shared utilities for HTMX request handling.

Provides common functions for detecting HTMX requests and rendering templates
across all API routers.
"""

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

# Initialize templates once at module level
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def is_htmx_request(request: Request) -> bool:
    """Check if the request is an HTMX request.

    Args:
        request: The incoming FastAPI request.

    Returns:
        True if the request has the HX-Request header.
    """
    return request.headers.get("HX-Request") == "true"


def get_templates() -> Jinja2Templates:
    """Get the shared Jinja2 templates instance.

    Returns:
        Configured Jinja2Templates instance.
    """
    return templates
