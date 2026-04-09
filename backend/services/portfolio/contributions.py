"""Marginal portfolio contribution helpers."""

from __future__ import annotations

from dataclasses import dataclass

from backend.services.risk import PositionExposure


@dataclass(frozen=True)
class MarginalRiskContribution:
    """Normalized marginal contribution for one position bucket."""

    position_key: str
    symbol: str
    strategy_family: str
    contribution_ratio: float
    gross_exposure: float


def calculate_marginal_risk_contribution(
    positions: tuple[PositionExposure, ...],
) -> tuple[MarginalRiskContribution, ...]:
    """Approximate marginal portfolio contribution from gross exposure shares."""

    total_gross = sum(abs(position.notional_exposure) for position in positions)
    if total_gross <= 0:
        return ()

    return tuple(
        MarginalRiskContribution(
            position_key=f"{position.symbol}:{position.strategy_family}:{index}",
            symbol=position.symbol,
            strategy_family=position.strategy_family,
            contribution_ratio=abs(position.notional_exposure) / total_gross,
            gross_exposure=abs(position.notional_exposure),
        )
        for index, position in enumerate(positions, start=1)
    )


__all__ = [
    "MarginalRiskContribution",
    "calculate_marginal_risk_contribution",
]
