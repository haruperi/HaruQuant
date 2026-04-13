from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import apply_pending_migrations, default_migrations_dir


def test_trade_hypotheses_migration_enforces_confidence_constraint(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO core_workflows (
                workflow_id, workflow_type, environment, operating_mode, state,
                objective, scope_json, initiator_type, initiator_id,
                timeout_policy_json, stop_conditions_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "wf_001", "trade_review", "paper", "MODE-002", "CREATED",
                "Review EURUSD setup", "{}", "user", "operator_001", "{}", "[]"
            ),
        )
        connection.execute(
            """
            INSERT INTO core_trade_hypotheses (
                hypothesis_id, workflow_id, strategy_id, symbol, direction,
                thesis_text, entry_rationale, invalidation_rationale,
                stop_loss_logic_json, take_profit_logic_json, holding_horizon,
                confidence_score, calibration_note, strategy_family,
                feature_version, strategy_code_hash, evidence_bundle_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "hyp_001", "wf_001", "strat_001", "EURUSD", "long",
                "Momentum continuation", "Breakout above range", "Loss of trend support",
                '{"type":"atr_stop"}', '{"type":"rr_target"}', "intraday",
                0.82, "well calibrated", "fx_momentum", "v1", "hash_001", None
            ),
        )
        connection.commit()

        row = connection.execute(
            "SELECT hypothesis_id, symbol, confidence_score FROM core_trade_hypotheses"
        ).fetchone()

        failed = False
        try:
            connection.execute(
                """
                INSERT INTO core_trade_hypotheses (
                    hypothesis_id, workflow_id, strategy_id, symbol, direction,
                    thesis_text, entry_rationale, invalidation_rationale,
                    stop_loss_logic_json, take_profit_logic_json, holding_horizon,
                    confidence_score, calibration_note, strategy_family,
                    feature_version, strategy_code_hash, evidence_bundle_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "hyp_002", "wf_001", "strat_001", "GBPUSD", "short",
                    "Mean reversion", "Exhaustion at resistance", "Breakout continuation",
                    '{"type":"swing_stop"}', None, "swing",
                    1.5, None, "fx_reversion", "v1", "hash_002", None
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError:
            failed = True
            connection.rollback()
    finally:
        connection.close()

    assert row == ("hyp_001", "EURUSD", 0.82)
    assert failed is True
