from __future__ import annotations

from datetime import datetime, timezone
from statistics import quantiles
from time import perf_counter

from apps.core import FixedClock
from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend.contracts.trade_proposal.model import TradeProposal, TradeProposalPayload
from backend.services.execution import SymbolMetadataCache, SymbolMetadataCacheEntry, run_pre_send_validation
from backend.services.execution.pre_send import PreSendValidationRequest


UTC = timezone.utc


def _p95(samples_ms: list[float]) -> float:
    return quantiles(samples_ms, n=100)[94]


def _proposal() -> TradeProposal:
    return TradeProposal(
        workflow_id="wf_perf_001",
        correlation_id="corr_perf_001",
        causation_id="evt_prop_perf_001",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="agent", id="strategy_agent"),
        environment="prod",
        operating_mode="MODE-003",
        compliance_profile_id="comp_uae_enterprise",
        payload=TradeProposalPayload(
            proposal_id="prop_perf_001",
            source_hypothesis_id="hyp_perf_001",
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


def _decision() -> RiskAssessmentDecision:
    return RiskAssessmentDecision(
        workflow_id="wf_perf_001",
        correlation_id="corr_perf_001",
        causation_id="evt_risk_perf_001",
        timestamp_utc="2026-04-09T10:01:00Z",
        originator=Originator(type="service", id="risk_governor"),
        environment="prod",
        operating_mode="MODE-003",
        compliance_profile_id="comp_uae_enterprise",
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id="risk_perf_001",
            proposal_id="prop_perf_001",
            decision="APPROVE",
            reasons=["within live limits"],
            limit_constraints=[],
            risk_metrics_snapshot={"var_95": 1.0},
            freshness_expiry=datetime(2026, 4, 9, 10, 10, tzinfo=UTC),
            policy_version="pol_001",
            formula_version="formula_v1",
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id="bundle_perf_001",
                account_snapshot_ref="acct_perf_001",
                market_snapshot_ref="mkt_perf_001",
            ),
            approval_token="approval_perf_001",
        ),
    )


def test_execution_readiness_validation_p95_under_400ms() -> None:
    proposal = _proposal()
    decision = _decision()
    metadata_cache = SymbolMetadataCache()
    metadata_cache.put(
        SymbolMetadataCacheEntry(
            snapshot_id="meta_perf_001",
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

    samples_ms: list[float] = []
    for _ in range(250):
        started = perf_counter()
        readiness = run_pre_send_validation(
            PreSendValidationRequest(
                approved_proposal=proposal,
                current_proposal=proposal,
                risk_decision=decision,
                requested_fill_mode="market",
                terminal_connected=True,
                stop_distance_points=20,
            ),
            metadata_cache=metadata_cache,
            clock=FixedClock(datetime(2026, 4, 9, 10, 2, 5, tzinfo=UTC)),
        )
        samples_ms.append((perf_counter() - started) * 1000)
        assert readiness.allowed is True

    assert _p95(samples_ms) <= 400.0

