"""
FastAPI application for bball-ref-local.

Provides a local API for basketball reference data using DuckDB as the backend.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import players_router, teams_router, games_router, stats_router
from app.services.database import (
    close_db_connection,
    get_db_connection,
    init_db,
    set_app_metadata,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI application.

    Handles startup and shutdown events, including DuckDB connection management.
    """
    # Startup: Initialize database and create tables
    init_db()

    # Set app version
    set_app_metadata("version", "0.1.0")

    yield

    # Shutdown: Close database connection
    close_db_connection()


# Create FastAPI app with lifespan
app = FastAPI(
    title="BBall Ref Local",
    description="Local basketball reference data API",
    version="0.1.0",
    lifespan=lifespan,
)

# Set up templates and static files
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include API routers
app.include_router(players_router, prefix="/api/v1")
app.include_router(teams_router, prefix="/api/v1")
app.include_router(games_router, prefix="/api/v1")
app.include_router(stats_router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Root endpoint - renders home page."""
    return templates.TemplateResponse(
        "index.html", {"request": request, "title": "BBall Ref Local"}
    )


@app.get("/health")
async def health_check() -> dict[str, str | bool]:
    """Health check endpoint.

    Returns:
        Status information about the application and database connection.
    """
    try:
        # Test database connection
        conn = get_db_connection()
        conn.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "version": "0.1.0",
    }


@app.get("/api/v1/status")
async def api_status() -> dict[str, str]:
    """API status endpoint."""
    return {
        "name": "bball-ref-local",
        "version": "0.1.0",
        "status": "operational",
    }


@app.get("/players", response_class=HTMLResponse)
async def players_page(request: Request) -> HTMLResponse:
    """Players listing page."""
    return templates.TemplateResponse("players/list.html", {"request": request, "title": "Players"})


@app.get("/teams", response_class=HTMLResponse)
async def teams_page(request: Request) -> HTMLResponse:
    """Teams listing page."""
    return templates.TemplateResponse("teams/list.html", {"request": request, "title": "Teams"})


@app.get("/games", response_class=HTMLResponse)
async def games_page(request: Request) -> HTMLResponse:
    """Games listing page."""
    return templates.TemplateResponse("games/list.html", {"request": request, "title": "Games"})


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request) -> HTMLResponse:
    """Stats/leaders page."""
    return templates.TemplateResponse("stats/leaders.html", {"request": request, "title": "Stats"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
