"""
Volatility, tail risk, and capital risk.

from backend.common.logger import logger
Focus: worst-case scenarios
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
# Volatility
# =========================================================================


def volatility(returns: pd.Series) -> float:
    """
    Compute volatility using standard deviation.

    Args:
        returns: Returns series

    Returns:
        Volatility value
    """
    if len(returns) < 2:
        return 0.0
    return float(returns.std())


def annualized_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    Calculate annualized volatility.

    Args:
        returns: Returns series
        periods_per_year: Number of periods per year (default 252 for daily)

    Returns:
        Annualized volatility value
    """
    if len(returns) < 2:
        return 0.0

    vol = returns.std()
    return float(vol * np.sqrt(periods_per_year))


def downside_volatility(returns: pd.Series, target: float = 0.0) -> float:
    """
    Calculate downside volatility (semi-deviation).

    Only considers returns below target

    Args:
        returns: Returns series
        target: Target return threshold

    Returns:
        Downside volatility value
    """
    if len(returns) < 2:
        return 0.0

    downside_returns = returns[returns < target]

    if len(downside_returns) == 0:
        return 0.0

    return float(downside_returns.std())


# =========================================================================
# Tail Risk
# =========================================================================


def value_at_risk(
    returns: pd.Series,
    confidence: float = 0.95,
    method: Literal["historical", "parametric", "cornish_fisher"] = "historical",
) -> float:
    """
    Calculate Value at Risk (VaR) - maximum expected loss at confidence level.

    Args:
        returns: Returns series
        confidence: Confidence level (e.g., 0.95 for 95%)
        method: Calculation method
            - 'historical': Historical percentile
            - 'parametric': Assumes normal distribution
            - 'cornish_fisher': Adjusts for skewness and kurtosis

    Returns:
        VaR value (positive = loss)
    """
    if len(returns) == 0:
        return 0.0

    if method == "historical":
        # Historical VaR
        var = returns.quantile(1 - confidence)
        return float(abs(var))

    elif method == "parametric":
        # Parametric VaR (assumes normality)
        mean = returns.mean()
        std = returns.std()
        z_score = abs(
            np.percentile(np.random.standard_normal(10000), (1 - confidence) * 100)
        )
        var = mean - z_score * std
        return float(abs(var))

    elif method == "cornish_fisher":
        # Cornish-Fisher VaR (adjusts for skewness and kurtosis)
        mean = returns.mean()
        std = returns.std()
        skew = returns.skew()
        kurt = returns.kurtosis()

        # Standard normal quantile
        z = abs(np.percentile(np.random.standard_normal(10000), (1 - confidence) * 100))

        # Cornish-Fisher expansion
        z_cf = (
            z
            + (z**2 - 1) * skew / 6
            + (z**3 - 3 * z) * kurt / 24
            - (2 * z**3 - 5 * z) * skew**2 / 36
        )

        var = mean - z_cf * std
        return float(abs(var))

    return 0.0


def conditional_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Calculate Conditional Value at Risk (CVaR) / Expected Shortfall.

    Average loss beyond VaR threshold

    Args:
        returns: Returns series
        confidence: Confidence level

    Returns:
        CVaR value (positive = loss)
    """
    if len(returns) == 0:
        return 0.0

    # Get VaR threshold
    var_threshold = -value_at_risk(returns, confidence, method="historical")

    # Get returns worse than VaR
    tail_returns = returns[returns <= var_threshold]

    if len(tail_returns) == 0:
        return 0.0

    return float(abs(tail_returns.mean()))


def expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Calculate Expected Shortfall (same as CVaR).

    Args:
        returns: Returns series
        confidence: Confidence level

    Returns:
        Expected shortfall value
    """
    return conditional_var(returns, confidence)


# =========================================================================
# Capital Risk
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
            # Sample random outcome
            idx = np.random.randint(0, n_outcomes)
            outcome = outcomes[idx]

            # Apply outcome
            capital += outcome * risk_per_trade

            # Check for ruin
            if capital <= ruin_threshold:
                ruin_count += 1
                break
    return ruin_count


def risk_of_ruin(
    trades: pd.DataFrame,
    risk_per_trade: float,
    target_drawdown: float = 50.0,
    num_simulations: int = 10000,
) -> float:
    """
    Calculate Risk of Ruin - probability of hitting target drawdown.

    Monte Carlo simulation of trade outcomes

    Args:
        trades: Trades DataFrame
        risk_per_trade: Risk per trade as % of capital
        target_drawdown: Target drawdown % to consider "ruin"
        num_simulations: Number of Monte Carlo simulations

    Returns:
        Probability of ruin (0-1)
    """
    if len(trades) == 0:
        return 0.0

    # Get trade outcomes as percentages
    if "profit_loss" not in trades.columns:
        return 0.0

    # Use R-multiples if available, otherwise estimate from P&L
    if "r_multiple" in trades.columns:
        outcomes = trades["r_multiple"].astype(float).values
    else:
        # Estimate R-multiples assuming equal risk per trade
        avg_trade_value = trades["profit_loss"].abs().mean()
        if avg_trade_value == 0:
            return 0.0
        outcomes = (trades["profit_loss"].values / avg_trade_value).astype(float)

    ruin_count = _risk_of_ruin_kernel(
        outcomes,
        float(risk_per_trade),
        float(target_drawdown),
        int(num_simulations),
        100.0,
    )

    return float(ruin_count / num_simulations)


def max_loss_probability(trades: pd.DataFrame, loss_threshold: float = -5.0) -> float:
    """
    Calculate probability of loss exceeding threshold.

    Args:
        trades: Trades DataFrame
        loss_threshold: Loss threshold (negative value)

    Returns:
        Probability of exceeding threshold
    """
    if len(trades) == 0:
        return 0.0

    losses = trades[trades["profit_loss"] < 0]["profit_loss"]

    if len(losses) == 0:
        return 0.0

    # Calculate probability
    extreme_losses = losses[losses < loss_threshold]
    probability = len(extreme_losses) / len(losses)

    return float(probability)


def drawdown_probability(equity_curve: pd.Series, threshold: float) -> float:
    """
    Calculate probability of drawdown exceeding threshold.

    Args:
        equity_curve: Equity series
        threshold: Drawdown threshold (positive value)

    Returns:
        Probability of exceeding threshold
    """
    if len(equity_curve) == 0:
        return 0.0

    # Calculate drawdowns
    running_max = equity_curve.expanding().max()
    drawdowns = equity_curve - running_max

    # Percentage drawdowns
    pct_drawdowns = (drawdowns / running_max) * 100

    # Count periods exceeding threshold
    exceeded = (pct_drawdowns < -threshold).sum()
    total = len(pct_drawdowns)

    return float(exceeded / total)


# =========================================================================
# Exposure
# =========================================================================


def max_exposure(trades: pd.DataFrame) -> float:
    """
    Calculate maximum capital exposure.

    Calculated from position sizes

    Args:
        trades: Trades DataFrame

    Returns:
        Maximum exposure value
    """
    if len(trades) == 0 or "size" not in trades.columns:
        return 0.0

    # Assuming size is in lots and standard lot size
    # This is simplified - in reality depends on symbol
    exposure = trades["size"] * 100000  # Standard forex lot

    return float(exposure.max())


def avg_exposure(trades: pd.DataFrame) -> float:
    """
    Calculate average capital exposure.

    Args:
        trades: Trades DataFrame

    Returns:
        Average exposure value
    """
    if len(trades) == 0 or "size" not in trades.columns:
        return 0.0

    exposure = trades["size"] * 100000

    return float(exposure.mean())


def exposure_time_ratio(
    trades: pd.DataFrame, total_time_hours: Optional[float] = None
) -> float:
    """
    Calculate percentage of time in market.

    Args:
        trades: Trades DataFrame
        total_time_hours: Total time period in hours (auto-calculated if None)

    Returns:
        Exposure time ratio (0-1)
    """
    if len(trades) == 0 or "time_in_trade" not in trades.columns:
        return 0.0

    total_trade_time = trades["time_in_trade"].sum()

    if total_time_hours is None:
        # Calculate from first open to last close
        if "open_time" not in trades.columns or "close_time" not in trades.columns:
            return 0.0

        first_open = trades["open_time"].min()
        last_close = trades["close_time"].max()

        total_time_hours = (last_close - first_open).total_seconds() / 3600

    if total_time_hours == 0:
        return 0.0

    return float(total_trade_time / total_time_hours)
