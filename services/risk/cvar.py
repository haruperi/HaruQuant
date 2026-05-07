"""CVaR risk service."""

from __future__ import annotations


def historical_cvar(returns: list[float], confidence: float = 0.95) -> float:
    if not returns:
        raise ValueError("missing_returns")
    ordered = sorted(returns)
    count = max(1, int((1.0 - confidence) * len(ordered)))
    tail = ordered[:count]
    return abs(sum(tail) / len(tail))


def incremental_cvar(current_returns: list[float], proposed_returns: list[float], confidence: float = 0.95) -> float:
    combined = [a + b for a, b in zip(current_returns, proposed_returns, strict=False)] or current_returns
    return historical_cvar(combined, confidence) - historical_cvar(current_returns, confidence)
