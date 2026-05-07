"""Simulation scoring helpers."""

from __future__ import annotations

from typing import Any


def score_backtest(metrics: dict[str, Any]) -> float:
    trade_score = min(1.0, float(metrics.get("trade_count", 0)) / 60.0)
    drawdown_score = max(0.0, 1.0 - abs(float(metrics.get("max_drawdown", 0.0))) / 0.2)
    concentration_score = max(0.0, 1.0 - float(metrics.get("profit_concentration", 1.0)))
    cost_score = min(1.0, float(metrics.get("cost_edge_ratio", 0.0)) / 2.0)
    return round((trade_score + drawdown_score + concentration_score + cost_score) / 4.0, 4)


def score_robustness(tests: dict[str, str]) -> float:
    if not tests:
        return 0.0
    passed = sum(1 for value in tests.values() if value == "pass")
    return round(passed / len(tests), 4)
