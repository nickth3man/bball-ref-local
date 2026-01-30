# 🏀 BBall Ref Local

A local basketball reference data API built with FastAPI and DuckDB.

## Features

- **FastAPI** - Modern, fast web framework for building APIs
- **DuckDB** - High-performance analytical database for local data storage
- **NBA API** - Integration with the official NBA API for data ingestion
- **Jinja2 Templates** - Server-side rendering for web views
- **uv** - Fast Python package manager and virtual environment

## Project Structure

```
bball-ref-local/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry
│   ├── routers/             # API route handlers
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   ├── templates/           # Jinja2 templates
│   └── static/              # Static assets
├── data/                    # Database and parquet files
├── tests/                   # Test files
├── scripts/                 # ETL and utility scripts
└── docs/                    # Documentation
```

## Getting Started

### Prerequisites

- Python 3.12+
- uv (package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bball-ref-local.git
cd bball-ref-local
```

2. Sync dependencies with uv:
```bash
uv sync
```

3. Copy environment variables:
```bash
cp .env.example .env
```

### Running the Application

Start the development server:
```bash
uv run fastapi dev app/main.py
```

The API will be available at `http://localhost:8000`

- API documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/health`

### Running Tests

```bash
uv run pytest
```

## Development

### Code Quality

This project uses ruff for linting and formatting:

```bash
# Check code
uv run ruff check .

# Format code
uv run ruff format .
```

### Adding Dependencies

```bash
# Add runtime dependency
uv add <package>

# Add development dependency
uv add --dev <package>
```

## License

MIT License
