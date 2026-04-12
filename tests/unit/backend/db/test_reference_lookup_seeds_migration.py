from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import apply_pending_migrations


def test_reference_lookup_seed_integrity(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        workflow_count = connection.execute(
            "SELECT COUNT(*) FROM ref_workflow_states"
        ).fetchone()[0]
        proposal_count = connection.execute(
            "SELECT COUNT(*) FROM ref_proposal_states"
        ).fetchone()[0]
        operating_modes = connection.execute(
            "SELECT code, label FROM ref_operating_modes ORDER BY sort_order"
        ).fetchall()
        strategy_states = {
            row[0]
            for row in connection.execute(
                "SELECT code FROM ref_strategy_lifecycle_states"
            ).fetchall()
        }
        approval_states = {
            row[0]
            for row in connection.execute(
                "SELECT code FROM ref_approval_states"
            ).fetchall()
        }
    finally:
        connection.close()

    assert workflow_count == 14
    assert proposal_count == 14
    assert operating_modes[0] == ("MODE-000", "Research Only")
    assert operating_modes[-1] == ("MODE-004", "Bounded Autonomous Live")
    assert "LIVE_PRODUCTION" in strategy_states
    assert "PARTIALLY_APPROVED" in approval_states
