"""
Summary:
-------
HaruQuant Analytics Common Utilities.
Shared constants and low-level data processing primitives for trade and equity analysis.
This module provides the core data extraction and cleaning helpers used across all analytics modules.

Summary of Methods:
------------------
Data Extraction & Cleaning:
    - get_trades_pnl: Extract raw P&L values from trade records.
    - get_r_multiples: Calculate R-multiple risk-to-reward metrics.
    - get_durations: Calculate trade durations in seconds or hours.
    - get_equity_series: Extract daily/periodic equity series from a backtest result.
    - clean_series: Convert input data to a finite numeric pandas Series.
    - clean_returns: Normalize input data to a finite 1D NumPy float array.
"""

from typing import List, Optional, Tuple
import numpy as np
import pandas as pd

EPSILON = 1e-4


try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        def decorator(f):
            return f
        return decorator


# =========================================================================
# Data Access & Column Primitives
# =========================================================================


def _has_col(df: pd.DataFrame, col: str) -> bool:
    """Check if a column exists in a DataFrame."""
    return col in df.columns


def get_closed_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Filter for closed trades.
    A trade is open if exit_reason is 'END_OF_DATA', 'OPEN', or if close_time is null.
    """
    if trades.empty:
        return trades.copy()

    closed = trades.copy()
    if "exit_reason" in closed.columns:
        open_reasons = {"END_OF_DATA", "OPEN"}
        closed = closed[~closed["exit_reason"].isin(open_reasons)]

    if "close_time" in closed.columns:
        closed = closed[closed["close_time"].notna()]

    return closed


def _to_1d_float_array(values) -> np.ndarray:
    """Normalize numeric inputs to a finite float NumPy array."""
    if isinstance(values, pd.Series):
        array = values.astype(float).to_numpy()
    else:
        array = np.asarray(values, dtype=float)

    if array.ndim == 0:
        array = array.reshape(1)

    return array[np.isfinite(array)]


def _to_datetime_series(series: pd.Series) -> pd.Series:
    """Convert a timestamp series safely, supporting datetime values and Unix seconds."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_datetime(series, unit="s")
    return pd.to_datetime(series)


# =========================================================================
# Core Trade Statistics (The Analytics Foundation)
# =========================================================================


def classify_trades(trades: pd.DataFrame, pnl_col: str = "profit_loss") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Classify trades into wins, losses, and breakevens using a consistent threshold.
    """
    if trades.empty or not _has_col(trades, pnl_col):
        empty = pd.DataFrame(columns=trades.columns)
        return empty, empty, empty

    pnl = trades[pnl_col]
    wins = trades[pnl > EPSILON]
    losses = trades[pnl < -EPSILON]
    breakevens = trades[pnl.abs() <= EPSILON]
    return wins, losses, breakevens


def avg_loss(trades: pd.DataFrame) -> float:
    """Mean loss of losing trades."""
    if trades.empty or not _has_col(trades, "profit_loss"):
        return 0.0
    _, losses, _ = classify_trades(get_closed_trades(trades))
    return float(losses["profit_loss"].mean()) if not losses.empty else 0.0


def get_r_multiples(trades: pd.DataFrame, closed_only: bool = True) -> pd.Series:
    """
    Get R-multiples for trades. 
    Priority:
    1. 'initial_risk_amount' (Monetary risk)
    2. 'initial_risk' (Generic risk amount)
    3. Fallback: abs(avg_loss) as estimated proxy.
    """
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "profit_loss"):
        return pd.Series(dtype=float)

    # 1. Official Risk Amount (Monetary)
    for col in ["initial_risk_amount", "initial_risk"]:
        if col in data.columns:
            risk = data[col].abs().replace(0, np.nan)
            r = data["profit_loss"] / risk
            r = r.replace([np.inf, -np.inf], np.nan).dropna()
            if not r.empty:
                return r

    # 2. Fallback: Use Average Loss as proxy for 1R baseline
    avg_l = abs(avg_loss(data))
    if avg_l > EPSILON:
        r = data["profit_loss"] / avg_l
        return r.replace([np.inf, -np.inf], np.nan).dropna()

    return pd.Series(dtype=float)


# =========================================================================
# Exposure & Market Presence Primitives (Shared)
# =========================================================================


@njit(cache=True)
def _exposure_kernel(sizes):
    """Accumulates size changes and returns the maximum peak reached."""
    current = 0.0
    peak = 0.0
    for i in range(len(sizes)):
        current += sizes[i]
        # Precision correction
        if abs(current) < 1e-9:
            current = 0.0
        if current > peak:
            peak = current
    return peak


@njit(cache=True)
def _time_weighted_kernel(times, sizes):
    """Calculates time-weighted average of a step-function (area under curve / duration)."""
    if len(times) < 2:
        return 0.0
    
    total_area = 0.0
    current_size = 0.0
    
    for i in range(len(times) - 1):
        current_size += sizes[i]
        # Precision correction
        if abs(current_size) < 1e-9:
            current_size = 0.0
            
        duration = times[i+1] - times[i]
        if duration > 0:
            total_area += current_size * duration
            
    total_duration = times[-1] - times[0]
    if total_duration <= 0:
        return 0.0
        
    return total_area / total_duration


@njit(cache=True)
def _exposure_curve_kernel(times, sizes):
    """Generates the step-function values for a given series of events."""
    n = len(times)
    curve = np.zeros(n, dtype=np.float64)
    current = 0.0
    for i in range(n):
        current += sizes[i]
        if abs(current) < 1e-9:
            current = 0.0
        curve[i] = current
    return curve


def max_gross_size_held(
    trades: pd.DataFrame, 
    end_time: Optional[pd.Timestamp] = None
) -> float:
    """Maximum absolute total size held across all positions (Gross Exposure)."""
    if trades.empty: return 0.0
    
    # Identify size column
    size_col = None
    for col in ["size", "quantity", "volume"]:
        if col in trades.columns:
            size_col = col
            break
            
    if not size_col: return 0.0

    # For gross exposure, use absolute size
    open_times = trades["open_time"].values
    close_times = trades["close_time"].fillna(end_time if end_time else trades["open_time"].max()).values
    sizes = trades[size_col].abs().values
    
    event_times = np.concatenate([open_times, close_times])
    event_sizes = np.concatenate([sizes, -sizes])
    
    # Secondary sort by sizes descending to handle simultaneous open/close events correctly
    idx = np.lexsort((-event_sizes, event_times))
    sorted_sizes = event_sizes[idx]
    
    return float(_exposure_kernel(sorted_sizes))


@njit(cache=True)
def _merge_intervals_kernel(starts, ends):
    n = len(starts)
    if n == 0:
        return np.empty((0, 2), dtype=starts.dtype)
    
    # Pre-allocate worst case
    merged = np.empty((n, 2), dtype=starts.dtype)
    m_ptr = 0
    
    curr_start = starts[0]
    curr_end = ends[0]
    
    for i in range(1, n):
        if starts[i] <= curr_end:
            if ends[i] > curr_end:
                curr_end = ends[i]
        else:
            merged[m_ptr, 0] = curr_start
            merged[m_ptr, 1] = curr_end
            m_ptr += 1
            curr_start = starts[i]
            curr_end = ends[i]
            
    merged[m_ptr, 0] = curr_start
    merged[m_ptr, 1] = curr_end
    m_ptr += 1
    
    return merged[:m_ptr]


def _merge_intervals(
    trades: pd.DataFrame,
    end_time: Optional[pd.Timestamp] = None,
) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    """Merge overlapping trade intervals."""
    if trades.empty or "open_time" not in trades.columns or "close_time" not in trades.columns:
        return []

    data = trades.copy()
    fallback = end_time if end_time is not None else data["open_time"].max()
    data["close_time"] = data["close_time"].fillna(fallback)

    data = data.dropna(subset=["open_time", "close_time"])
    if data.empty: return []

    starts_dt = _to_datetime_series(data["open_time"])
    ends_dt = _to_datetime_series(data["close_time"])

    valid = ends_dt >= starts_dt
    starts_dt = starts_dt[valid]
    ends_dt = ends_dt[valid]

    if starts_dt.empty: return []

    idx = np.argsort(starts_dt.values)
    starts = starts_dt.values[idx].astype("datetime64[ns]").view("int64")
    ends = ends_dt.values[idx].astype("datetime64[ns]").view("int64")

    merged_raw = _merge_intervals_kernel(starts, ends)

    return [
        (pd.Timestamp(merged_raw[i, 0]), pd.Timestamp(merged_raw[i, 1]))
        for i in range(len(merged_raw))
    ]


def time_in_market_duration(
    trades: pd.DataFrame,
    end_time: Optional[pd.Timestamp] = None
) -> pd.Timedelta:
    """Calculate total duration where at least one position was open."""
    merged_intervals = _merge_intervals(trades, end_time)
    total_duration = pd.Timedelta(0)
    for start, end in merged_intervals:
        total_duration += end - start
    return total_duration


def percent_time_in_market(
    trades: pd.DataFrame,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> float:
    """Calculate percent of the trading period spent in the market (0-100)."""
    if len(trades) == 0:
        return 0.0

    t_start = start_time if start_time else trades["open_time"].min()
    t_end = end_time if end_time else (trades["close_time"].max() if "close_time" in trades.columns else trades["open_time"].max())

    if pd.isna(t_start) or pd.isna(t_end) or t_end <= t_start:
        return 0.0

    total_period = t_end - t_start
    market_time = time_in_market_duration(trades, end_time)
    ratio = market_time.total_seconds() / total_period.total_seconds()
    return float(min(1.0, ratio) * 100.0)
