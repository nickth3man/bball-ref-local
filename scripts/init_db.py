"""Standalone script to initialize the database without running the full app.

Usage:
    python scripts/init_db.py

This script is useful for first-time setup or resetting the database.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.database import (
    close_db_connection,
    get_app_metadata,
    init_db,
    set_app_metadata,
)


def main() -> int:
    """Initialize the database.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    print("Initializing bball-ref-local database...")
    print(f"Database location: {project_root / 'data' / 'bball_ref.db'}")
    
    try:
        # Initialize database with all tables
        init_db()
        
        # Set initial metadata
        set_app_metadata("version", "0.1.0")
        set_app_metadata("initialized_at", "CURRENT_TIMESTAMP")
        
        # Verify initialization
        version = get_app_metadata("version")
        
        print("[OK] Database initialized successfully")
        print(f"[OK] App version: {version}")
        print("\nCreated tables:")
        print("  - teams")
        print("  - players")
        print("  - games")
        print("  - player_game_stats")
        print("  - app_metadata")
        print("\nCreated indexes for performance optimization")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}", file=sys.stderr)
        return 1
        
    finally:
        close_db_connection()


if __name__ == "__main__":
    sys.exit(main())
