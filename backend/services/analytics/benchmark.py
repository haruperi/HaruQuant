"""
Summary:
-------
HaruQuant Benchmark & Relative Analytics.
Comparing strategy performance against external indices or peer groups.
This module provides metrics to evaluate performance against a market benchmark, including 
standard statistics (Alpha, Beta) and relative strength measures (Capture Ratios).

Summary of Methods:
------------------
Market Sensitivity (Alpha & Beta):
    - beta: Strategy sensitivity to market movements.
    - alpha: Jensen's Alpha - annualized risk-adjusted excess return.
    - r_squared: Percentage of variance explained by the benchmark.
    - tracking_error: Annualized volatility of excess returns.

Relative Performance Analysis:
    - relative_drawdown: Maximum underperformance vs benchmark equity.
    - batting_average: Percentage of periods outperforming the market.
    - up_down_capture: Ratios of performance in rising vs falling markets.
    - excess_returns: Time series of active returns.
"""

from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd

from .common import EPSILON


# =========================================================================
# Shared Helpers & Alignment
# =========================================================================


def _clean_series(data: pd.Series) -> pd.Series:
    """Normalize numeric series, replace infinities, drop NaNs, and sort by index."""
    s = pd.to_numeric(data, errors="coerce")
    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    
    # Ensure index is datetime-like for resampling safety
    if not isinstance(s.index, pd.DatetimeIndex):
        try:
            s.index = pd.to_datetime(s.index)
        except (ValueError, TypeError):
            pass
            
    return s.astype(float).sort_index()


def _align_returns(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> pd.DataFrame:
    """Align two return series by their index, dropping missing periods."""
    s = _clean_series(strategy_returns)
    b = _clean_series(benchmark_returns)

    aligned = pd.DataFrame({"strategy": s, "benchmark": b}).dropna()
    return aligned


# =========================================================================
# Benchmark Data Processing
# =========================================================================


def benchmark_returns(benchmark_equity: pd.Series, freq: Optional[str] = None) -> pd.Series:
    """
    Generate a return series from benchmark equity (prices).
    
    Args:
        benchmark_equity: Series of prices/equity values.
        freq: Optional resampling frequency (e.g., 'D', 'W', 'M'). 
             If provided, forward-fills gaps before calculating returns.
    """
    equity = _clean_series(benchmark_equity)
    if len(equity) < 2:
        return pd.Series(dtype=float)

    if freq is not None:
        equity = equity.resample(freq).last().ffill()

    rets = equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    return rets


# =========================================================================
# Relative Risk & Return
# =========================================================================


def beta(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Beta coefficient relative to the benchmark.
    Measures the strategy's sensitivity to benchmark movements.
    """
    aligned = _align_returns(strategy_returns, benchmark_returns)
    if len(aligned) < 2:
        return 0.0

    cov = aligned["strategy"].cov(aligned["benchmark"])
    var_bench = aligned["benchmark"].var()

    if pd.isna(cov) or pd.isna(var_bench) or var_bench < 1e-12:
        # Default to 0.0 (sensitivity undefined/none)
        return 0.0
        
    return float(cov / var_bench)


def alpha(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Annualized Jensen's Alpha (Percentage).
    Returns the excess return of the strategy over its beta-adjusted benchmark.
    
    Example: 5.2 for 5.2% annualized alpha.
    """
    aligned = _align_returns(strategy_returns, benchmark_returns)
    if len(aligned) < 2:
        return 0.0

    # Convert annual risk-free rate to period rate
    period_rf = risk_free_rate / periods_per_year
    
    s_avg = aligned["strategy"].mean()
    b_avg = aligned["benchmark"].mean()
    
    b_val = beta(aligned["strategy"], aligned["benchmark"])
    
    # Alpha per period
    alpha_period = (s_avg - period_rf) - b_val * (b_avg - period_rf)
    
    return float(alpha_period * periods_per_year * 100.0)


def r_squared(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    R-squared (Coefficient of Determination).
    Percentage of strategy variance explained by benchmark variance.
    """
    aligned = _align_returns(strategy_returns, benchmark_returns)
    if len(aligned) < 2:
        return 0.0

    corr = aligned["strategy"].corr(aligned["benchmark"])
    if pd.isna(corr):
        return 0.0
        
    return float(corr**2)


def tracking_error(
    strategy_returns: pd.Series, 
    benchmark_returns: pd.Series,
    periods_per_year: int = 252
) -> float:
    """
    Annualized Tracking Error (Percentage).
    Standard deviation of the excess returns (Active Risk).
    """
    aligned = _align_returns(strategy_returns, benchmark_returns)
    if len(aligned) < 2:
        return 0.0

    excess = aligned["strategy"] - aligned["benchmark"]
    te_period = excess.std(ddof=1)
    
    if pd.isna(te_period) or te_period < 1e-12:
        return 0.0
        
    return float(te_period * np.sqrt(periods_per_year) * 100.0)


def information_ratio(
    strategy_returns: pd.Series, 
    benchmark_returns: pd.Series,
    periods_per_year: int = 252
) -> float:
    """
    Information Ratio (Relative Sharpe).
    Active Return / Active Risk.
    """
    aligned = _align_returns(strategy_returns, benchmark_returns)
    if len(aligned) < 2:
        return 0.0

    excess_rets = aligned["strategy"] - aligned["benchmark"]
    avg_excess = excess_rets.mean()
    te_period = excess_rets.std(ddof=1)

    if pd.isna(te_period) or te_period < 1e-12:
        return 0.0

    # (avg_excess * periods) / (std_excess * sqrt(periods)) = (avg/std) * sqrt(periods)
    return float((avg_excess / te_period) * np.sqrt(periods_per_year))


# =========================================================================
# Relative Drawdown & Underperformance
# =========================================================================


def relative_drawdown_series(strategy_equity: pd.Series, benchmark_equity: pd.Series) -> pd.Series:
    """
    Generate a series of relative underperformance (negative percentage).
    Relative Equity = Strategy Equity / Benchmark Equity.
    """
    s = _clean_series(strategy_equity)
    b = _clean_series(benchmark_equity)
    
    aligned = pd.DataFrame({"strategy": s, "benchmark": b}).dropna()
    # Guard against zero benchmark
    aligned = aligned[aligned["benchmark"].abs() > 1e-12]
    
    if aligned.empty:
        return pd.Series(dtype=float)

    rel_eq = aligned["strategy"] / aligned["benchmark"]
    rel_dd = (rel_eq / rel_eq.expanding().max()) - 1.0
    return rel_dd


def max_relative_drawdown_percent(strategy_equity: pd.Series, benchmark_equity: pd.Series) -> float:
    """
    Maximum relative underperformance experienced (Positive Percentage).
    """
    dd_series = relative_drawdown_series(strategy_equity, benchmark_equity)
    if dd_series.empty:
        return 0.0
    return float(abs(dd_series.min()) * 100.0)


# =========================================================================
# Market Capture & Frequency
# =========================================================================


def batting_average(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Percentage of periods where the strategy outperformed the benchmark.
    """
    aligned = _align_returns(strategy_returns, benchmark_returns)
    if len(aligned) == 0:
        return 0.0

    better = (aligned["strategy"] > aligned["benchmark"]).sum()
    return float(better / len(aligned) * 100.0)


def up_down_capture(strategy_returns: pd.Series, benchmark_returns: pd.Series) -> Tuple[float, float]:
    """
    Calculate Up and Down Capture Ratios (Percentage).
    
    Up Capture: How much of the benchmark's gains were captured during positive months.
    Down Capture: How much of the benchmark's losses were realized during negative months.
    
    Returns (up_capture, down_capture).
    Note: Down capture < 100% is generally good (less loss realized than benchmark).
    """
    aligned = _align_returns(strategy_returns, benchmark_returns)
    if len(aligned) == 0:
        return 0.0, 0.0

    up_market = aligned[aligned["benchmark"] > 0]
    down_market = aligned[aligned["benchmark"] < 0]

    up_cap = 0.0
    if not up_market.empty:
        up_bench_avg = up_market["benchmark"].mean()
        if up_bench_avg > EPSILON:
            up_cap = (up_market["strategy"].mean() / up_bench_avg) * 100.0

    down_cap = 0.0
    if not down_market.empty:
        down_bench_avg = down_market["benchmark"].mean()
        if abs(down_bench_avg) > EPSILON:
            down_cap = (down_market["strategy"].mean() / down_bench_avg) * 100.0

    return float(up_cap), float(down_cap)
