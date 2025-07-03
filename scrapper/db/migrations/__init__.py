"""
Database migrations configuration and utilities.
"""
from pathlib import Path

# Migrations directory
MIGRATIONS_DIR = Path(__file__).parent / 'versions'

# Ensure migrations directory exists
MIGRATIONS_DIR.mkdir(exist_ok=True)

def get_migration_files():
    """Get all migration files in order."""
    return sorted(
        [f for f in MIGRATIONS_DIR.glob('*.sql') if f.is_file()],
        key=lambda x: x.stem
    ) 