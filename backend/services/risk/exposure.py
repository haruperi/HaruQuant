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


@dataclass(frozen=True)
class ConcentrationResult:
    """Concentration summary for one grouping dimension."""

    total_gross_exposure: float
    concentrations: dict[str, float]
    threshold: float
    breached_keys: tuple[str, ...]


def calculate_exposure_summary(positions: tuple[PositionExposure, ...]) -> ExposureSummary:
    """Calculate gross and net exposure from normalized open positions."""

    gross_exposure = sum(abs(position.notional_exposure) for position in positions)
    net_exposure = sum(position.signed_exposure for position in positions)
    return ExposureSummary(
        gross_exposure=gross_exposure,
        net_exposure=net_exposure,
        position_count=len(positions),
    )


def calculate_symbol_concentration(
    positions: tuple[PositionExposure, ...],
    *,
    threshold: float,
) -> ConcentrationResult:
    """Calculate gross concentration share for each symbol."""

    gross_total = sum(abs(position.notional_exposure) for position in positions)
    concentrations: dict[str, float] = {}
    if gross_total > 0:
        for position in positions:
            concentrations[position.symbol] = concentrations.get(position.symbol, 0.0) + (
                abs(position.notional_exposure) / gross_total
            )

    breached_keys = tuple(
        key for key, value in sorted(concentrations.items()) if value > threshold
    )
    return ConcentrationResult(
        total_gross_exposure=gross_total,
        concentrations=concentrations,
        threshold=threshold,
        breached_keys=breached_keys,
    )


def calculate_currency_concentration(
    positions: tuple[PositionExposure, ...],
    *,
    threshold: float,
) -> ConcentrationResult:
    """Calculate gross concentration share for each currency bucket."""

    gross_total = sum(abs(position.notional_exposure) for position in positions)
    concentrations: dict[str, float] = {}
    if gross_total > 0:
        for position in positions:
            concentrations[position.currency] = concentrations.get(position.currency, 0.0) + (
                abs(position.notional_exposure) / gross_total
            )

    breached_keys = tuple(
        key for key, value in sorted(concentrations.items()) if value > threshold
    )
    return ConcentrationResult(
        total_gross_exposure=gross_total,
        concentrations=concentrations,
        threshold=threshold,
        breached_keys=breached_keys,
    )


def calculate_strategy_family_concentration(
    positions: tuple[PositionExposure, ...],
    *,
    threshold: float,
) -> ConcentrationResult:
    """Calculate gross concentration share for each strategy family."""

    gross_total = sum(abs(position.notional_exposure) for position in positions)
    concentrations: dict[str, float] = {}
    if gross_total > 0:
        for position in positions:
            concentrations[position.strategy_family] = concentrations.get(
                position.strategy_family,
                0.0,
            ) + (abs(position.notional_exposure) / gross_total)

    breached_keys = tuple(
        key for key, value in sorted(concentrations.items()) if value > threshold
    )
    return ConcentrationResult(
        total_gross_exposure=gross_total,
        concentrations=concentrations,
        threshold=threshold,
        breached_keys=breached_keys,
    )


__all__ = [
    "ConcentrationResult",
    "ExposureSummary",
    "PositionExposure",
    "calculate_exposure_summary",
    "calculate_currency_concentration",
    "calculate_strategy_family_concentration",
    "calculate_symbol_concentration",
]
