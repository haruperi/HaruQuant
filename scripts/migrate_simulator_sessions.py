"""
Migration script for simulator sessions/trades tables.

This script is safe to run multiple times.
"""

import os
import sqlite3


def main() -> None:
    """Create simulator session/trade tables and indexes."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    db_path = os.path.join(project_root, "data", "database", "haruquant.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_name TEXT,
            mode TEXT NOT NULL DEFAULT 'manual',
            status TEXT NOT NULL DEFAULT 'running',
            symbol TEXT,
            timeframe TEXT,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            initial_balance REAL,
            speed_multiplier REAL DEFAULT 1.0,
            current_bar_index INTEGER DEFAULT 0,
            total_bars INTEGER,
            replay_source TEXT,
            replay_backtest_id INTEGER,
            replay_file_name TEXT,
            config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation_trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            time TIMESTAMP,
            symbol TEXT,
            side TEXT,
            price REAL,
            volume REAL,
            sl REAL,
            tp REAL,
            pnl REAL,
            reason TEXT,
            source TEXT,
            payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES simulation_sessions (session_id) ON DELETE CASCADE
        );
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_simulation_sessions_user ON simulation_sessions(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_simulation_sessions_status ON simulation_sessions(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_simulation_sessions_created ON simulation_sessions(created_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_simulation_trades_session ON simulation_trades(session_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_simulation_trades_time ON simulation_trades(time)"
    )

    conn.commit()
    conn.close()
    print("Simulator session tables migrated successfully.")


if __name__ == "__main__":
    main()
