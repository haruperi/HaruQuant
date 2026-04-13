from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import apply_pending_migrations, default_migrations_dir


def test_execution_receipts_migration_supports_normalized_receipt_insert(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review setup", "{}", "user", "operator_001", "{}", "[]"))
        connection.execute("INSERT INTO core_trade_hypotheses (hypothesis_id, workflow_id, strategy_id, symbol, direction, thesis_text, entry_rationale, invalidation_rationale, stop_loss_logic_json, take_profit_logic_json, holding_horizon, confidence_score, calibration_note, strategy_family, feature_version, strategy_code_hash, evidence_bundle_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("hyp_001", "wf_001", "strat_001", "EURUSD", "long", "Momentum", "Breakout", "Loss of support", '{"type":"atr_stop"}', '{"type":"rr_target"}', "intraday", 0.82, None, "fx_momentum", "v1", "hash_001", None))
        connection.execute("INSERT INTO core_trade_proposals (proposal_id, workflow_id, hypothesis_id, state, symbol, direction, candidate_price_logic_json, proposed_size_json, operating_envelope_json, session_restrictions_json, expiry_at, transformation_version, readiness_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("prop_001", "wf_001", "hyp_001", "READY_FOR_RISK", "EURUSD", "buy", '{"type":"limit"}', '{"units":1000}', '{"max_slippage_bps":5}', '{"session":"london"}', "2026-04-08T12:00:00Z", "v1", "ready_for_risk"))
        connection.execute("INSERT INTO risk_risk_assessment_requests (risk_request_id, workflow_id, proposal_id, action_type, account_snapshot_ref, portfolio_snapshot_ref, market_snapshot_ref, requested_freshness_json, strategy_lifecycle_state, active_policy_bundle_json, compliance_profile_id, current_kill_switch_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("risk_req_001", "wf_001", "prop_001", "open_position", "acct_snap_001", "port_snap_001", "mkt_snap_001", '{"market":"fresh"}', "PAPER_VERIFIED", '{"policy_version":"risk_policy_1"}', None, "DISARMED"))
        connection.execute("INSERT INTO risk_risk_decisions (risk_decision_id, risk_request_id, proposal_id, workflow_id, decision, rationale_text, risk_metrics_snapshot_json, freshness_expiry, policy_version_id, formula_version, provenance_bundle_id, approval_token, freshness_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("risk_dec_001", "risk_req_001", "prop_001", "wf_001", "APPROVE", "Within limits", '{"var":0.02}', "2026-04-08T12:30:00Z", "risk_policy_1", "formula_1", None, "approval_001", "fresh"))
        connection.execute("INSERT INTO core_execution_intents (execution_intent_id, workflow_id, proposal_id, risk_decision_id, action_type, symbol, side, order_type, size_json, price_params_json, sl_tp_params_json, idempotency_key, client_order_id, status, expiry_at, pre_send_validation_snapshot_ref) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("exec_001", "wf_001", "prop_001", "risk_dec_001", "open_position", "EURUSD", "buy", "limit", '{"units":1000}', '{"limit_price":1.0832}', '{"stop_loss":1.0800}', "idem_001", "client_001", "PENDING", "2026-04-08T12:45:00Z", "presend_001"))
        connection.execute(
            "INSERT INTO core_execution_receipts (receipt_id, execution_intent_id, broker, broker_order_id, broker_deal_id, receipt_status, requested_price, fill_price, fill_qty, spread_points, slippage_points, slippage_bps, raw_receipt_ref, broker_message, broker_retcode, authoritative_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("rcpt_001", "exec_001", "mt5", "order_001", "deal_001", "filled", 1.0832, 1.08325, 1000.0, 12.0, 0.5, 0.4, "raw_001", "filled", 10009, "FINAL"),
        )
        connection.commit()

        row = connection.execute(
            "SELECT receipt_id, execution_intent_id, broker_order_id, receipt_status FROM core_execution_receipts"
        ).fetchone()
    finally:
        connection.close()

    assert row == ("rcpt_001", "exec_001", "order_001", "filled")
