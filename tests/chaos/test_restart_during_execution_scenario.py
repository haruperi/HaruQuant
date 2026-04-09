from __future__ import annotations

from pathlib import Path

from backend.db import ExecutionRepository, apply_pending_migrations
from backend.services.reconciliation import ReconciliationStartupLoader


def test_restart_during_execution_chaos_scenario_recovers_inflight_intent_on_startup(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ExecutionRepository(database_path)
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-003", "CREATED", "restart during execution", "{}", "user", "operator_001", "{}", "[]"),
        )
        connection.execute(
            """
            INSERT INTO core_trade_hypotheses (
                hypothesis_id, workflow_id, strategy_id, symbol, direction, thesis_text, entry_rationale, invalidation_rationale,
                stop_loss_logic_json, take_profit_logic_json, holding_horizon, confidence_score, calibration_note,
                strategy_family, feature_version, strategy_code_hash, evidence_bundle_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "hyp_001",
                "wf_001",
                "strat_001",
                "EURUSD",
                "buy",
                "Breakout continuation",
                "Retest holds",
                "Breakout fails",
                '{"type":"swing_low"}',
                '{"type":"rr_multiple","value":2}',
                "intraday",
                0.81,
                "calibrated",
                "fx_momentum",
                "v1",
                "hash_001",
                None,
            ),
        )
        connection.execute(
            """
            INSERT INTO core_trade_proposals (
                proposal_id, workflow_id, hypothesis_id, state, symbol, direction,
                candidate_price_logic_json, proposed_size_json, operating_envelope_json,
                session_restrictions_json, expiry_at, transformation_version, readiness_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "prop_001",
                "wf_001",
                "hyp_001",
                "SENT",
                "EURUSD",
                "buy",
                '{"entry_price":1.0842}',
                '{"units":1000}',
                '{"max_slippage_bps":5}',
                '{"session":"london"}',
                "2026-04-09T10:20:00Z",
                "proposal_v1",
                "ready_for_risk",
            ),
        )
        connection.execute(
            """
            INSERT INTO risk_risk_assessment_requests (
                risk_request_id, workflow_id, proposal_id, action_type, account_snapshot_ref, portfolio_snapshot_ref,
                market_snapshot_ref, requested_freshness_json, strategy_lifecycle_state, active_policy_bundle_json,
                compliance_profile_id, current_kill_switch_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "risk_req_001",
                "wf_001",
                "prop_001",
                "new_entry",
                "acct_001",
                "port_001",
                "mkt_001",
                '{"market":"fresh"}',
                "PAPER_APPROVED",
                '{"policy_version":"pol_001","formula_version":"formula_v1"}',
                "cmp_001",
                "ARMED",
            ),
        )
        connection.execute(
            """
            INSERT INTO risk_risk_decisions (
                risk_decision_id, risk_request_id, proposal_id, workflow_id, decision, rationale_text,
                risk_metrics_snapshot_json, freshness_expiry, policy_version_id, formula_version, provenance_bundle_id,
                approval_token, freshness_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "risk_001",
                "risk_req_001",
                "prop_001",
                "wf_001",
                "APPROVE",
                "Within bounded paper envelope",
                '{"var_95":1.2}',
                "2026-04-09T10:10:00Z",
                "pol_001",
                "formula_v1",
                "bundle_001",
                "approval_001",
                "fresh",
            ),
        )
    repository.create_intent(
        execution_intent_id="exec_001",
        workflow_id="wf_001",
        proposal_id="prop_001",
        risk_decision_id="risk_001",
        action_type="submit_order",
        symbol="EURUSD",
        side="buy",
        order_type="market",
        size_json="{}",
        idempotency_key="idem_001",
        status="SENT",
    )

    inflight = ReconciliationStartupLoader(repository).load_in_flight_execution_intents()

    assert [record.execution_intent_id for record in inflight] == ["exec_001"]
