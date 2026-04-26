"""
HaruQuant Analytics Service.

Comprehensive financial analytics for trading systems.
Provides deterministic, side-effect free, and composable metrics for strategy evaluation.

This service utilizes Hybrid Vectorization with Numba-jitted kernels for high-performance 
computation of metrics, drawdowns, and statistical robustness tests.

Sub-Modules:
-----------
- overview: Parallel aggregator and API payload builder.
- metrics: Trade-based statistics and system-quality measures (SQN, Kelly).
- returns: Profit/Loss, CAGR, and period-based performance.
- drawdowns: Peak-to-valley analysis, duration, and recovery metrics.
- ratios: Risk-adjusted performance (Sharpe, Sortino, Calmar, etc.).
- risks: Volatility, Value at Risk (VaR), and Risk of Ruin.
- benchmark: Relative performance against market benchmarks (Alpha/Beta).
- distributions: Statistical moments, normality tests, and outlier detection.
- efficiency: Capital deployment, time efficiency, and MFE/MAE capture.
- statistical_tests: Robustness validation (DSR, White's Reality Check, Bootstrap).
"""

from . import (
    benchmark,
    distributions,
    drawdowns,
    efficiency,
    metrics,
    overview,
    ratios,
    returns,
    risks,
    statistical_tests,
)

__all__ = [
    "overview",
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
