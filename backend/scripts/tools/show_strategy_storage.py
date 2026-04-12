"""Show where the Simple MA Crossover strategy is stored."""

import json
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from backend.db.sqlite.database_operations import DatabaseManager  # noqa: E402


def main():
    """Run the script to show strategy storage locations."""
    db = DatabaseManager()

    print("=" * 70)
    print("STRATEGY STORAGE LOCATIONS")
    print("=" * 70)

    # Get strategy from database
    print("\n1. DATABASE STORAGE (Metadata)")
    print("-" * 70)
    strategy = db.get_strategy(1)
    if strategy:
        print("Location: backend/data/database/haruquant.db")
        print("Table: strategies")
        print("\nStrategy Details:")
        print(f"  ID: {strategy['id']}")
        print(f"  Name: {strategy['name']}")
        print(f"  Description: {strategy['description']}")
        print(f"  Status: {strategy['status']}")
        print(f"  Category: {strategy['category']}")
        print(f"  Active Version: {strategy['active_version']}")
        print(f"  Created: {strategy['created_at']}")
        print(f"  Updated: {strategy['updated_at']}")

    # Get versions
    print("\n2. VERSION HISTORY (Database)")
    print("-" * 70)
    versions = db.get_strategy_versions(1)
    print("Location: backend/data/database/haruquant.db")
    print("Table: strategy_versions")
    print(f"\nVersions ({len(versions)} total):")
    for v in versions:
        print(f"  v{v['version']}")
        print(f"    - Version ID: {v['id']}")
        print(f"    - Parameters: {v['parameters']}")
        print(f"    - Changelog: {v['changelog']}")
        print(f"    - Created: {v['created_at']}")
        print()

    # Show file storage
    print("3. FILE STORAGE (Strategy Code)")
    print("-" * 70)
    user_id = 1
    strategy_id = 1

    strategy_dir = f"backend/data/strategies/user_{user_id}/strategy_{strategy_id}"
    print(f"Base Location: {strategy_dir}")
    print("\nVersion Directories:")

    if os.path.exists(strategy_dir):
        for version_dir in sorted(os.listdir(strategy_dir)):
            version_path = os.path.join(strategy_dir, version_dir)
            if os.path.isdir(version_path):
                print(f"\n  📁 {version_dir}/")

                # Show files
                for file in os.listdir(version_path):
                    file_path = os.path.join(version_path, file)
                    size = os.path.getsize(file_path)
                    print(f"     📄 {file} ({size} bytes)")

                    # Show metadata.json content
                    if file == "metadata.json":
                        with open(file_path, "r") as f:
                            metadata = json.load(f)
                            print(f"        Content: {json.dumps(metadata, indent=10)}")

                    # Show first few lines of strategy.py
                    if file == "strategy.py":
                        with open(file_path, "r") as f:
                            lines = f.readlines()[:5]
                            print("        Preview:")
                            for line in lines:
                                print(f"          {line.rstrip()}")
    else:
        print("  ⚠️  Directory not found!")

    print("\n" + "=" * 70)
    print("STORAGE ARCHITECTURE SUMMARY")
    print("=" * 70)
    print(
        """
The strategy uses a HYBRID STORAGE approach:

1. Database (SQLite): Stores metadata and searchable information
   - Strategy name, description, status, category
   - Version information and changelogs
   - User ownership and permissions
   - Backtest results and statistics
   - Fast queries and filtering

2. File System: Stores actual Python code
   - Each version has its own directory
   - Contains strategy.py (the code)
   - Contains metadata.json (parameters, settings)
   - Easy to edit, version control (git), and backup
   - Can be imported/exported as ZIP files

Why Hybrid?
- Best of both worlds
- Database is great for searching/filtering
- Files are great for code editing and git
- Separation of concerns
- Easy backup and migration
    """
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
