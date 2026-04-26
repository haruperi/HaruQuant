"""
Volatility, tail risk, and capital risk metrics.

Focus: worst-case scenarios and risk distributions

This module provides functions to quantify the risk profile of a strategy.
It includes volatility measures, Value at Risk (VaR), Conditional VaR (CVaR),
Monte Carlo-based Risk of Ruin, and position exposure analysis.

Summary of Methods:
------------------
Volatility Metrics:
    - volatility: Standard deviation of returns.
    - annualized_volatility: Volatility scaled to yearly terms.
    - downside_volatility: Standard deviation of negative returns (semi-deviation).

Tail Risk & Loss Thresholds:
    - value_at_risk (VaR): Maximum expected loss at a given confidence level.
    - conditional_var (CVaR): Average loss beyond the VaR threshold.
    - expected_shortfall: Same as CVaR, measures extreme tail risk.
    - max_loss_probability: Probability of a single trade loss exceeding a threshold.
    - drawdown_probability: Probability of equity drawdown exceeding a threshold.

Capital Risk & Ruin:
    - risk_of_ruin: Monte Carlo simulation to estimate the probability of hitting a ruin threshold.

Market Exposure:
    - max_exposure: Maximum capital allocated to open positions.
    - avg_exposure: Average capital exposure over time.
    - exposure_time_ratio: Percentage of the total period spent in the market.
"""

from typing import Literal, Optional

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


@njit(cache=True)
def _risk_of_ruin_kernel(
    outcomes, risk_per_trade, target_drawdown, num_simulations, initial_capital
):
    ruin_count = 0
    n_outcomes = len(outcomes)
    simulation_length = n_outcomes * 2
    ruin_threshold = initial_capital - target_drawdown

    for _ in range(num_simulations):
        capital = initial_capital
        for _ in range(simulation_length):
            idx = np.random.randint(0, n_outcomes)
            outcome = outcomes[idx]
            capital += outcome * risk_per_trade
            if capital <= ruin_threshold:
                ruin_count += 1
                break
    return ruin_count


# =========================================================================
# Volatility Metrics
# =========================================================================


def volatility(rets: pd.Series) -> float:
    """Standard deviation of returns."""
    return float(rets.std()) if len(rets) >= 2 else 0.0


def annualized_volatility(rets: pd.Series, periods_per_year: int = 252) -> float:
    """Volatility scaled to yearly terms."""
    if len(rets) < 2:
        return 0.0
    return float(rets.std() * np.sqrt(periods_per_year))


def downside_volatility(rets: pd.Series, target: float = 0.0) -> float:
    """Standard deviation of returns below target threshold."""
    downside = rets[rets < target]
    return float(downside.std()) if len(downside) >= 2 else 0.0


# =========================================================================
# Tail Risk & Loss Thresholds
# =========================================================================


def value_at_risk(
    rets: pd.Series,
    confidence: float = 0.95,
    method: Literal["historical", "parametric", "cornish_fisher"] = "historical",
) -> float:
    """Calculate Value at Risk (VaR) - maximum expected loss at confidence level."""
    if len(rets) == 0:
        return 0.0

    if method == "historical":
        return float(abs(rets.quantile(1 - confidence)))

    elif method == "parametric":
        mean, std = rets.mean(), rets.std()
        z_score = abs(np.percentile(np.random.standard_normal(10000), (1 - confidence) * 100))
        return float(abs(mean - z_score * std))

    elif method == "cornish_fisher":
        mean, std = rets.mean(), rets.std()
        skew, kurt = rets.skew(), rets.kurtosis()
        z = abs(np.percentile(np.random.standard_normal(10000), (1 - confidence) * 100))
        z_cf = (z + (z**2 - 1) * skew / 6 + (z**3 - 3 * z) * kurt / 24 - (2 * z**3 - 5 * z) * skew**2 / 36)
        return float(abs(mean - z_cf * std))

    return 0.0


def conditional_var(rets: pd.Series, confidence: float = 0.95) -> float:
    """Calculate Conditional Value at Risk (CVaR) / Expected Shortfall."""
    if len(rets) == 0:
        return 0.0
    var_threshold = -value_at_risk(rets, confidence, method="historical")
    tail_returns = rets[rets <= var_threshold]
    return float(abs(tail_returns.mean())) if len(tail_returns) > 0 else 0.0


def expected_shortfall(rets: pd.Series, confidence: float = 0.95) -> float:
    """Calculate Expected Shortfall (same as CVaR)."""
    return conditional_var(rets, confidence)


def max_loss_probability(trades: pd.DataFrame, loss_threshold: float = -5.0) -> float:
    """Probability of a single trade loss exceeding a threshold."""
    if len(trades) == 0:
        return 0.0
    losses = trades[trades["profit_loss"] < 0]["profit_loss"]
    if len(losses) == 0:
        return 0.0
    extreme_losses = losses[losses < loss_threshold]
    return float(len(extreme_losses) / len(losses))


def drawdown_probability(equity: pd.Series, threshold: float) -> float:
    """Probability of equity drawdown exceeding a threshold percentage."""
    if len(equity) == 0:
        return 0.0
    running_max = equity.expanding().max()
    pct_drawdowns = ((equity - running_max) / running_max) * 100
    exceeded = (pct_drawdowns < -threshold).sum()
    return float(exceeded / len(pct_drawdowns))


# =========================================================================
# Capital Risk & Ruin
# =========================================================================


def risk_of_ruin(
    trades: pd.DataFrame,
    risk_per_trade: float,
    target_drawdown: float = 50.0,
    num_simulations: int = 10000,
) -> float:
    """Monte Carlo simulation of trade outcomes to estimate ruin probability."""
    if len(trades) == 0 or "profit_loss" not in trades.columns:
        return 0.0

    if "r_multiple" in trades.columns:
        outcomes = trades["r_multiple"].astype(float).values
    else:
        avg_trade_val = trades["profit_loss"].abs().mean()
        if avg_trade_val == 0: return 0.0
        outcomes = (trades["profit_loss"].values / avg_trade_val).astype(float)

    ruin_count = _risk_of_ruin_kernel(
        outcomes, float(risk_per_trade), float(target_drawdown), int(num_simulations), 100.0
    )
    return float(ruin_count / num_simulations)


# =========================================================================
# Market Exposure
# =========================================================================


def max_exposure(trades: pd.DataFrame) -> float:
    """Maximum capital allocated to open positions (simplified)."""
    if len(trades) == 0 or "size" not in trades.columns:
        return 0.0
    return float((trades["size"] * 100000).max())


def avg_exposure(trades: pd.DataFrame) -> float:
    """Average capital exposure over all trades."""
    if len(trades) == 0 or "size" not in trades.columns:
        return 0.0
    return float((trades["size"] * 100000).mean())


def exposure_time_ratio(
    trades: pd.DataFrame, total_time_hours: Optional[float] = None
) -> float:
    """Percentage of the total period spent in the market."""
    if len(trades) == 0 or "time_in_trade" not in trades.columns:
        return 0.0

    if total_time_hours is None:
        if "open_time" not in trades.columns or "close_time" not in trades.columns:
            return 0.0
        duration = (trades["close_time"].max() - trades["open_time"].min()).total_seconds() / 3600
        total_time_hours = duration

    if total_time_hours == 0:
        return 0.0

    return float(trades["time_in_trade"].sum() / total_time_hours)
