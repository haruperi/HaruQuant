from __future__ import annotations

from datetime import datetime, timezone

from backend.common import FixedClock
from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload
from backend.services.execution import SymbolMetadataCache, SymbolMetadataCacheEntry
from backend.services.execution.pre_send import PreSendValidationRequest, run_pre_send_validation


def _proposal(*, symbol: str = "EURUSD") -> TradeProposal:
    return TradeProposal(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_prop",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="paper",
        operating_mode="MODE-002",
        payload=TradeProposalPayload(
            proposal_id="prop_001",
            source_hypothesis_id="hyp_001",
            symbol=symbol,
            direction="buy",
            candidate_price_logic={"entry_rationale": "retest"},
            proposed_size={"units": 1000},
            operating_envelope={"max_spread_pips": 1.5},
            session_restrictions={},
            expiry_at=datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc),
            transformation_version="proposal_v1",
            readiness_state="ready_for_risk",
        ),
    )


def _decision() -> RiskAssessmentDecision:
    return RiskAssessmentDecision(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_risk",
        timestamp_utc="2026-04-09T10:01:00Z",
        originator=Originator(type="service", id="risk_governor"),
        environment="paper",
        operating_mode="MODE-002",
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id="risk_001",
            proposal_id="prop_001",
            decision="APPROVE",
            reasons=["approved"],
            limit_constraints=[],
            risk_metrics_snapshot={"var_95": 1.2},
            freshness_expiry=datetime(2026, 4, 9, 10, 10, tzinfo=timezone.utc),
            policy_version="pol_001",
            formula_version="formula_v1",
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id="bundle_001",
                account_snapshot_ref="acct_001",
                market_snapshot_ref="mkt_001",
            ),
        ),
    )


def _cache() -> SymbolMetadataCache:
    cache = SymbolMetadataCache()
    cache.put(
        SymbolMetadataCacheEntry(
            snapshot_id="snap_001",
            symbol="EURUSD",
            observed_at=datetime(2026, 4, 9, 10, 0, tzinfo=timezone.utc),
            market_open=True,
            tradable=True,
            supported_fill_modes=("fok", "ioc"),
            stop_level_points=10,
            freeze_level_points=5,
            tick_size=0.00001,
            point_value=0.0001,
            contract_size=100000,
            max_age_seconds=30,
        )
    )
    return cache


def test_run_pre_send_validation_returns_aggregate_success() -> None:
    result = run_pre_send_validation(
        PreSendValidationRequest(
            approved_proposal=_proposal(),
            current_proposal=_proposal(),
            risk_decision=_decision(),
            requested_fill_mode="fok",
            terminal_connected=True,
            stop_distance_points=12,
        ),
        metadata_cache=_cache(),
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 10, tzinfo=timezone.utc)),
    )
    assert result.allowed is True


def test_run_pre_send_validation_fails_closed_on_readiness_chain_errors() -> None:
    result = run_pre_send_validation(
        PreSendValidationRequest(
            approved_proposal=_proposal(),
            current_proposal=_proposal(symbol="EURUSD"),
            risk_decision=_decision(),
            requested_fill_mode="unsupported",
            terminal_connected=False,
            stop_distance_points=1,
        ),
        metadata_cache=_cache(),
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 40, tzinfo=timezone.utc)),
    )
    assert result.allowed is False
    assert "stale_price_snapshot" in result.reason_codes
    assert "unsupported_fill_mode" in result.reason_codes
    assert "terminal_disconnected" in result.reason_codes
