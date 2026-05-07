"""VaR risk service."""

from __future__ import annotations


def historical_var(returns: list[float], confidence: float = 0.95) -> float:
    if not returns:
        raise ValueError("missing_returns")
    ordered = sorted(returns)
    index = max(0, int((1.0 - confidence) * len(ordered)) - 1)
    return abs(ordered[index])


def incremental_var(current_returns: list[float], proposed_returns: list[float], confidence: float = 0.95) -> float:
    return historical_var([a + b for a, b in zip(current_returns, proposed_returns, strict=False)] or current_returns, confidence) - historical_var(current_returns, confidence)
