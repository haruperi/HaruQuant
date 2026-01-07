"""
Strategy vs benchmark comparison.

Focus: relative performance
"""

from typing import Tuple

import numpy as np
import pandas as pd

# =========================================================================
# Benchmark Returns
# =========================================================================


def benchmark_returns(benchmark_equity: pd.Series) -> pd.Series:
    """
    Calculate returns from benchmark equity curve.

    Args:
        benchmark_equity: Benchmark equity series

    Returns:
        Benchmark returns series
    """
    if len(benchmark_equity) < 2:
        return pd.Series(dtype=float)

    return benchmark_equity.pct_change(fill_method=None).dropna()


def excess_returns(
    strategy_returns: pd.Series, benchmark_returns: pd.Series
) -> pd.Series:
    """
    Calculate excess returns (strategy - benchmark).

    Args:
        strategy_returns: Strategy returns series
        benchmark_returns: Benchmark returns series

    Returns:
        Excess returns series
    """
    # Align returns
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()

    if len(aligned) == 0:
        return pd.Series(dtype=float)

    return aligned["strategy"] - aligned["benchmark"]


# =========================================================================
# Market Statistics
# =========================================================================


def beta(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Beta - sensitivity to market movements.

    Beta = Cov(Strategy, Benchmark) / Var(Benchmark)

    Args:
        strategy_returns: Strategy returns series
        benchmark_returns: Benchmark returns series

    Returns:
        Beta value
    """
    # Align returns
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()

    if len(aligned) < 2:
        return 0.0

    covariance = aligned["strategy"].cov(aligned["benchmark"])
    variance = aligned["benchmark"].var()

    if variance == 0:
        return 0.0

    return float(covariance / variance)


def alpha(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float = 0.0,
) -> float:
    """
    Jensen's Alpha - risk-adjusted excess return.

    Alpha = Strategy Return - [RiskFree + Beta × (Benchmark - RiskFree)]

    Args:
        strategy_returns: Strategy returns series
        benchmark_returns: Benchmark returns series
        risk_free_rate: Risk-free rate (annualized)

    Returns:
        Alpha value (annualized)
    """
    # Align returns
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()

    if len(aligned) < 2:
        return 0.0

    # Calculate beta
    beta_value = beta(strategy_returns, benchmark_returns)

    # Average returns
    avg_strategy = aligned["strategy"].mean()
    avg_benchmark = aligned["benchmark"].mean()

    # Daily risk-free rate
    daily_rf = risk_free_rate / 252

    # Alpha = Strategy - [RiskFree + Beta × (Benchmark - RiskFree)]
    alpha_value = avg_strategy - (daily_rf + beta_value * (avg_benchmark - daily_rf))

    # Annualize
    annualized_alpha = alpha_value * 252

    return float(annualized_alpha)


def r_squared(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    R-squared - proportion of variance explained by benchmark.

    Measures how well strategy movements are explained by benchmark

    Args:
        strategy_returns: Strategy returns series
        benchmark_returns: Benchmark returns series

    Returns:
        R-squared value (0-1)
    """
    # Align returns
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()

    if len(aligned) < 2:
        return 0.0

    correlation = aligned["strategy"].corr(aligned["benchmark"])

    return float(correlation**2)


def tracking_error(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Tracking Error - volatility of excess returns.

    Measures consistency of outperformance/underperformance

    Args:
        strategy_returns: Strategy returns series
        benchmark_returns: Benchmark returns series

    Returns:
        Tracking error (annualized)
    """
    # Align returns
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()

    if len(aligned) < 2:
        return 0.0

    excess = aligned["strategy"] - aligned["benchmark"]
    te = excess.std()

    # Annualize
    annualized_te = te * np.sqrt(252)

    return float(annualized_te)


# =========================================================================
# Relative Performance
# =========================================================================


def relative_drawdown(
    strategy_equity: pd.Series, benchmark_equity: pd.Series
) -> pd.Series:
    """
    Relative drawdown vs benchmark.

    Shows periods where strategy underperforms benchmark

    Args:
        strategy_equity: Strategy equity curve
        benchmark_equity: Benchmark equity curve

    Returns:
        Relative drawdown series
    """
    # Align equity curves
    aligned = pd.DataFrame(
        {"strategy": strategy_equity, "benchmark": benchmark_equity}
    ).dropna()

    if len(aligned) == 0:
        return pd.Series(dtype=float)

    # Calculate relative equity
    relative_equity = aligned["strategy"] / aligned["benchmark"]

    # Calculate drawdown of relative equity
    running_max = relative_equity.expanding().max()
    drawdown = relative_equity - running_max

    return drawdown


def batting_average(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Batting Average - percentage of periods outperforming benchmark.

    Args:
        strategy_returns: Strategy returns series
        benchmark_returns: Benchmark returns series

    Returns:
        Batting average (0-100)
    """
    # Align returns
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()

    if len(aligned) == 0:
        return 0.0

    outperform = (aligned["strategy"] > aligned["benchmark"]).sum()
    total = len(aligned)

    return float((outperform / total) * 100)


def up_down_capture(
    strategy_returns: pd.Series, benchmark_returns: pd.Series
) -> Tuple[float, float]:
    """
    Up/Down Capture Ratios.

    Up Capture: Strategy performance when benchmark is positive
    Down Capture: Strategy performance when benchmark is negative

    Higher up capture = better at capturing gains
    Lower down capture = better at avoiding losses

    Args:
        strategy_returns: Strategy returns series
        benchmark_returns: Benchmark returns series

    Returns:
        Tuple of (up_capture, down_capture) percentages
    """
    # Align returns
    aligned = pd.DataFrame(
        {"strategy": strategy_returns, "benchmark": benchmark_returns}
    ).dropna()

    if len(aligned) == 0:
        return (0.0, 0.0)

    # Up capture (benchmark positive periods)
    up_periods = aligned[aligned["benchmark"] > 0]

    if len(up_periods) > 0:
        strategy_up = up_periods["strategy"].mean()
        benchmark_up = up_periods["benchmark"].mean()
        up_capture = (strategy_up / benchmark_up * 100) if benchmark_up != 0 else 0.0
    else:
        up_capture = 0.0

    # Down capture (benchmark negative periods)
    down_periods = aligned[aligned["benchmark"] < 0]

    if len(down_periods) > 0:
        strategy_down = down_periods["strategy"].mean()
        benchmark_down = down_periods["benchmark"].mean()
        down_capture = (
            (strategy_down / benchmark_down * 100) if benchmark_down != 0 else 0.0
        )
    else:
        down_capture = 0.0

    return (float(up_capture), float(down_capture))
