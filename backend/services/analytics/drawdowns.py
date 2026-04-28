"""
Summary:
-------
HaruQuant Drawdown & Risk Analytics Module.
Drawdown depth, duration, recovery behavior, and pain indices.
This module provides production-grade analytics for quantifying downside risk, including 
equity-curve drawdowns and high-fidelity trade-level excursions (MFE/MAE).

Summary of Methods:
------------------
Equity Drawdowns:
    - max_drawdown: Deepest percentage decline.
    - avg_drawdown: Mean depth of all drawdown periods.
    - drawdown_series: Running peak-to-valley decline series.
    - drawdown_distribution: Quantile and moment analysis of drawdown depth.

Duration & Recovery:
    - max_drawdown_duration: Longest time spent in drawdown (seconds).
    - avg_drawdown_duration: Mean time to recovery.
    - recovery_factor: Total return divided by max drawdown.

Trade Excursions (MFE/MAE):
    - mfe_mae_summary: Max Favorable/Adverse Excursion analysis.
    - max_consecutive_drawdown_trades: Worst sequence of losing trades.
    - max_drawdown_duration: Longest period spent in drawdown.
    - avg_drawdown_duration: Average length of drawdown periods.
    - time_to_recovery: List of recovery durations for each distinct drawdown.
    - recovery_factor: Net profit relative to maximum drawdown depth.

Trade-Level Diagnostics:
    - max_close_to_close_drawdown: Max drawdown including intra-trade MFE/MAE excursions.
    - max_close_to_close_drawdown_percent: Percentage version of high-fidelity drawdown.
    - avg_trade_drawdown: Mean depth of trade-level balance drawdowns.
    - account_size_required: Minimum capital required to buffer max trade-level dips.

Periodic & Temporal Metrics:
    - avg_yearly_max_drawdown: Mean of the maximum drawdowns observed in each year.
    - max_strategy_drawdown_date: Timestamp of the deepest strategy valley.
    - max_close_to_close_drawdown_date: Timestamp of the deepest trade-level valley.

Pain & Volatility Indices:
    - ulcer_index: Quadratic mean of percentage drawdowns (stress metric).
    - pain_index: Mean absolute percentage drawdown across all periods.
    - avg_underwater_drawdown_percent: Mean drawdown depth only while below peak.
    - pain_ratio: Total return normalized by the Pain Index.
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import common
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


def _sort_trades_for_drawdown(trades: pd.DataFrame) -> pd.DataFrame:
    """Safely sort trades by close_time or open_time for drawdown analysis."""
    if "close_time" in trades.columns:
        return trades.sort_values("close_time")
    if "open_time" in trades.columns:
        return trades.sort_values("open_time")
    return trades.copy()


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

    return array[np.isfinite(array)]


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
    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) == 0:
        return pd.Series(dtype=float)
    running_max = equity_curve.expanding().max()
    return equity_curve - running_max


def drawdown_duration_series(equity_curve: pd.Series) -> pd.Series:
    """Calculate drawdown duration series."""
    equity_curve = _clean_equity(equity_curve)
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
    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) == 0:
        return 0.0
    dd_series = drawdown_series(equity_curve)
    return float(abs(dd_series.min()))


def max_strategy_drawdown_percent(equity_curve: pd.Series) -> float:
    """Deepest percentage decline relative to running peak."""
    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) == 0:
        return 0.0
    running_max = equity_curve.expanding().max()
    # Guard against zero/negative peaks for percentage calculation
    running_max = running_max.replace(0, np.nan).ffill().fillna(1e-9)
    pct_drawdown = ((equity_curve - running_max) / running_max) * 100
    return float(abs(pct_drawdown.min()))


def max_drawdown(returns: pd.Series | np.ndarray) -> float:
    """Maximum drawdown from returns as a positive percentage."""
    normalized = _returns_array(returns)
    if len(normalized) == 0:
        return 0.0

    cumulative = np.concatenate([[1.0], np.cumprod(1.0 + normalized)])
    running_max = np.maximum.accumulate(cumulative)
    drawdowns_vals = (cumulative - running_max) / running_max

    return float(abs(np.min(drawdowns_vals)) * 100.0)


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


def max_drawdown_duration_from_equity(equity_curve: pd.Series) -> int:
    """Maximum number of periods spent in drawdown from equity curve."""
    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) == 0:
        return 0
    equity_arr = equity_curve.astype(float).to_numpy()
    return _max_drawdown_duration_kernel(equity_arr)


def max_drawdown_duration_from_returns(returns: pd.Series | np.ndarray) -> int:
    """Maximum number of periods spent in drawdown from returns series."""
    rets = _returns_array(returns)
    if len(rets) == 0:
        return 0

    cumulative = np.concatenate([[1.0], np.cumprod(1.0 + rets)])
    duration = _max_drawdown_duration_kernel(cumulative)
    return max(0, int(duration))


def max_drawdown_duration(values, input_type: str = "equity") -> int:
    """
    Maximum number of periods spent in drawdown.
    Explicitly define input_type as 'equity' or 'returns'.
    """
    if input_type == "returns":
        return max_drawdown_duration_from_returns(values)
    return max_drawdown_duration_from_equity(values)


def avg_drawdown_duration(equity_curve: pd.Series) -> float:
    """Average duration of drawdown episodes (recovery intervals)."""
    recoveries = time_to_recovery(equity_curve)
    return float(np.mean(recoveries)) if recoveries else 0.0


def time_to_recovery(equity_curve: pd.Series) -> List[int]:
    """List of recovery periods for each unique drawdown."""
    equity_curve = _clean_equity(equity_curve)
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

        total_return_pct = (np.prod(1.0 + normalized) - 1.0) * 100.0
        drawdown_pct = max_drawdown(normalized)

        if drawdown_pct == 0:
            return float("inf") if total_return_pct > 0 else float("nan")

        return float(total_return_pct / drawdown_pct)

    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) < 2:
        return 0.0
        
    net_profit_val = equity_curve.iloc[-1] - equity_curve.iloc[0]
    max_dd_val = max_strategy_drawdown(equity_curve)
    
    if max_dd_val == 0:
        return 0.0 if net_profit_val == 0 else float("inf")
        
    return float(net_profit_val / max_dd_val)


# =========================================================================
# Trade-Level Drawdowns
# =========================================================================


def trade_level_drawdowns(trades: pd.DataFrame, closed_only: bool = True) -> pd.Series:
    """Calculate cumulative P&L drawdowns at trade close points, starting from 0."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or "profit_loss" not in data.columns:
        return pd.Series(dtype=float)
    
    sorted_trades = _sort_trades_for_drawdown(data)
    pnl = sorted_trades["profit_loss"].astype(float)
    cumulative_pnl = pnl.cumsum()
    
    # Prepend starting equity 0
    zero_idx = pd.Index(["START"])
    full_curve = pd.concat([pd.Series([0.0], index=zero_idx), cumulative_pnl])
    
    running_max = full_curve.expanding().max()
    dd_curve = full_curve - running_max
    return dd_curve.iloc[1:] # Drop START


def max_close_to_close_drawdown(trades: pd.DataFrame, closed_only: bool = True) -> float:
    """Max drawdown from peak (including MFE) to valley (including MAE or close)."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty:
        return 0.0
        
    sorted_trades = _sort_trades_for_drawdown(data)
    
    # Check if we have high-fidelity excursion data
    if _has_col(sorted_trades, "mfe_usd") and _has_col(sorted_trades, "mae_usd"):
        mfe_arr = np.maximum(sorted_trades["mfe_usd"].astype(float).to_numpy(), 0.0)
        mae_arr = np.abs(sorted_trades["mae_usd"].astype(float).to_numpy())
        pnl_arr = sorted_trades["profit_loss"].astype(float).to_numpy()
        return _max_close_to_close_drawdown_kernel(mfe_arr, mae_arr, pnl_arr, 0.0)
        
    # Fallback: starting balance 0.0
    if _has_col(sorted_trades, "profit_loss"):
        pnl = sorted_trades["profit_loss"].astype(float).to_numpy()
        cumulative_pnl = np.concatenate([[0.0], np.cumsum(pnl)])
        running_max = np.maximum.accumulate(cumulative_pnl)
        return float(np.max(running_max - cumulative_pnl))
        
    return 0.0


def max_close_to_close_drawdown_percent(
    trades: pd.DataFrame, initial_balance: float, closed_only: bool = True
) -> float:
    """Percentage version of close-to-close drawdown."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or initial_balance <= 0:
        return 0.0
        
    sorted_trades = _sort_trades_for_drawdown(data)
    
    if _has_col(sorted_trades, "mfe_usd") and _has_col(sorted_trades, "mae_usd"):
        mfe_arr = np.maximum(sorted_trades["mfe_usd"].astype(float).to_numpy(), 0.0)
        mae_arr = np.abs(sorted_trades["mae_usd"].astype(float).to_numpy())
        pnl_arr = sorted_trades["profit_loss"].astype(float).to_numpy()
        return _max_close_to_close_drawdown_percent_kernel(
            mfe_arr, mae_arr, pnl_arr, float(initial_balance)
        )
        
    # Fallback
    if _has_col(sorted_trades, "profit_loss"):
        pnl_arr = sorted_trades["profit_loss"].astype(float).to_numpy()
        cumulative_pnl = np.concatenate([[0.0], np.cumsum(pnl_arr)]) + initial_balance
        return max_strategy_drawdown_percent(pd.Series(cumulative_pnl))
        
    return 0.0


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


def max_consecutive_drawdown_trades(trades: pd.DataFrame, closed_only: bool = True) -> int:
    """Maximum number of consecutive trades within a single strategy drawdown."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or "profit_loss" not in data.columns:
        return 0
    
    sorted_trades = _sort_trades_for_drawdown(data)
    pnl = sorted_trades["profit_loss"].astype(float)
    cumulative_pnl = pnl.cumsum()
    
    running_max = cumulative_pnl.expanding().max()
    is_underwater = cumulative_pnl < running_max
    
    max_streak = 0
    current_streak = 0
    
    for underwater in is_underwater:
        if underwater:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
        else:
            current_streak = 0
            
    return int(max_streak)


# =========================================================================
# Periodic & Time-Based Metrics
# =========================================================================


def avg_yearly_max_drawdown(equity_curve: pd.Series) -> float:
    """Average of the maximum drawdowns observed in each year."""
    equity_curve = _clean_equity(equity_curve)
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
    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) == 0:
        return None
    dd_series = drawdown_series(equity_curve)
    try:
        return dd_series.idxmin()
    except (ValueError, TypeError):
        return None


def max_close_to_close_drawdown_date(trades: pd.DataFrame, closed_only: bool = True) -> Optional[pd.Timestamp]:
    """Date of the deepest trade-level valley."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty:
        return None
        
    time_col = "close_time" if "close_time" in data.columns else "open_time" if "open_time" in data.columns else None
    if time_col is None:
        return None
        
    sorted_trades = _sort_trades_for_drawdown(data)
    if "mfe_usd" not in data.columns or "mae_usd" not in data.columns:
        pnl = sorted_trades["profit_loss"].astype(float).to_numpy()
        cumulative_pnl = np.concatenate([[0.0], np.cumsum(pnl)])
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = running_max - cumulative_pnl
        
        if len(drawdown) < 2: return None
        # idxmin/argmax of the drawdown (positive)
        idx = np.argmax(drawdown)
        if idx == 0: return None # No drawdown
        return sorted_trades.iloc[idx - 1][time_col]

    current_equity, running_max_equity, max_dd = 0.0, 0.0, 0.0
    max_dd_date = None
    for _, trade in sorted_trades.iterrows():
        mfe = max(float(trade.get("mfe_usd", 0.0)), 0.0)
        mae = abs(float(trade.get("mae_usd", 0.0)))
        pnl = float(trade.get("profit_loss", 0.0))

        trade_peak = current_equity + mfe
        trade_valley = current_equity - mae
        trade_close = current_equity + pnl
        
        running_max_equity = max(running_max_equity, trade_peak)
        dd_valley = running_max_equity - trade_valley
        dd_close = running_max_equity - trade_close
        
        if dd_valley > max_dd:
            max_dd = dd_valley
            max_dd_date = trade[time_col]
        if dd_close > max_dd:
            max_dd = dd_close
            max_dd_date = trade[time_col]
            
        current_equity = trade_close
    return max_dd_date


# =========================================================================
# Pain & Volatility Indices
# =========================================================================


def ulcer_index(equity_curve: pd.Series) -> float:
    """Ulcer Index: sqrt(mean(drawdown_pct^2))."""
    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) == 0:
        return 0.0
    running_max = equity_curve.expanding().max()
    # Guard against non-positive peaks
    ref_max = running_max.where(running_max > 0).ffill().fillna(1e-9)
    pct_drawdown = ((equity_curve - ref_max) / ref_max) * 100
    return float(np.sqrt((pct_drawdown**2).mean()))


def pain_index(equity_curve: pd.Series) -> float:
    """Pain Index: mean absolute percentage drawdown across all periods."""
    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) == 0:
        return 0.0

    running_max = equity_curve.expanding().max()
    ref_max = running_max.where(running_max > 0).ffill().fillna(1e-9)

    pct_drawdown = ((equity_curve - ref_max) / ref_max) * 100.0
    return float(abs(pct_drawdown).mean())


def avg_underwater_drawdown_percent(equity_curve: pd.Series) -> float:
    """Average drawdown depth only for periods where equity is below peak."""
    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) == 0:
        return 0.0

    running_max = equity_curve.expanding().max()
    ref_max = running_max.where(running_max > 0).ffill().fillna(1e-9)

    pct_drawdown = ((equity_curve - ref_max) / ref_max) * 100.0
    dips = pct_drawdown[pct_drawdown < 0]

    return float(abs(dips.mean())) if not dips.empty else 0.0


def pain_ratio(equity_curve: pd.Series) -> float:
    """Pain Ratio: Total Percentage Return / Pain Index."""
    equity_curve = _clean_equity(equity_curve)
    if len(equity_curve) < 2:
        return 0.0
    pain = pain_index(equity_curve)
    if pain == 0:
        return 0.0
    total_return_pct = ((equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1.0) * 100.0
    return float(total_return_pct / pain)
