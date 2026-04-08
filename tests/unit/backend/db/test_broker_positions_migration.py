from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.db import apply_pending_migrations


def test_broker_positions_migration_supports_snapshot_insert(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            INSERT INTO core_broker_positions (
                broker_position_id, environment, account_id, symbol, side,
                quantity, avg_price, stop_loss, take_profit,
                authoritative_snapshot_at, local_status, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "bp_001", "paper", "acct_001", "EURUSD", "buy",
                1000.0, 1.0832, 1.0800, 1.0890,
                "2026-04-08T12:40:00Z", "OPEN", '{"source":"broker_sync"}'
            ),
        )
        connection.commit()

        row = connection.execute(
            "SELECT broker_position_id, account_id, symbol, local_status FROM core_broker_positions"
        ).fetchone()
    finally:
        connection.close()

    assert row == ("bp_001", "acct_001", "EURUSD", "OPEN")
