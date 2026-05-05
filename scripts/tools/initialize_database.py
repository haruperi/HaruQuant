"""
Initialize database with strategy tables.

Run this script to create the strategy-related tables in your database.
"""

import os
import sys

# Add repository root to path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from data.database.sqlite import SQLiteDatabase  # noqa: E402


def main():
    """
    Initialize complete database schema.

    Creates the canonical JSON-backed schema:
    - Layer 1: User management tables
    - Layer 2: Strategy management tables
    - Layer 3: Backtests snapshot table
    - Layer 4: Optimization tables
    - Layer 5: Live trading tables
    - Layer 6: Market data tables
    """
    db = SQLiteDatabase(db_path="data/database/haruquant.db")

    # Initialize all tables and indices
    success = db.initialize_database()

    if success:
        print("Database schema initialized successfully")
        print("\nTables created:")
        print("  User Management:")
        print("    - users")
        print("    - user_settings")
        print("    - user_sessions")
        print("  Strategy Management:")
        print("    - strategies")
        print("    - strategy_versions")
        print("    - strategy_shares")
        print("  Backtests:")
        print("    - backtests")
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


if __name__ == "__main__":
    main()
