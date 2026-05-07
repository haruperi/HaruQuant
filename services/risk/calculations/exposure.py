"""Exposure and concentration primitives for deterministic risk checks."""

from __future__ import annotations

from dataclasses import dataclass

from services.utils.logger import logger

from services.risk.calculations.math_utils import notional_exposure

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


def exposure_snapshot(positions: list[dict[str, object]], *, equity: float = 100000.0) -> dict[str, object]:
    """Build a lightweight exposure map from raw position dictionaries."""

    by_symbol: dict[str, float] = {}
    by_strategy: dict[str, float] = {}
    gross = 0.0
    net = 0.0
    for position in positions:
        symbol = str(position.get("symbol", "UNKNOWN"))
        strategy = str(position.get("strategy_id", "strategy-unknown"))
        signed = float(position.get("notional", float(position.get("volume", 0.0)) * float(position.get("price", 1.0)) * 100000.0))
        if position.get("side") == "sell":
            signed *= -1
        by_symbol[symbol] = by_symbol.get(symbol, 0.0) + signed
        by_strategy[strategy] = by_strategy.get(strategy, 0.0) + signed
        gross += abs(signed)
        net += signed
    denominator = max(float(equity), 1.0)
    return {
        "symbol_exposure": {key: abs(value) / denominator for key, value in by_symbol.items()},
        "strategy_exposure": {key: abs(value) / denominator for key, value in by_strategy.items()},
        "gross_exposure": gross / denominator,
        "net_exposure": net / denominator,
    }


def proposed_exposure_impact(proposal: dict[str, object], portfolio_snapshot: dict[str, object]) -> dict[str, float]:
    """Calculate symbol exposure after a proposed trade."""

    equity = float(portfolio_snapshot.get("equity", 100000.0))
    current_symbol = float(portfolio_snapshot.get("symbol_exposure", 0.0))
    proposed = notional_exposure(proposal) / max(equity, 1.0)
    return {"current_symbol_exposure": current_symbol, "proposed_exposure": proposed, "post_symbol_exposure": current_symbol + proposed}


def concentration_failures(impact: dict[str, float], thresholds: dict[str, object]) -> list[str]:
    """Return deterministic concentration rule failures."""

    if impact["post_symbol_exposure"] > float(thresholds["max_symbol_exposure_pct"]):
        return ["max_symbol_concentration"]
    return []


__all__ = [
    "ConcentrationResult",
    "ExposureSummary",
    "PositionExposure",
    "concentration_failures",
    "calculate_exposure_summary",
    "calculate_currency_concentration",
    "calculate_strategy_family_concentration",
    "calculate_symbol_concentration",
    "exposure_snapshot",
    "proposed_exposure_impact",
]
