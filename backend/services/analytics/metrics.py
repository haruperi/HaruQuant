"""
Trade-based statistics & system-quality metrics.

Focus: trades, sequences, expectancy, system edge

This module provides a comprehensive suite of analytical functions for trading strategy performance evaluation.
It includes trade counts, P&L statistics, R-multiple analytics, sequence quality, time-based metrics, 
and system-level metrics like SQN and Kelly Criterion.

Summary of Methods:
------------------
Utility & Kernel Helpers:
    - win_rate_fraction: Win rate on a 0-1 scale.
    - avg_win_loss: Mean winning and losing outcomes.
    - consecutive_wins_losses: Max consecutive wins and losses (wrapper for kernel).
    - median_mae_mfe: Median MAE and MFE from R-space.
    - t_statistic: T-statistic for mean outcome.

Core Trade Counts & Costs:
    - open_position_pnl: Profit/loss for currently open positions.
    - total_trades: Total number of trades.
    - winning_trades / losing_trades / breakeven_trades: Count trades by outcome.
    - long_trades / short_trades: Count trades by direction.
    - count_open_trades: Number of trades still open.
    - slippage_paid / commission_paid / swap_paid: Total costs paid.
    - max_size_held: Maximum contracts/units held at any one time.

Trade P&L Statistics:
    - win_rate / loss_rate: Percentage of winning/losing trades.
    - avg_win / avg_loss: Average P&L of winning/losing trades.
    - largest_win / largest_loss: Max/min P&L values.
    - median_win / median_loss: Median P&L of winning/losing trades.

R-Multiple Analytics:
    - avg_r_multiple / median_r_multiple: Statistics for R-multiples.
    - r_multiple_distribution: Detailed distribution (mean, std, quartiles).
    - r_expectancy: Expected value per trade in R-terms.
    - max_r_multiple / min_r_multiple: Extreme R-multiple values.

Trade Sequence Quality:
    - max_consecutive_wins / max_consecutive_losses: Longest streaks.
    - avg_consecutive_wins / avg_consecutive_losses: Average streak lengths.
    - win_loss_streaks: Lists of all streak lengths.

Time-in-Trade:
    - avg_time_in_trade / median_time_in_trade: Statistics for trade duration.
    - max_time_in_trade / min_time_in_trade: Extreme trade durations.

System Quality Metrics:
    - sqn: System Quality Number (Van Tharp).
    - kelly_criterion: Optimal fraction of capital to risk.
    - compute_trade_metrics: High-level dictionary of trade-based analytics.
    - compute_equity_metrics: High-level dictionary of equity-based analytics (Sharpe, etc.).

Advanced Performance & Information:
    - trade_efficiency: Realized R captured relative to available MFE/MAE.
    - expectancy_variance: Measure of expectancy stability.
    - trade_outcome_entropy: Shannon entropy of trade outcomes (predictability).

Time-Based Period Metrics:
    - trading_period_duration: Total duration of the test period.
    - time_in_market_duration: Total duration with at least one open position.
    - percent_time_in_market: Percentage of time spent in the market.
    - longest_flat_period_duration: Maximum time between trades.

Equity Curve Metrics:
    - max_runup: Maximum peak-to-valley gain.
    - max_runup_date: Timestamp of the peak of max run-up.
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import drawdowns, ratios


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


def _to_1d_float_array(values) -> np.ndarray:
    """Normalize 1D numeric inputs to a float NumPy array."""
    if isinstance(values, pd.Series):
        array = values.astype(float).to_numpy()
    else:
        array = np.asarray(values, dtype=float)

    if array.ndim == 0:
        array = array.reshape(1)

    return array[~np.isnan(array)]


def win_rate_fraction(values) -> float:
    """Calculate win rate on a 0-1 scale from 1D numeric input."""
    normalized = _to_1d_float_array(values)
    if len(normalized) == 0:
        return float("nan")
    return float(np.mean(normalized > 0))


def avg_win_loss(values) -> tuple[float, float]:
    """Calculate mean winning and losing outcomes from 1D numeric input."""
    normalized = _to_1d_float_array(values)
    wins = normalized[normalized > 0]
    losses = normalized[normalized < 0]
    avg_win = float(np.mean(wins)) if len(wins) else float("nan")
    avg_loss = float(np.mean(losses)) if len(losses) else float("nan")
    return avg_win, avg_loss


@njit(cache=True)
def _consecutive_wins_losses_kernel(wins_bool_arr):
    max_wins = 0
    max_losses = 0
    current_wins = 0
    current_losses = 0
    for is_win in wins_bool_arr:
        if is_win:
            current_wins += 1
            if current_wins > max_wins:
                max_wins = current_wins
            current_losses = 0
        else:
            current_losses += 1
            if current_losses > max_losses:
                max_losses = current_losses
            current_wins = 0
    return max_wins, max_losses


def consecutive_wins_losses(values) -> tuple[int, int]:
    """Calculate max consecutive wins and losses from 1D numeric input."""
    normalized = _to_1d_float_array(values)
    if len(normalized) == 0:
        return 0, 0

    wins = normalized > 0
    return _consecutive_wins_losses_kernel(wins)


def median_mae_mfe(mae: np.ndarray, mfe: np.ndarray) -> tuple[float, float]:
    """Calculate median MAE and MFE from R-space arrays."""
    mae = np.asarray(mae, dtype=float)
    mfe = np.asarray(mfe, dtype=float)
    return (
        float(np.median(mae)) if len(mae) else float("nan"),
        float(np.median(mfe)) if len(mfe) else float("nan"),
    )


@njit(cache=True)
def _max_size_held_kernel(times, sizes):
    # events are (time, size_change)
    current_held = 0.0
    max_held = 0.0
    for i in range(len(sizes)):
        current_held += sizes[i]
        if abs(current_held) < 1e-9:
            current_held = 0.0
        if current_held > max_held:
            max_held = current_held
    return max_held


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


def t_statistic(values) -> float:
    """Calculate t-statistic for mean outcome."""
    normalized = _to_1d_float_array(values)
    n = len(normalized)
    if n < 2:
        return float("nan")

    mean = np.mean(normalized)
    std = np.std(normalized, ddof=1)
    if std == 0:
        return float("inf") if mean > 0 else float("-inf") if mean < 0 else float("nan")

    return float(mean / (std / np.sqrt(n)))


# =========================================================================
# Core Trade Counts & Costs
# =========================================================================


def open_position_pnl(open_trades: pd.DataFrame) -> Optional[float]:
    """
    Calculate Open Position P/L.

    The profit/loss for the position currently open.
    Returns None if no positions are open, to signify 'N/A'.
    """
    if len(open_trades) == 0:
        return None

    return float(open_trades["profit_loss"].sum())


def total_trades(trades: pd.DataFrame) -> int:
    """
    Calculate the total number of trades generated by a strategy.

    The total number of trades (both winning and losing) generated by a strategy. The total
    number of trades is important for a number of reasons. For example, no matter how large
    is the strategies Total Net Profit, one must be sure the value is staistically valid,
    i.e. the number of trades is large enough. Also important is the relation between the
    number of trades and time; even good, profitable trades may be taking place too rarely
    or too frequently for your needs.
    """
    return len(trades)


def winning_trades(trades: pd.DataFrame) -> int:
    """Calculate number of winning trades."""
    return int((trades["profit_loss"] > 1).sum())


def losing_trades(trades: pd.DataFrame) -> int:
    """Calculate number of losing trades."""
    return int((trades["profit_loss"] < -1).sum())


def breakeven_trades(trades: pd.DataFrame) -> int:
    """Calculate number of breakeven trades."""
    return int(((trades["profit_loss"] >= -1) & (trades["profit_loss"] <= 1)).sum())


def long_trades(trades: pd.DataFrame) -> int:
    """Calculate number of long trades."""
    return int((trades["type"] == "buy").sum())


def short_trades(trades: pd.DataFrame) -> int:
    """Calculate number of short trades."""
    return int((trades["type"] == "sell").sum())


def count_open_trades(trades: pd.DataFrame) -> int:
    """Calculate number of open trades (exit_reason="END_OF_DATA")."""
    if len(trades) == 0 or "exit_reason" not in trades.columns:
        return 0
    return int((trades["exit_reason"] == "END_OF_DATA").sum())


def slippage_paid(trades: pd.DataFrame) -> float:
    """Calculate total slippage paid."""
    if len(trades) == 0 or "slippage" not in trades.columns:
        return 0.0
    return float(trades["slippage"].sum())


def commission_paid(trades: pd.DataFrame) -> float:
    """Calculate total commission paid."""
    if len(trades) == 0 or "commission" not in trades.columns:
        return 0.0
    return float(trades["commission"].sum())


def swap_paid(trades: pd.DataFrame) -> float:
    """Calculate total swap paid."""
    if len(trades) == 0 or "swap" not in trades.columns:
        return 0.0
    return float(trades["swap"].sum())


def max_size_held(trades: pd.DataFrame) -> float:
    """
    Maximum number of contracts held at any one time.
    """
    if len(trades) == 0:
        return 0.0

    has_time = "open_time" in trades.columns and "close_time" in trades.columns
    has_size = "size" in trades.columns or "quantity" in trades.columns or "volume" in trades.columns

    if not has_size:
        return 0.0
    
    size_col = "size" if "size" in trades.columns else ("quantity" if "quantity" in trades.columns else "volume")

    if not has_time:
        return float(trades[size_col].max())

    # Create events: (timestamp, size_change)
    open_times = trades["open_time"].values
    close_times = trades["close_time"].values
    sizes = trades[size_col].values
    
    # Combine into a flat array of events for sorting
    event_times = np.concatenate([open_times, close_times])
    # Open adds size, Close removes size
    event_sizes = np.concatenate([sizes, -sizes])
    
    # Sort events by time, then size (exits before entries if times equal)
    idx = np.lexsort((event_sizes, event_times))
    
    sorted_sizes = event_sizes[idx]
    
    return float(_max_size_held_kernel(None, sorted_sizes))


# =========================================================================
# Trade P&L Statistics
# =========================================================================


def win_rate(trades: pd.DataFrame) -> float:
    """Calculate win rate as percentage (0-100)."""
    if len(trades) == 0:
        return 0.0
    return (winning_trades(trades) / len(trades)) * 100


def loss_rate(trades: pd.DataFrame) -> float:
    """Calculate loss rate as percentage (0-100)."""
    if len(trades) == 0:
        return 0.0
    return (losing_trades(trades) / len(trades)) * 100


def avg_win(trades: pd.DataFrame) -> float:
    """Calculate average winning trade P&L."""
    winners = trades[trades["profit_loss"] > 1]["profit_loss"]
    return float(winners.mean()) if len(winners) > 0 else 0.0


def avg_loss(trades: pd.DataFrame) -> float:
    """Calculate average losing trade P&L (negative value)."""
    losers = trades[trades["profit_loss"] < -1]["profit_loss"]
    return float(losers.mean()) if len(losers) > 0 else 0.0


def largest_win(trades: pd.DataFrame) -> float:
    """Calculate largest winning trade."""
    return float(trades["profit_loss"].max()) if len(trades) > 0 else 0.0


def largest_loss(trades: pd.DataFrame) -> float:
    """Calculate largest losing trade (negative value)."""
    return float(trades["profit_loss"].min()) if len(trades) > 0 else 0.0


def median_win(trades: pd.DataFrame) -> float:
    """Calculate median winning trade P&L."""
    winners = trades[trades["profit_loss"] > 1]["profit_loss"]
    return float(winners.median()) if len(winners) > 0 else 0.0


def median_loss(trades: pd.DataFrame) -> float:
    """Calculate median losing trade P&L (negative value)."""
    losers = trades[trades["profit_loss"] < -1]["profit_loss"]
    return float(losers.median()) if len(losers) > 0 else 0.0


# =========================================================================
# R-Multiple Analytics
# =========================================================================


def avg_r_multiple(trades: pd.DataFrame) -> float:
    """Calculate average R-multiple across all trades."""
    if len(trades) == 0 or "r_multiple" not in trades.columns:
        return 0.0
    return float(trades["r_multiple"].mean())


def median_r_multiple(trades: pd.DataFrame) -> float:
    """Calculate median R-multiple."""
    if len(trades) == 0 or "r_multiple" not in trades.columns:
        return 0.0
    return float(trades["r_multiple"].median())


def r_multiple_distribution(trades: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate R-multiple distribution statistics.

    Returns:
        Dict with mean, median, std, min, max, 25th, 75th percentiles
    """
    if len(trades) == 0 or "r_multiple" not in trades.columns:
        return {
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "q25": 0.0,
            "q75": 0.0,
        }

    r_values = trades["r_multiple"]

    return {
        "mean": float(r_values.mean()),
        "median": float(r_values.median()),
        "std": float(r_values.std()),
        "min": float(r_values.min()),
        "max": float(r_values.max()),
        "q25": float(r_values.quantile(0.25)),
        "q75": float(r_values.quantile(0.75)),
    }


def r_expectancy(trades: pd.DataFrame) -> float:
    """Calculate R-expectancy (same as avg_r_multiple, but explicit name)."""
    return avg_r_multiple(trades)


def max_r_multiple(trades: pd.DataFrame) -> float:
    """Calculate maximum R-multiple achieved."""
    if len(trades) == 0 or "r_multiple" not in trades.columns:
        return 0.0
    return float(trades["r_multiple"].max())


def min_r_multiple(trades: pd.DataFrame) -> float:
    """Calculate minimum R-multiple achieved."""
    if len(trades) == 0 or "r_multiple" not in trades.columns:
        return 0.0
    return float(trades["r_multiple"].min())


# =========================================================================
# Trade Sequence Quality
# =========================================================================


def max_consecutive_wins(trades: pd.DataFrame) -> int:
    """Calculate maximum consecutive winning trades."""
    if len(trades) == 0:
        return 0

    is_win = (trades["profit_loss"] > 1).astype(int)
    max_streak = 0
    current_streak = 0

    for win in is_win:
        if win:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    return max_streak


def max_consecutive_losses(trades: pd.DataFrame) -> int:
    """Calculate maximum consecutive losing trades."""
    if len(trades) == 0:
        return 0

    is_loss = (trades["profit_loss"] < -1).astype(int)
    max_streak = 0
    current_streak = 0

    for loss in is_loss:
        if loss:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    return max_streak


def avg_consecutive_wins(trades: pd.DataFrame) -> float:
    """Calculate average length of winning streaks."""
    if len(trades) == 0:
        return 0.0

    is_win = (trades["profit_loss"] > 1).astype(int)
    streaks = []
    current_streak = 0

    for win in is_win:
        if win:
            current_streak += 1
        else:
            if current_streak > 0:
                streaks.append(current_streak)
            current_streak = 0

    if current_streak > 0:
        streaks.append(current_streak)

    return float(np.mean(streaks)) if streaks else 0.0


def avg_consecutive_losses(trades: pd.DataFrame) -> float:
    """Calculate average length of losing streaks."""
    if len(trades) == 0:
        return 0.0

    is_loss = (trades["profit_loss"] < -1).astype(int)
    streaks = []
    current_streak = 0

    for loss in is_loss:
        if loss:
            current_streak += 1
        else:
            if current_streak > 0:
                streaks.append(current_streak)
            current_streak = 0

    if current_streak > 0:
        streaks.append(current_streak)

    return float(np.mean(streaks)) if streaks else 0.0


def win_loss_streaks(trades: pd.DataFrame) -> Dict[str, List[int]]:
    """
    Get all winning and losing streaks.

    Returns:
        Dict with 'win_streaks' and 'loss_streaks' lists
    """
    if len(trades) == 0:
        return {"win_streaks": [], "loss_streaks": []}

    is_win = (trades["profit_loss"] > 1).astype(int)

    win_streaks = []
    loss_streaks = []
    current_win_streak = 0
    current_loss_streak = 0

    for win in is_win:
        if win:
            if current_loss_streak > 0:
                loss_streaks.append(current_loss_streak)
                current_loss_streak = 0
            current_win_streak += 1
        else:
            if current_win_streak > 0:
                win_streaks.append(current_win_streak)
                current_win_streak = 0
            current_loss_streak += 1

    # Add final streak
    if current_win_streak > 0:
        win_streaks.append(current_win_streak)
    if current_loss_streak > 0:
        loss_streaks.append(current_loss_streak)

    return {"win_streaks": win_streaks, "loss_streaks": loss_streaks}


# =========================================================================
# Time-in-Trade
# =========================================================================


def avg_time_in_trade(trades: pd.DataFrame) -> float:
    """Calculate average time in trade (hours)."""
    if len(trades) == 0 or "time_in_trade" not in trades.columns:
        return 0.0
    return float(trades["time_in_trade"].mean())


def median_time_in_trade(trades: pd.DataFrame) -> float:
    """Calculate median time in trade (hours)."""
    if len(trades) == 0 or "time_in_trade" not in trades.columns:
        return 0.0
    return float(trades["time_in_trade"].median())


def max_time_in_trade(trades: pd.DataFrame) -> float:
    """Calculate maximum time in trade (hours)."""
    if len(trades) == 0 or "time_in_trade" not in trades.columns:
        return 0.0
    return float(trades["time_in_trade"].max())


def min_time_in_trade(trades: pd.DataFrame) -> float:
    """Calculate minimum time in trade (hours)."""
    if len(trades) == 0 or "time_in_trade" not in trades.columns:
        return 0.0
    return float(trades["time_in_trade"].min())


# =========================================================================
# System Quality Metrics
# =========================================================================


def sqn(trades: pd.DataFrame | pd.Series | np.ndarray) -> float:
    """
    Calculate System Quality Number (Van Tharp).

    SQN = sqrt(N) × (Avg R / Std R)
    """
    if isinstance(trades, pd.DataFrame):
        if len(trades) == 0 or "r_multiple" not in trades.columns:
            return 0.0
        r_values = trades["r_multiple"].astype(float).to_numpy()
    else:
        r_values = _to_1d_float_array(trades)

    n = len(r_values)
    if n < 2:
        return 0.0

    avg_r = r_values.mean()
    std_r = np.std(r_values, ddof=1)

    if std_r == 0:
        return 0.0

    return float(np.sqrt(n) * (avg_r / std_r))


def kelly_criterion(trades: pd.DataFrame | pd.Series | np.ndarray) -> float:
    """
    Calculate Kelly Criterion fraction.

    Returns:
        Fraction of capital to risk, clipped at 0 on the lower bound.
    """
    if isinstance(trades, pd.DataFrame):
        if len(trades) == 0 or "profit_loss" not in trades.columns:
            return 0.0
        values = trades["profit_loss"].astype(float).to_numpy()
    else:
        values = _to_1d_float_array(trades)

    if len(values) == 0:
        return 0.0

    win_prob = win_rate_fraction(values)
    avg_win_val, avg_loss_val = avg_win_loss(values)
    avg_loss_abs = abs(float(avg_loss_val)) if not np.isnan(avg_loss_val) else 0.0

    if np.isnan(win_prob) or avg_loss_abs <= 0.0 or np.isnan(avg_win_val) or avg_win_val <= 0.0:
        return 0.0

    payoff_ratio = float(avg_win_val / avg_loss_abs)
    if payoff_ratio <= 0.0:
        return 0.0

    lose_prob = 1.0 - float(win_prob)
    return float(max(0.0, float(win_prob) - (lose_prob / payoff_ratio)))


def compute_trade_metrics(
    values,
    mae: Optional[np.ndarray] = None,
    mfe: Optional[np.ndarray] = None,
) -> dict:
    """Compute Edge-style trade metrics from 1D R-space inputs."""
    normalized = _to_1d_float_array(values)

    summary = {
        "n_trades": len(normalized),
        "expectancy": ratios.expectancy(normalized),
        "win_rate": win_rate_fraction(normalized),
        "profit_factor": ratios.profit_factor(normalized),
        "sqn": sqn(normalized),
        "kelly_criterion": kelly_criterion(normalized),
        "t_stat": t_statistic(normalized),
    }

    avg_win_val, avg_loss_val = avg_win_loss(normalized)
    summary["avg_win"] = avg_win_val
    summary["avg_loss"] = avg_loss_val
    summary["payoff_ratio"] = ratios.payoff_ratio(normalized)

    max_cons_wins, max_cons_losses = consecutive_wins_losses(normalized)
    summary["max_consecutive_wins"] = max_cons_wins
    summary["max_consecutive_losses"] = max_cons_losses

    if mae is not None:
        mae = np.asarray(mae, dtype=float)
        summary["median_mae"] = float(np.median(mae)) if len(mae) else float("nan")

    if mfe is not None:
        mfe = np.asarray(mfe, dtype=float)
        summary["median_mfe"] = float(np.median(mfe)) if len(mfe) else float("nan")
        if mae is not None:
            summary["edge_ratio"] = _r_edge_ratio(mfe, mae)
            summary["trade_efficiency"] = _r_trade_efficiency(normalized, mfe)

    return summary


def compute_equity_metrics(returns_input, periods_per_year: int = 252) -> dict:
    """Compute Edge-style equity metrics from returns inputs."""
    normalized = _to_1d_float_array(returns_input)
    total_return = float(np.prod(1 + normalized) - 1) if len(normalized) else float("nan")
    annual_return = (
        float(np.mean(normalized) * periods_per_year) if len(normalized) else float("nan")
    )

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "sharpe_ratio": ratios.sharpe_ratio(normalized, annualize=True),
        "sortino_ratio": ratios.sortino_ratio(normalized, annualize=True),
        "calmar_ratio": ratios.calmar_ratio(normalized, periods_per_year=periods_per_year),
        "max_drawdown": drawdowns.max_drawdown(normalized),
        "max_dd_duration": drawdowns.max_drawdown_duration(normalized),
        "recovery_factor": drawdowns.recovery_factor(normalized),
    }


# =========================================================================
# Advanced Performance & Information (Efficiency & Entropy)
# =========================================================================


def _r_trade_efficiency(r: np.ndarray, mfe: np.ndarray) -> float:
    """Calculate realized R captured relative to available MFE."""
    r = np.asarray(r, dtype=float)
    mfe = np.asarray(mfe, dtype=float)
    if len(r) != len(mfe) or len(r) == 0:
        return float("nan")

    mask = mfe > 0
    if not np.any(mask):
        return float("nan")

    return float(np.mean(r[mask] / mfe[mask]))


def _r_edge_ratio(mfe: np.ndarray, mae: np.ndarray) -> float:
    """Calculate excursion edge ratio as MFE divided by MAE magnitude."""
    mfe = np.asarray(mfe, dtype=float)
    mae = np.asarray(mae, dtype=float)
    if len(mfe) != len(mae) or len(mfe) == 0:
        return float("nan")

    mae_abs = np.abs(mae)
    mask = mae_abs > 0
    if not np.any(mask):
        return float("inf") if np.mean(mfe) > 0 else float("nan")

    return float(np.mean(mfe[mask] / mae_abs[mask]))


def trade_efficiency(trades: pd.DataFrame) -> float:
    """
    Calculate trade efficiency based on MFE/MAE ratio.
    """
    if len(trades) == 0:
        return 0.0

    if "mfe_pips" not in trades.columns or "mae_pips" not in trades.columns:
        return 0.0

    valid_trades = trades[trades["mae_pips"] > 0]
    if len(valid_trades) == 0:
        return 0.0

    efficiency_ratios = valid_trades["mfe_pips"] / valid_trades["mae_pips"]
    return float(efficiency_ratios.mean())


def expectancy_variance(trades: pd.DataFrame) -> float:
    """Calculate variance of trade P&L (measure of expectancy stability)."""
    if len(trades) == 0:
        return 0.0
    return float(trades["profit_loss"].var())


def trade_outcome_entropy(trades: pd.DataFrame) -> float:
    """
    Calculate Shannon entropy of trade outcomes.
    """
    if len(trades) == 0:
        return 0.0

    wins = winning_trades(trades)
    losses = losing_trades(trades)
    be = breakeven_trades(trades)
    total = len(trades)

    probs = []
    if wins > 0:
        probs.append(wins / total)
    if losses > 0:
        probs.append(losses / total)
    if be > 0:
        probs.append(be / total)

    if not probs:
        return 0.0

    entropy = -sum(p * np.log2(p) for p in probs if p > 0)
    return float(entropy)


# =========================================================================
# Time-Based Period Metrics
# =========================================================================


def _merge_intervals(trades: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """
    Merge overlapping time intervals from trades using optimized Numba kernel.
    """
    if len(trades) == 0:
        return []

    if "open_time" not in trades.columns or "close_time" not in trades.columns:
        return []

    # Sort by open_time using NumPy
    sorted_df = trades.sort_values("open_time")
    starts = sorted_df["open_time"].values.view("int64")
    ends = sorted_df["close_time"].values.view("int64")
    
    merged_raw = _merge_intervals_kernel(starts, ends)
    
    return [
        (pd.Timestamp(merged_raw[i, 0]), pd.Timestamp(merged_raw[i, 1]))
        for i in range(len(merged_raw))
    ]


def trading_period_duration(
    trades: pd.DataFrame,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> pd.Timedelta:
    """
    Calculate total duration of the trading period (Test Period).
    """
    if len(trades) == 0:
        if start_time and end_time:
            return end_time - start_time
        return pd.Timedelta(0)

    t_start = start_time if start_time else trades["open_time"].min()
    t_end = end_time if end_time else trades["close_time"].max()

    if pd.isna(t_start) or pd.isna(t_end) or t_end < t_start:
        return pd.Timedelta(0)

    return t_end - t_start


def time_in_market_duration(trades: pd.DataFrame) -> pd.Timedelta:
    """
    Calculate total duration where at least one position was open.
    """
    merged_intervals = _merge_intervals(trades)
    total_duration = pd.Timedelta(0)
    for start, end in merged_intervals:
        total_duration += end - start
    return total_duration


def percent_time_in_market(
    trades: pd.DataFrame,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> float:
    """
    Calculate percent of the trading period spent in the market.
    """
    total_period = trading_period_duration(trades, start_time, end_time)
    if total_period.total_seconds() == 0:
        return 0.0

    market_time = time_in_market_duration(trades)
    ratio = market_time.total_seconds() / total_period.total_seconds()
    return float(ratio * 100.0)


def longest_flat_period_duration(
    trades: pd.DataFrame,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> pd.Timedelta:
    """
    Calculate longest period the strategy refrained from trading (flat).
    """
    t_start = start_time if start_time else (trades["open_time"].min() if len(trades) > 0 else None)
    t_end = end_time if end_time else (trades["close_time"].max() if len(trades) > 0 else None)

    if t_start is None or t_end is None or pd.isna(t_start) or pd.isna(t_end):
        return pd.Timedelta(0)

    if len(trades) == 0:
        return t_end - t_start

    merged_intervals = _merge_intervals(trades)
    max_flat = pd.Timedelta(0)

    if merged_intervals:
        # Start gap
        first_open = merged_intervals[0][0]
        if first_open > t_start:
            max_flat = max(max_flat, first_open - t_start)

        # Gaps between
        prev_close = merged_intervals[0][1]
        for i in range(1, len(merged_intervals)):
            curr_open = merged_intervals[i][0]
            gap = curr_open - prev_close
            if gap > pd.Timedelta(0):
                max_flat = max(max_flat, gap)
            prev_close = merged_intervals[i][1]

        # End gap
        last_close = merged_intervals[-1][1]
        if last_close < t_end:
            max_flat = max(max_flat, t_end - last_close)

    return max_flat


# =========================================================================
# Equity Curve Metrics
# =========================================================================


def max_runup(equity_curve: pd.Series) -> float:
    """
    Max Run-up: maximum gain from a valley to a peak.
    """
    if len(equity_curve) == 0:
        return 0.0
    running_min = equity_curve.expanding().min()
    runup_series = equity_curve - running_min
    return float(runup_series.max())


def max_runup_date(equity_curve: pd.Series) -> Optional[pd.Timestamp]:
    """
    Date of Max Run-up peak.
    """
    if len(equity_curve) == 0:
        return None
    running_min = equity_curve.expanding().min()
    runup_series = equity_curve - running_min
    try:
        return runup_series.idxmax()
    except (ValueError, TypeError):
        return None
