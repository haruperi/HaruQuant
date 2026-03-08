"""Edge Lab performance metrics and statistics.

This module provides trade-level and portfolio-level performance metrics
for evaluating edge discovery results.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from apps.utils.logger import logger

# =============================================================================
# BASIC TRADE METRICS
# =============================================================================


def expectancy(r: np.ndarray) -> float:
    """Calculate average R-multiple (expectancy).

    Args:
        r: Array of R-multiples

    Returns:
        Mean R-multiple (expectancy)
    """
    r = np.asarray(r, dtype=float)
    return float(np.mean(r)) if len(r) else float("nan")


def win_rate(r: np.ndarray) -> float:
    """Calculate win rate (percentage of winning trades).

    Args:
        r: Array of R-multiples

    Returns:
        Win rate (0-1)
    """
    r = np.asarray(r, dtype=float)
    return float(np.mean(r > 0)) if len(r) else float("nan")


def profit_factor(r: np.ndarray) -> float:
    """Calculate profit factor (gross profit / gross loss).

    Args:
        r: Array of R-multiples

    Returns:
        Profit factor (>1 means profitable)
    """
    r = np.asarray(r, dtype=float)
    wins = r[r > 0].sum()
    losses = -r[r < 0].sum()
    if losses <= 0:
        return float("inf") if wins > 0 else float("nan")
    return float(wins / losses)


def median_mae_mfe(mae: np.ndarray, mfe: np.ndarray) -> Tuple[float, float]:
    """Calculate median MAE and MFE.

    Args:
        mae: Array of Maximum Adverse Excursion values
        mfe: Array of Maximum Favorable Excursion values

    Returns:
        Tuple of (median_mae, median_mfe)
    """
    mae = np.asarray(mae, dtype=float)
    mfe = np.asarray(mfe, dtype=float)
    return (
        float(np.median(mae)) if len(mae) else float("nan"),
        float(np.median(mfe)) if len(mfe) else float("nan"),
    )


def avg_win_loss(r: np.ndarray) -> Tuple[float, float]:
    """Calculate average winning and losing trade R-multiples.

    Args:
        r: Array of R-multiples

    Returns:
        Tuple of (avg_win, avg_loss)
    """
    r = np.asarray(r, dtype=float)
    wins = r[r > 0]
    losses = r[r < 0]

    avg_win = float(np.mean(wins)) if len(wins) else float("nan")
    avg_loss = float(np.mean(losses)) if len(losses) else float("nan")

    return avg_win, avg_loss


def payoff_ratio(r: np.ndarray) -> float:
    """Calculate payoff ratio (avg win / |avg loss|).

    Also known as reward-to-risk ratio.

    Args:
        r: Array of R-multiples

    Returns:
        Payoff ratio
    """
    avg_win, avg_loss = avg_win_loss(r)
    if np.isnan(avg_win) or np.isnan(avg_loss) or avg_loss == 0:
        return float("nan")
    return abs(avg_win / avg_loss)


def expectancy_score(r: np.ndarray) -> float:
    """Calculate expectancy score (win_rate * payoff - loss_rate).

    A more refined expectancy metric that accounts for both
    probability and magnitude of wins/losses.

    Args:
        r: Array of R-multiples

    Returns:
        Expectancy score
    """
    wr = win_rate(r)
    pr = payoff_ratio(r)

    if np.isnan(wr) or np.isnan(pr):
        return float("nan")

    return wr * pr - (1 - wr)


# =============================================================================
# RISK-ADJUSTED METRICS
# =============================================================================


def sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Calculate Sharpe ratio.

    Args:
        returns: Array of period returns (not R-multiples)
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of trading periods per year

    Returns:
        Annualized Sharpe ratio
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 2:
        return float("nan")

    excess_returns = returns - risk_free_rate / periods_per_year
    mean_excess = np.mean(excess_returns)
    std_excess = np.std(excess_returns, ddof=1)

    if std_excess == 0:
        return (
            float("inf")
            if mean_excess > 0
            else float("-inf") if mean_excess < 0 else float("nan")
        )

    return float(mean_excess / std_excess * np.sqrt(periods_per_year))


def sortino_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Calculate Sortino ratio (downside risk only).

    Args:
        returns: Array of period returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of trading periods per year

    Returns:
        Annualized Sortino ratio
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 2:
        return float("nan")

    excess_returns = returns - risk_free_rate / periods_per_year
    mean_excess = np.mean(excess_returns)

    # Downside deviation
    negative_returns = excess_returns[excess_returns < 0]
    if len(negative_returns) == 0:
        return float("inf") if mean_excess > 0 else float("nan")

    downside_std = np.sqrt(np.mean(negative_returns**2))

    if downside_std == 0:
        return float("inf") if mean_excess > 0 else float("nan")

    return float(mean_excess / downside_std * np.sqrt(periods_per_year))


def calmar_ratio(
    returns: np.ndarray,
    periods_per_year: int = 252,
) -> float:
    """Calculate Calmar ratio (return / max drawdown).

    Args:
        returns: Array of period returns
        periods_per_year: Number of trading periods per year

    Returns:
        Calmar ratio
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 2:
        return float("nan")

    annual_return = np.mean(returns) * periods_per_year
    mdd = max_drawdown(returns)

    if mdd == 0:
        return float("inf") if annual_return > 0 else float("nan")

    return float(annual_return / abs(mdd))


# =============================================================================
# DRAWDOWN METRICS
# =============================================================================


def max_drawdown(returns: np.ndarray) -> float:
    """Calculate maximum drawdown from returns.

    Args:
        returns: Array of period returns

    Returns:
        Maximum drawdown (negative value)
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    if len(returns) == 0:
        return float("nan")

    # Cumulative returns (wealth curve)
    cum_returns = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cum_returns)
    drawdowns = (cum_returns - running_max) / running_max

    return float(np.min(drawdowns))


def max_drawdown_duration(returns: np.ndarray) -> int:
    """Calculate maximum drawdown duration (in periods).

    Args:
        returns: Array of period returns

    Returns:
        Number of periods in longest drawdown
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    if len(returns) == 0:
        return 0

    cum_returns = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cum_returns)

    in_drawdown = cum_returns < running_max

    max_duration = 0
    current_duration = 0

    for dd in in_drawdown:
        if dd:
            current_duration += 1
            max_duration = max(max_duration, current_duration)
        else:
            current_duration = 0

    return max_duration


def recovery_factor(returns: np.ndarray) -> float:
    """Calculate recovery factor (total return / max drawdown).

    Args:
        returns: Array of period returns

    Returns:
        Recovery factor
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    if len(returns) == 0:
        return float("nan")

    total_return = np.prod(1 + returns) - 1
    mdd = max_drawdown(returns)

    if mdd == 0:
        return float("inf") if total_return > 0 else float("nan")

    return float(total_return / abs(mdd))


# =============================================================================
# TRADE ANALYSIS METRICS
# =============================================================================


def consecutive_wins_losses(r: np.ndarray) -> Tuple[int, int]:
    """Calculate max consecutive wins and losses.

    Args:
        r: Array of R-multiples

    Returns:
        Tuple of (max_consecutive_wins, max_consecutive_losses)
    """
    r = np.asarray(r, dtype=float)

    if len(r) == 0:
        return 0, 0

    wins = r > 0

    max_wins = 0
    max_losses = 0
    current_wins = 0
    current_losses = 0

    for w in wins:
        if w:
            current_wins += 1
            max_wins = max(max_wins, current_wins)
            current_losses = 0
        else:
            current_losses += 1
            max_losses = max(max_losses, current_losses)
            current_wins = 0

    return max_wins, max_losses


def trade_efficiency(r: np.ndarray, mfe: np.ndarray) -> float:
    """Calculate trade efficiency (actual R / MFE).

    Measures how well trades capture available profit.

    Args:
        r: Array of R-multiples
        mfe: Array of Maximum Favorable Excursion

    Returns:
        Average efficiency (0-1)
    """
    r = np.asarray(r, dtype=float)
    mfe = np.asarray(mfe, dtype=float)

    if len(r) != len(mfe) or len(r) == 0:
        return float("nan")

    # Only consider winning trades where MFE > 0
    mask = mfe > 0
    if not np.any(mask):
        return float("nan")

    efficiency = r[mask] / mfe[mask]
    return float(np.mean(efficiency))


def edge_ratio(mfe: np.ndarray, mae: np.ndarray) -> float:
    """Calculate edge ratio (MFE / MAE).

    Higher values indicate better trade location.

    Args:
        mfe: Array of Maximum Favorable Excursion
        mae: Array of Maximum Adverse Excursion

    Returns:
        Edge ratio
    """
    mfe = np.asarray(mfe, dtype=float)
    mae = np.asarray(mae, dtype=float)

    if len(mfe) != len(mae) or len(mfe) == 0:
        return float("nan")

    # MAE should be negative, take absolute value
    mae_abs = np.abs(mae)
    mask = mae_abs > 0

    if not np.any(mask):
        return float("inf") if np.mean(mfe) > 0 else float("nan")

    return float(np.mean(mfe[mask] / mae_abs[mask]))


# =============================================================================
# STATISTICAL SIGNIFICANCE
# =============================================================================


def t_statistic(r: np.ndarray) -> float:
    """Calculate t-statistic for expectancy.

    Tests if expectancy is significantly different from zero.

    Args:
        r: Array of R-multiples

    Returns:
        T-statistic
    """
    r = np.asarray(r, dtype=float)
    n = len(r)

    if n < 2:
        return float("nan")

    mean = np.mean(r)
    std = np.std(r, ddof=1)

    if std == 0:
        return float("inf") if mean > 0 else float("-inf") if mean < 0 else float("nan")

    return float(mean / (std / np.sqrt(n)))


def sqn(r: np.ndarray) -> float:
    """Calculate System Quality Number (Van Tharp).

    SQN = sqrt(n) * expectancy / std(R)

    Interpretation:
    - SQN < 1.6: Poor
    - 1.6-2.0: Below average
    - 2.0-2.5: Average
    - 2.5-3.0: Good
    - 3.0-5.0: Excellent
    - 5.0-7.0: Superb
    - > 7.0: Holy Grail

    Args:
        r: Array of R-multiples

    Returns:
        SQN value
    """
    r = np.asarray(r, dtype=float)
    n = len(r)

    if n < 30:
        logger.warning(f"SQN calculated with only {n} trades (recommended: 30+)")

    if n < 2:
        return float("nan")

    mean = np.mean(r)
    std = np.std(r, ddof=1)

    if std == 0:
        return float("inf") if mean > 0 else float("-inf") if mean < 0 else float("nan")

    # Cap at 100 trades for stability
    effective_n = min(n, 100)
    return float(np.sqrt(effective_n) * mean / std)


# =============================================================================
# SUMMARY FUNCTIONS
# =============================================================================


def compute_trade_metrics(
    r: np.ndarray,
    mae: Optional[np.ndarray] = None,
    mfe: Optional[np.ndarray] = None,
) -> dict:
    """Compute comprehensive trade metrics.

    Args:
        r: Array of R-multiples
        mae: Optional array of MAE values
        mfe: Optional array of MFE values

    Returns:
        Dictionary of metrics
    """
    r = np.asarray(r, dtype=float)

    metrics = {
        "n_trades": len(r),
        "expectancy": expectancy(r),
        "win_rate": win_rate(r),
        "profit_factor": profit_factor(r),
        "sqn": sqn(r),
        "t_stat": t_statistic(r),
    }

    avg_win, avg_loss = avg_win_loss(r)
    metrics["avg_win"] = avg_win
    metrics["avg_loss"] = avg_loss
    metrics["payoff_ratio"] = payoff_ratio(r)

    max_cons_wins, max_cons_losses = consecutive_wins_losses(r)
    metrics["max_consecutive_wins"] = max_cons_wins
    metrics["max_consecutive_losses"] = max_cons_losses

    if mae is not None:
        mae = np.asarray(mae, dtype=float)
        metrics["median_mae"] = float(np.median(mae)) if len(mae) else float("nan")

    if mfe is not None:
        mfe = np.asarray(mfe, dtype=float)
        metrics["median_mfe"] = float(np.median(mfe)) if len(mfe) else float("nan")

        if mae is not None:
            metrics["edge_ratio"] = edge_ratio(mfe, mae)
            metrics["trade_efficiency"] = trade_efficiency(r, mfe)

    return metrics


def compute_equity_metrics(returns: np.ndarray, periods_per_year: int = 252) -> dict:
    """Compute equity curve / portfolio metrics.

    Args:
        returns: Array of period returns
        periods_per_year: Trading periods per year

    Returns:
        Dictionary of metrics
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[~np.isnan(returns)]

    total_return = float(np.prod(1 + returns) - 1) if len(returns) else float("nan")
    annual_return = (
        float(np.mean(returns) * periods_per_year) if len(returns) else float("nan")
    )

    metrics = {
        "total_return": total_return,
        "annual_return": annual_return,
        "sharpe_ratio": sharpe_ratio(returns, periods_per_year=periods_per_year),
        "sortino_ratio": sortino_ratio(returns, periods_per_year=periods_per_year),
        "calmar_ratio": calmar_ratio(returns, periods_per_year=periods_per_year),
        "max_drawdown": max_drawdown(returns),
        "max_dd_duration": max_drawdown_duration(returns),
        "recovery_factor": recovery_factor(returns),
    }

    return metrics

