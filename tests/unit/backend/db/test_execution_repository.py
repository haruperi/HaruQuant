from __future__ import annotations

from pathlib import Path

from data.database import ExecutionRepository, apply_pending_migrations, default_migrations_dir


def test_execution_repository_supports_idempotency_and_attempt_persistence(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ExecutionRepository(database_path)

    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review setup", "{}", "user", "operator_001", "{}", "[]"),
        )
        connection.execute(
            "INSERT INTO core_trade_hypotheses (hypothesis_id, workflow_id, strategy_id, symbol, direction, thesis_text, entry_rationale, invalidation_rationale, stop_loss_logic_json, take_profit_logic_json, holding_horizon, confidence_score, calibration_note, strategy_family, feature_version, strategy_code_hash, evidence_bundle_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("hyp_001", "wf_001", "strat_001", "EURUSD", "long", "Momentum", "Breakout", "Loss of support", '{"type":"atr_stop"}', '{"type":"rr_target"}', "intraday", 0.82, None, "fx_momentum", "v1", "hash_001", None),
        )
        connection.execute(
            "INSERT INTO core_trade_proposals (proposal_id, workflow_id, hypothesis_id, state, symbol, direction, candidate_price_logic_json, proposed_size_json, operating_envelope_json, session_restrictions_json, expiry_at, transformation_version, readiness_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("prop_001", "wf_001", "hyp_001", "READY_FOR_RISK", "EURUSD", "buy", '{"type":"limit"}', '{"units":1000}', '{"max_slippage_bps":5}', '{"session":"london"}', "2026-04-08T12:00:00Z", "v1", "ready_for_risk"),
        )
        connection.execute(
            "INSERT INTO risk_risk_assessment_requests (risk_request_id, workflow_id, proposal_id, action_type, account_snapshot_ref, portfolio_snapshot_ref, market_snapshot_ref, requested_freshness_json, strategy_lifecycle_state, active_policy_bundle_json, compliance_profile_id, current_kill_switch_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("risk_req_001", "wf_001", "prop_001", "open_position", None, None, None, '{}', "PAPER_APPROVED", '{"policy_version":"risk_policy_1"}', None, "ARMED"),
        )
        connection.execute(
            "INSERT INTO risk_risk_decisions (risk_decision_id, risk_request_id, proposal_id, workflow_id, decision, rationale_text, risk_metrics_snapshot_json, freshness_expiry, policy_version_id, formula_version, provenance_bundle_id, approval_token, freshness_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("risk_dec_001", "risk_req_001", "prop_001", "wf_001", "APPROVE", "Within limits", '{"var":0.02}', "2026-04-08T12:30:00Z", "risk_policy_1", "formula_1", None, "approval_001", "fresh"),
        )

    intent = repository.create_intent(
        execution_intent_id="exec_001",
        workflow_id="wf_001",
        proposal_id="prop_001",
        risk_decision_id="risk_dec_001",
        action_type="open_position",
        symbol="EURUSD",
        side="buy",
        order_type="limit",
        size_json='{"units":1000}',
        idempotency_key="idem_001",
        status="PENDING",
    )
    assert intent.execution_intent_id == "exec_001"

    by_key = repository.get_intent_by_idempotency_key("idem_001")
    assert by_key is not None
    assert by_key.execution_intent_id == "exec_001"

    attempt = repository.add_send_attempt(
        execution_intent_id="exec_001",
        attempt_no=1,
        submitted_payload_hash="hash_001",
        transport_status="sent",
        broker_request_ref="broker_req_001",
        latency_ms=120,
    )
    assert attempt.attempt_no == 1

    receipt = repository.add_receipt(
        receipt_id="rcpt_001",
        execution_intent_id="exec_001",
        receipt_status="filled",
        broker_order_id="order_001",
        broker_deal_id="deal_001",
        requested_price=1.0832,
        fill_price=1.08325,
        fill_qty=1000.0,
    )
    assert receipt.receipt_status == "filled"

    reconciliation = repository.add_reconciliation_run(
        execution_intent_id="exec_001",
        run_reason="restart_recovery",
        result_state="MATCHED",
        broker_truth_json='{"broker_status":"filled"}',
        local_truth_json='{"local_status":"filled"}',
    )
    assert reconciliation.result_state == "MATCHED"
