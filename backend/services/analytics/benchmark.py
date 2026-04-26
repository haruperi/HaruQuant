"""
Strategy vs benchmark comparison.

Focus: relative performance and market sensitivity

This module provides metrics to compare a trading strategy against a benchmark (market).
It includes standard market statistics like Alpha, Beta, and R-Squared, 
as well as relative performance measures like Tracking Error, Batting Average, and Capture Ratios.

Summary of Methods:
------------------
Core Returns Alignment:
    - benchmark_returns: Calculate percentage returns from benchmark equity.
    - excess_returns: Strategy returns minus benchmark returns (alpha series).

Market Statistics (Alpha & Beta):
    - beta: Sensitivity of strategy returns to market movements.
    - alpha: Jensen's Alpha - risk-adjusted excess return.
    - r_squared: Proportion of strategy variance explained by the benchmark.
    - tracking_error: Annualized volatility of excess returns.

Relative Performance Analysis:
    - relative_drawdown: Underperformance periods of strategy equity relative to benchmark equity.
    - batting_average: Percentage of periods where the strategy outperformed the benchmark.
    - up_down_capture: Ratios showing performance in rising vs falling markets.
"""

from typing import Tuple

import numpy as np
import pandas as pd


# =========================================================================
# Core Returns Alignment
# =========================================================================


def benchmark_returns(benchmark_equity: pd.Series) -> pd.Series:
    """Calculate percentage returns from benchmark equity curve."""
    if len(benchmark_equity) < 2:
        return pd.Series(dtype=float)
    return benchmark_equity.pct_change(fill_method=None).dropna()


def excess_returns(
    strategy_returns: pd.Series, benchmark_returns: pd.Series
) -> pd.Series:
    """Calculate excess returns (strategy - benchmark)."""
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()
    return aligned["strategy"] - aligned["benchmark"] if not aligned.empty else pd.Series(dtype=float)


# =========================================================================
# Market Statistics (Alpha & Beta)
# =========================================================================


def beta(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Beta - sensitivity of strategy to benchmark movements."""
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()
    if len(aligned) < 2: return 0.0
    var = aligned["benchmark"].var()
    return float(aligned["strategy"].cov(aligned["benchmark"]) / var) if var != 0 else 0.0


def alpha(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float = 0.0,
) -> float:
    """Jensen's Alpha - annualized risk-adjusted excess return."""
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()
    if len(aligned) < 2: return 0.0
    
    b = beta(strategy_returns, benchmark_returns)
    daily_rf = risk_free_rate / 252
    alpha_val = aligned["strategy"].mean() - (daily_rf + b * (aligned["benchmark"].mean() - daily_rf))
    return float(alpha_val * 252)


def r_squared(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """R-squared - proportion of variance explained by benchmark."""
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()
    if len(aligned) < 2: return 0.0
    corr = aligned["strategy"].corr(aligned["benchmark"])
    return float(corr**2) if not pd.isna(corr) else 0.0


def tracking_error(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Annualized tracking error (volatility of excess returns)."""
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()
    if len(aligned) < 2: return 0.0
    te = (aligned["strategy"] - aligned["benchmark"]).std()
    return float(te * np.sqrt(252))


# =========================================================================
# Relative Performance Analysis
# =========================================================================


def relative_drawdown(
    strategy_equity: pd.Series, benchmark_equity: pd.Series
) -> pd.Series:
    """Relative drawdown (peak-to-valley underperformance vs benchmark)."""
    aligned = pd.DataFrame(
        {"strategy": strategy_equity, "benchmark": benchmark_equity}
    ).dropna()
    if aligned.empty: return pd.Series(dtype=float)
    rel_eq = aligned["strategy"] / aligned["benchmark"]
    return rel_eq - rel_eq.expanding().max()


def batting_average(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Percentage of periods where strategy outpaced the benchmark."""
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()
    if aligned.empty: return 0.0
    return float((aligned["strategy"] > aligned["benchmark"]).mean() * 100)


def up_down_capture(
    strategy_returns: pd.Series, benchmark_returns: pd.Series
) -> Tuple[float, float]:
    """Up/Down capture ratios showing behavior in rising vs falling markets."""
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()
    if aligned.empty: return (0.0, 0.0)

    up = aligned[aligned["benchmark"] > 0]
    up_cap = (up["strategy"].mean() / up["benchmark"].mean() * 100) if not up.empty and up["benchmark"].mean() != 0 else 0.0

    down = aligned[aligned["benchmark"] < 0]
    down_cap = (down["strategy"].mean() / down["benchmark"].mean() * 100) if not down.empty and down["benchmark"].mean() != 0 else 0.0

    return (float(up_cap), float(down_cap))
