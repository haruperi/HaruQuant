"""
Summary:
-------
HaruQuant Returns & Growth Analytics Module.
Equity curves, CAGR, periodic returns, and capital efficiency.
This module provides production-grade growth analytics, distinguishing between realized balance curves 
(closed-trade jumps) and mark-to-market equity curves.

Summary of Methods:
------------------
Basic Profit & Loss:
    - net_profit: Total realized profit/loss.
    - total_return: Total percentage return from initial capital.
    - total_return_usd: Total dollar return.

Curve & Return Generation:
    - balance_curve_from_closed_trades: Realized balance curve indexed by time.
    - returns_series / log_returns_series: Periodic percentage and log returns.
    - periodic_returns (daily, weekly, monthly, annual): Resampled performance series.

Compounding & Growth Rates:
    - cagr: Compound Annual Growth Rate (percentage).
    - geometric_mean_return: Time-weighted average return.
    - best_return / worst_return: Extremes of the return distribution.
    - compound_monthly_growth_rate: CMGR.
    - annualized_return: Geometric annualized return factor.
    - geometric_mean_return: Growth factor per period.

Return Stability & Moments:
    - return_volatility / downside_return_volatility: Standard deviation metrics.
    - return_skewness / return_kurtosis: Distributional moments.

Adjusted & Select Metrics:
    - adjusted_net_profit: Significance-adjusted realized profit.
    - select_net_profit: Outlier-removed realized profit (3-sigma P&L).

Return Ratios & Capital Relations:
    - return_on_max_strategy_drawdown: USD return / Max USD drawdown.
    - return_on_initial_capital: Net profit as percentage of starting balance.
    - return_on_account: Efficiency relative to required margin/drawdown.
"""

from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis

from . import common, drawdowns
from .common import EPSILON, _has_col, get_closed_trades


try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        def decorator(f):
            return f
        return decorator





def _clean_equity(equity: pd.Series) -> pd.Series:
    """Helper to ensure equity series is clean, sorted, and datetime-indexed."""
    if equity is None or len(equity) == 0:
        return pd.Series(dtype=float)

    equity = equity.replace([np.inf, -np.inf], np.nan).dropna()

    if not isinstance(equity.index, pd.DatetimeIndex):
        try:
            equity.index = pd.to_datetime(equity.index)
        except (ValueError, TypeError):
            # If conversion fails, keep as is (likely numeric index)
            pass

    return equity.sort_index()


def _clean_rets(rets: pd.Series) -> pd.Series:
    """Normalize numeric series, replace infinities, drop NaNs."""
    if rets is None or len(rets) == 0:
        return pd.Series(dtype=float)
    s = pd.to_numeric(rets, errors="coerce")
    return s.replace([np.inf, -np.inf], np.nan).dropna().astype(float)


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


def _remove_pnl_outliers(trades: pd.DataFrame, sigma: float = 3.0) -> pd.DataFrame:
    """Remove trades that are outliers (> sigma * std) based on raw P&L."""
    if len(trades) < 2 or not _has_col(trades, "profit_loss"):
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


def total_return_usd(equity: pd.Series) -> float:
    """Total return in currency units from equity curve."""
    equity = _clean_equity(equity)
    if len(equity) < 2:
        return 0.0
    return float(equity.iloc[-1] - equity.iloc[0])


def total_return(equity: pd.Series) -> float:
    """Total return as a percentage of initial capital."""
    equity = _clean_equity(equity)
    if len(equity) < 2 or equity.iloc[0] == 0:
        return 0.0
    profit = total_return_usd(equity)
    initial_capital = float(equity.iloc[0])
    return (profit / initial_capital) * 100.0


def net_profit(trades: pd.DataFrame, closed_only: bool = True) -> float:
    """Total realized profit/loss from closed trades."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "profit_loss"):
        return 0.0
    return float(data["profit_loss"].sum())


def gross_profit(trades: pd.DataFrame, closed_only: bool = True) -> float:
    """Sum of all winning trades (> EPSILON)."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "profit_loss"):
        return 0.0
    wins = data[data["profit_loss"] > EPSILON]
    return float(wins["profit_loss"].sum())


def gross_loss(trades: pd.DataFrame, closed_only: bool = True) -> float:
    """Sum of all losing trades (< -EPSILON)."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "profit_loss"):
        return 0.0
    losses = data[data["profit_loss"] < -EPSILON]
    return float(losses["profit_loss"].sum())


# =========================================================================
# Equity & Returns Generation
# =========================================================================


def balance_curve_from_closed_trades(
    trades: pd.DataFrame,
    initial_balance: float,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> pd.Series:
    """
    Generate a realized balance curve from closed trades.
    Note: This is NOT a mark-to-market equity curve.
    """
    if trades.empty:
        idx = []
        vals = []
        if start_time:
            idx.append(start_time)
            vals.append(initial_balance)
        if end_time:
            idx.append(end_time)
            vals.append(initial_balance)
        if not idx:
            return pd.Series([initial_balance], dtype=float)
        return pd.Series(vals, index=pd.DatetimeIndex(idx))

    closed = get_closed_trades(trades)
    if closed.empty:
        idx = [start_time] if start_time else [trades["open_time"].min()]
        if end_time: idx.append(end_time)
        return pd.Series([initial_balance] * len(idx), index=pd.DatetimeIndex(idx))

    sorted_trades = closed.sort_values("close_time")
    pnl_arr = sorted_trades["profit_loss"].values.astype(np.float64)
    equity_values = _equity_curve_kernel(pnl_arr, float(initial_balance))
    
    first_time = start_time if start_time else sorted_trades.iloc[0]["open_time"]
    indices = np.concatenate([np.array([first_time]), sorted_trades["close_time"].values])
    
    if end_time and end_time > indices[-1]:
        indices = np.concatenate([indices, np.array([end_time])])
        equity_values = np.concatenate([equity_values, np.array([equity_values[-1]])])

    curve = pd.Series(equity_values, index=pd.to_datetime(indices))
    return curve.groupby(level=0).last()


def balance_curve(
    trades: pd.DataFrame,
    initial_balance: float,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> pd.Series:
    """Alias for balance_curve_from_closed_trades."""
    return balance_curve_from_closed_trades(
        trades=trades,
        initial_balance=initial_balance,
        start_time=start_time,
        end_time=end_time,
    )


def equity_curve(
    trades: pd.DataFrame,
    initial_balance: float,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> pd.Series:
    """Alias for balance_curve_from_closed_trades (common orchestration name)."""
    return balance_curve_from_closed_trades(
        trades=trades,
        initial_balance=initial_balance,
        start_time=start_time,
        end_time=end_time,
    )


def returns_series(equity: pd.Series) -> pd.Series:
    """Calculate percentage returns between equity points."""
    equity = _clean_equity(equity)
    if len(equity) < 2:
        return pd.Series(dtype=float)
    
    rets = equity.pct_change().dropna()
    return rets.replace([np.inf, -np.inf], np.nan).dropna()


def log_returns_series(equity: pd.Series) -> pd.Series:
    """Calculate logarithmic returns."""
    equity = _clean_equity(equity)
    if len(equity) < 2:
        return pd.Series(dtype=float)
    
    equity = equity[equity > 0]
    return np.log(equity / equity.shift(1)).dropna()


# =========================================================================
# Resampled Period Returns
# =========================================================================


def daily_returns(equity: pd.Series, calendar: str = "D") -> pd.Series:
    """
    Daily percentage returns from equity curve.
    Includes flat days by forward-filling equity.
    """
    equity = _clean_equity(equity)
    if len(equity) < 2:
        return pd.Series(dtype=float)

    daily_equity = equity.resample(calendar).last().ffill()
    return daily_equity.pct_change().fillna(0.0)


def weekly_returns(equity: pd.Series) -> pd.Series:
    """Weekly percentage returns with forward-filling for flat weeks."""
    equity = _clean_equity(equity)
    if len(equity) < 2:
        return pd.Series(dtype=float)
        
    weekly_equity = equity.resample("W").last().ffill()
    return weekly_equity.pct_change().fillna(0.0)


def monthly_returns(equity: pd.Series) -> pd.Series:
    """Monthly percentage returns (ME) with forward-filling for flat months."""
    equity = _clean_equity(equity)
    if len(equity) < 2:
        return pd.Series(dtype=float)
        
    monthly_equity = equity.resample("ME").last().ffill()
    return monthly_equity.pct_change().fillna(0.0)


def annual_returns(equity: pd.Series) -> pd.Series:
    """Annual percentage returns (YE) with forward-filling for flat years."""
    equity = _clean_equity(equity)
    if len(equity) < 2:
        return pd.Series(dtype=float)
        
    annual_equity = equity.resample("YE").last().ffill()
    return annual_equity.pct_change().fillna(0.0)


# =========================================================================
# Compounding & Growth Rates
# =========================================================================


def cagr(equity: pd.Series) -> float:
    """Compound Annual Growth Rate as percentage."""
    equity = _clean_equity(equity)
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
    return float(((end_val / start_val) ** (1 / years) - 1) * 100.0)


def compound_monthly_growth_rate(equity: pd.Series) -> float:
    """Compound Monthly Growth Rate as percentage."""
    equity = _clean_equity(equity)
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
    return float(((end_val / start_val) ** (1 / months) - 1) * 100.0)


def avg_monthly_return(equity: pd.Series) -> float:
    """Arithmetic mean of monthly returns as percentage."""
    m_ret = monthly_returns(equity)
    return float(m_ret.mean() * 100) if len(m_ret) > 0 else 0.0


def monthly_return_stddev(equity: pd.Series) -> float:
    """Volatility of monthly returns as percentage."""
    m_ret = monthly_returns(equity)
    return float(m_ret.std() * 100) if len(m_ret) >= 2 else 0.0


def annualized_return(
    rets: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """
    Geometric annualized return as percentage.
    """
    if len(rets) == 0:
        return 0.0

    rets = rets.replace([np.inf, -np.inf], np.nan).dropna()
    if len(rets) == 0:
        return 0.0

    growth = (1.0 + rets).prod()
    if growth <= 0:
        return -100.0

    return float((growth ** (periods_per_year / len(rets)) - 1.0) * 100.0)


def geometric_mean_return(rets: pd.Series) -> float:
    """Calculate geometric mean return as a percentage."""
    rets = _clean_rets(rets)
    if len(rets) < 1:
        return 0.0
    
    # (Product(1 + r)) ^ (1/n) - 1
    # Adding a small shift to handle zero/negative returns gracefully if needed, 
    # though usually calculated on (1+r).
    g_mean = float(np.prod(1 + rets) ** (1 / len(rets)) - 1)
    return g_mean * 100.0


def best_return(rets: pd.Series) -> float:
    """Maximum single-period return as percentage."""
    s = pd.Series(rets).replace([np.inf, -np.inf], np.nan).dropna()
    return float(s.max() * 100.0) if not s.empty else 0.0


def worst_return(rets: pd.Series) -> float:
    """Minimum single-period return as percentage."""
    s = pd.Series(rets).replace([np.inf, -np.inf], np.nan).dropna()
    return float(s.min() * 100.0) if not s.empty else 0.0


# =========================================================================
# Benchmarking
# =========================================================================


def buy_and_hold_return(price_data: pd.Series, **kwargs) -> float:
    """Total percentage return of asset if bought and held."""
    if price_data is None or len(price_data) < 2 or price_data.iloc[0] == 0:
        return 0.0
    return float(((price_data.iloc[-1] / price_data.iloc[0]) - 1.0) * 100.0)


def buy_and_hold_cagr(price_data: pd.Series, **kwargs) -> float:
    """CAGR of a buy-and-hold position based on price data."""
    if price_data is None or len(price_data) < 2:
        return 0.0
    return cagr(price_data)


# =========================================================================
# Return Stability & Moments
# =========================================================================


def return_volatility(rets: pd.Series) -> float:
    """Standard deviation of returns as a percentage."""
    vol = float(rets.std()) if len(rets) >= 2 else 0.0
    return vol * 100.0


def downside_return_volatility(rets: pd.Series, target: float = 0.0) -> float:
    """Standard deviation of returns below target as a percentage."""
    downside = rets[rets < target]
    vol = float(downside.std()) if len(downside) >= 2 else 0.0
    return vol * 100.0


def return_skewness(rets: pd.Series) -> float:
    """Population skewness of returns distribution."""
    if len(rets) < 3:
        return 0.0
    return float(skew(rets, bias=True))


def return_kurtosis(rets: pd.Series) -> float:
    """Fisher's population excess kurtosis of returns distribution."""
    if len(rets) < 4:
        return 0.0
    return float(kurtosis(rets, bias=True))


# =========================================================================
# Adjusted & Select Metrics
# =========================================================================


def adjusted_gross_profit(trades: pd.DataFrame, closed_only: bool = True) -> float:
    """Adjusted Gross Profit: (N - sqrt(N)) * AvgWin."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "profit_loss"): return 0.0
    
    winners = data[data["profit_loss"] > EPSILON]
    n = len(winners)
    return float((n - np.sqrt(n)) * winners["profit_loss"].mean()) if n > 0 else 0.0


def adjusted_gross_loss(trades: pd.DataFrame, closed_only: bool = True) -> float:
    """Adjusted Gross Loss: (N + sqrt(N)) * AvgLoss."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "profit_loss"): return 0.0
    
    losers = data[data["profit_loss"] < -EPSILON]
    n = len(losers)
    return float((n + np.sqrt(n)) * losers["profit_loss"].mean()) if n > 0 else 0.0


def adjusted_net_profit(trades: pd.DataFrame, closed_only: bool = True) -> float:
    """Difference between adjusted gross profit and adjusted gross loss."""
    return adjusted_gross_profit(trades, closed_only) + adjusted_gross_loss(trades, closed_only)


def select_net_profit(trades: pd.DataFrame, closed_only: bool = True) -> float:
    """Net profit after removing 3-sigma P&L outliers."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "profit_loss"): return 0.0
    return float(_remove_pnl_outliers(data, 3.0)["profit_loss"].sum())


def select_gross_profit(trades: pd.DataFrame, closed_only: bool = True) -> float:
    """Gross profit after removing 3-sigma P&L outliers."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "profit_loss"): return 0.0
    filtered = _remove_pnl_outliers(data, 3.0)
    return float(filtered[filtered["profit_loss"] > EPSILON]["profit_loss"].sum())


def select_gross_loss(trades: pd.DataFrame, closed_only: bool = True) -> float:
    """Gross loss after removing 3-sigma P&L outliers."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "profit_loss"): return 0.0
    filtered = _remove_pnl_outliers(data, 3.0)
    return float(filtered[filtered["profit_loss"] < -EPSILON]["profit_loss"].sum())


# =========================================================================
# Return Ratios & Capital Relations
# =========================================================================


def return_on_max_strategy_drawdown(equity: pd.Series) -> float:
    """Total Return (USD) / Max Strategy Drawdown (USD)."""
    dd = drawdowns.max_strategy_drawdown(equity)
    return total_return_usd(equity) / dd if dd != 0 else 0.0


def return_on_max_close_to_close_drawdown(trades: pd.DataFrame) -> float:
    """Net Profit / Max Close-to-Close Drawdown."""
    dd = drawdowns.max_close_to_close_drawdown(trades)
    return net_profit(trades) / dd if dd != 0 else 0.0


def return_on_account(trades: pd.DataFrame) -> float:
    """Return on required account size."""
    return return_on_max_close_to_close_drawdown(trades)


def return_on_initial_capital(trades: pd.DataFrame, initial_capital: float) -> float:
    """Net profit as a percentage of initial capital."""
    if initial_capital == 0:
        return 0.0
    return float((net_profit(trades) / initial_capital) * 100.0)


# =========================================================================
# Run-up Metrics (Valley-to-Peak Gain)
# =========================================================================


def max_runup(equity_curve: pd.Series) -> float:
    """
    Max Run-up: maximum gain from a valley to a peak.
    """
    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) == 0:
        return 0.0
    running_min = equity_curve.expanding().min()
    runup_series = equity_curve - running_min
    return float(runup_series.max())


def max_runup_date(equity_curve: pd.Series) -> Optional[pd.Timestamp]:
    """
    Date of Max Run-up peak.
    """
    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) == 0:
        return None
    running_min = equity_curve.expanding().min()
    runup_series = equity_curve - running_min
    try:
        return runup_series.idxmax()
    except (ValueError, TypeError):
        return None
