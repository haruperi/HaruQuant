"""
Usage examples for apps.sqlite.base.py

This module demonstrates:
- DatabaseBase class for connection management
- UserAlreadyExistsError exception handling
- Default database path configuration
"""

from apps.sqlite.base import DatabaseBase, UserAlreadyExistsError
import os


def example_database_base_creation():
    """
    Example: Creating a DatabaseBase instance

    DatabaseBase provides the foundation for database connection management.
    It handles database path resolution and WAL mode configuration.
    """
    # Create with default path
    db = DatabaseBase()
    print(f"Default database path: {db.db_path}")

    # Create with custom path
    custom_db = DatabaseBase(db_path="my_custom/database.db")
    print(f"Custom database path: {custom_db.db_path}")


def example_default_path_resolution():
    """
    Example: Understanding default path resolution

    The default path is determined by _get_default_db_path():
    - Gets the current file directory (apps/sqlite)
    - Navigates to project root (../../)
    - Creates path: <project_root>/data/database/haruquant.db
    """
    db = DatabaseBase()

    print("Path resolution:")
    print(f"  Database path: {db.db_path}")
    print(f"  Directory exists: {os.path.exists(os.path.dirname(db.db_path))}")
    print(f"  Database exists: {os.path.exists(db.db_path)}")


def example_wal_mode_initialization():
    """
    Example: WAL mode for concurrent access

    DatabaseBase automatically enables Write-Ahead Logging (WAL) mode
    for better concurrent read/write performance.

    Benefits of WAL mode:
    - Readers don't block writers
    - Writers don't block readers
    - Better concurrency for multi-process access
    """
    # When DatabaseBase is initialized, it attempts to enable WAL mode
    db = DatabaseBase(db_path="test_wal.db")

    # If database exists, WAL mode is enabled
    # If database doesn't exist yet, a message is logged
    print("DatabaseBase created with WAL mode enabled (if DB exists)")


def example_user_already_exists_error():
    """
    Example: UserAlreadyExistsError exception

    This custom exception is raised when attempting to create
    a user with an email or username that already exists.
    """
    try:
        # Simulate a scenario where user creation fails
        raise UserAlreadyExistsError("Username 'trader123' already exists")
    except UserAlreadyExistsError as e:
        print(f"Caught UserAlreadyExistsError: {e}")
        print("Handle by: retrieving existing user or prompting for different username")


def example_inheritance_pattern():
    """
    Example: Using DatabaseBase as a mixin

    DatabaseBase is designed to be inherited along with other mixins
    to create a complete database interface.
    """
    class MyDatabaseManager(DatabaseBase):
        """Custom database manager inheriting from DatabaseBase"""

        def my_custom_operation(self):
            """Example custom operation using db_path"""
            print(f"Performing operation on database: {self.db_path}")

    # Create instance
    manager = MyDatabaseManager(db_path="custom.db")
    manager.my_custom_operation()


def example_directory_creation():
    """
    Example: Automatic directory creation

    DatabaseBase ensures that the database directory exists
    by calling os.makedirs(db_dir, exist_ok=True)
    """
    # Create database in nested directories
    db = DatabaseBase(db_path="deeply/nested/path/database.db")

    # The directories are automatically created
    db_dir = os.path.dirname(db.db_path)
    print(f"Database directory: {db_dir}")
    print(f"Directory exists: {os.path.exists(db_dir)}")


def example_multiple_instances():
    """
    Example: Creating multiple database instances

    You can have multiple DatabaseBase instances pointing to
    different databases for different purposes.
    """
    # Production database
    prod_db = DatabaseBase(db_path="data/prod/haruquant.db")

    # Test database
    test_db = DatabaseBase(db_path="data/test/haruquant_test.db")

    # Analytics database
    analytics_db = DatabaseBase(db_path="data/analytics/metrics.db")

    print("Multiple database instances:")
    print(f"  Production: {prod_db.db_path}")
    print(f"  Testing: {test_db.db_path}")
    print(f"  Analytics: {analytics_db.db_path}")


def example_error_scenarios():
    """
    Example: Handling initialization errors

    Shows various error scenarios and how they're handled.
    """
    # Scenario 1: Database doesn't exist yet (WAL mode fails gracefully)
    db_new = DatabaseBase(db_path="nonexistent/new_database.db")
    print(f"Created DatabaseBase for new database: {db_new.db_path}")
    print("Note: WAL mode will be enabled when database is created")

    # Scenario 2: Valid database path
    db_valid = DatabaseBase(db_path="data/database/haruquant.db")
    print(f"Created DatabaseBase for existing path: {db_valid.db_path}")


if __name__ == "__main__":
    print("=" * 80)
    print("DatabaseBase Usage Examples")
    print("=" * 80)

    print("\n1. DatabaseBase Creation")
    print("-" * 80)
    example_database_base_creation()

    print("\n2. Default Path Resolution")
    print("-" * 80)
    example_default_path_resolution()

    print("\n3. WAL Mode Initialization")
    print("-" * 80)
    example_wal_mode_initialization()

    print("\n4. UserAlreadyExistsError Exception")
    print("-" * 80)
    example_user_already_exists_error()

    print("\n5. Inheritance Pattern")
    print("-" * 80)
    example_inheritance_pattern()

    print("\n6. Automatic Directory Creation")
    print("-" * 80)
    example_directory_creation()

    print("\n7. Multiple Database Instances")
    print("-" * 80)
    example_multiple_instances()

    print("\n8. Error Scenarios")
    print("-" * 80)
    example_error_scenarios()
