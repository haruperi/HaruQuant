"""
Finance Module.

Comprehensive financial analytics for trading systems.
All functions accept pd.DataFrame with canonical HaruQuant trade schema.

Design principles:
- Deterministic
- Side-effect free
- Composable
- ML-ready

Modules:
- metrics: Trade-based statistics & system-quality metrics
- returns: Return calculations & period-based analysis
- drawdowns: Drawdown depth, duration, and recovery
- ratios: Risk-adjusted performance ratios
- risks: Volatility, tail risk, and capital risk
- benchmark: Strategy vs benchmark comparison
- distributions: Statistical structure of returns & trades
- efficiency: Capital and time efficiency metrics
"""

from . import (
    benchmark,
    distributions,
    drawdowns,
    efficiency,
    metrics,
    ratios,
    returns,
    risks,
    statistical_tests,
)

__all__ = [
    "metrics",
    "returns",
    "drawdowns",
    "ratios",
    "risks",
    "benchmark",
    "distributions",
    "efficiency",
    "statistical_tests",
]
