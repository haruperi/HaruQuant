"""Margin and sizing helpers for deterministic risk checks."""

from __future__ import annotations

from dataclasses import dataclass

from services.utils.logger import logger

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


@dataclass(frozen=True)
class DrawdownState:
    """Current drawdown amount, ratio, and coarse state band."""

    peak_equity: float
    current_equity: float
    drawdown_amount: float
    drawdown_ratio: float
    band: str


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


def calculate_drawdown_state(
    *,
    peak_equity: float,
    current_equity: float,
) -> DrawdownState:
    """Classify drawdown into simple governance bands."""

    if peak_equity <= 0:
        raise ValueError("peak_equity must be positive")

    drawdown_amount = max(peak_equity - current_equity, 0.0)
    drawdown_ratio = drawdown_amount / peak_equity
    if drawdown_ratio < 0.05:
        band = "normal"
    elif drawdown_ratio < 0.1:
        band = "elevated"
    elif drawdown_ratio < 0.2:
        band = "restricted"
    else:
        band = "critical"

    return DrawdownState(
        peak_equity=peak_equity,
        current_equity=current_equity,
        drawdown_amount=drawdown_amount,
        drawdown_ratio=drawdown_ratio,
        band=band,
    )


def margin_impact(proposal: dict[str, object], account_state: dict[str, object]) -> dict[str, float]:
    """Calculate post-trade margin state from raw dictionaries."""

    equity = float(account_state.get("equity", 100000.0))
    used_margin = float(account_state.get("used_margin", account_state.get("margin_used", 0.0)))
    free_margin = float(account_state.get("free_margin", equity - used_margin))
    margin_level = float(account_state.get("margin_level", 999.0))
    required_margin = float(proposal.get("required_margin", float(proposal.get("margin_impact", 0.0)) * equity))
    post_used = used_margin + required_margin
    post_free = free_margin - required_margin
    post_margin_usage = post_used / max(equity, 1.0)
    post_margin_level = (equity / post_used * 100.0) if post_used else margin_level
    return {
        "required_margin": required_margin,
        "post_used_margin": post_used,
        "post_free_margin": post_free,
        "post_free_margin_pct": post_free / max(equity, 1.0),
        "post_margin_usage_pct": post_margin_usage,
        "post_margin_level_pct": post_margin_level,
    }


def margin_failures(impact: dict[str, float], thresholds: dict[str, object]) -> list[str]:
    """Return deterministic margin rule failures."""

    failures: list[str] = []
    if impact["post_margin_usage_pct"] > float(thresholds["max_total_margin_usage_pct"]):
        failures.append("max_total_margin_usage")
    if impact["post_free_margin_pct"] < float(thresholds["min_free_margin_pct"]):
        failures.append("min_free_margin")
    if impact["post_margin_level_pct"] < float(thresholds["min_margin_level_pct"]):
        failures.append("min_margin_level")
    return failures


__all__ = [
    "DrawdownState",
    "MarginUtilization",
    "VolatilityAdjustedSizing",
    "calculate_drawdown_state",
    "calculate_margin_utilization",
    "calculate_volatility_adjusted_size",
    "margin_failures",
    "margin_impact",
]
