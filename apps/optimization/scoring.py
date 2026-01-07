"""
Scoring Functions.

Functions to score backtest results for optimization.
"""

import apps.backtest.stats as stats
from apps.backtest.result import BacktestResult


def sharpe_score(result: BacktestResult) -> float:
    """Score based on Sharpe ratio."""
    return float(stats.sharpe_ratio(result))


def sortino_score(result: BacktestResult) -> float:
    """Score based on Sortino ratio."""
    return float(stats.sortino_ratio(result))


def calmar_score(result: BacktestResult) -> float:
    """Score based on Calmar ratio."""
    return float(stats.calmar_ratio(result))


def profit_factor_score(result: BacktestResult) -> float:
    """Score based on profit factor."""
    pf = stats.profit_factor(result)
    return float(pf if pf != float("inf") else 0.0)


def custom_score(
    result: BacktestResult,
    return_weight: float = 0.3,
    sharpe_weight: float = 0.4,
    dd_weight: float = 0.3,
) -> float:
    """
    Compute a custom composite score.

    Args:
        result: BacktestResult
        return_weight: Weight for return component
        sharpe_weight: Weight for Sharpe ratio
        dd_weight: Weight for drawdown (penalty)

    Returns:
        Weighted score
    """
    total_ret = float(stats.total_return(result))
    sharpe = float(stats.sharpe_ratio(result))
    max_dd = float(abs(stats.max_drawdown(result)))

    # Normalize and combine
    # Higher return = better
    # Higher Sharpe = better
    # Lower drawdown = better (so we penalize high DD)

    score = (
        (total_ret / 100) * return_weight
        + sharpe * sharpe_weight
        - (max_dd / 100) * dd_weight
    )

    return score
