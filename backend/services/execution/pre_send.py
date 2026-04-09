"""Pre-send validation orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from apps.core import Clock
from backend.contracts.risk_assessment_decision.model import RiskAssessmentDecision
from backend.contracts.trade_proposal.model import TradeProposal

from .metadata_cache import SymbolMetadataCache
from .readiness import (
    ReadinessAggregateResult,
    aggregate_readiness_results,
    validate_fill_mode_compatibility,
    validate_market_open,
    validate_price_freshness,
    validate_risk_decision_for_execution,
    validate_stop_and_freeze_levels,
    validate_symbol_tradability,
    validate_terminal_connectivity,
)


@dataclass(frozen=True)
class PreSendValidationRequest:
    """Inputs required to orchestrate the execution readiness chain."""

    approved_proposal: TradeProposal
    current_proposal: TradeProposal
    risk_decision: RiskAssessmentDecision
    requested_fill_mode: str
    terminal_connected: bool
    stop_distance_points: float | None = None
    modify_distance_points: float | None = None


def run_pre_send_validation(
    request: PreSendValidationRequest,
    *,
    metadata_cache: SymbolMetadataCache,
    clock: Clock | None = None,
) -> ReadinessAggregateResult:
    """Run the full fail-closed readiness chain before broker send."""

    metadata = metadata_cache.get(request.current_proposal.payload.symbol)
    if metadata is None:
        raise LookupError(f"symbol metadata not found: {request.current_proposal.payload.symbol}")

    checks = (
        validate_market_open(metadata),
        validate_symbol_tradability(metadata),
        validate_price_freshness(metadata, clock=clock),
        validate_stop_and_freeze_levels(
            metadata,
            stop_distance_points=request.stop_distance_points,
            modify_distance_points=request.modify_distance_points,
        ),
        validate_fill_mode_compatibility(
            metadata,
            requested_fill_mode=request.requested_fill_mode,
        ),
        validate_terminal_connectivity(connected=request.terminal_connected),
        validate_risk_decision_for_execution(
            request.risk_decision,
            approved_proposal=request.approved_proposal,
            current_proposal=request.current_proposal,
            clock=clock,
        ),
    )
    return aggregate_readiness_results(checks)
