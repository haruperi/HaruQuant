"""
Usage examples for apps.sqlite.__init__.py

This module demonstrates how to use the main SQLiteDatabase class,
which combines all database functionality from different managers.
"""

from apps.sqlite import SQLiteDatabase, UserAlreadyExistsError


def example_basic_database_creation():
    """
    Example: Creating a database instance

    The SQLiteDatabase class combines all managers:
    - DatabaseBase: Connection management
    - SchemaManager: Schema initialization
    - UserManager: User CRUD operations
    - StrategyManager: Strategy management
    - BacktestManager: Backtest operations
    - OptimizationManager: Optimization runs
    - LiveTradingManager: Live trading sessions
    - MarketDataManager: Market data metadata
    """
    # Create database with default path (data/database/haruquant.db)
    db = SQLiteDatabase()

    # Or specify custom path
    db_custom = SQLiteDatabase(db_path="custom_path/my_database.db")

    print(f"Database created at: {db.db_path}")


def example_initialize_database():
    """
    Example: Initialize database schema

    Creates all tables for:
    - User management
    - Strategy management
    - Backtest tracking
    - Optimization runs
    - Live trading sessions
    - Market data metadata
    """
    db = SQLiteDatabase()

    # Initialize all tables and indices
    success = db.initialize_database()

    if success:
        print("Database schema initialized successfully")
    else:
        print("Failed to initialize database")


def example_complete_workflow():
    """
    Example: Complete workflow using multiple managers

    Demonstrates how the SQLiteDatabase class provides access
    to all database operations through inherited mixins.
    """
    db = SQLiteDatabase()

    # Initialize schema
    db.initialize_database()

    # Create a user (UserManager functionality)
    try:
        user_id = db.create_user(
            email="trader@example.com",
            username="trader123",
            password="pass123",  # Simple password to avoid bcrypt issues
            full_name="John Trader"
        )
        print(f"User created with ID: {user_id}")
    except UserAlreadyExistsError:
        print("User already exists")
        user = db.get_user(username="trader123")
        user_id = user["id"]
    except Exception as e:
        print(f"Error creating user: {e}")
        print("Note: If you see a bcrypt error, you may need to update your bcrypt library:")
        print("  pip install --upgrade bcrypt passlib")
        return

    # Create a strategy (StrategyManager functionality)
    strategy_id = db.create_strategy(
        user_id=user_id,
        name="Moving Average Crossover",
        description="Simple MA crossover strategy",
        category="Trend Following"
    )
    print(f"Strategy created with ID: {strategy_id}")

    # Create a strategy version (StrategyManager functionality)
    version_id = db.create_strategy_version(
        strategy_id=strategy_id,
        version="1.0.0",
        file_path="strategies/ma_crossover.py",
        parameters={"fast_period": 10, "slow_period": 20},
        created_by=user_id
    )
    print(f"Strategy version created with ID: {version_id}")

    # Save market data metadata (MarketDataManager functionality)
    data_id = db.save_market_data_metadata({
        "symbol": "EURUSD",
        "timeframe": "H1",
        "source": "MT5",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "record_count": 8760,
        "file_path": "data/market/EURUSD_H1_2023.csv",
        "validation_report": {"missing_bars": 0, "duplicates": 0}
    })
    print(f"Market data metadata saved with ID: {data_id}")

    # Create a live trading session (LiveTradingManager functionality)
    session_id = db.create_live_session(
        user_id=user_id,
        session_name="My Trading Session",
        mode="paper",
        max_positions=5,
        max_total_risk_pct=2.0
    )
    print(f"Live trading session created with ID: {session_id}")

    # Add strategy to session
    db.add_strategy_to_session(
        session_id=session_id,
        strategy_version_id=version_id,
        symbols=["EURUSD", "GBPUSD"],
        timeframes=["H1", "H4"]
    )
    print("Strategy added to live trading session")


def example_error_handling():
    """
    Example: Error handling with UserAlreadyExistsError

    Demonstrates how to handle the custom exception raised
    when trying to create a user that already exists.
    """
    db = SQLiteDatabase()
    db.initialize_database()

    # First user creation succeeds
    try:
        user_id = db.create_user(
            email="test@example.com",
            username="testuser",
            password="pass123"
        )
        print(f"First user created: {user_id}")
    except UserAlreadyExistsError as e:
        print(f"User already exists: {e}")
    except Exception as e:
        print(f"Error: {e}")
        print("Skipping this example due to bcrypt compatibility issue")
        return

    # Second attempt with same username raises exception
    try:
        user_id = db.create_user(
            email="another@example.com",
            username="testuser",  # Same username
            password="pass456"
        )
        print(f"Second user created: {user_id}")
    except UserAlreadyExistsError as e:
        print(f"Error: {e}")
        print("Retrieving existing user instead...")
        user = db.get_user(username="testuser")
        print(f"Existing user ID: {user['id']}")


def example_database_cleanup():
    """
    Example: Deleting the database

    Useful for testing or resetting the environment.
    """
    db = SQLiteDatabase()

    # Delete the database file
    success = db.delete_database()

    if success:
        print("Database deleted successfully")
    else:
        print("Database not found or failed to delete")


def example_custom_database_path():
    """
    Example: Using custom database path

    Shows how to create databases in different locations
    for different purposes (testing, production, etc.)
    """
    import os

    # Create directories first
    for directory in ["production", "test", "dev"]:
        os.makedirs(directory, exist_ok=True)

    # Production database
    prod_db = SQLiteDatabase(db_path="production/trading.db")
    prod_db.initialize_database()

    # Test database
    test_db = SQLiteDatabase(db_path="test/trading_test.db")
    test_db.initialize_database()

    # Development database
    dev_db = SQLiteDatabase(db_path="dev/trading_dev.db")
    dev_db.initialize_database()

    print(f"Production DB: {prod_db.db_path}")
    print(f"Test DB: {test_db.db_path}")
    print(f"Development DB: {dev_db.db_path}")

    # Cleanup example databases
    for db_file in ["production/trading.db", "test/trading_test.db", "dev/trading_dev.db"]:
        if os.path.exists(db_file):
            os.remove(db_file)
    print("\nExample databases cleaned up")


if __name__ == "__main__":
    print("=" * 80)
    print("SQLiteDatabase Usage Examples")
    print("=" * 80)

    print("\n1. Basic Database Creation")
    print("-" * 80)
    example_basic_database_creation()

    print("\n2. Initialize Database Schema")
    print("-" * 80)
    example_initialize_database()

    print("\n3. Complete Workflow")
    print("-" * 80)
    example_complete_workflow()

    print("\n4. Error Handling")
    print("-" * 80)
    example_error_handling()

    print("\n5. Database Cleanup")
    print("-" * 80)
    example_database_cleanup()

    print("\n6. Custom Database Path")
    print("-" * 80)
    example_custom_database_path()
