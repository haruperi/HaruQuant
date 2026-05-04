from __future__ import annotations

import sqlite3

from backend.data.database import apply_pending_migrations, default_migrations_dir


def test_agentic_firm_phase4_tables_views_and_append_only_audit(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, default_migrations_dir())

    connection = sqlite3.connect(database_path)
    try:
        names = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view')"
            ).fetchall()
        }

        expected_tables = {
            "agent_tasks",
            "agent_task_events",
            "agent_tool_calls",
            "agent_observations",
            "agent_decisions",
            "evidence_refs",
            "research_reports",
            "strategy_specs",
            "strategy_reviews",
            "backtest_run_refs",
            "robustness_run_refs",
            "risk_review_refs",
            "paper_trade_refs",
            "live_trade_refs",
            "strategy_lifecycle",
            "strategy_versions",
            "strategy_status_history",
            "strategy_promotion_requests",
            "strategy_retirement_records",
            "audit_log",
        }
        expected_views = {
            "risk_approvals",
            "risk_rejections",
            "trade_proposals",
            "execution_requests",
            "execution_results",
            "execution_audit",
        }

        assert {name for name in expected_tables if names.get(name) == "table"} == expected_tables
        assert {name for name in expected_views if names.get(name) == "view"} == expected_views

        connection.execute(
            """
            INSERT INTO audit_log (
                audit_id,
                actor_name,
                action_type,
                input_hash
            ) VALUES (?, ?, ?, ?)
            """,
            ("audit-1", "ceo", "test_action", "input-hash"),
        )
        connection.commit()

        try:
            connection.execute(
                "UPDATE audit_log SET output_hash = ? WHERE audit_id = ?",
                ("changed", "audit-1"),
            )
        except sqlite3.DatabaseError as exc:
            assert "append-only" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("audit_log update should be blocked")

        try:
            connection.execute("DELETE FROM audit_log WHERE audit_id = ?", ("audit-1",))
        except sqlite3.DatabaseError as exc:
            assert "append-only" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("audit_log delete should be blocked")
    finally:
        connection.close()
