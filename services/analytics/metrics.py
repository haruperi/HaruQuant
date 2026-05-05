"""
Summary:
-------
HaruQuant Trade Diagnostics Module.
Trade-based statistics, system-quality metrics, and temporal exposure analytics.
This module provides a production-grade suite of analytical functions for trading strategy 
performance evaluation, with a focus on normalized R-multiple stability, sequence quality, 
and market exposure.

Summary of Methods:
------------------
Utility & Kernel Helpers:
    - get_closed_trades: Filter for realized (non-open) trades.
    - get_ordered_closed_trades: Filter and sort trades by exit time.
    - classify_trades: Win/Loss/Breakeven categorization.
    - win_rate: Fraction of winning trades.
    - profit_factor: Total profit divided by total loss.
    - avg_win_loss: Mean winner vs mean loser.
    - expectancy: Expected profit per trade (notional or R).
    - sqn: System Quality Number - statistical expectancy.
    - exposure_metrics: Time in market and exposure time analysis.
    - winning_trades / losing_trades / breakeven_trades: Trade counts.
    - long_trades / short_trades: Counts by trade direction.
    - count_open_trades: Number of currently active positions.
    - slippage_paid / commission_paid / swap_paid: Total execution costs (absolute positive).
    - max_gross_size_held: Maximum total contracts held.
    - max_net_size_held: Maximum directional net exposure.

Trade P&L Statistics:
    - win_rate / loss_rate: Percentage of winning/losing trades.
    - avg_win / avg_loss: Average P&L of winning/losing trades.
    - largest_win / largest_loss: Extreme P&L outcomes.
    - median_win / median_loss: Median P&L outcomes.

R-Multiple Analytics:
    - get_r_multiples: Generate R-multiple series from risk-adjusted profit.
    - avg_r_multiple / median_r_multiple: Central tendencies in R-terms.
    - r_multiple_distribution: Detailed distribution (mean, std, quartiles).
    - r_expectancy: Expected value per trade in R-terms.

Trade Sequence & Stability:
    - runs_test_zscore: Wald-Wolfowitz Z-Score for sequence randomness.
    - win_after_win_probability: Probability of consecutive winning outcomes.
    - r_signal_to_noise: Mean R / Std R (unannualized Trade Sharpe).
    - rolling_expectancy_stability: Consistency of the edge over time.
    - max_consecutive_wins / max_consecutive_losses: Streak diagnostics.

System Quality Metrics:
    - sqn: System Quality Number (Van Tharp).
    - kelly_criterion: Optimal fraction of capital to risk.
    - trade_efficiency: Realized R captured relative to available MFE.
    - trade_outcome_entropy: Shannon entropy of outcomes (predictability).

Temporal exposure:
    - trading_period_duration: Total duration of the test.
    - time_in_market_duration: Total time with at least one active position.
    - percent_time_in_market: Percentage of test period spent in-market.
    - longest_flat_period_duration: Maximum duration between trade intervals.

Equity Curve Metrics:
    - max_runup: Maximum peak-to-valley gain.
    - max_runup_date: Timestamp of the peak of max run-up.
"""

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from . import common, ratios, drawdowns
from .common import (
    EPSILON, _has_col, get_closed_trades, classify_trades, 
    _to_1d_float_array, get_r_multiples, max_gross_size_held,
    percent_time_in_market, _merge_intervals, time_in_market_duration
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


def get_ordered_closed_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Filter for closed trades and sort them by time to ensure sequence-dependent metrics are correct.
    Priority: close_time, then open_time.
    """
    closed = get_closed_trades(trades).copy()
    if closed.empty:
        return closed
        
    if "close_time" in closed.columns:
        return closed.sort_values("close_time")
    if "open_time" in closed.columns:
        return closed.sort_values("open_time")
    return closed


def _to_datetime_series(series: pd.Series) -> pd.Series:
    """Convert a timestamp series safely, supporting datetime values and Unix seconds."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_datetime(series, unit="s")
    return pd.to_datetime(series)


def win_rate_fraction(values, epsilon: float = EPSILON) -> float:
    """Win rate on a 0-1 scale."""
    normalized = _to_1d_float_array(values)
    if len(normalized) == 0:
        return float("nan")
    return float(np.mean(normalized > epsilon))


def avg_win_loss(values, epsilon: float = EPSILON) -> tuple[float, float]:
    """Mean winning and losing outcomes."""
    normalized = _to_1d_float_array(values)
    wins = normalized[normalized > epsilon]
    losses = normalized[normalized < -epsilon]
    
    avg_win = float(np.mean(wins)) if len(wins) else float("nan")
    avg_loss = float(np.mean(losses)) if len(losses) else float("nan")
    return avg_win, avg_loss


def consecutive_wins_losses(values, epsilon: float = EPSILON) -> tuple[int, int]:
    """
    Max consecutive wins and losses from a 1D array.
    Breakeven trades (abs < epsilon) break both streaks.
    """
    normalized = _to_1d_float_array(values)
    
    max_wins = 0
    max_losses = 0
    curr_wins = 0
    curr_losses = 0
    
    for val in normalized:
        if val > epsilon:
            curr_wins += 1
            curr_losses = 0
        elif val < -epsilon:
            curr_losses += 1
            curr_wins = 0
        else:
            curr_wins = 0
            curr_losses = 0
            
        if curr_wins > max_wins: max_wins = curr_wins
        if curr_losses > max_losses: max_losses = curr_losses
        
    return max_wins, max_losses





# Helper kernels and functions moved or unified above.


def median_mae_mfe(mae: np.ndarray, mfe: np.ndarray) -> tuple[float, float]:
    """Calculate median MAE and MFE."""
    mae = np.asarray(mae, dtype=float)
    mfe = np.asarray(mfe, dtype=float)
    return (
        float(np.median(mae)) if len(mae) else 0.0,
        float(np.median(mfe)) if len(mfe) else 0.0,
    )


def get_mae_mfe_r(trades: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Get MAE and MFE normalized to R-space."""
    if trades.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
        
    # Prefer pre-calculated R-space columns
    if "mae_r" in trades.columns and "mfe_r" in trades.columns:
        return trades["mae_r"], trades["mfe_r"]
        
    # Fallback: calculate from USD and risk amount
    if "initial_risk_amount" in trades.columns:
        risk = trades["initial_risk_amount"].abs().replace(0, np.nan)
        mae_usd = trades["mae_usd"] if "mae_usd" in trades.columns else pd.Series(0.0, index=trades.index)
        mfe_usd = trades["mfe_usd"] if "mfe_usd" in trades.columns else pd.Series(0.0, index=trades.index)
        return mae_usd / risk, mfe_usd / risk
        
    return pd.Series(0.0, index=trades.index), pd.Series(0.0, index=trades.index)





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


def open_position_pnl(open_trades: pd.DataFrame) -> float:
    """Total unrealized P&L from open positions."""
    if open_trades.empty or not _has_col(open_trades, "profit_loss"):
        return 0.0
    return float(open_trades["profit_loss"].sum())


def total_trades(trades: pd.DataFrame) -> int:
    """Total number of closed trades."""
    return len(get_closed_trades(trades))


def winning_trades(trades: pd.DataFrame) -> int:
    """Count of closed winning trades (> EPSILON)."""
    wins, _, _ = classify_trades(get_closed_trades(trades))
    return len(wins)


def losing_trades(trades: pd.DataFrame) -> int:
    """Count of closed losing trades (< -EPSILON)."""
    _, losses, _ = classify_trades(get_closed_trades(trades))
    return len(losses)


def breakeven_trades(trades: pd.DataFrame) -> int:
    """Count of closed trades with |PnL| <= EPSILON."""
    _, _, be = classify_trades(get_closed_trades(trades))
    return len(be)


def long_trades(trades: pd.DataFrame) -> int:
    """Count of closed long trades."""
    closed = get_closed_trades(trades)
    if "type" not in closed.columns: return 0
    return len(closed[closed["type"] == "buy"])


def short_trades(trades: pd.DataFrame) -> int:
    """Count of closed short trades."""
    closed = get_closed_trades(trades)
    if "type" not in closed.columns: return 0
    return len(closed[closed["type"] == "sell"])


def count_open_trades(trades: pd.DataFrame) -> int:
    """Count of trades currently open."""
    closed = get_closed_trades(trades)
    return len(trades) - len(closed)


def slippage_paid(trades: pd.DataFrame, closed_only: bool = False) -> float:
    """Total absolute slippage costs paid (Option A: positive paid)."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "slippage_usd"):
        return 0.0
    return float(data["slippage_usd"].abs().sum())


def commission_paid(trades: pd.DataFrame, closed_only: bool = False) -> float:
    """Total absolute commission costs paid (Option A: positive paid)."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "commission"):
        return 0.0
    return float(data["commission"].abs().sum())


def swap_paid(trades: pd.DataFrame, closed_only: bool = False) -> float:
    """Total absolute swap costs paid (Option A: positive paid)."""
    data = get_closed_trades(trades) if closed_only else trades
    if data.empty or not _has_col(data, "swap"):
        return 0.0
    return float(data["swap"].abs().sum())


# =========================================================================
# Trade P&L Statistics
# =========================================================================


def win_rate(trades: pd.DataFrame) -> float:
    """Percentage of winning trades (0-100)."""
    closed = get_closed_trades(trades)
    if len(closed) == 0: return 0.0
    return (winning_trades(closed) / len(closed)) * 100.0


def loss_rate(trades: pd.DataFrame) -> float:
    """Percentage of losing trades (0-100)."""
    closed = get_closed_trades(trades)
    if len(closed) == 0: return 0.0
    return (losing_trades(closed) / len(closed)) * 100.0


def avg_win(trades: pd.DataFrame) -> float:
    """Mean profit of winning trades."""
    if trades.empty or not _has_col(trades, "profit_loss"): return 0.0
    wins, _, _ = classify_trades(get_closed_trades(trades))
    return float(wins["profit_loss"].mean()) if not wins.empty else 0.0


def avg_loss(trades: pd.DataFrame) -> float:
    """Mean loss of losing trades."""
    if trades.empty or not _has_col(trades, "profit_loss"): return 0.0
    _, losses, _ = classify_trades(get_closed_trades(trades))
    return float(losses["profit_loss"].mean()) if not losses.empty else 0.0


def largest_win(trades: pd.DataFrame) -> float:
    """Maximum profit from a single trade."""
    if trades.empty or not _has_col(trades, "profit_loss"): return 0.0
    closed = get_closed_trades(trades)
    return float(closed["profit_loss"].max()) if not closed.empty else 0.0


def largest_loss(trades: pd.DataFrame) -> float:
    """Maximum loss from a single trade."""
    if trades.empty or not _has_col(trades, "profit_loss"): return 0.0
    closed = get_closed_trades(trades)
    return float(closed["profit_loss"].min()) if not closed.empty else 0.0


def median_win(trades: pd.DataFrame) -> float:
    """Median P&L of winning trades."""
    wins, _, _ = classify_trades(get_closed_trades(trades))
    return float(wins["profit_loss"].median()) if not wins.empty else 0.0


def median_loss(trades: pd.DataFrame) -> float:
    """Median P&L of losing trades."""
    _, losses, _ = classify_trades(get_closed_trades(trades))
    return float(losses["profit_loss"].median()) if not losses.empty else 0.0


def expectancy(trades: pd.DataFrame) -> float:
    """Calculate expectancy using ratios module."""
    return ratios.expectancy(trades)


def expectancy_r(r_values: pd.Series | np.ndarray) -> float:
    """Calculate R-expectancy using ratios module."""
    return ratios.expectancy_r(r_values)


def max_size_held(trades: pd.DataFrame) -> float:
    """Maximum total contracts held (Gross). Wrapper for max_gross_size_held."""
    return max_gross_size_held(trades)


def max_net_size_held(
    trades: pd.DataFrame,
    end_time: Optional[pd.Timestamp] = None
) -> float:
    """Maximum net directional size held (Long - Short). Returns absolute peak."""
    if trades.empty: return 0.0
    
    size_col = _get_size_col(trades)
    if not size_col or "type" not in trades.columns: return 0.0

    is_buy = (trades["type"] == "buy").values
    raw_sizes = trades[size_col].abs().values # Standardize to positive size, then apply type
    
    open_sizes = np.where(is_buy, raw_sizes, -raw_sizes)
    close_sizes = -open_sizes
    
    o_times = trades["open_time"].values
    c_times = trades["close_time"].fillna(end_time if end_time else trades["open_time"].max()).values
    
    event_times = np.concatenate([o_times, c_times])
    event_sizes = np.concatenate([open_sizes, close_sizes])
    
    idx = np.lexsort((-event_sizes, event_times))
    sorted_sizes = event_sizes[idx]
    
    current = 0.0
    peak = 0.0
    for s in sorted_sizes:
        current += s
        if abs(current) > peak:
            peak = abs(current)
            
    return float(peak)


def max_long_size_held(trades: pd.DataFrame) -> float:
    """Maximum total long contracts held at any one time."""
    return max_gross_size_held(trades[trades["type"] == "buy"]) if "type" in trades.columns else 0.0


def max_short_size_held(trades: pd.DataFrame) -> float:
    """Maximum total short contracts held at any one time."""
    return max_gross_size_held(trades[trades["type"] == "sell"]) if "type" in trades.columns else 0.0


def _get_size_col(trades: pd.DataFrame) -> Optional[str]:
    for col in ["size", "quantity", "volume"]:
        if col in trades.columns: return col
    return None


# =========================================================================
# R-Multiple Analytics
# =========================================================================





def avg_r_multiple(trades: pd.DataFrame) -> float:
    """Calculate average R-multiple across all trades."""
    r_values = get_r_multiples(trades)
    if r_values.empty:
        return 0.0
    return float(r_values.mean())


def median_r_multiple(trades: pd.DataFrame) -> float:
    """Calculate median R-multiple."""
    r_values = get_r_multiples(trades)
    if r_values.empty:
        return 0.0
    return float(r_values.median())


def r_multiple_distribution(trades: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate R-multiple distribution statistics.

    Returns:
        Dict with mean, median, std, min, max, 25th, 75th percentiles
    """
    r_values = get_r_multiples(trades)
    if r_values.empty:
        return {
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "q25": 0.0,
            "q75": 0.0,
        }

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
    """Calculate R-expectancy using ratios module."""
    return ratios.expectancy_r(get_r_multiples(trades))


def max_r_multiple(trades: pd.DataFrame) -> float:
    """Calculate maximum R-multiple achieved."""
    r_values = get_r_multiples(trades)
    if r_values.empty:
        return 0.0
    return float(r_values.max())


def min_r_multiple(trades: pd.DataFrame) -> float:
    """Calculate minimum R-multiple achieved."""
    r_values = get_r_multiples(trades)
    if r_values.empty:
        return 0.0
    return float(r_values.min())


def median_mae_r(trades: pd.DataFrame) -> float:
    """Median Maximum Adverse Excursion in R-multiple terms."""
    if trades.empty or "mae_usd" not in trades.columns:
        return 0.0
    
    # Extract risk for normalization
    risk_cols = ["initial_risk_amount", "initial_risk"]
    risk = pd.Series(dtype=float)
    for col in risk_cols:
        if col in trades.columns:
            risk = trades[col].abs().replace(0, np.nan)
            break
            
    if risk.empty:
        # Fallback to avg loss as risk proxy if no explicit risk
        from .common import avg_loss
        risk_val = abs(avg_loss(trades))
        if risk_val < EPSILON: return 0.0
        mae_r = trades["mae_usd"].abs() / risk_val
    else:
        mae_r = trades["mae_usd"].abs() / risk
        
    return float(mae_r.dropna().median())


def median_mfe_r(trades: pd.DataFrame) -> float:
    """Median Maximum Favorable Excursion in R-multiple terms."""
    if trades.empty or "mfe_usd" not in trades.columns:
        return 0.0
        
    risk_cols = ["initial_risk_amount", "initial_risk"]
    risk = pd.Series(dtype=float)
    for col in risk_cols:
        if col in trades.columns:
            risk = trades[col].abs().replace(0, np.nan)
            break
            
    if risk.empty:
        from .common import avg_loss
        risk_val = abs(avg_loss(trades))
        if risk_val < EPSILON: return 0.0
        mfe_r = trades["mfe_usd"].abs() / risk_val
    else:
        mfe_r = trades["mfe_usd"].abs() / risk
        
    return float(mfe_r.dropna().median())


# =========================================================================
# Trade Sequence Quality
# =========================================================================


@njit(cache=True)
def _consecutive_kernel(is_win):
    """
    Calculates max consecutive wins or losses.
    NOTE: Input must be a boolean array where True is the event of interest (Win).
    Any non-win (Loss or Breakeven) breaks the streak.
    """
    max_streak = 0
    current_streak = 0
    for i in range(len(is_win)):
        if is_win[i]:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
        else:
            current_streak = 0
    return max_streak


def max_consecutive_wins(trades: pd.DataFrame) -> int:
    """Calculate maximum consecutive winning trades."""
    ordered = get_ordered_closed_trades(trades)
    if ordered.empty: return 0
    return int(_consecutive_kernel((ordered["profit_loss"] > EPSILON).values))


def max_consecutive_losses(trades: pd.DataFrame) -> int:
    """Calculate maximum consecutive losing trades."""
    ordered = get_ordered_closed_trades(trades)
    if ordered.empty: return 0
    return int(_consecutive_kernel((ordered["profit_loss"] < -EPSILON).values))

def avg_consecutive_wins(trades: pd.DataFrame) -> float:
    """Average length of winning streaks."""
    streaks = win_loss_streaks(trades)["win_streaks"]
    return float(np.mean(streaks)) if streaks else 0.0


def avg_consecutive_losses(trades: pd.DataFrame) -> float:
    """Average length of losing streaks."""
    streaks = win_loss_streaks(trades)["loss_streaks"]
    return float(np.mean(streaks)) if streaks else 0.0


def win_loss_streaks(trades: pd.DataFrame) -> Dict[str, List[int]]:
    """
    Get all winning and losing streaks.
    Breakeven trades break BOTH win and loss streaks.
    """
    ordered = get_ordered_closed_trades(trades)
    if ordered.empty: return {"win_streaks": [], "loss_streaks": []}
    
    pnl = ordered["profit_loss"].values
    
    win_streaks = []
    loss_streaks = []
    current_win = 0
    current_loss = 0

    for val in pnl:
        if val > EPSILON:
            # Win
            if current_loss > 0:
                loss_streaks.append(current_loss)
                current_loss = 0
            current_win += 1
        elif val < -EPSILON:
            # Loss
            if current_win > 0:
                win_streaks.append(current_win)
                current_win = 0
            current_loss += 1
        else:
            # Breakeven - breaks both
            if current_win > 0:
                win_streaks.append(current_win)
            if current_loss > 0:
                loss_streaks.append(current_loss)
            current_win = 0
            current_loss = 0

    if current_win > 0: win_streaks.append(current_win)
    if current_loss > 0: loss_streaks.append(current_loss)

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
        r_series = get_r_multiples(trades)
        if r_series.empty:
            return 0.0
        r_values = r_series.astype(float).to_numpy()
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
    Calculate Kelly Criterion percentage based on R-multiples (if available) or Returns.
    This provides a normalized edge estimate independent of raw dollar sizing.

    Returns:
        Fraction of capital to risk (0.0-1.0).
    """
    if isinstance(trades, pd.DataFrame):
        # Prefer R-multiples for Kelly as it normalizes for position size
        values = get_r_multiples(trades).values
    else:
        values = _to_1d_float_array(trades)

    if len(values) == 0:
        return 0.0

    # Probability of win (R > EPSILON)
    wins = values[values > EPSILON]
    losses = values[values < -EPSILON]
    
    n_total = len(values)
    if n_total == 0: return 0.0
    
    p = len(wins) / n_total
    q = 1.0 - p
    
    avg_w = float(np.mean(wins)) if len(wins) > 0 else 0.0
    avg_l = abs(float(np.mean(losses))) if len(losses) > 0 else 0.0

    if avg_l == 0:
        return p if avg_w > 0 else 0.0
        
    if avg_w == 0:
        return -1.0 if avg_l > 0 else 0.0

    payoff_ratio = avg_w / avg_l
    kelly_fraction = p - (q / payoff_ratio)

    return float(kelly_fraction)


def compute_r_trade_metrics(
    r_values: np.ndarray,
    mae_r: Optional[np.ndarray] = None,
    mfe_r: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """
    Calculate trade metrics from R-multiple space.
    All inputs should be normalized to R (Realized R, MAE R, MFE R).
    """
    normalized = _to_1d_float_array(r_values)

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

    if mae_r is not None:
        mae = np.asarray(mae_r, dtype=float)
        summary["median_mae"] = float(np.median(mae)) if len(mae) else float("nan")

    if mfe_r is not None:
        mfe = np.asarray(mfe_r, dtype=float)
        summary["median_mfe"] = float(np.median(mfe)) if len(mfe) else float("nan")
        if mae_r is not None:
            summary["edge_ratio"] = _r_edge_ratio(mfe, mae)
            summary["trade_efficiency"] = _r_trade_efficiency(normalized, mfe)

    return summary


def compute_trade_metrics(
    r_values: np.ndarray,
    mae: Optional[np.ndarray] = None,
    mfe: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Compute trade metrics from numeric R values and optional MAE/MFE arrays."""
    return compute_r_trade_metrics(r_values, mae_r=mae, mfe_r=mfe)


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
    Efficiency = Realized Outcome / Maximum Favorable Excursion.
    Uses closed trades only.
    """
    closed = get_closed_trades(trades)
    if closed.empty:
        return 0.0

    # 1. Try to get R-multiples (normalized)
    r_vals = get_r_multiples(closed, closed_only=False)
    
    # 2. Identify MFE source
    mfe = pd.Series(dtype=float)
    if "mfe_r" in closed.columns:
        mfe = closed["mfe_r"]
    elif "mfe_usd" in closed.columns:
        # If we have R-multiples, we need MFE in R-terms
        if not r_vals.empty and "initial_risk_amount" in closed.columns:
            risk = closed["initial_risk_amount"].abs().replace(0, np.nan)
            mfe = closed["mfe_usd"] / risk
        else:
            # Fallback: Just use USD vs USD (Ratio is still valid)
            mfe = closed["mfe_usd"]
            r_vals = closed["profit_loss"] if "profit_loss" in closed.columns else pd.Series(dtype=float)
    elif "mfe_pips" in closed.columns:
        mfe = closed["mfe_pips"]
        r_vals = closed["profit_pips"] if "profit_pips" in closed.columns else pd.Series(dtype=float)

    if mfe.empty or r_vals.empty:
        return 0.0

    # Ensure index alignment and drop non-finite
    aligned = pd.concat(
        [r_vals.rename("r"), mfe.rename("mfe")],
        axis=1
    ).replace([np.inf, -np.inf], np.nan).dropna()

    # Efficiency is only defined for trades that were in profit at some point
    aligned = aligned[aligned["mfe"] > EPSILON]

    if aligned.empty:
        return 0.0

    # Mean of (Realized / MFE)
    return float((aligned["r"] / aligned["mfe"]).mean())


def r_signal_to_noise(trades: pd.DataFrame) -> float:
    """
    Measure of trade expectancy normalized by its volatility (Mean R / Std R).
    Also known as unannualized Trade Sharpe.
    """
    r_vals = get_r_multiples(trades)
    if len(r_vals) < 5: return 0.0
    
    mu = r_vals.mean()
    sigma = r_vals.std()
    
    if sigma == 0: return float("inf") if mu > 0 else 0.0
    return float(mu / sigma)


def rolling_expectancy_stability(trades: pd.DataFrame, window: int = 50) -> float:
    """
    Measure of how stable the expectancy is over time using a rolling window.
    Calculates (Mean of Rolling Mean R) / (Std of Rolling Mean R).
    """
    r = get_r_multiples(trades)
    if len(r) < window: return 0.0
    
    rolling_exp = r.rolling(window).mean().dropna()
    if rolling_exp.empty: return 0.0
    
    mu = rolling_exp.mean()
    sigma = rolling_exp.std()
    
    if sigma == 0: return float("inf") if mu > 0 else 0.0
    return float(mu / sigma)


def win_after_win_probability(trades: pd.DataFrame) -> float:
    """Probability that a win is followed by another win."""
    ordered = get_ordered_closed_trades(trades)
    if len(ordered) < 2: return 0.0
    wins = (ordered["profit_loss"] > EPSILON).values
    
    win_followed_by_win = 0
    total_wins_except_last = 0
    
    for i in range(len(wins) - 1):
        if wins[i]:
            total_wins_except_last += 1
            if wins[i+1]:
                win_followed_by_win += 1
                
    if total_wins_except_last == 0: return 0.0
    return float(win_followed_by_win / total_wins_except_last)


def runs_test_zscore(trades: pd.DataFrame) -> float:
    """
    Wald-Wolfowitz Runs Test Z-Score.
    Tests if the sequence of wins/losses is random.
    """
    ordered = get_ordered_closed_trades(trades)
    if len(ordered) < 10: return 0.0
    
    # Binary sequence: 1 for Win, 0 for Loss (Breakeven treated as Loss for binary test)
    seq = (ordered["profit_loss"] > EPSILON).astype(int).values
    n1 = np.sum(seq)      # Wins
    n2 = len(seq) - n1    # Non-Wins
    
    if n1 == 0 or n2 == 0: return 0.0
    
    # Count runs
    runs = 1
    for i in range(1, len(seq)):
        if seq[i] != seq[i-1]:
            runs += 1
            
    # Expected runs
    mu = ((2.0 * n1 * n2) / (n1 + n2)) + 1
    # Variance
    var = (2.0 * n1 * n2 * (2.0 * n1 * n2 - n1 - n2)) / (((n1 + n2)**2) * (n1 + n2 - 1))
    
    if var <= 0: return 0.0
    z = (runs - mu) / np.sqrt(var)
    return float(z)


def trading_period_duration(
    trades: pd.DataFrame,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> pd.Timedelta:
    """Calculate total duration of the trading period."""
    if start_time is not None and end_time is not None:
        return pd.Timestamp(end_time) - pd.Timestamp(start_time)

    if trades.empty or "open_time" not in trades.columns:
        return pd.Timedelta(0)

    start = pd.to_datetime(trades["open_time"]).min()
    if "close_time" in trades.columns:
        end = pd.to_datetime(trades["close_time"]).max()
    else:
        end = pd.to_datetime(trades["open_time"]).max()

    return end - start


def trade_outcome_entropy(trades: pd.DataFrame) -> float:
    """
    Calculate Shannon entropy of trade outcomes.
    """
    closed = get_closed_trades(trades)
    if closed.empty:
        return 0.0

    wins = winning_trades(closed)
    losses = losing_trades(closed)
    be = breakeven_trades(closed)
    total = len(closed)

    probs = [x / total for x in [wins, losses, be] if x > 0]
    if not probs:
        return 0.0

    entropy = -sum(p * np.log2(p) for p in probs)
    return float(entropy)





def longest_flat_period_duration(
    trades: pd.DataFrame,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> pd.Timedelta:
    """
    Calculate longest period the strategy refrained from trading (flat).
    """
    if trades.empty:
        return trading_period_duration(trades, start_time, end_time)
        
    merged = _merge_intervals(trades, end_time)
    if not merged:
        return trading_period_duration(trades, start_time, end_time)
        
    gaps_ns = []
    
    # Gap before first trade
    if start_time:
        s_val = start_time.value
        m_start_val = merged[0][0].value
        if m_start_val > s_val:
            gaps_ns.append(m_start_val - s_val)
            
    # Gaps between trades
    for i in range(len(merged) - 1):
        gap = merged[i+1][0].value - merged[i][1].value
        if gap > 0:
            gaps_ns.append(gap)
            
    # Gap after last trade
    if end_time:
        e_val = end_time.value
        m_end_val = merged[-1][1].value
        if e_val > m_end_val:
            gaps_ns.append(e_val - m_end_val)
            
    if not gaps_ns:
        return pd.Timedelta(0)
        
    return pd.Timedelta(max(gaps_ns), unit="ns")


