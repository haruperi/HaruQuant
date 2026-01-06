"""
Usage examples for apps.sqlite.schema.py

This module demonstrates:
- SchemaManager class for database schema management
- initialize_database() - Creates all tables and indices
- delete_database() - Removes the database file
"""

from apps.sqlite import SQLiteDatabase
import os


def example_initialize_database():
    """
    Example: Initialize complete database schema

    Creates all tables in a 4-layer architecture:
    - Layer 1: User management tables
    - Layer 2: Strategy management tables
    - Layer 3: Backtest tables (run, trades, events, equity)
    - Layer 4: Finance metrics tables
    - Layer 5: Optimization tables
    - Layer 6: Live trading tables
    - Layer 7: Market data tables
    """
    db = SQLiteDatabase(db_path="test_schema.db")

    # Initialize all tables and indices
    success = db.initialize_database()

    if success:
        print("Database schema initialized successfully")
        print("\nTables created:")
        print("  User Management:")
        print("    - users")
        print("    - user_settings")
        print("  Strategy Management:")
        print("    - strategies")
        print("    - strategy_versions")
        print("    - strategy_shares")
        print("  Backtest Layer 1 (Run):")
        print("    - backtest_runs")
        print("  Backtest Layer 2 (Facts):")
        print("    - backtest_trades")
        print("    - backtest_trade_events")
        print("    - backtest_equity_curve")
        print("  Backtest Layer 3 (Derived Finance Metrics):")
        print("    - finance_trade_metrics")
        print("    - finance_return_metrics")
        print("    - finance_drawdown_metrics")
        print("    - finance_ratio_metrics")
        print("    - finance_risk_metrics")
        print("    - finance_efficiency_metrics")
        print("  Backtest Layer 4 (Research):")
        print("    - finance_benchmark_metrics")
        print("    - finance_distributions")
        print("  Optimization:")
        print("    - optimization_runs")
        print("    - optimization_results")
        print("    - walk_forward_windows")
        print("    - monte_carlo_simulations")
        print("  Live Trading:")
        print("    - live_trading_sessions")
        print("    - session_strategies")
        print("    - live_signals")
        print("    - live_positions")
        print("    - live_position_events")
        print("    - live_risk_rules")
        print("    - live_session_logs")
        print("  Market Data:")
        print("    - market_data")
    else:
        print("Failed to initialize database schema")


def example_schema_features():
    """
    Example: Schema features enabled during initialization

    Demonstrates the various database features that are configured:
    - Foreign key constraints
    - Cascade deletes
    - Default values
    - Timestamps
    - Indices for performance
    """
    db = SQLiteDatabase(db_path="test_features.db")
    db.initialize_database()

    print("Schema Features:")
    print("\n1. Foreign Key Constraints:")
    print("   - user_settings.user_id -> users.id")
    print("   - strategies.user_id -> users.id")
    print("   - strategy_versions.strategy_id -> strategies.id")
    print("   - backtest_runs.user_id -> users.id")
    print("   - backtest_trades.backtest_id -> backtest_runs.backtest_id")
    print("   - live_positions.session_id -> live_trading_sessions.session_id")

    print("\n2. Cascade Deletes:")
    print("   - Deleting a user cascades to their strategies")
    print("   - Deleting a strategy cascades to its versions")
    print("   - Deleting a backtest cascades to trades and metrics")
    print("   - Deleting a session cascades to positions and signals")

    print("\n3. Default Values:")
    print("   - users.is_active = 1")
    print("   - users.is_superuser = 0")
    print("   - strategies.status = 'inactive'")
    print("   - backtest_runs.status = 'pending'")
    print("   - live_trading_sessions.status = 'stopped'")

    print("\n4. Automatic Timestamps:")
    print("   - created_at = CURRENT_TIMESTAMP")
    print("   - updated_at = CURRENT_TIMESTAMP")

    print("\n5. Performance Indices:")
    print("   - idx_backtest_trades_backtest_id")
    print("   - idx_backtest_trades_open_time")
    print("   - idx_optimization_results_score")
    print("   - idx_live_positions_mt5_ticket")


def example_idempotent_initialization():
    """
    Example: Idempotent schema initialization

    initialize_database() can be called multiple times safely.
    It uses CREATE TABLE IF NOT EXISTS, so existing tables aren't affected.
    """
    db = SQLiteDatabase(db_path="test_idempotent.db")

    # First initialization
    print("First initialization...")
    success1 = db.initialize_database()
    print(f"  Result: {success1}")

    # Second initialization (no error)
    print("\nSecond initialization...")
    success2 = db.initialize_database()
    print(f"  Result: {success2}")

    # Third initialization (still no error)
    print("\nThird initialization...")
    success3 = db.initialize_database()
    print(f"  Result: {success3}")

    print("\nAll initializations succeeded without errors")
    print("Existing data is preserved")


def example_delete_database():
    """
    Example: Deleting the database file

    Useful for:
    - Testing cleanup
    - Environment reset
    - Starting fresh
    """
    db = SQLiteDatabase(db_path="test_delete.db")

    # Create the database
    db.initialize_database()
    print(f"Database created at: {db.db_path}")
    print(f"File exists: {os.path.exists(db.db_path)}")

    # Delete the database
    success = db.delete_database()

    if success:
        print("\nDatabase deleted successfully")
        print(f"File exists: {os.path.exists(db.db_path)}")
    else:
        print("\nFailed to delete database")


def example_fresh_start_workflow():
    """
    Example: Fresh start workflow

    Shows how to completely reset a database by deleting and reinitializing.
    """
    db = SQLiteDatabase(db_path="test_fresh.db")

    print("Step 1: Delete existing database")
    db.delete_database()

    print("\nStep 2: Initialize fresh schema")
    db.initialize_database()

    print("\nStep 3: Verify empty database")
    user = db.get_user(user_id=1)
    if user is None:
        print("Database is empty (no users found)")
    else:
        print(f"User found: {user}")

    print("\nDatabase is ready for fresh data")


def example_schema_migration_safety():
    """
    Example: Schema safety features

    Demonstrates how the schema protects data integrity:
    - UNIQUE constraints prevent duplicates
    - Foreign keys maintain referential integrity
    - CHECK constraints enforce business rules
    """
    db = SQLiteDatabase(db_path="test_safety.db")
    db.initialize_database()

    print("Schema Safety Features:")

    print("\n1. UNIQUE Constraints:")
    print("   - users.username UNIQUE")
    print("   - users.email UNIQUE")
    print("   - strategy_versions(strategy_id, version) UNIQUE")
    print("   - strategy_shares(strategy_id, shared_with_user_id) UNIQUE")
    print("   Prevents duplicate entries")

    print("\n2. Foreign Key Constraints:")
    print("   - ON DELETE CASCADE: Child records deleted with parent")
    print("   - ON DELETE SET NULL: Reference set to NULL on parent delete")
    print("   Maintains referential integrity")

    print("\n3. NOT NULL Constraints:")
    print("   - users.username NOT NULL")
    print("   - users.email NOT NULL")
    print("   - strategies.name NOT NULL")
    print("   Ensures required fields are always present")


def example_wal_mode_configuration():
    """
    Example: WAL mode configuration

    The schema initialization works with WAL mode for better concurrency.
    WAL mode is configured in DatabaseBase.__init__
    """
    db = SQLiteDatabase(db_path="test_wal_config.db")

    print("WAL Mode Benefits:")
    print("  - Readers don't block writers")
    print("  - Writers don't block readers")
    print("  - Multiple readers can access simultaneously")
    print("  - Better performance for concurrent operations")

    # Initialize schema (works seamlessly with WAL mode)
    db.initialize_database()

    print("\nSchema initialized with WAL mode enabled")
    print("Database is ready for concurrent access")


if __name__ == "__main__":
    print("=" * 80)
    print("SchemaManager Usage Examples")
    print("=" * 80)

    print("\n1. Initialize Database Schema")
    print("-" * 80)
    example_initialize_database()

    print("\n2. Schema Features")
    print("-" * 80)
    example_schema_features()

    print("\n3. Idempotent Initialization")
    print("-" * 80)
    example_idempotent_initialization()

    print("\n4. Delete Database")
    print("-" * 80)
    example_delete_database()

    print("\n5. Fresh Start Workflow")
    print("-" * 80)
    example_fresh_start_workflow()

    print("\n6. Schema Migration Safety")
    print("-" * 80)
    example_schema_migration_safety()

    print("\n7. WAL Mode Configuration")
    print("-" * 80)
    example_wal_mode_configuration()
