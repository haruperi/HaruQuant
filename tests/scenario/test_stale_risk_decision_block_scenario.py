from __future__ import annotations

from datetime import datetime, timezone

from services.utils import FixedClock
from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload
from services.execution import SymbolMetadataCache, SymbolMetadataCacheEntry, run_pre_send_validation
from services.execution.pre_send import PreSendValidationRequest


UTC = timezone.utc


def test_live_entry_blocked_when_risk_decision_is_stale() -> None:
    proposal = TradeProposal(
        workflow_id="wf_live_stale_001",
        correlation_id="corr_live_stale_001",
        causation_id="evt_prop_live_stale",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="prod",
        operating_mode="MODE-003",
        compliance_profile_id="comp_uae_enterprise",
        payload=TradeProposalPayload(
            proposal_id="prop_live_stale_001",
            source_hypothesis_id="hyp_live_stale_001",
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
    stale_decision = RiskAssessmentDecision(
        workflow_id="wf_live_stale_001",
        correlation_id="corr_live_stale_001",
        causation_id="evt_risk_live_stale",
        timestamp_utc="2026-04-09T10:01:00Z",
        originator=Originator(type="service", id="risk_governor"),
        environment="prod",
        operating_mode="MODE-003",
        compliance_profile_id="comp_uae_enterprise",
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id="risk_live_stale_001",
            proposal_id="prop_live_stale_001",
            decision="APPROVE",
            reasons=["originally within limits"],
            limit_constraints=[],
            risk_metrics_snapshot={"var_95": 1.1},
            freshness_expiry=datetime(2026, 4, 9, 10, 2, tzinfo=UTC),
            policy_version="pol_001",
            formula_version="formula_v1",
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id="bundle_live_stale_001",
                account_snapshot_ref="acct_live_stale_001",
                market_snapshot_ref="mkt_live_stale_001",
            ),
        ),
    )

    metadata_cache = SymbolMetadataCache()
    metadata_cache.put(
        SymbolMetadataCacheEntry(
            snapshot_id="meta_live_stale_001",
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
            risk_decision=stale_decision,
            requested_fill_mode="market",
            terminal_connected=True,
            stop_distance_points=20,
        ),
        metadata_cache=metadata_cache,
        clock=FixedClock(datetime(2026, 4, 9, 10, 2, 5, tzinfo=UTC)),
    )

    assert readiness.allowed is False
    assert "risk_decision_expired" in readiness.reason_codes

