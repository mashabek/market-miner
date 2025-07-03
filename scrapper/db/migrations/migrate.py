"""
Migration runner script.
Uses DATABASE_URL from environment variables.
"""
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv('DATABASE_URL')
print(DATABASE_URL)
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment variables")
    sys.exit(1)

# Get migrations directory
MIGRATIONS_DIR = Path(__file__).parent / 'versions'
if not MIGRATIONS_DIR.exists():
    print(f"Error: Migrations directory not found at {MIGRATIONS_DIR}")
    sys.exit(1)

def run_yoyo(command: str):
    """Run a yoyo command."""
    full_command = f"yoyo {command} --database {DATABASE_URL} ./versions"
    os.system(full_command)

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migrate.py <command>")
        print("\nAvailable commands:")
        print("  apply     - Apply pending migrations")
        print("  rollback  - Rollback last migration")
        print("  list      - List migration status")
        print("  reapply   - Rollback and reapply last migration")
        sys.exit(1)

    command = sys.argv[1]
    
    if command == 'apply':
        run_yoyo('apply')
    elif command == 'rollback':
        run_yoyo('rollback')
    elif command == 'list':
        run_yoyo('list')
    elif command == 'reapply':
        run_yoyo('rollback')
        run_yoyo('apply')
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main() 