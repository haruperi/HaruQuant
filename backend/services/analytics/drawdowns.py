"""
Drawdown depth, duration, and recovery.

from backend.common.logger import logger
Focus: capital pain & recovery behavior
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


# =========================================================================
# Core Drawdowns
# =========================================================================


def drawdown_series(equity_curve: pd.Series) -> pd.Series:
    """
    Calculate drawdown series from equity curve.

    Args:
        equity_curve: Equity series

    Returns:
        Series of drawdown values (negative values)
    """
    if len(equity_curve) == 0:
        return pd.Series(dtype=float)

    # Calculate running maximum
    running_max = equity_curve.expanding().max()

    # Drawdown = current - running max
    drawdown = equity_curve - running_max

    return drawdown


def max_strategy_drawdown(equity_curve: pd.Series) -> float:
    """
    Max Strategy Drawdown (High-Low / Bar-to-Bar).

    Calculated from the detailed equity curve (e.g., daily/hourly bars).
    Measures the deepest peak-to-valley decline in the equity curve.

    Args:
        equity_curve: Equity series

    Returns:
        Maximum drawdown (positive value) in currency units
    """
    if len(equity_curve) == 0:
        return 0.0

    dd_series = drawdown_series(equity_curve)
    return float(abs(dd_series.min()))


def max_strategy_drawdown_percent(equity_curve: pd.Series) -> float:
    """
    Max Strategy Drawdown Percentage.

    Args:
        equity_curve: Equity series

    Returns:
        Maximum percentage drawdown (positive value)
    """
    if len(equity_curve) == 0:
        return 0.0

    running_max = equity_curve.expanding().max()
    # Avoid division by zero
    running_max[running_max == 0] = 1e-9

    pct_drawdown = ((equity_curve - running_max) / running_max) * 100
    return float(abs(pct_drawdown.min()))


def avg_drawdown(equity_curve: pd.Series) -> float:
    """
    Average drawdown.

    Args:
        equity_curve: Equity series

    Returns:
        Average drawdown value
    """
    if len(equity_curve) == 0:
        return 0.0

    dd_series = drawdown_series(equity_curve)
    # Only consider periods with actual drawdown
    dd_values = dd_series[dd_series < 0]

    if len(dd_values) == 0:
        return 0.0

    return float(abs(dd_values.mean()))


def drawdown_distribution(equity_curve: pd.Series) -> Dict[str, float]:
    """
    Drawdown distribution statistics.

    Returns:
        Dict with max, avg, median, std, 95th percentile
    """
    if len(equity_curve) == 0:
        return {
            "max": 0.0,
            "avg": 0.0,
            "median": 0.0,
            "std": 0.0,
            "p95": 0.0,
        }

    dd_series = drawdown_series(equity_curve)
    dd_values = abs(dd_series[dd_series < 0])

    if len(dd_values) == 0:
        return {
            "max": 0.0,
            "avg": 0.0,
            "median": 0.0,
            "std": 0.0,
            "p95": 0.0,
        }

    return {
        "max": float(dd_values.max()),
        "avg": float(dd_values.mean()),
        "median": float(dd_values.median()),
        "std": float(dd_values.std()),
        "p95": float(dd_values.quantile(0.95)),
    }


# =========================================================================
# Drawdown Duration
# =========================================================================


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


def drawdown_duration_series(equity_curve: pd.Series) -> pd.Series:
    """
    Calculate drawdown duration series.

    Returns number of periods in drawdown at each point

    Args:
        equity_curve: Equity series

    Returns:
        Series of drawdown durations
    """
    if len(equity_curve) == 0:
        return pd.Series(dtype=int)

    equity_arr = equity_curve.astype(float).to_numpy()
    durations = _drawdown_duration_series_kernel(equity_arr)
    return pd.Series(durations, index=equity_curve.index)


def max_drawdown_duration(equity_curve: pd.Series | np.ndarray) -> int:
    """
    Maximum drawdown duration in periods.

    Args:
        equity_curve: Equity series

    Returns:
        Maximum number of periods in drawdown
    """
    if not isinstance(equity_curve, pd.Series):
        returns = _returns_array(equity_curve)
        if len(returns) == 0:
            return 0
        cumulative = np.cumprod(1 + returns)
        return _max_drawdown_duration_kernel(cumulative)

    if len(equity_curve) == 0:
        return 0

    equity_arr = equity_curve.astype(float).to_numpy()
    return _max_drawdown_duration_kernel(equity_arr)


def avg_drawdown_duration(equity_curve: pd.Series) -> float:
    """
    Average drawdown duration.

    Args:
        equity_curve: Equity series

    Returns:
        Average number of periods in drawdown
    """
    if len(equity_curve) == 0:
        return 0.0

    duration_series = drawdown_duration_series(equity_curve)
    # Only consider periods actually in drawdown
    dd_periods = duration_series[duration_series > 0]

    if len(dd_periods) == 0:
        return 0.0

    return float(dd_periods.mean())


def max_drawdown(returns: pd.Series | np.ndarray) -> float:
    """Calculate maximum drawdown from a returns series."""
    normalized = _returns_array(returns)
    if len(normalized) == 0:
        return float("nan")

    cumulative = np.cumprod(1 + normalized)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    return float(np.min(drawdowns))


def time_to_recovery(equity_curve: pd.Series) -> List[int]:
    """
    Time to recovery for each drawdown period.

    Returns list of recovery times (in periods) for each drawdown

    Args:
        equity_curve: Equity series

    Returns:
        List of recovery periods
    """
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


# =========================================================================
# Risk-of-Ruin Style Metrics
# =========================================================================


def ulcer_index(equity_curve: pd.Series) -> float:
    """
    Ulcer Index - measure of downside volatility.

    Square root of mean squared drawdown percentage

    Args:
        equity_curve: Equity series

    Returns:
        Ulcer Index value
    """
    if len(equity_curve) == 0:
        return 0.0

    # Calculate percentage drawdowns
    running_max = equity_curve.expanding().max()
    pct_drawdown = ((equity_curve - running_max) / running_max) * 100

    # Ulcer Index = sqrt(mean(drawdown^2))
    ulcer = np.sqrt((pct_drawdown**2).mean())

    return float(ulcer)


def pain_index(equity_curve: pd.Series) -> float:
    """
    Pain Index - average squared drawdown.

    Similar to Ulcer Index but without square root

    Args:
        equity_curve: Equity series

    Returns:
        Pain Index value
    """
    if len(equity_curve) == 0:
        return 0.0

    dd_series = drawdown_series(equity_curve)
    running_max = equity_curve.expanding().max()

    # Calculate percentage drawdowns
    pct_drawdown = (dd_series / running_max) * 100

    # Pain = mean(drawdown^2)
    pain = (pct_drawdown**2).mean()

    return float(abs(pain))


def pain_ratio(equity_curve: pd.Series, returns: pd.Series) -> float:
    """
    Pain Ratio - return divided by pain.

    Higher is better

    Args:
        equity_curve: Equity series
        returns: Returns series

    Returns:
        Pain ratio value
    """
    if len(equity_curve) == 0 or len(returns) == 0:
        return 0.0

    pain = pain_index(equity_curve)

    if pain == 0:
        return 0.0

    total_return = returns.sum()

    return float(total_return / pain)


def recovery_factor(equity_curve: pd.Series | np.ndarray) -> float:
    """
    Recovery Factor - net profit divided by maximum drawdown.

    Measures how many times the profit covers the worst loss.
    Higher values indicate better recovery from drawdowns.

    Args:
        equity_curve: Equity series

    Returns:
        Recovery factor value (net profit / max drawdown)
    """
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

    # Calculate net profit
    net_profit = equity_curve.iloc[-1] - equity_curve.iloc[0]

    # Calculate max drawdown
    max_dd = max_strategy_drawdown(equity_curve)

    if max_dd == 0:
        return 0.0 if net_profit == 0 else float("inf")

    return float(net_profit / max_dd)


# =========================================================================
# Trade-Based Drawdowns
# =========================================================================


def trade_level_drawdowns(trades: pd.DataFrame) -> pd.Series:
    """
    Calculate drawdowns at trade level.

    Args:
        trades: Trades DataFrame

    Returns:
        Series of drawdown values per trade
    """
    if len(trades) == 0:
        return pd.Series(dtype=float)

    # Sort by close time
    sorted_trades = trades.sort_values("close_time")

    # Cumulative P&L
    cumulative_pnl = sorted_trades["profit_loss"].cumsum()

    # Running maximum
    running_max = cumulative_pnl.expanding().max()

    # Drawdown
    drawdown = cumulative_pnl - running_max

    return drawdown


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


def max_close_to_close_drawdown(trades: pd.DataFrame) -> float:
    """
    Max 'Close To Close' Drawdown (using User's Run-Up Definition).

    The user defines "Run-Up ($)" as the max unrealized profit (MFE).
    This logic calculates the drawdown from the highest equity peak (using MFE)
    to the lowest equity point (using MAE or Close).
    """
    if len(trades) == 0:
        return 0.0

    # Ensure we have the necessary columns, if not fall back to simple PL
    if "mfe_usd" not in trades.columns or "mae_usd" not in trades.columns:
        # Sort by close_time to be consistent
        sorted_trades = trades.sort_values("close_time")
        # For simple cumulative PnL, we can use vectorized numpy
        cumulative_pnl = sorted_trades["profit_loss"].cumsum().to_numpy()
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = running_max - cumulative_pnl
        return float(np.max(drawdown))

    # Sort trades to ensure correct equity sequence
    sorted_trades = trades.sort_values("close_time")

    mfe_arr = sorted_trades["mfe_usd"].astype(float).to_numpy()
    mae_arr = sorted_trades["mae_usd"].astype(float).to_numpy()
    pnl_arr = sorted_trades["profit_loss"].astype(float).to_numpy()

    return _max_close_to_close_drawdown_kernel(mfe_arr, mae_arr, pnl_arr, 0.0)


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


def max_close_to_close_drawdown_percent(
    trades: pd.DataFrame, initial_balance: float
) -> float:
    """
    Max 'Close To Close' Drawdown Percentage.

    Same logic as above but relative to the peak equity value.
    """
    if len(trades) == 0 or initial_balance <= 0:
        return 0.0

    if "mfe_usd" not in trades.columns or "mae_usd" not in trades.columns:
        # Fallback
        c_pnl = (
            trades.sort_values("close_time")["profit_loss"].cumsum() + initial_balance
        )
        return max_strategy_drawdown_percent(c_pnl)

    sorted_trades = trades.sort_values("close_time")

    mfe_arr = sorted_trades["mfe_usd"].astype(float).to_numpy()
    mae_arr = sorted_trades["mae_usd"].astype(float).to_numpy()
    pnl_arr = sorted_trades["profit_loss"].astype(float).to_numpy()

    return _max_close_to_close_drawdown_percent_kernel(
        mfe_arr, mae_arr, pnl_arr, float(initial_balance)
    )


def avg_trade_drawdown(trades: pd.DataFrame) -> float:
    """
    Average drawdown at trade level.

    Args:
        trades: Trades DataFrame

    Returns:
        Average trade-level drawdown
    """
    if len(trades) == 0:
        return 0.0

    dd_series = trade_level_drawdowns(trades)
    dd_values = dd_series[dd_series < 0]

    if len(dd_values) == 0:
        return 0.0

    return float(abs(dd_values.mean()))


def account_size_required(trades: pd.DataFrame) -> float:
    """
    Account Size Required.

    Based on Max Close To Close Drawdown. The amount of money required to trade the strategy
    to withstand the equity dips (at trade close granularity).

    Formula: AbsValue of Max Close To Close Drawdown.
    """
    return max_close_to_close_drawdown(trades)


def avg_yearly_max_drawdown(equity_curve: pd.Series) -> float:
    """
    Average Yearly Maximum Drawdown.

    Splits the equity curve by year and calculates the max drawdown for each year,
    then averages them. Drawdown is calculated as positive value (depth).

    Args:
        equity_curve: Equity series with DateTime index

    Returns:
        Average of annual max drawdowns (positive float).
    """
    if len(equity_curve) == 0:
        return 0.0

    # Ensure index is datetime
    if not isinstance(equity_curve.index, pd.DatetimeIndex):
        # Allow conversion if possible, else fail?
        # Assuming standard usage with DatetimeIndex
        return 0.0

    # Resample to yearly groups? Or groupby year?
    yearly_groups = equity_curve.groupby(pd.Grouper(freq="YE"))

    max_dds = []

    for _, yearly_equity in yearly_groups:
        if len(yearly_equity) > 0:
            # Re-calculate drawdown for this specific year's curve?
            # Or use the global drawdown series filtered by year?
            # "Average Yearly Maximum Drawdown" usually means:
            # For each year, what was the max drawdown *within that year*?
            # This implies running max resets at start of year, or carry over?
            # Standard interpretation is usually "Max Peak-to-Valley occuring within the year".
            # Which often implies resetting the high-water mark at Jan 1.
            # Let's assume reset High Water Mark for independent yearly stats.

            mdd = max_strategy_drawdown(yearly_equity)
            max_dds.append(mdd)

    if not max_dds:
        return 0.0

    return float(np.mean(max_dds))


# =========================================================================
# Date/Time Metrics
# =========================================================================


def max_strategy_drawdown_date(equity_curve: pd.Series) -> Optional[pd.Timestamp]:
    """
    Date of the Maximum Strategy Drawdown.

    Returns the timestamp where the equity curve reached the deepest valley
    (max drawdown).

    Args:
        equity_curve: Equity series with DatetimeIndex

    Returns:
        Timestamp of max drawdown or None
    """
    if len(equity_curve) == 0:
        return None

    dd_series = drawdown_series(equity_curve)

    # Find the index of the minimum value (deepest drawdown)
    # idxmin returns the index label.
    try:
        min_idx = dd_series.idxmin()
        return min_idx
    except (ValueError, TypeError):
        return None


def max_close_to_close_drawdown_date(trades: pd.DataFrame) -> Optional[pd.Timestamp]:
    """
    Date of the Maximum Close To Close Drawdown.

    Returns the close time of the trade that marked the bottom of the max drawdown.
    Uses the MFE/MAE-based 'Run-Up' logic if available, matching max_close_to_close_drawdown.

    Args:
        trades: Trades DataFrame

    Returns:
        Timestamp or None
    """
    if len(trades) == 0:
        return None

    if "close_time" not in trades.columns:
        return None

    # Check for MFE/MAE columns
    use_mfe = "mfe_usd" in trades.columns and "mae_usd" in trades.columns

    sorted_trades = trades.sort_values("close_time")

    if not use_mfe:
        # Fallback to simple cumulative P&L logic
        cumulative_pnl = sorted_trades["profit_loss"].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = cumulative_pnl - running_max
        try:
            min_idx = drawdown.idxmin()
            return sorted_trades.loc[min_idx, "close_time"]
        except (ValueError, TypeError, KeyError):
            return None

    # MFE Logic
    current_equity = 0.0
    running_max_equity = 0.0
    max_dd = 0.0
    max_dd_date = None

    # Initialize with first close time just in case, though 0 DD implies no date strictly
    # But usually we return the date where the peak-to-valley is largest.

    for _, trade in sorted_trades.iterrows():
        trade_peak = current_equity + trade["mfe_usd"]
        trade_valley = current_equity - trade["mae_usd"]
        trade_close = current_equity + trade["profit_loss"]

        running_max_equity = max(running_max_equity, trade_peak)

        # Drawdowns
        dd_valley = running_max_equity - trade_valley
        dd_close = running_max_equity - trade_close

        # Check if this trade sets a new Max DD
        if dd_valley > max_dd:
            max_dd = dd_valley
            max_dd_date = trade["close_time"]

        if dd_close > max_dd:
            max_dd = dd_close
            max_dd_date = trade["close_time"]

        current_equity = trade_close

    return max_dd_date
