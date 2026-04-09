"""Margin and sizing helpers for deterministic risk checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarginUtilization:
    """Margin usage summary used in risk decisions and limits."""

    balance: float
    equity: float
    free_margin: float
    margin_used: float
    utilization_ratio: float


@dataclass(frozen=True)
class VolatilityAdjustedSizing:
    """Normalized size recommendation after volatility scaling."""

    base_size: float
    volatility_ratio: float
    adjusted_size: float


def calculate_margin_utilization(
    *,
    balance: float,
    equity: float,
    free_margin: float,
    margin_used: float,
) -> MarginUtilization:
    """Calculate current margin utilization from account state."""

    denominator = margin_used + free_margin
    utilization_ratio = 0.0 if denominator <= 0 else margin_used / denominator
    return MarginUtilization(
        balance=balance,
        equity=equity,
        free_margin=free_margin,
        margin_used=margin_used,
        utilization_ratio=utilization_ratio,
    )


def calculate_volatility_adjusted_size(
    *,
    base_size: float,
    reference_volatility: float,
    observed_volatility: float,
    min_scale: float = 0.25,
    max_scale: float = 2.0,
) -> VolatilityAdjustedSizing:
    """Scale proposed size inversely to observed volatility."""

    if reference_volatility <= 0:
        raise ValueError("reference_volatility must be positive")
    if observed_volatility <= 0:
        raise ValueError("observed_volatility must be positive")

    raw_ratio = reference_volatility / observed_volatility
    bounded_ratio = max(min(raw_ratio, max_scale), min_scale)
    return VolatilityAdjustedSizing(
        base_size=base_size,
        volatility_ratio=bounded_ratio,
        adjusted_size=base_size * bounded_ratio,
    )


__all__ = [
    "MarginUtilization",
    "VolatilityAdjustedSizing",
    "calculate_margin_utilization",
    "calculate_volatility_adjusted_size",
]
