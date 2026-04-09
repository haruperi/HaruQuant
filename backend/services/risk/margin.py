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


__all__ = [
    "MarginUtilization",
    "calculate_margin_utilization",
]
