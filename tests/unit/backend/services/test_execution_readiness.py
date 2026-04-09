from __future__ import annotations

from datetime import datetime, timezone

from apps.core import FixedClock
from backend.contracts.common import Originator
from backend.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)
from backend.contracts.trade_proposal.model import TradeProposal
from backend.services import (
    aggregate_readiness_results,
    SymbolMetadataCacheEntry,
    validate_fill_mode_compatibility,
    validate_market_open,
    validate_price_freshness,
    validate_risk_decision_for_execution,
    validate_stop_and_freeze_levels,
    validate_terminal_connectivity,
    validate_symbol_tradability,
)


UTC = timezone.utc


def _metadata(*, market_open: bool = True, tradable: bool = True) -> SymbolMetadataCacheEntry:
    return SymbolMetadataCacheEntry(
        snapshot_id="meta_001",
        symbol="EURUSD",
        observed_at=datetime(2026, 4, 9, 10, 0, tzinfo=UTC),
        market_open=market_open,
        tradable=tradable,
        supported_fill_modes=("IOC", "FOK"),
        stop_level_points=10,
        freeze_level_points=5,
        tick_size=0.0001,
        point_value=10.0,
        contract_size=100000.0,
        max_age_seconds=5,
    )


def _proposal(*, size_units: int) -> TradeProposal:
    return TradeProposal.model_validate(
        {
            "workflow_id": "wf_001",
            "correlation_id": "corr_001",
            "causation_id": "evt_001",
            "timestamp_utc": "2026-04-09T10:00:00Z",
            "originator": {"type": "service", "id": "proposal-service"},
            "environment": "dev",
            "operating_mode": "MODE-002",
            "contract_type": "TradeProposal",
            "payload": {
                "proposal_id": "prop_001",
                "source_hypothesis_id": "hyp_001",
                "symbol": "EURUSD",
                "direction": "buy",
                "candidate_price_logic": {"entry": "market"},
                "proposed_size": {"units": size_units},
                "operating_envelope": {"strategy_id": "strat_001"},
                "session_restrictions": {"session": "london"},
                "expiry_at": "2026-04-09T10:05:00Z",
                "transformation_version": "proposal_v1",
                "readiness_state": "ready_for_risk",
            },
        }
    )


def _risk_decision() -> RiskAssessmentDecision:
    return RiskAssessmentDecision(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_001",
        originator=Originator(type="service", id="risk-governor"),
        environment="dev",
        operating_mode="MODE-002",
        payload=RiskAssessmentDecisionPayload(
            risk_decision_id="risk_001",
            proposal_id="prop_001",
            decision="APPROVE",
            reasons=["ok"],
            limit_constraints=[],
            risk_metrics_snapshot={"margin_utilization": 0.3},
            freshness_expiry=datetime(2026, 4, 9, 10, 0, 30, tzinfo=UTC),
            policy_version="risk_bundle_v1",
            formula_version="formula_v1",
            provenance_bundle_ref=ProvenanceBundleRef(
                bundle_id="bundle_001",
                account_snapshot_ref="acct_001",
                market_snapshot_ref="mkt_001",
            ),
        ),
    )


def test_validate_market_open_rejects_closed_market() -> None:
    result = validate_market_open(_metadata(market_open=False))

    assert result.allowed is False
    assert result.reason_codes == ("market_closed",)


def test_validate_symbol_tradability_rejects_non_tradable_symbol() -> None:
    result = validate_symbol_tradability(_metadata(tradable=False))

    assert result.allowed is False
    assert result.reason_codes == ("symbol_not_tradable",)


def test_validate_price_freshness_rejects_stale_snapshot() -> None:
    result = validate_price_freshness(
        _metadata(),
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 6, tzinfo=UTC)),
    )

    assert result.allowed is False
    assert result.reason_codes == ("stale_price_snapshot",)


def test_validate_stop_and_freeze_levels_rejects_too_close_distances() -> None:
    result = validate_stop_and_freeze_levels(
        _metadata(),
        stop_distance_points=8,
        modify_distance_points=3,
    )

    assert result.allowed is False
    assert result.reason_codes == ("stop_level_too_close", "freeze_level_too_close")


def test_validate_fill_mode_compatibility_rejects_unsupported_mode() -> None:
    result = validate_fill_mode_compatibility(
        _metadata(),
        requested_fill_mode="RETURN",
    )

    assert result.allowed is False
    assert result.reason_codes == ("unsupported_fill_mode",)


def test_validate_terminal_connectivity_rejects_disconnected_terminal() -> None:
    result = validate_terminal_connectivity(connected=False)

    assert result.allowed is False
    assert result.reason_codes == ("terminal_disconnected",)


def test_validate_risk_decision_for_execution_rejects_stale_or_mismatched_approval() -> None:
    result = validate_risk_decision_for_execution(
        _risk_decision(),
        approved_proposal=_proposal(size_units=1000),
        current_proposal=_proposal(size_units=1200),
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 31, tzinfo=UTC)),
    )

    assert result.allowed is False
    assert result.reason_codes == ("risk_decision_expired", "material_proposal_change")


def test_aggregate_readiness_results_collects_all_failure_reasons() -> None:
    aggregate = aggregate_readiness_results(
        (
            validate_market_open(_metadata(market_open=False)),
            validate_terminal_connectivity(connected=False),
        )
    )

    assert aggregate.allowed is False
    assert aggregate.reason_codes == ("market_closed", "terminal_disconnected")
    assert len(aggregate.checks) == 2
