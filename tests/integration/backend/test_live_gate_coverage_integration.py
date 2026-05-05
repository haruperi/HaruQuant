from __future__ import annotations

from datetime import datetime, timezone

import pytest

from haruquant.utils import FixedClock, ValidationError
from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload
from backend.mcp.mt5_mcp import MT5ToolAuthorizationError, MT5ToolAuthorizer
from backend.orchestration.workflow import KillSwitchState
from haruquant.risk import require_live_execution_profile
from haruquant.execution import SymbolMetadataCache, SymbolMetadataCacheEntry, run_pre_send_validation
from haruquant.execution import PreSendValidationRequest
from haruquant.risk import evaluate_new_entry_block


UTC = timezone.utc


def _proposal() -> TradeProposal:
    return TradeProposal(
        workflow_id="wf_live_gate_001",
        correlation_id="corr_live_gate_001",
        causation_id="evt_prop_001",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="prod",
        operating_mode="MODE-003",
        compliance_profile_id="comp_uae_enterprise",
        payload=TradeProposalPayload(
            proposal_id="prop_live_gate_001",
            source_hypothesis_id="hyp_live_gate_001",
            symbol="EURUSD",
            direction="buy",
            candidate_price_logic={"entry_price": 1.0842},
            proposed_size={"units": 1000},
            operating_envelope={"autonomy_ceiling": "human_approved_live"},
            session_restrictions={"session": "london"},
            expiry_at=datetime(2026, 4, 9, 10, 20, tzinfo=UTC),
            transformation_version="proposal_v1",
            readiness_state="ready_for_risk",
        ),
    )


def _decision(*, freshness_expiry: datetime) -> RiskAssessmentDecision:
    return RiskAssessmentDecision(
        workflow_id="wf_live_gate_001",
        correlation_id="corr_live_gate_001",
        causation_id="evt_risk_001",
        timestamp_utc="2026-04-09T10:01:00Z",
        originator=Originator(type="service", id="risk_governor"),
        environment="prod",
        operating_mode="MODE-003",
        compliance_profile_id="comp_uae_enterprise",
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id="risk_live_gate_001",
            proposal_id="prop_live_gate_001",
            decision="APPROVE",
            reasons=["within live limits"],
            limit_constraints=[],
            risk_metrics_snapshot={"var_95": 1.0},
            freshness_expiry=freshness_expiry,
            policy_version="pol_001",
            formula_version="formula_v1",
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id="bundle_live_gate_001",
                account_snapshot_ref="acct_live_gate_001",
                market_snapshot_ref="mkt_live_gate_001",
            ),
            approval_token="approval_live_gate_001",
        ),
    )


def test_every_live_path_has_hard_technical_gate_before_broker_mutation() -> None:
    proposal = _proposal()

    with pytest.raises(ValidationError, match="compliance profile"):
        require_live_execution_profile(
            compliance_profile_id=None,
            operating_mode="MODE-003",
        )

    kill_switch_block = evaluate_new_entry_block(KillSwitchState.HARD_TRIGGERED)
    assert kill_switch_block.blocked is True

    metadata_cache = SymbolMetadataCache()
    metadata_cache.put(
        SymbolMetadataCacheEntry(
            snapshot_id="meta_live_gate_001",
            symbol="EURUSD",
            observed_at=datetime(2026, 4, 9, 10, 2, tzinfo=UTC),
            market_open=True,
            tradable=True,
            supported_fill_modes=("market",),
            stop_level_points=10,
            freeze_level_points=5,
            tick_size=0.0001,
            point_value=10.0,
            contract_size=100000.0,
            max_age_seconds=30,
        )
    )
    readiness = run_pre_send_validation(
        PreSendValidationRequest(
            approved_proposal=proposal,
            current_proposal=proposal,
            risk_decision=_decision(freshness_expiry=datetime(2026, 4, 9, 10, 2, tzinfo=UTC)),
            requested_fill_mode="market",
            terminal_connected=True,
            stop_distance_points=20,
        ),
        metadata_cache=metadata_cache,
        clock=FixedClock(datetime(2026, 4, 9, 10, 2, 5, tzinfo=UTC)),
    )
    assert readiness.allowed is False
    assert "risk_decision_expired" in readiness.reason_codes

    with pytest.raises(MT5ToolAuthorizationError, match="not authorized"):
        MT5ToolAuthorizer().authorize(tool_name="mt5.place_order", role="operator")

