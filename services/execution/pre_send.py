"""Pre-send validation orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from services.utils import Clock
from services.utils.logger import logger
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

    symbol = request.current_proposal.payload.symbol
    metadata = metadata_cache.get(symbol)
    if metadata is None:
        logger.error(
            "Symbol metadata not found — blocking pre-send",
            component="execution.pre_send",
            symbol=symbol,
        )
        raise LookupError(f"symbol metadata not found: {symbol}")

    logger.debug(
        "Running pre-send readiness validation",
        component="execution.pre_send",
        symbol=symbol,
        fill_mode=request.requested_fill_mode,
        terminal_connected=request.terminal_connected,
    )

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
    result = aggregate_readiness_results(checks)

    if not result.allowed:
        logger.warning(
            "Pre-send validation blocked execution",
            component="execution.pre_send",
            symbol=symbol,
            reason_codes=result.reason_codes,
        )
    else:
        logger.debug(
            "Pre-send validation passed",
            component="execution.pre_send",
            symbol=symbol,
        )

    return result

