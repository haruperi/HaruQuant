from __future__ import annotations

from pathlib import Path

from data.database import ProposalRepository, apply_pending_migrations, default_migrations_dir


def test_proposal_repository_persists_state_transitions(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ProposalRepository(database_path)

    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review EURUSD setup", "{}", "user", "operator_001", "{}", "[]"),
        )
        connection.execute(
            "INSERT INTO core_trade_hypotheses (hypothesis_id, workflow_id, strategy_id, symbol, direction, thesis_text, entry_rationale, invalidation_rationale, stop_loss_logic_json, take_profit_logic_json, holding_horizon, confidence_score, calibration_note, strategy_family, feature_version, strategy_code_hash, evidence_bundle_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("hyp_001", "wf_001", "strat_001", "EURUSD", "long", "Momentum continuation", "Breakout above range", "Loss of trend support", '{"type":"atr_stop"}', '{"type":"rr_target"}', "intraday", 0.82, None, "fx_momentum", "v1", "hash_001", None),
        )

    created = repository.create_proposal(
        proposal_id="prop_001",
        workflow_id="wf_001",
        hypothesis_id="hyp_001",
        state="DRAFT",
        symbol="EURUSD",
        direction="buy",
        candidate_price_logic_json='{"type":"limit"}',
        proposed_size_json='{"units":1000}',
        transformation_version="v1",
        readiness_state="draft",
    )
    assert created.state == "DRAFT"

    updated = repository.update_state(
        proposal_id="prop_001",
        state="READY_FOR_RISK",
        readiness_state="ready_for_risk",
        expiry_at="2026-04-08T12:00:00Z",
    )
    assert updated.state == "READY_FOR_RISK"
    assert updated.readiness_state == "ready_for_risk"
    assert updated.expiry_at == "2026-04-08T12:00:00Z"
