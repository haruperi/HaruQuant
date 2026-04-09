"""Exposure and concentration primitives for deterministic risk checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionExposure:
    """Normalized position input used by exposure and concentration calculators."""

    symbol: str
    currency: str
    strategy_family: str
    notional_exposure: float
    direction: str

    @property
    def signed_exposure(self) -> float:
        if self.direction == "buy":
            return self.notional_exposure
        if self.direction == "sell":
            return -self.notional_exposure
        raise ValueError(f"unsupported direction: {self.direction}")


@dataclass(frozen=True)
class ExposureSummary:
    """Portfolio-level gross and net exposure summary."""

    gross_exposure: float
    net_exposure: float
    position_count: int


def calculate_exposure_summary(positions: tuple[PositionExposure, ...]) -> ExposureSummary:
    """Calculate gross and net exposure from normalized open positions."""

    gross_exposure = sum(abs(position.notional_exposure) for position in positions)
    net_exposure = sum(position.signed_exposure for position in positions)
    return ExposureSummary(
        gross_exposure=gross_exposure,
        net_exposure=net_exposure,
        position_count=len(positions),
    )


__all__ = [
    "ExposureSummary",
    "PositionExposure",
    "calculate_exposure_summary",
]
