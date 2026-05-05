from __future__ import annotations

from pathlib import Path

from data.database import RiskRepository, apply_pending_migrations, default_migrations_dir


def test_risk_repository_supports_fetch_by_token_and_expiry(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = RiskRepository(database_path)

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

    request = repository.create_request(
        risk_request_id="risk_req_001",
        workflow_id="wf_001",
        proposal_id="prop_001",
        action_type="open_position",
        strategy_lifecycle_state="PAPER_APPROVED",
        active_policy_bundle_json='{"policy_version":"risk_policy_1"}',
        current_kill_switch_state="ARMED",
    )
    assert request.risk_request_id == "risk_req_001"

    decision = repository.create_decision(
        risk_decision_id="risk_dec_001",
        risk_request_id="risk_req_001",
        proposal_id="prop_001",
        workflow_id="wf_001",
        decision="APPROVE",
        rationale_text="Within limits",
        risk_metrics_snapshot_json='{"var":0.02}',
        freshness_expiry="2026-04-08T12:30:00Z",
        policy_version_id="risk_policy_1",
        formula_version="formula_1",
        approval_token="approval_001",
    )
    assert decision.approval_token == "approval_001"

    constraint = repository.add_constraint(
        risk_decision_id="risk_dec_001",
        constraint_type="max_position_size",
        constraint_value_json='{"units":1000}',
    )
    assert constraint.constraint_type == "max_position_size"

    by_token = repository.get_decision_by_approval_token("approval_001")
    assert by_token is not None
    assert by_token.risk_decision_id == "risk_dec_001"

    expired = repository.list_decisions_expired_before("2026-04-08T13:00:00Z")
    assert [item.risk_decision_id for item in expired] == ["risk_dec_001"]
