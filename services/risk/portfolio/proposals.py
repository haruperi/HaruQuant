"""Advisory-only portfolio proposal generators."""

from __future__ import annotations

from dataclasses import dataclass, field

from services.risk import PositionExposure

from services.utils.logger import logger

@dataclass(frozen=True)
class AdvisoryPortfolioProposal:
    """Minimal advisory-only portfolio action proposal."""

    action_type: str
    rationale: str
    advisory_only: bool = True
    symbol: str | None = None
    target_size: dict[str, float] = field(default_factory=dict)
    target_allocations: dict[str, float] = field(default_factory=dict)
    hedge_symbols: tuple[str, ...] = ()
    affected_symbols: tuple[str, ...] = ()


def generate_resize_proposal(
    *,
    position: PositionExposure,
    target_notional_exposure: float,
) -> AdvisoryPortfolioProposal:
    """Generate an advisory resize proposal for one position."""

    if target_notional_exposure < 0:
        raise ValueError("target_notional_exposure must be non-negative")

    delta = target_notional_exposure - position.notional_exposure
    direction = "increase" if delta > 0 else "decrease"
    return AdvisoryPortfolioProposal(
        action_type="resize",
        symbol=position.symbol,
        target_size={"current": position.notional_exposure, "target": target_notional_exposure},
        affected_symbols=(position.symbol,),
        rationale=f"{direction} {position.symbol} exposure toward target notional size",
    )


def generate_rebalance_proposal(
    *,
    target_allocations: dict[str, float],
) -> AdvisoryPortfolioProposal:
    """Generate an advisory rebalance proposal for target portfolio weights."""

    if not target_allocations:
        raise ValueError("target_allocations must not be empty")
    allocation_total = sum(target_allocations.values())
    if allocation_total <= 0:
        raise ValueError("target_allocations must sum to a positive value")

    normalized_allocations = {
        symbol: value / allocation_total
        for symbol, value in sorted(target_allocations.items())
    }
    return AdvisoryPortfolioProposal(
        action_type="rebalance",
        target_allocations=normalized_allocations,
        affected_symbols=tuple(normalized_allocations.keys()),
        rationale="rebalance portfolio weights toward target symbol allocation mix",
    )


def generate_hedge_proposal(
    *,
    source_position: PositionExposure,
    hedge_symbols: tuple[str, ...],
) -> AdvisoryPortfolioProposal:
    """Generate an advisory hedge proposal around one source position."""

    if not hedge_symbols:
        raise ValueError("hedge_symbols must not be empty")

    return AdvisoryPortfolioProposal(
        action_type="hedge",
        symbol=source_position.symbol,
        hedge_symbols=hedge_symbols,
        affected_symbols=(source_position.symbol, *hedge_symbols),
        rationale=f"introduce hedge coverage for {source_position.symbol} concentration",
    )


def generate_derisk_proposal(
    *,
    affected_symbols: tuple[str, ...],
    target_reduction_ratio: float,
) -> AdvisoryPortfolioProposal:
    """Generate an advisory de-risking proposal for one or more symbols."""

    if not affected_symbols:
        raise ValueError("affected_symbols must not be empty")
    if not 0 < target_reduction_ratio <= 1:
        raise ValueError("target_reduction_ratio must be within (0, 1]")

    return AdvisoryPortfolioProposal(
        action_type="de_risk",
        affected_symbols=affected_symbols,
        target_size={"reduction_ratio": target_reduction_ratio},
        rationale="reduce portfolio risk exposure across the selected symbols",
    )


__all__ = [
    "AdvisoryPortfolioProposal",
    "generate_derisk_proposal",
    "generate_hedge_proposal",
    "generate_rebalance_proposal",
    "generate_resize_proposal",
]
