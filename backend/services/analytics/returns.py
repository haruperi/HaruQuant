"""
Return calculations & period-based growth analysis.

Focus: equity growth, compounding, time normalization

This module provides functions to calculate raw and compounded returns, 
generate equity curves from trades, and perform time-period resampling (daily, monthly, annual).
It also includes adjusted profit metrics and benchmarking utilities.

Summary of Methods:
------------------
Basic Profit & Loss:
    - total_return: Net gain/loss from an equity curve.
    - net_profit: Total P&L from all closed trades.
    - gross_profit: Sum of all winning trades.
    - gross_loss: Sum of all losing trades (negative).

Equity & Returns Generation:
    - equity_curve: Generate a time-series of account equity from trades.
    - balance_curve: Generate a time-series of realized balance.
    - returns_series: Calculate percentage returns between equity points.
    - log_returns_series: Calculate logarithmic returns.

Resampled Period Returns:
    - daily_returns / weekly_returns: Period-resampled percentage returns.
    - monthly_returns / annual_returns: Period-resampled percentage returns.

Compounding & Growth Rates:
    - cagr: Compound Annual Growth Rate.
    - compound_monthly_growth_rate (CMGR): Monthly equivalent of CAGR.
    - avg_monthly_return: Arithmetic mean of monthly returns.
    - monthly_return_stddev: Volatility of monthly returns.
    - annualized_return: Scale sub-annual returns to yearly terms.
    - geometric_mean_return: Average growth factor per period.

Benchmarking:
    - buy_and_hold_return: Return if asset was held from start to end.
    - buy_and_hold_cagr: CAGR of a buy-and-hold position.

Return Stability & Moments:
    - return_volatility: Standard deviation of returns.
    - downside_return_volatility: Standard deviation of negative returns only.
    - return_skewness: Measure of return distribution asymmetry.
    - return_kurtosis: Measure of "fat tails" in returns.

Adjusted & Select Metrics:
    - adjusted_net_profit: Net profit adjusted for statistical significance.
    - select_net_profit: Net profit after removing 3-sigma outliers.
    - adjusted_gross_profit / adjusted_gross_loss: Scaled components of adjusted profit.
    - select_gross_profit / select_gross_loss: Outlier-removed profit components.

Return Ratios & Capital Relations:
    - return_on_max_strategy_drawdown: Total return relative to max peak-to-valley dip.
    - return_on_max_close_to_close_drawdown: Net profit relative to trade-level max dip.
    - return_on_account: Return relative to required capital.
    - return_on_initial_capital: Return relative to starting balance.
"""

from typing import Optional

import numpy as np
import pandas as pd

from . import drawdowns


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
def _equity_curve_kernel(pnl_arr, initial_balance):
    n = len(pnl_arr)
    out = np.empty(n + 1, dtype=np.float64)
    out[0] = initial_balance
    curr = initial_balance
    for i in range(n):
        curr += pnl_arr[i]
        out[i + 1] = curr
    return out


@njit(cache=True)
def _outlier_mask_kernel(pnl_arr, mean, std, sigma):
    n = len(pnl_arr)
    mask = np.ones(n, dtype=np.bool_)
    lower = mean - (sigma * std)
    upper = mean + (sigma * std)
    for i in range(n):
        if pnl_arr[i] < lower or pnl_arr[i] > upper:
            mask[i] = False
    return mask


def _remove_outliers(trades: pd.DataFrame, sigma: float = 3.0) -> pd.DataFrame:
    """Remove trades that are outliers (> sigma * std)."""
    if len(trades) < 2:
        return trades
    pnl_arr = trades["profit_loss"].values.astype(np.float64)
    mean = np.mean(pnl_arr)
    std = np.std(pnl_arr)
    if std == 0:
        return trades
    mask = _outlier_mask_kernel(pnl_arr, float(mean), float(std), float(sigma))
    return trades[mask]


# =========================================================================
# Basic Profit & Loss
# =========================================================================


def total_return(equity: pd.Series) -> float:
    """Total return in currency units from equity curve."""
    if len(equity) == 0:
        return 0.0
    return float(equity.iloc[-1] - equity.iloc[0])


def net_profit(trades: pd.DataFrame) -> float:
    """Total realized profit/loss from closed trades."""
    if len(trades) == 0:
        return 0.0
    return float(trades["profit_loss"].sum())


def gross_profit(trades: pd.DataFrame) -> float:
    """Sum of all winning trades."""
    if len(trades) == 0:
        return 0.0
    return float(trades[trades["profit_loss"] > 0]["profit_loss"].sum())


def gross_loss(trades: pd.DataFrame) -> float:
    """Sum of all losing trades (negative)."""
    if len(trades) == 0:
        return 0.0
    return float(trades[trades["profit_loss"] < 0]["profit_loss"].sum())


# =========================================================================
# Equity & Returns Generation
# =========================================================================


def equity_curve(trades: pd.DataFrame, initial_balance: float) -> pd.Series:
    """Generate a time-indexed equity curve from trades."""
    if len(trades) == 0:
        return pd.Series([initial_balance])

    sorted_trades = trades.sort_values("close_time")
    pnl_arr = sorted_trades["profit_loss"].values.astype(np.float64)
    equity_values = _equity_curve_kernel(pnl_arr, float(initial_balance))
    
    first_time = sorted_trades.iloc[0]["open_time"]
    indices = np.concatenate([np.array([first_time]), sorted_trades["close_time"].values])
    return pd.Series(equity_values, index=indices)


def balance_curve(trades: pd.DataFrame, initial_balance: float) -> pd.Series:
    """Generate balance curve (equivalent to equity curve for closed trades)."""
    return equity_curve(trades, initial_balance)


def returns_series(equity: pd.Series) -> pd.Series:
    """Calculate percentage returns between equity points."""
    if len(equity) < 2:
        return pd.Series(dtype=float)
    return equity.pct_change().dropna()


def log_returns_series(equity: pd.Series) -> pd.Series:
    """Calculate logarithmic returns."""
    if len(equity) < 2:
        return pd.Series(dtype=float)
    return np.log(equity / equity.shift(1)).dropna()


# =========================================================================
# Resampled Period Returns
# =========================================================================


def daily_returns(equity: pd.Series) -> pd.Series:
    """Resample equity curve to daily percentage returns."""
    if len(equity) < 2:
        return pd.Series(dtype=float)
    daily_equity = equity.resample("D").last().dropna()
    return daily_equity.pct_change().dropna()


def weekly_returns(equity: pd.Series) -> pd.Series:
    """Resample equity curve to weekly percentage returns."""
    if len(equity) < 2:
        return pd.Series(dtype=float)
    weekly_equity = equity.resample("W").last().dropna()
    return weekly_equity.pct_change().dropna()


def monthly_returns(equity: pd.Series) -> pd.Series:
    """Resample equity curve to monthly percentage returns."""
    if len(equity) < 2:
        return pd.Series(dtype=float)
    monthly_equity = equity.resample("ME").last().dropna()
    return monthly_equity.pct_change().dropna()


def annual_returns(equity: pd.Series) -> pd.Series:
    """Resample equity curve to annual percentage returns."""
    if len(equity) < 2:
        return pd.Series(dtype=float)
    annual_equity = equity.resample("YE").last().dropna()
    return annual_equity.pct_change().dropna()


# =========================================================================
# Compounding & Growth Rates
# =========================================================================


def cagr(equity: pd.Series) -> float:
    """Compound Annual Growth Rate as percentage."""
    if len(equity) < 2:
        return 0.0
    start_val, end_val = equity.iloc[0], equity.iloc[-1]
    if start_val <= 0:
        return 0.0
    years = (equity.index[-1] - equity.index[0]).total_seconds() / (365.25 * 24 * 3600)
    if years == 0:
        return 0.0
    if end_val <= 0:
        return -100.0
    return float(((end_val / start_val) ** (1 / years) - 1) * 100)


def compound_monthly_growth_rate(equity: pd.Series) -> float:
    """Compound Monthly Growth Rate as percentage."""
    if len(equity) < 2:
        return 0.0
    start_val, end_val = equity.iloc[0], equity.iloc[-1]
    if start_val <= 0:
        return 0.0
    months = (equity.index[-1] - equity.index[0]).total_seconds() / (30.44 * 24 * 3600)
    if months == 0:
        return 0.0
    if end_val <= 0:
        return -100.0
    return float(((end_val / start_val) ** (1 / months) - 1) * 100)


def avg_monthly_return(equity: pd.Series) -> float:
    """Arithmetic mean of monthly returns as percentage."""
    m_ret = monthly_returns(equity)
    return float(m_ret.mean() * 100) if len(m_ret) > 0 else 0.0


def monthly_return_stddev(equity: pd.Series) -> float:
    """Volatility of monthly returns as percentage."""
    m_ret = monthly_returns(equity)
    return float(m_ret.std() * 100) if len(m_ret) >= 2 else 0.0


def annualized_return(
    rets: pd.Series, periods_per_year: Optional[int] = None
) -> float:
    """Scale sub-annual returns to yearly terms."""
    if len(rets) == 0:
        return 0.0
    if periods_per_year is None:
        if isinstance(rets.index, pd.DatetimeIndex):
            mean_diff = (rets.index[-1] - rets.index[0]) / len(rets)
            days = mean_diff.total_seconds() / (24 * 3600)
            periods_per_year = 252 if days < 2 else (52 if days < 8 else (12 if days < 35 else 1))
        else:
            periods_per_year = 252
    return float(((1 + rets.mean()) ** periods_per_year - 1) * 100)


def geometric_mean_return(rets: pd.Series) -> float:
    """Calculate geometric mean return factor."""
    if len(rets) == 0:
        return 0.0
    return float((1 + rets).prod() ** (1 / len(rets)) - 1)


# =========================================================================
# Benchmarking
# =========================================================================


def buy_and_hold_return(price_data: pd.Series) -> float:
    """Total percentage return if asset was bought and held."""
    if len(price_data) < 2 or price_data.iloc[0] == 0:
        return 0.0
    return ((price_data.iloc[-1] - price_data.iloc[0]) / price_data.iloc[0]) * 100.0


def buy_and_hold_cagr(price_data: pd.Series) -> float:
    """CAGR of a buy-and-hold position."""
    return cagr(price_data) if len(price_data) >= 2 else 0.0


# =========================================================================
# Return Stability & Moments
# =========================================================================


def return_volatility(rets: pd.Series) -> float:
    """Standard deviation of returns."""
    return float(rets.std()) if len(rets) >= 2 else 0.0


def downside_return_volatility(rets: pd.Series, target: float = 0.0) -> float:
    """Standard deviation of returns below target."""
    downside = rets[rets < target]
    return float(downside.std()) if len(downside) >= 2 else 0.0


def return_skewness(rets: pd.Series) -> float:
    """Skewness of returns distribution."""
    return float(rets.skew()) if len(rets) >= 3 else 0.0


def return_kurtosis(rets: pd.Series) -> float:
    """Excess kurtosis of returns distribution."""
    return float(rets.kurtosis()) if len(rets) >= 4 else 0.0


# =========================================================================
# Adjusted & Select Metrics
# =========================================================================


def adjusted_gross_profit(trades: pd.DataFrame) -> float:
    """Adjusted Gross Profit: (N - sqrt(N)) * AvgWin."""
    winners = trades[trades["profit_loss"] > 0]
    n = len(winners)
    return float((n - np.sqrt(n)) * winners["profit_loss"].mean()) if n > 0 else 0.0


def adjusted_gross_loss(trades: pd.DataFrame) -> float:
    """Adjusted Gross Loss: (N + sqrt(N)) * AvgLoss."""
    losers = trades[trades["profit_loss"] < 0]
    n = len(losers)
    return float((n + np.sqrt(n)) * losers["profit_loss"].mean()) if n > 0 else 0.0


def adjusted_net_profit(trades: pd.DataFrame) -> float:
    """Difference between adjusted gross profit and adjusted gross loss."""
    return adjusted_gross_profit(trades) + adjusted_gross_loss(trades)


def select_net_profit(trades: pd.DataFrame) -> float:
    """Net profit after removing 3-sigma outliers."""
    if len(trades) == 0: return 0.0
    return float(_remove_outliers(trades, 3.0)["profit_loss"].sum())


def select_gross_profit(trades: pd.DataFrame) -> float:
    """Gross profit after removing 3-sigma outliers."""
    if len(trades) == 0: return 0.0
    filtered = _remove_outliers(trades, 3.0)
    return float(filtered[filtered["profit_loss"] > 0]["profit_loss"].sum())


def select_gross_loss(trades: pd.DataFrame) -> float:
    """Gross loss after removing 3-sigma outliers."""
    if len(trades) == 0: return 0.0
    filtered = _remove_outliers(trades, 3.0)
    return float(filtered[filtered["profit_loss"] < 0]["profit_loss"].sum())


# =========================================================================
# Return Ratios & Capital Relations
# =========================================================================


def return_on_max_strategy_drawdown(equity: pd.Series) -> float:
    """Total Return / Max Strategy Drawdown."""
    dd = drawdowns.max_strategy_drawdown(equity)
    return total_return(equity) / dd if dd != 0 else 0.0


def return_on_max_close_to_close_drawdown(trades: pd.DataFrame) -> float:
    """Net Profit / Max Close-to-Close Drawdown."""
    dd = drawdowns.max_close_to_close_drawdown(trades)
    return net_profit(trades) / dd if dd != 0 else 0.0


def return_on_account(trades: pd.DataFrame) -> float:
    """Return on required account size."""
    return return_on_max_close_to_close_drawdown(trades)


def return_on_initial_capital(trades: pd.DataFrame, initial_capital: float) -> float:
    """Net Profit / Initial Capital."""
    return net_profit(trades) / initial_capital if initial_capital != 0 else 0.0
