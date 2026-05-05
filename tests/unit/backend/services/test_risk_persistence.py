from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import LimitConstraint
from backend.data.database import apply_pending_migrations, default_migrations_dir
from services.risk import (
    RiskDecisionEnvelopeContext,
    RiskDecisionPersistenceService,
    RiskDecisionProvenance,
    compose_risk_decision,
    pack_risk_decision_rationale_and_provenance,
)
from services.risk.restrictions import RestrictionEvaluation


UTC = timezone.utc


def test_risk_decision_persistence_service_saves_decision_and_constraints(tmp_path):
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = RiskDecisionPersistenceService(database_path)

    with service.repository._connect() as connection:  # noqa: SLF001
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
            ("risk_req_001", "wf_001", "prop_001", "new_entry", "acct_snap_001", "port_snap_001", "mkt_snap_001", '{"market_snapshot":"HOT"}', "paper", '{"policy_version":"risk_bundle_v1"}', "comp_internal", "inactive"),
        )

    composed = compose_risk_decision(
        checks=(RestrictionEvaluation(allowed=True),),
        limit_constraints=(LimitConstraint(constraint_type="max_size", value={"units": 1000}),),
    )
    packed = pack_risk_decision_rationale_and_provenance(
        composed=composed,
        context=RiskDecisionEnvelopeContext(
            workflow_id="wf_001",
            correlation_id="corr_001",
            causation_id="evt_001",
            originator=Originator(type="service", id="risk-governor"),
            environment="paper",
            operating_mode="MODE-002",
            compliance_profile_id="comp_internal",
        ),
        provenance=RiskDecisionProvenance(
            proposal_id="prop_001",
            rationale_text="All checks passed but size is capped.",
            risk_metrics_snapshot={"gross_exposure": 0.2},
            freshness_expiry=datetime(2026, 4, 9, 12, 0, tzinfo=UTC),
            policy_version="risk_bundle_v1",
            formula_version="formula_v1",
            provenance_bundle_id="bundle_001",
            account_snapshot_ref="acct_snap_001",
            market_snapshot_ref="mkt_snap_001",
            approval_token="approval_001",
        ),
        risk_decision_id="risk_001",
    )

    decision, constraints = service.save(risk_request_id="risk_req_001", packed=packed)

    assert decision.risk_decision_id == "risk_001"
    assert decision.rationale_text == "All checks passed but size is capped."
    assert decision.policy_version_id == "risk_bundle_v1"
    assert len(constraints) == 1
    assert constraints[0].constraint_type == "max_size"
