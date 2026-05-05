"""
Summary:
-------
HaruQuant Risk & Tail Analytics.
Volatility, tail risk, and capital preservation analysis.
This module provides institutional-grade risk metrics including classical volatility measures, 
Value-at-Risk (VaR), Conditional VaR (CVaR), and Monte Carlo-based Risk of Ruin simulations.

Summary of Methods:
------------------
Volatility Measures:
    - return_volatility: Annualized standard deviation of returns.
    - downside_return_volatility: Volatility of negative returns only (Semi-Deviation).

Tail Risk (VaR/CVaR):
    - value_at_risk: Maximum expected loss over a time horizon at a given confidence.
    - conditional_value_at_risk: Expected loss given that the loss exceeds the VaR (Expected Shortfall).
    - ulcer_index: Measure of the depth and duration of drawdowns.

Systemic & Ruin Risk:
    - risk_of_ruin: Probability of account depletion based on win rate and payoff ratio.
    - max_gross_exposure: Maximum total capital committed to the market at any point.
"""

from typing import Literal, Optional
import numpy as np
import pandas as pd

from . import common
from .common import (
    EPSILON, _to_1d_float_array, get_closed_trades, 
    get_r_multiples, max_gross_size_held, percent_time_in_market
)


try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        def decorator(f):
            return f
        return decorator


# =========================================================================
# Utility & Kernel Helpers
# =========================================================================


@njit(cache=True)
def _risk_of_ruin_kernel(
    outcomes, risk_per_trade, target_drawdown, num_simulations, initial_capital
):
    """
    Monte Carlo simulation of trade outcomes to estimate ruin probability.
    
    This simulates fixed fractional risk based on initial capital, 
    not dynamic compounding risk. Each 1R outcome is converted to 
    a capital unit change based on risk_per_trade.
    """
    ruin_count = 0
    n_outcomes = len(outcomes)
    simulation_length = n_outcomes * 2
    ruin_threshold = initial_capital - target_drawdown

    for _ in range(num_simulations):
        capital = initial_capital
        for _ in range(simulation_length):
            idx = np.random.randint(0, n_outcomes)
            outcome = outcomes[idx]
            capital += outcome * risk_per_trade
            if capital <= ruin_threshold:
                ruin_count += 1
                break
    return ruin_count


# =========================================================================
# Volatility Metrics
# =========================================================================


def volatility(rets: pd.Series | np.ndarray) -> float:
    """Standard deviation of returns as positive percentage."""
    normalized = _to_1d_float_array(rets)
    if len(normalized) < 2:
        return 0.0
    return float(np.std(normalized, ddof=1) * 100.0)


def annualized_volatility(rets: pd.Series | np.ndarray, periods_per_year: int = 252) -> float:
    """Annualized volatility as positive percentage."""
    v = volatility(rets)
    return float(v * np.sqrt(periods_per_year))


def downside_volatility(rets: pd.Series | np.ndarray, target: float = 0.0) -> float:
    """
    Downside deviation as positive percentage.
    target is a per-period target return, in fractional units (e.g. 0.0).
    """
    normalized = _to_1d_float_array(rets)
    if len(normalized) < 2:
        return 0.0

    downside_diffs = np.minimum(normalized - target, 0.0)
    downside_risk = np.sqrt(np.mean(downside_diffs**2))

    return float(downside_risk * 100.0)


# =========================================================================
# Tail Risk & Loss Thresholds
# =========================================================================


def value_at_risk(
    rets: pd.Series | np.ndarray,
    confidence: float = 0.95,
    method: Literal["historical", "parametric"] = "historical",
) -> float:
    """
    Value at Risk as positive percentage.
    Example: 2.5 means 2.5% loss.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    normalized = _to_1d_float_array(rets)
    if len(normalized) == 0:
        return 0.0

    if method == "historical":
        q = np.quantile(normalized, 1.0 - confidence)
        return float(max(0.0, -q) * 100.0)

    if method == "parametric":
        if len(normalized) < 2:
            return 0.0

        from scipy.stats import norm

        mean = np.mean(normalized)
        std = np.std(normalized, ddof=1)
        z_score = norm.ppf(1.0 - confidence)

        var_return = mean + z_score * std
        return float(max(0.0, -var_return) * 100.0)

    raise ValueError("method must be 'historical' or 'parametric'")


def conditional_var(rets: pd.Series | np.ndarray, confidence: float = 0.95) -> float:
    """
    CVaR / Expected Shortfall as positive percentage.
    Example: 3.2 means average tail loss of 3.2%.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    normalized = _to_1d_float_array(rets)
    if len(normalized) == 0:
        return 0.0

    var_threshold = np.quantile(normalized, 1.0 - confidence)
    tail_returns = normalized[normalized <= var_threshold]

    if len(tail_returns) == 0:
        return float(max(0.0, -var_threshold) * 100.0)

    tail_mean = np.mean(tail_returns)
    return float(max(0.0, -tail_mean) * 100.0)


def expected_shortfall(rets: pd.Series | np.ndarray, confidence: float = 0.95) -> float:
    """Calculate Expected Shortfall (alias for CVaR)."""
    return conditional_var(rets, confidence)


def max_loss_probability(trades: pd.DataFrame, loss_threshold_r: float = -1.0) -> float:
    """
    Probability of a single trade loss exceeding a threshold in R-units.
    Example: loss_threshold_r = -2.0 means loss > 2R.
    """
    r_multiples = get_r_multiples(trades)
    if r_multiples.empty:
        return 0.0
    
    # We want losses worse than threshold (e.g. -2.5 < -2.0)
    extreme_losses = r_multiples[r_multiples < loss_threshold_r]
    return float(len(extreme_losses) / len(r_multiples))


def drawdown_probability(returns_in: pd.Series | np.ndarray, threshold_pct: float) -> float:
    """
    Probability that the strategy will experience a drawdown exceeding threshold_pct.
    Calculated as frequency of periods spent in such drawdowns.
    """
    normalized = _to_1d_float_array(returns_in)
    if len(normalized) == 0:
        return 0.0
        
    # Prepend starting equity 1.0 to capture first-period drawdown
    equity = np.concatenate([[1.0], np.cumprod(1.0 + normalized)])
    running_max = np.maximum.accumulate(equity)
    drawdowns = (running_max - equity) / running_max
    
    threshold_fraction = threshold_pct / 100.0
    
    # Exclude synthetic point from denominator
    dd_after_start = drawdowns[1:]
    exceeded = (dd_after_start > threshold_fraction).sum()
    
    return float(exceeded / len(dd_after_start))


# =========================================================================
# Capital Risk & Ruin
# =========================================================================


def risk_of_ruin(
    trades: pd.DataFrame,
    risk_per_trade_pct: float | None = None,
    target_drawdown_pct: float = 50.0,
    num_simulations: int = 10000,
    **kwargs,
) -> float:
    """
    Monte Carlo simulation of trade outcomes to estimate ruin probability.
    
    This simulates fixed fractional risk based on initial capital, not dynamic compounding.
    
    Args:
        trades: DataFrame of trades.
        risk_per_trade_pct: Risk per trade as % of initial capital (e.g. 1.0 for 1%).
        target_drawdown_pct: Drawdown at which ruin is defined (e.g. 50.0).
        num_simulations: Number of paths to simulate.
    """
    if risk_per_trade_pct is None:
        risk_per_trade_pct = kwargs.pop("risk_per_trade", 0.0)
    if "target_drawdown" in kwargs:
        target_drawdown_pct = kwargs.pop("target_drawdown")

    if risk_per_trade_pct <= 0 or target_drawdown_pct <= 0 or num_simulations <= 0:
        return 0.0

    r_outcomes = get_r_multiples(trades).values
    if len(r_outcomes) < 5:
        return 0.0

    # _risk_of_ruin_kernel uses initial_capital=100.0
    ruin_count = _risk_of_ruin_kernel(
        r_outcomes, 
        float(risk_per_trade_pct), 
        float(target_drawdown_pct), 
        int(num_simulations), 
        100.0
    )
    return float(ruin_count / num_simulations)


# =========================================================================
# Market Exposure (Capacity & Utilization)
# =========================================================================


def max_nominal_exposure_simple(trades: pd.DataFrame, contract_size: float = 100000.0) -> float:
    """
    Maximum total nominal exposure held at any one time.
    
    Assumes 1 lot = contract_size and ignores price/account-currency conversion.
    Calculated as (Max Gross Size Held * contract_size).
    """
    if trades.empty:
        return 0.0
    
    max_gross_size = max_gross_size_held(trades)
    return float(max_gross_size * contract_size)


def max_gross_exposure(trades: pd.DataFrame, contract_size: float = 100000.0) -> float:
    """Maximum total nominal exposure held (Gross Exposure)."""
    return max_nominal_exposure_simple(trades, contract_size)


def avg_trade_nominal_exposure(trades: pd.DataFrame, contract_size: float = 100000.0) -> float:
    """
    Average nominal exposure per trade (not time-weighted).
    
    Assumes 1 lot = contract_size and ignores price/account-currency conversion.
    """
    if trades.empty:
        return 0.0
        
    # Find size column
    size_col = None
    for col in ["size", "quantity", "volume"]:
        if col in trades.columns:
            size_col = col
            break
            
    if not size_col:
        return 0.0
        
    return float(trades[size_col].abs().mean() * contract_size)


def exposure_time_ratio(
    trades: pd.DataFrame,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> float:
    """
    Percentage of the total period spent in the market (0-100).
    Alias for percent_time_in_market.
    """
    return percent_time_in_market(trades, start_time, end_time)


def max_single_trade_margin_utilization(trades: pd.DataFrame, account_equity: float) -> float:
    """Maximum absolute margin used by a single trade as percentage of equity."""
    if trades.empty or account_equity <= 0:
        return 0.0
        
    if "margin_used" in trades.columns:
        return float((trades["margin_used"].abs().max() / account_equity) * 100.0)
        
    return 0.0


def avg_single_trade_margin_utilization(trades: pd.DataFrame, account_equity: float) -> float:
    """Average absolute margin used per trade as percentage of equity."""
    if trades.empty or account_equity <= 0:
        return 0.0
        
    if "margin_used" in trades.columns:
        return float((trades["margin_used"].abs().mean() / account_equity) * 100.0)
        
    return 0.0


# =========================================================================
# Advanced Portfolio & Compounding Risks
# =========================================================================


@njit(cache=True)
def _compounding_ruin_kernel(
    outcomes, risk_fraction, target_drawdown, num_simulations, initial_capital
):
    """
    Monte Carlo simulation using dynamic compounding risk.
    Each 1R outcome risks a fraction of *current* capital.
    """
    ruin_count = 0
    n_outcomes = len(outcomes)
    simulation_length = n_outcomes * 2
    # target_drawdown is percentage (e.g. 50.0)
    ruin_threshold = initial_capital * (1.0 - target_drawdown / 100.0)

    for _ in range(num_simulations):
        capital = initial_capital
        for _ in range(simulation_length):
            idx = np.random.randint(0, n_outcomes)
            outcome = outcomes[idx]
            # Compounding: outcome * (current_capital * risk_fraction)
            capital += outcome * (capital * risk_fraction)
            if capital <= ruin_threshold:
                ruin_count += 1
                break
    return ruin_count


@njit(cache=True)
def _horizon_ruin_kernel(
    outcomes, risk_per_trade, target_drawdown, num_simulations, initial_capital, horizon
):
    """
    Monte Carlo simulation with a fixed trade horizon.
    """
    ruin_count = 0
    n_outcomes = len(outcomes)
    ruin_threshold = initial_capital - target_drawdown

    for _ in range(num_simulations):
        capital = initial_capital
        for _ in range(horizon):
            idx = np.random.randint(0, n_outcomes)
            outcome = outcomes[idx]
            capital += outcome * risk_per_trade
            if capital <= ruin_threshold:
                ruin_count += 1
                break
    return ruin_count


def time_weighted_avg_exposure(trades: pd.DataFrame, contract_size: float = 100000.0, end_time: Optional[pd.Timestamp] = None) -> float:
    """
    Time-weighted average notional exposure held.
    """
    if trades.empty:
        return 0.0
    
    size_col = None
    for col in ["size", "quantity", "volume"]:
        if col in trades.columns:
            size_col = col
            break
    if not size_col: return 0.0

    open_times = trades["open_time"].values
    fallback = end_time if end_time else trades["open_time"].max()
    close_times = trades["close_time"].fillna(fallback).values
    sizes = trades[size_col].abs().values
    
    event_times = np.concatenate([open_times, close_times])
    event_sizes = np.concatenate([sizes, -sizes])
    
    idx = np.lexsort((-event_sizes, event_times))
    sorted_times = event_times[idx].astype("datetime64[ns]").view("int64")
    sorted_sizes = event_sizes[idx]
    
    tw_avg = common._time_weighted_kernel(sorted_times, sorted_sizes)
    return float(tw_avg * contract_size)


def portfolio_margin_utilization_curve(trades: pd.DataFrame, account_equity: float, end_time: Optional[pd.Timestamp] = None) -> pd.Series:
    """
    Generate the curve of total aggregate margin utilization over time.
    """
    if trades.empty or "margin_used" not in trades.columns or account_equity <= 0:
        return pd.Series(dtype=float)

    open_times = trades["open_time"].values
    fallback = end_time if end_time else trades["open_time"].max()
    close_times = trades["close_time"].fillna(fallback).values
    margins = trades["margin_used"].abs().values
    
    event_times = np.concatenate([open_times, close_times])
    event_changes = np.concatenate([margins, -margins])
    
    idx = np.argsort(event_times)
    sorted_times = event_times[idx]
    sorted_changes = event_changes[idx]
    
    curve_values = common._exposure_curve_kernel(sorted_times, sorted_changes)
    utilization_pct = (curve_values / account_equity) * 100.0
    
    return pd.Series(utilization_pct, index=pd.to_datetime(sorted_times))


def compounding_risk_of_ruin(
    trades: pd.DataFrame,
    risk_fraction: float,
    target_drawdown_pct: float = 50.0,
    num_simulations: int = 10000,
) -> float:
    """
    Monte Carlo simulation of ruin probability using dynamic compounding risk.
    risk_fraction = 0.01 for 1% risk per trade.
    """
    if risk_fraction <= 0 or target_drawdown_pct <= 0 or num_simulations <= 0:
        return 0.0

    r_outcomes = get_r_multiples(trades).values
    if len(r_outcomes) < 5:
        return 0.0

    ruin_count = _compounding_ruin_kernel(
        r_outcomes, 
        float(risk_fraction), 
        float(target_drawdown_pct), 
        int(num_simulations), 
        100.0
    )
    return float(ruin_count / num_simulations)


def risk_of_ruin_with_custom_horizon(
    trades: pd.DataFrame,
    risk_per_trade_pct: float,
    horizon: int,
    target_drawdown_pct: float = 50.0,
    num_simulations: int = 10000,
) -> float:
    """
    Monte Carlo simulation of ruin probability over a fixed number of future trades.
    """
    if risk_per_trade_pct <= 0 or horizon <= 0 or target_drawdown_pct <= 0 or num_simulations <= 0:
        return 0.0

    r_outcomes = get_r_multiples(trades).values
    if len(r_outcomes) < 5:
        return 0.0

    ruin_count = _horizon_ruin_kernel(
        r_outcomes, 
        float(risk_per_trade_pct), 
        float(target_drawdown_pct), 
        int(num_simulations), 
        100.0,
        int(horizon)
    )
    return float(ruin_count / num_simulations)


def historical_var_by_symbol(
    trades: pd.DataFrame,
    confidence: float = 0.95
) -> pd.Series:
    """
    Calculate historical VaR (as positive profit_loss units) for each symbol individually.
    Based on realized trade outcomes, not price returns.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    data = get_closed_trades(trades)
    if data.empty or "symbol" not in data.columns or "profit_loss" not in data.columns:
        return pd.Series(dtype=float)
        
    def _calc_var(group):
        pnl = group["profit_loss"].values
        if len(pnl) == 0: return 0.0
        q = np.quantile(pnl, 1.0 - confidence)
        return float(max(0.0, -q))
        
    return data.groupby("symbol").apply(_calc_var)


def portfolio_var_from_covariance(
    returns_df: pd.DataFrame,
    weights: Optional[np.ndarray] = None,
    confidence: float = 0.95
) -> float:
    """
    Calculate Portfolio VaR using Variance-Covariance (Parametric) method.
    returns_df: Columns are assets, rows are periodic returns.
    weights: Optional array of portfolio weights (defaults to equal weighting).
    Returns positive percentage.
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    if returns_df.empty:
        return 0.0
        
    n_assets = returns_df.shape[1]
    if weights is None:
        weights = np.ones(n_assets) / n_assets
    else:
        if len(weights) != n_assets:
            raise ValueError(f"weights length ({len(weights)}) must match number of assets ({n_assets})")
        # Normalize weights to sum to 1
        weights = weights / weights.sum()
        
    cov_matrix = returns_df.cov().values
    portfolio_std = np.sqrt(weights.T @ cov_matrix @ weights)
    portfolio_mean = returns_df.mean() @ weights
    
    from scipy.stats import norm
    z_score = norm.ppf(1.0 - confidence)
    
    var_return = portfolio_mean + z_score * portfolio_std
    return float(max(0.0, -var_return) * 100.0)
