"""
Drawdown depth, duration, and recovery metrics.

Focus: capital pain & recovery behavior

This module provides functions to calculate the extent and persistence of declines in equity.
It includes peak-to-valley drawdown analysis, recovery times, trade-level excursions,
and specialized risk indices like the Ulcer Index.

Summary of Methods:
------------------
Utility Helpers:
    - drawdown_series: Calculate series of drawdown values from equity.
    - drawdown_duration_series: Number of periods in drawdown at each point.

Core Equity Drawdowns:
    - max_strategy_drawdown: Deepest peak-to-valley decline (currency).
    - max_strategy_drawdown_percent: Deepest decline as a percentage.
    - max_drawdown: Maximum drawdown calculated from a returns series.
    - avg_drawdown: Mean depth of drawdown periods.
    - drawdown_distribution: Detailed stats (max, avg, median, std, p95).

Drawdown Duration & Recovery:
    - max_drawdown_duration: Longest period spent in drawdown.
    - avg_drawdown_duration: Average length of drawdown periods.
    - time_to_recovery: List of recovery periods for each drawdown.
    - recovery_factor: Net profit relative to maximum drawdown.

Trade-Level Drawdowns:
    - trade_level_drawdowns: Drawdowns calculated at individual trade close points.
    - max_close_to_close_drawdown: Max drawdown using MFE/MAE excursions.
    - max_close_to_close_drawdown_percent: Percentage version of close-to-close drawdown.
    - avg_trade_drawdown: Mean depth of trade-level drawdowns.
    - account_size_required: Capital required to withstand max close-to-close dips.

Periodic & Time-Based Metrics:
    - avg_yearly_max_drawdown: Average of the maximum drawdowns for each year.
    - max_strategy_drawdown_date: Timestamp of the deepest strategy valley.
    - max_close_to_close_drawdown_date: Timestamp of the deepest trade-level valley.

Pain & Volatility Indices:
    - ulcer_index: Square root of mean squared drawdown percentage.
    - pain_index: Average squared percentage drawdown.
    - pain_ratio: Total return relative to the Pain Index.
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd


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


def _returns_array(values) -> np.ndarray:
    """Normalize returns-like input to a float NumPy array."""
    if isinstance(values, pd.Series):
        array = values.astype(float).to_numpy()
    else:
        array = np.asarray(values, dtype=float)

    if array.ndim == 0:
        array = array.reshape(1)

    return array[~np.isnan(array)]


@njit(cache=True)
def _max_drawdown_duration_kernel(cumulative_equity):
    running_max = -1e18
    max_duration = 0
    current_duration = 0
    for val in cumulative_equity:
        if val >= running_max:
            running_max = val
            current_duration = 0
        else:
            current_duration += 1
            if current_duration > max_duration:
                max_duration = current_duration
    return max_duration


@njit(cache=True)
def _drawdown_duration_series_kernel(equity_arr):
    n = len(equity_arr)
    durations = np.zeros(n, dtype=np.int64)
    running_max = -1e18
    current_duration = 0
    for i in range(n):
        val = equity_arr[i]
        if val >= running_max:
            running_max = val
            current_duration = 0
        else:
            current_duration += 1
        durations[i] = current_duration
    return durations


@njit(cache=True)
def _max_close_to_close_drawdown_kernel(mfe_arr, mae_arr, pnl_arr, initial_equity):
    current_equity = initial_equity
    running_max_equity = initial_equity
    max_dd = 0.0

    for i in range(len(mfe_arr)):
        mfe = mfe_arr[i]
        mae = mae_arr[i]
        pnl = pnl_arr[i]

        trade_peak = current_equity + mfe
        trade_valley = current_equity - mae
        trade_close = current_equity + pnl

        if trade_peak > running_max_equity:
            running_max_equity = trade_peak

        dd_valley = running_max_equity - trade_valley
        dd_close = running_max_equity - trade_close

        if dd_valley > max_dd:
            max_dd = dd_valley
        if dd_close > max_dd:
            max_dd = dd_close

        current_equity = trade_close
    return max_dd


@njit(cache=True)
def _max_close_to_close_drawdown_percent_kernel(
    mfe_arr, mae_arr, pnl_arr, initial_balance
):
    current_equity = initial_balance
    running_max_equity = initial_balance
    max_dd_pct = 0.0

    for i in range(len(mfe_arr)):
        mfe = mfe_arr[i]
        mae = mae_arr[i]
        pnl = pnl_arr[i]

        trade_peak = current_equity + mfe
        trade_valley = current_equity - mae
        trade_close = current_equity + pnl

        if trade_peak > running_max_equity:
            running_max_equity = trade_peak

        peak_ref = running_max_equity if running_max_equity > 0 else 1e-9

        dd_valley_pct = (running_max_equity - trade_valley) / peak_ref * 100
        dd_close_pct = (running_max_equity - trade_close) / peak_ref * 100

        if dd_valley_pct > max_dd_pct:
            max_dd_pct = dd_valley_pct
        if dd_close_pct > max_dd_pct:
            max_dd_pct = dd_close_pct

        current_equity = trade_close
    return max_dd_pct


# =========================================================================
# Utility Functions
# =========================================================================


def drawdown_series(equity_curve: pd.Series) -> pd.Series:
    """Calculate drawdown series from equity curve."""
    if len(equity_curve) == 0:
        return pd.Series(dtype=float)
    running_max = equity_curve.expanding().max()
    return equity_curve - running_max


def drawdown_duration_series(equity_curve: pd.Series) -> pd.Series:
    """Calculate drawdown duration series."""
    if len(equity_curve) == 0:
        return pd.Series(dtype=int)
    equity_arr = equity_curve.astype(float).to_numpy()
    durations = _drawdown_duration_series_kernel(equity_arr)
    return pd.Series(durations, index=equity_curve.index)


# =========================================================================
# Core Equity Drawdowns
# =========================================================================


def max_strategy_drawdown(equity_curve: pd.Series) -> float:
    """Deepest peak-to-valley decline in the equity curve (currency)."""
    if len(equity_curve) == 0:
        return 0.0
    dd_series = drawdown_series(equity_curve)
    return float(abs(dd_series.min()))


def max_strategy_drawdown_percent(equity_curve: pd.Series) -> float:
    """Deepest percentage decline relative to running peak."""
    if len(equity_curve) == 0:
        return 0.0
    running_max = equity_curve.expanding().max()
    running_max[running_max == 0] = 1e-9
    pct_drawdown = ((equity_curve - running_max) / running_max) * 100
    return float(abs(pct_drawdown.min()))


def max_drawdown(returns: pd.Series | np.ndarray) -> float:
    """Calculate maximum drawdown from a returns series (pct)."""
    normalized = _returns_array(returns)
    if len(normalized) == 0:
        return float("nan")
    cumulative = np.cumprod(1 + normalized)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    return float(np.min(drawdowns))


def avg_drawdown(equity_curve: pd.Series) -> float:
    """Average depth of drawdown periods."""
    if len(equity_curve) == 0:
        return 0.0
    dd_series = drawdown_series(equity_curve)
    dd_values = dd_series[dd_series < 0]
    if len(dd_values) == 0:
        return 0.0
    return float(abs(dd_values.mean()))


def drawdown_distribution(equity_curve: pd.Series) -> Dict[str, float]:
    """Detailed drawdown distribution statistics."""
    if len(equity_curve) == 0:
        return {"max": 0.0, "avg": 0.0, "median": 0.0, "std": 0.0, "p95": 0.0}
    dd_series = drawdown_series(equity_curve)
    dd_values = abs(dd_series[dd_series < 0])
    if len(dd_values) == 0:
        return {"max": 0.0, "avg": 0.0, "median": 0.0, "std": 0.0, "p95": 0.0}
    return {
        "max": float(dd_values.max()),
        "avg": float(dd_values.mean()),
        "median": float(dd_values.median()),
        "std": float(dd_values.std()),
        "p95": float(dd_values.quantile(0.95)),
    }


# =========================================================================
# Drawdown Duration & Recovery
# =========================================================================


def max_drawdown_duration(equity_curve: pd.Series | np.ndarray) -> int:
    """Maximum number of periods spent in drawdown."""
    if not isinstance(equity_curve, pd.Series):
        rets = _returns_array(equity_curve)
        if len(rets) == 0:
            return 0
        cumulative = np.cumprod(1 + rets)
        return _max_drawdown_duration_kernel(cumulative)
    if len(equity_curve) == 0:
        return 0
    equity_arr = equity_curve.astype(float).to_numpy()
    return _max_drawdown_duration_kernel(equity_arr)


def avg_drawdown_duration(equity_curve: pd.Series) -> float:
    """Average duration of drawdown periods."""
    if len(equity_curve) == 0:
        return 0.0
    duration_series = drawdown_duration_series(equity_curve)
    dd_periods = duration_series[duration_series > 0]
    if len(dd_periods) == 0:
        return 0.0
    return float(dd_periods.mean())


def time_to_recovery(equity_curve: pd.Series) -> List[int]:
    """List of recovery periods for each unique drawdown."""
    if len(equity_curve) == 0:
        return []
    running_max = equity_curve.expanding().max()
    at_high = equity_curve >= running_max
    recovery_times = []
    current_duration = 0
    in_drawdown = False
    for is_high in at_high:
        if not is_high:
            in_drawdown = True
            current_duration += 1
        else:
            if in_drawdown:
                recovery_times.append(current_duration)
                current_duration = 0
                in_drawdown = False
    return recovery_times


def recovery_factor(equity_curve: pd.Series | np.ndarray) -> float:
    """Net profit relative to maximum drawdown."""
    if not isinstance(equity_curve, pd.Series):
        normalized = _returns_array(equity_curve)
        if len(normalized) == 0:
            return float("nan")
        total_return = np.prod(1 + normalized) - 1
        drawdown = max_drawdown(normalized)
        if drawdown == 0:
            return float("inf") if total_return > 0 else float("nan")
        return float(total_return / abs(drawdown))
    if len(equity_curve) < 2:
        return 0.0
    net_profit = equity_curve.iloc[-1] - equity_curve.iloc[0]
    max_dd = max_strategy_drawdown(equity_curve)
    if max_dd == 0:
        return 0.0 if net_profit == 0 else float("inf")
    return float(net_profit / max_dd)


# =========================================================================
# Trade-Level Drawdowns
# =========================================================================


def trade_level_drawdowns(trades: pd.DataFrame) -> pd.Series:
    """Calculate cumulative P&L drawdowns at trade close points."""
    if len(trades) == 0:
        return pd.Series(dtype=float)
    sorted_trades = trades.sort_values("close_time")
    cumulative_pnl = sorted_trades["profit_loss"].cumsum()
    running_max = cumulative_pnl.expanding().max()
    return cumulative_pnl - running_max


def max_close_to_close_drawdown(trades: pd.DataFrame) -> float:
    """Max drawdown from peak (including MFE) to valley (including MAE or close)."""
    if len(trades) == 0:
        return 0.0
    if "mfe_usd" not in trades.columns or "mae_usd" not in trades.columns:
        sorted_trades = trades.sort_values("close_time")
        cumulative_pnl = sorted_trades["profit_loss"].cumsum().to_numpy()
        running_max = np.maximum.accumulate(cumulative_pnl)
        return float(np.max(running_max - cumulative_pnl))
    sorted_trades = trades.sort_values("close_time")
    mfe_arr = sorted_trades["mfe_usd"].astype(float).to_numpy()
    mae_arr = sorted_trades["mae_usd"].astype(float).to_numpy()
    pnl_arr = sorted_trades["profit_loss"].astype(float).to_numpy()
    return _max_close_to_close_drawdown_kernel(mfe_arr, mae_arr, pnl_arr, 0.0)


def max_close_to_close_drawdown_percent(
    trades: pd.DataFrame, initial_balance: float
) -> float:
    """Percentage version of close-to-close drawdown."""
    if len(trades) == 0 or initial_balance <= 0:
        return 0.0
    if "mfe_usd" not in trades.columns or "mae_usd" not in trades.columns:
        c_pnl = trades.sort_values("close_time")["profit_loss"].cumsum() + initial_balance
        return max_strategy_drawdown_percent(c_pnl)
    sorted_trades = trades.sort_values("close_time")
    mfe_arr = sorted_trades["mfe_usd"].astype(float).to_numpy()
    mae_arr = sorted_trades["mae_usd"].astype(float).to_numpy()
    pnl_arr = sorted_trades["profit_loss"].astype(float).to_numpy()
    return _max_close_to_close_drawdown_percent_kernel(
        mfe_arr, mae_arr, pnl_arr, float(initial_balance)
    )


def avg_trade_drawdown(trades: pd.DataFrame) -> float:
    """Mean depth of trade-level close-to-close drawdowns."""
    if len(trades) == 0:
        return 0.0
    dd_series = trade_level_drawdowns(trades)
    dd_values = dd_series[dd_series < 0]
    if len(dd_values) == 0:
        return 0.0
    return float(abs(dd_values.mean()))


def account_size_required(trades: pd.DataFrame) -> float:
    """Capital required to withstand max close-to-close dips."""
    return max_close_to_close_drawdown(trades)


# =========================================================================
# Periodic & Time-Based Metrics
# =========================================================================


def avg_yearly_max_drawdown(equity_curve: pd.Series) -> float:
    """Average of the maximum drawdowns observed in each year."""
    if len(equity_curve) == 0 or not isinstance(equity_curve.index, pd.DatetimeIndex):
        return 0.0
    yearly_groups = equity_curve.groupby(pd.Grouper(freq="YE"))
    max_dds = []
    for _, yearly_equity in yearly_groups:
        if len(yearly_equity) > 0:
            max_dds.append(max_strategy_drawdown(yearly_equity))
    return float(np.mean(max_dds)) if max_dds else 0.0


def max_strategy_drawdown_date(equity_curve: pd.Series) -> Optional[pd.Timestamp]:
    """Date of the absolute deepest strategy equity valley."""
    if len(equity_curve) == 0:
        return None
    dd_series = drawdown_series(equity_curve)
    try:
        return dd_series.idxmin()
    except (ValueError, TypeError):
        return None


def max_close_to_close_drawdown_date(trades: pd.DataFrame) -> Optional[pd.Timestamp]:
    """Date of the deepest trade-level valley."""
    if len(trades) == 0 or "close_time" not in trades.columns:
        return None
    sorted_trades = trades.sort_values("close_time")
    if "mfe_usd" not in trades.columns or "mae_usd" not in trades.columns:
        cumulative_pnl = sorted_trades["profit_loss"].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = cumulative_pnl - running_max
        try:
            return sorted_trades.loc[drawdown.idxmin(), "close_time"]
        except:
            return None
    current_equity, running_max_equity, max_dd = 0.0, 0.0, 0.0
    max_dd_date = None
    for _, trade in sorted_trades.iterrows():
        trade_peak = current_equity + trade["mfe_usd"]
        trade_valley = current_equity - trade["mae_usd"]
        trade_close = current_equity + trade["profit_loss"]
        running_max_equity = max(running_max_equity, trade_peak)
        dd_valley = running_max_equity - trade_valley
        dd_close = running_max_equity - trade_close
        if dd_valley > max_dd:
            max_dd = dd_valley
            max_dd_date = trade["close_time"]
        if dd_close > max_dd:
            max_dd = dd_close
            max_dd_date = trade["close_time"]
        current_equity = trade_close
    return max_dd_date


# =========================================================================
# Pain & Volatility Indices
# =========================================================================


def ulcer_index(equity_curve: pd.Series) -> float:
    """Ulcer Index: sqrt(mean(drawdown_pct^2))."""
    if len(equity_curve) == 0:
        return 0.0
    running_max = equity_curve.expanding().max()
    pct_drawdown = ((equity_curve - running_max) / running_max) * 100
    return float(np.sqrt((pct_drawdown**2).mean()))


def pain_index(equity_curve: pd.Series) -> float:
    """Pain Index: mean(drawdown_pct^2)."""
    if len(equity_curve) == 0:
        return 0.0
    running_max = equity_curve.expanding().max()
    pct_drawdown = ((equity_curve - running_max.replace(0, 1e-9)) / running_max.replace(0, 1e-9)) * 100
    return float(abs((pct_drawdown**2).mean()))


def pain_ratio(equity_curve: pd.Series, returns_in: pd.Series) -> float:
    """Pain Ratio: Total Return / Pain Index."""
    if len(equity_curve) == 0 or len(returns_in) == 0:
        return 0.0
    pain = pain_index(equity_curve)
    if pain == 0:
        return 0.0
    return float(returns_in.sum() / pain)
