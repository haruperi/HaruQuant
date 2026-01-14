"""Migrate session_strategies table schema to remove restrictive constraint."""

import os
import sqlite3

DB_PATH = "d:/Trading/Applications/HaruQuant/data/database/haruquant.db"


def migrate():
    """Run the session_strategies table migration."""
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Starting migration of session_strategies table...")

        # 1. Rename existing table
        cursor.execute(
            "ALTER TABLE session_strategies RENAME TO session_strategies_old"
        )

        # 2. Create new table without the restrictive UNIQUE constraint
        # We can add a less restrictive constraint if needed, but for flexibility, removing it is safest.
        # We rely on the app logic to prevent senseless duplicates if needed.
        create_new_table_query = """
        CREATE TABLE session_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            strategy_version_id INTEGER NOT NULL,

            -- Strategy configuration
            is_active BOOLEAN DEFAULT 1,
            symbols TEXT NOT NULL,
            timeframes TEXT NOT NULL,

            -- Risk per strategy
            max_risk_per_trade_pct REAL DEFAULT 1.0,
            position_size_type TEXT DEFAULT 'risk',
            position_size_value REAL DEFAULT 1.0,

            -- Parameters override
            strategy_params TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (session_id) REFERENCES live_trading_sessions (session_id) ON DELETE CASCADE,
            FOREIGN KEY (strategy_version_id) REFERENCES strategy_versions (id) ON DELETE CASCADE
        );
        """
        cursor.execute(create_new_table_query)

        # 3. Copy data
        cursor.execute(
            """
            INSERT INTO session_strategies (
                id, session_id, strategy_version_id, is_active, symbols, timeframes,
                max_risk_per_trade_pct, position_size_type, position_size_value,
                strategy_params, created_at
            )
            SELECT
                id, session_id, strategy_version_id, is_active, symbols, timeframes,
                max_risk_per_trade_pct, position_size_type, position_size_value,
                strategy_params, created_at
            FROM session_strategies_old
        """
        )

        # 4. Drop old table
        cursor.execute("DROP TABLE session_strategies_old")

        conn.commit()
        print("Migration completed successfully.")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
