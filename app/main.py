"""
FastAPI application for bball-ref-local.

Provides a local API for basketball reference data using DuckDB as the backend.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import duckdb
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Database path
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "bball_ref.db"


class DatabaseConnection:
    """Manages DuckDB connection."""

    def __init__(self) -> None:
        self.conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Establish database connection."""
        self.conn = duckdb.connect(str(DB_PATH))
        return self.conn

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


# Global database instance
db = DatabaseConnection()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events, including DuckDB connection management.
    """
    # Startup: Connect to database
    conn = db.connect()
    
    # Create essential tables if they don't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_metadata (
            key VARCHAR PRIMARY KEY,
            value VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Set app version
    conn.execute("""
        INSERT OR REPLACE INTO app_metadata (key, value)
        VALUES ('version', '0.1.0')
    """)
    
    yield
    
    # Shutdown: Close database connection
    db.close()


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


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Root endpoint - renders home page."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "BBall Ref Local"}
    )


@app.get("/health")
async def health_check() -> dict[str, str | bool]:
    """
    Health check endpoint.
    
    Returns:
        Status information about the application and database connection.
    """
    try:
        # Test database connection
        if db.conn:
            db.conn.execute("SELECT 1")
            db_status = "connected"
        else:
            db_status = "disconnected"
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
