"""
Risk-adjusted performance ratios.

from backend.common.logger import logger
Focus: reward vs volatility vs downside
"""

import numpy as np
import pandas as pd

from . import drawdowns, metrics, returns


def _to_1d_float_array(values) -> np.ndarray:
    """Normalize 1D numeric inputs to a float NumPy array."""
    if isinstance(values, pd.Series):
        array = values.astype(float).to_numpy()
    else:
        array = np.asarray(values, dtype=float)

    if array.ndim == 0:
        array = array.reshape(1)

    return array[~np.isnan(array)]


def _expectancy_1d(values) -> float:
    """Calculate mean outcome from a trade frame or 1D numeric input."""
    if isinstance(values, pd.DataFrame):
        if len(values) == 0:
            return 0.0
        return float(values["profit_loss"].mean())

    normalized = _to_1d_float_array(values)
    if len(normalized) == 0:
        return float("nan")
    return float(np.mean(normalized))


def win_rate_fraction(values) -> float:
    """Calculate win rate on a 0-1 scale from 1D numeric input."""
    normalized = _to_1d_float_array(values)
    if len(normalized) == 0:
        return float("nan")
    return float(np.mean(normalized > 0))


def _avg_win_loss_1d(values) -> tuple[float, float]:
    """Calculate mean winning and losing outcomes from 1D numeric input."""
    normalized = _to_1d_float_array(values)
    wins = normalized[normalized > 0]
    losses = normalized[normalized < 0]
    avg_win = float(np.mean(wins)) if len(wins) else float("nan")
    avg_loss = float(np.mean(losses)) if len(losses) else float("nan")
    return avg_win, avg_loss

# =========================================================================
# Classical Ratios
# =========================================================================


def sharpe_ratio(
    returns: pd.Series | np.ndarray, risk_free_rate: float = 0.0, annualize: bool = True
) -> float:
    """
    Sharpe Ratio - excess return per unit of volatility.

    Formula: (Return - RiskFree) / Volatility

    If inputs are monthly returns, this is the Monthly Sharpe Ratio.
    To get Annualized Sharpe Ratio, set annualize=True (multiplies by sqrt(12), assuming monthly input).

    Args:
        returns: Returns series (e.g. Monthly Returns)
        risk_free_rate: Risk-free rate (per period, e.g. monthly)
        annualize: Whether to annualize the ratio

    Returns:
        Sharpe ratio value
    """
    normalized = _to_1d_float_array(returns)

    if len(normalized) < 2:
        return 0.0

    excess_returns = normalized - (risk_free_rate / 252)
    mean_excess = excess_returns.mean()
    std_excess = excess_returns.std(ddof=1)

    if std_excess == 0:
        return 0.0

    sharpe = mean_excess / std_excess

    if annualize:
        sharpe = sharpe * np.sqrt(252)

    return float(sharpe)


def annualized_sharpe_ratio(
    monthly_returns: pd.Series, risk_free_rate_monthly: float = 0.0
) -> float:
    """
    Annualized Sharpe Ratio.

    Product of Monthly Sharpe Ratio and sqrt(12).
    """
    monthly_sharpe = sharpe_ratio(
        monthly_returns, risk_free_rate_monthly, annualize=False
    )
    return float(monthly_sharpe * np.sqrt(12))


def sortino_ratio(
    returns: pd.Series | np.ndarray, target_return: float = 0.0, annualize: bool = True
) -> float:
    """
    Sortino Ratio - excess return per unit of downside volatility.

    Formula: (MR - MAR) / DD
    MR: Average return
    MAR: Minimal acceptable rate of return (target_return)
    DD: Downside risk (standard deviation of returns below MAR)
    """
    normalized = _to_1d_float_array(returns)

    if len(normalized) < 2:
        return 0.0

    excess_returns = normalized - target_return
    mean_excess = excess_returns.mean()

    # Downside deviation relative to target return
    # According to definition: "realizations below reference point... considered bad volatility"
    # We take all returns, check if < target.
    # Standard calculation: sqrt(mean(min(0, r - target)^2))
    # This is slightly different from "std dev of negative returns".
    # Let's use the explicit Lower Partial Moment (LPM) order 2 formula which is standard for Sortino.

    # Calculate deviations from target
    deviations = normalized - target_return
    # Keep only negative deviations (those failing to meet target)
    downside_deviations = deviations[deviations < 0]

    # If using standard deviation of ONLY the downside points:
    # downside_std = downside_deviations.std()

    # If using Root Mean Square of downside deviations (LPM 2):
    # This matches the "Downside Deviation" definition typically used with Sortino.
    sum_sq_diff = (downside_deviations**2).sum()
    n = len(normalized)
    downside_risk = np.sqrt(sum_sq_diff / n)

    if downside_risk == 0:
        return float("inf") if mean_excess > 0 else 0.0

    sortino = mean_excess / downside_risk

    if annualize:
        # Assuming monthly
        sortino = sortino * np.sqrt(12)

    return float(sortino)


def fouse_ratio(
    monthly_returns: pd.Series,
    risk_tolerance: float,
    risk_free_rate_monthly: float = 0.0,
) -> float:
    """
    Fouse Ratio (Fouse DD Index).

    Formula: rc - rt * dd^2
    rc: compound average return (we'll use mean return here to align with typical 'return' inputs, or CAGR?)
        User def says: "rc = compound average return"
    rt: risk tolerance
    dd: downside deviation
    """
    if len(monthly_returns) == 0:
        return 0.0

    # User def says "rc = compound average return".
    # For monthly data, this might be the CMGR or just the mean.
    # Let's use the geometric mean (compound average) of the monthly returns.
    growth_factors = 1 + monthly_returns
    rc = growth_factors.prod() ** (1 / len(monthly_returns)) - 1
    # Note: rc is per month.

    # Calculate downside deviation (dd)
    # Using 0 as target or risk_free_rate?
    # Definition implies "risk" is deviations below reference.
    # Usually Fouse uses a specific MAR. Let's assume 0 or RFR if not specified,
    # but the content implies referencing "Minimal acceptable rate".
    # We'll use risk_free_rate_monthly as the reference (MAR).

    target = risk_free_rate_monthly
    deviations = monthly_returns - target
    downside_deviations = deviations[deviations < 0]
    sum_sq_diff = (downside_deviations**2).sum()
    n = len(monthly_returns)
    dd = np.sqrt(sum_sq_diff / n)

    fouse = rc - (risk_tolerance * (dd**2))

    return float(fouse)


def upside_potential_ratio(returns: pd.Series, target: float = 0.0) -> float:
    """
    Upside Potential Ratio - upside potential / downside risk.

    Upside Potential: Probability-weighted average of returns above reference.
    Downside Risk: Downside deviation (LPM 2).

    Args:
        returns: Returns series
        target: Target return

    Returns:
        Upside potential ratio value
    """
    if len(returns) < 2:
        return 0.0

    # Downside Risk (same as Sortino denominator)
    deviations = returns - target
    downside_deviations = deviations[deviations < 0]
    sum_sq_diff_down = (downside_deviations**2).sum()
    n = len(returns)
    downside_risk = np.sqrt(sum_sq_diff_down / n)

    # Upside Potential
    # "Probability weighted average of returns above the reference rate"
    # = Sum(max(0, r - target)) / N
    upside_deviations = deviations[deviations > 0]
    sum_diff_up = upside_deviations.sum()
    upside_potential = sum_diff_up / n

    if downside_risk == 0:
        return float("inf") if upside_potential > 0 else 0.0

    return float(upside_potential / downside_risk)


def calmar_ratio(
    cagr_value: float | pd.Series | np.ndarray,
    max_dd: float | None = None,
    periods_per_year: int = 252,
) -> float:
    """
    Calmar Ratio - CAGR divided by maximum drawdown.

    Args:
        cagr_value: Compound annual growth rate (as percentage)
        max_dd: Maximum drawdown (positive value)

    Returns:
        Calmar ratio value
    """
    if max_dd is None and not np.isscalar(cagr_value):
        normalized = _to_1d_float_array(cagr_value)
        if len(normalized) < 2:
            return float("nan")

        annual_return = np.mean(normalized) * periods_per_year
        drawdown = drawdowns.max_drawdown(normalized)
        if drawdown == 0:
            return float("inf") if annual_return > 0 else float("nan")
        return float(annual_return / abs(drawdown))

    if max_dd is None:
        raise ValueError("max_dd is required when calmar_ratio receives a scalar CAGR")

    if max_dd == 0:
        return 0.0 if cagr_value == 0 else float("inf")

    return float(cagr_value / max_dd)


def information_ratio(
    returns: pd.Series,
    benchmark_returns: pd.Series,
    annualize: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Information Ratio - excess return per unit of tracking error.

    Measures consistency of outperformance

    Args:
        returns: Strategy returns
        benchmark_returns: Benchmark returns
        annualize: Whether to annualize the ratio

    Returns:
        Information ratio value
    """
    if len(returns) < 2 or len(benchmark_returns) < 2:
        return 0.0

    # Align returns
    aligned_returns = pd.DataFrame(
        {"strategy": returns, "benchmark": benchmark_returns}
    ).dropna()

    if len(aligned_returns) < 2:
        return 0.0

    excess_returns = aligned_returns["strategy"] - aligned_returns["benchmark"]

    mean_excess = excess_returns.mean()
    tracking_error = excess_returns.std()

    if tracking_error == 0:
        return 0.0

    ir = mean_excess / tracking_error

    if annualize:
        ir = ir * np.sqrt(252)

    return float(ir)


# =========================================================================
# Advanced Ratios
# =========================================================================


def omega_ratio(returns: pd.Series, threshold: float = 0.0) -> float:
    """
    Omega Ratio - probability-weighted ratio of gains vs losses.

    Formula: Sum(returns > threshold) / |Sum(returns < threshold)|

    Args:
        returns: Returns series
        threshold: Threshold return

    Returns:
        Omega ratio value
    """
    if len(returns) == 0:
        return 0.0

    gains = returns[returns > threshold] - threshold
    losses = threshold - returns[returns < threshold]

    sum_gains = gains.sum()
    sum_losses = losses.sum()

    if sum_losses == 0:
        return float("inf") if sum_gains > 0 else 1.0

    return float(sum_gains / sum_losses)


def gain_to_pain_ratio(returns: pd.Series) -> float:
    """
    Gain-to-Pain Ratio - sum of returns / sum of absolute negative returns.

    Args:
        returns: Returns series

    Returns:
        Gain-to-pain ratio value
    """
    if len(returns) == 0:
        return 0.0

    sum_returns = returns.sum()
    sum_negative = abs(returns[returns < 0].sum())

    if sum_negative == 0:
        return float("inf") if sum_returns > 0 else 0.0

    return float(sum_returns / sum_negative)


def kappa_ratio(returns: pd.Series, target: float = 0.0, order: int = 3) -> float:
    """
    Kappa Ratio - generalization of Sortino using higher moments.

    Args:
        returns: Returns series
        target: Target return
        order: Order of lower partial moment (default 3)

    Returns:
        Kappa ratio value
    """
    if len(returns) < 2:
        return 0.0

    excess_returns = returns - target
    mean_excess = excess_returns.mean()

    # Lower partial moment
    downside_returns = excess_returns[excess_returns < 0]

    if len(downside_returns) == 0:
        return float("inf") if mean_excess > 0 else 0.0

    lpm = (abs(downside_returns) ** order).mean() ** (1 / order)

    if lpm == 0:
        return 0.0

    return float(mean_excess / lpm)


# =========================================================================
# Trade-Based Ratios
# =========================================================================


def profit_to_mae_ratio(trades: pd.DataFrame) -> float:
    """
    Profit-to-MAE Ratio - measures efficiency of profit capture.

    Args:
        trades: Trades DataFrame

    Returns:
        Average profit / MAE ratio
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0

    # Filter trades with positive MAE
    valid_trades = trades[trades["mae_usd"] > 0]

    if len(valid_trades) == 0:
        return 0.0

    ratio = valid_trades["profit_loss"] / valid_trades["mae_usd"]

    return float(ratio.mean())


def mfe_to_mae_ratio(trades: pd.DataFrame) -> float:
    """
    MFE-to-MAE Ratio - favorable excursion vs adverse excursion.

    Measures how much favorable movement vs adverse movement

    Args:
        trades: Trades DataFrame

    Returns:
        Average MFE / MAE ratio
    """
    if len(trades) == 0:
        return 0.0

    if "mfe_usd" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0

    # Filter trades with positive MAE
    valid_trades = trades[trades["mae_usd"] > 0]

    if len(valid_trades) == 0:
        return 0.0

    ratio = valid_trades["mfe_usd"] / valid_trades["mae_usd"]

    return float(ratio.mean())


def return_over_drawdown(trades: pd.DataFrame) -> float:
    """
    Return-over-Drawdown Ratio - total return / max trade drawdown.

    Args:
        trades: Trades DataFrame

    Returns:
        Return / drawdown ratio
    """
    if len(trades) == 0:
        return 0.0

    total_return = trades["profit_loss"].sum()
    # Fix: max_trade_drawdown was renamed to max_close_to_close_drawdown
    max_dd = drawdowns.max_close_to_close_drawdown(trades)

    if max_dd == 0:
        return float("inf") if total_return > 0 else 0.0

    return float(total_return / max_dd)


def net_profit_as_percent_of_largest_loss(trades: pd.DataFrame) -> float:
    """
    Net Profit as % of Largest Loss.

    Formula: (Net Profit / Largest Loss) * 100

    Args:
        trades: Trades DataFrame

    Returns:
        Percentage (e.g. 500.0 for 500%)
    """
    if len(trades) == 0:
        return 0.0

    net_profit = returns.net_profit(trades)
    # Largest loss is usually returned as a negative number by metrics.largest_loss
    # We want magnitude (positive denominator)
    largest_loss_val = abs(metrics.largest_loss(trades))

    if largest_loss_val == 0:
        return float("inf") if net_profit > 0 else 0.0

    return float((net_profit / largest_loss_val) * 100.0)


def net_profit_as_percent_of_max_trade_drawdown(trades: pd.DataFrame) -> float:
    """
    Net Profit as % of Max Trade Drawdown.

    Formula: (Net Profit / Max Trade Drawdown) * 100
    Max Trade Drawdown = Max Close-to-Close Drawdown

    Args:
        trades: Trades DataFrame

    Returns:
        Percentage
    """
    if len(trades) == 0:
        return 0.0

    net_profit = returns.net_profit(trades)
    max_dd = drawdowns.max_close_to_close_drawdown(trades)

    if max_dd == 0:
        return float("inf") if net_profit > 0 else 0.0

    return float((net_profit / max_dd) * 100.0)


def net_profit_as_percent_of_max_strategy_drawdown(
    net_profit: float, max_strategy_drawdown: float
) -> float:
    """
    Net Profit as % of Max Strategy Drawdown.

    Formula: (Net Profit / Max Strategy Drawdown) * 100

    Args:
        net_profit: Net profit value
        max_strategy_drawdown: Maximum strategy drawdown (positive value)

    Returns:
        Percentage
    """
    if max_strategy_drawdown == 0:
        return float("inf") if net_profit > 0 else 0.0

    return float((net_profit / max_strategy_drawdown) * 100.0)


def select_net_profit_as_percent_of_largest_loss(trades: pd.DataFrame) -> float:
    """
    Select Net Profit as % of Largest Loss.

    Formula: (Select Net Profit / Largest Loss) * 100

    Args:
        trades: Trades DataFrame

    Returns:
        Percentage
    """
    if len(trades) == 0:
        return 0.0

    sel_net = returns.select_net_profit(trades)
    largest_loss_val = abs(metrics.largest_loss(trades))

    if largest_loss_val == 0:
        return float("inf") if sel_net > 0 else 0.0

    return float((sel_net / largest_loss_val) * 100.0)


def select_net_profit_as_percent_of_max_trade_drawdown(trades: pd.DataFrame) -> float:
    """
    Select Net Profit as % of Max Trade Drawdown.

    Formula: (Select Net Profit / Max Trade Drawdown) * 100

    Args:
        trades: Trades DataFrame

    Returns:
        Percentage
    """
    if len(trades) == 0:
        return 0.0

    sel_net = returns.select_net_profit(trades)
    max_dd = drawdowns.max_close_to_close_drawdown(trades)

    if max_dd == 0:
        return float("inf") if sel_net > 0 else 0.0

    return float((sel_net / max_dd) * 100.0)


def select_net_profit_as_percent_of_max_strategy_drawdown(
    select_net_profit: float, max_strategy_drawdown: float
) -> float:
    """
    Select Net Profit as % of Max Strategy Drawdown.

    Formula: (Select Net Profit / Max Strategy Drawdown) * 100

    Args:
        select_net_profit: Select Net Profit value
        max_strategy_drawdown: Max Strategy Drawdown (positive value)

    Returns:
        Percentage
    """
    if max_strategy_drawdown == 0:
        return float("inf") if select_net_profit > 0 else 0.0

    return float((select_net_profit / max_strategy_drawdown) * 100.0)


def adjusted_net_profit_as_percent_of_largest_loss(trades: pd.DataFrame) -> float:
    """
    Calculate adjusted net profit as % of largest loss.

    Formula: (Adjusted Net Profit / Largest Loss) * 100

    Args:
        trades: Trades DataFrame

    Returns:
        Percentage
    """
    if len(trades) == 0:
        return 0.0

    adj_net = returns.adjusted_net_profit(trades)
    largest_loss_val = abs(metrics.largest_loss(trades))

    if largest_loss_val == 0:
        return float("inf") if adj_net > 0 else 0.0

    return float((adj_net / largest_loss_val) * 100.0)


def adjusted_net_profit_as_percent_of_max_trade_drawdown(trades: pd.DataFrame) -> float:
    """
    Calculate adjusted net profit as % of max trade drawdown.

    Formula: (Adjusted Net Profit / Max Trade Drawdown) * 100

    Args:
        trades: Trades DataFrame

    Returns:
        Percentage
    """
    if len(trades) == 0:
        return 0.0

    adj_net = returns.adjusted_net_profit(trades)
    max_dd = drawdowns.max_close_to_close_drawdown(trades)

    if max_dd == 0:
        return float("inf") if adj_net > 0 else 0.0

    return float((adj_net / max_dd) * 100.0)


def adjusted_net_profit_as_percent_of_max_strategy_drawdown(
    adjusted_net_profit: float, max_strategy_drawdown: float
) -> float:
    """
    Calculate adjusted net profit as % of max strategy drawdown.

    Formula: (Adjusted Net Profit / Max Strategy Drawdown) * 100

    Args:
        adjusted_net_profit: Adjusted Net Profit value
        max_strategy_drawdown: Max Strategy Drawdown (positive value)

    Returns:
        Percentage
    """
    if max_strategy_drawdown == 0:
        return float("inf") if adjusted_net_profit > 0 else 0.0

    return float((adjusted_net_profit / max_strategy_drawdown) * 100.0)


def expectancy_over_variance(trades: pd.DataFrame) -> float:
    """
    Expectancy-over-Variance Ratio - stability of edge.

    Higher = more stable expectancy

    Args:
        trades: Trades DataFrame

    Returns:
        Expectancy / variance ratio
    """
    if len(trades) == 0:
        return 0.0

    expectancy_value = trades["profit_loss"].mean()
    variance = trades["profit_loss"].var()

    if variance == 0:
        return 0.0

    return float(expectancy_value / np.sqrt(variance))


# =========================================================================
# Expectancy & Edge
# =========================================================================


def expectancy(trades: pd.DataFrame) -> float:
    """
    Calculate expected value per trade.

    Formula: (Win% x Avg Win) + (Loss% x Avg Loss)
    """
    if not isinstance(trades, pd.DataFrame):
        return _expectancy_1d(trades)

    win_pct = metrics.win_rate(trades) / 100.0
    loss_pct = metrics.loss_rate(trades) / 100.0
    avg_win_val = metrics.avg_win(trades)
    avg_loss_val = metrics.avg_loss(trades)

    return (win_pct * avg_win_val) + (loss_pct * avg_loss_val)


def expectancy_r(trades: pd.DataFrame) -> float:
    """
    Calculate expectancy in R-multiples.

    Formula: (Win% x Avg R Win) + (Loss% x Avg R Loss)
    """
    if len(trades) == 0:
        return 0.0

    if "r_multiple" not in trades.columns:
        return 0.0

    win_pct = metrics.win_rate(trades) / 100.0
    loss_pct = metrics.loss_rate(trades) / 100.0

    winners = trades[trades["profit_loss"] > 0]
    losers = trades[trades["profit_loss"] < 0]

    avg_r_win = winners["r_multiple"].mean() if len(winners) > 0 else 0.0
    avg_r_loss = losers["r_multiple"].mean() if len(losers) > 0 else 0.0

    return (win_pct * avg_r_win) + (loss_pct * avg_r_loss)


def payoff_ratio(trades: pd.DataFrame | pd.Series | np.ndarray) -> float:
    """Measure payoff ratio: |Avg Win| / |Avg Loss|."""
    if not isinstance(trades, pd.DataFrame):
        avg_win_val, avg_loss_val = _avg_win_loss_1d(trades)
        if np.isnan(avg_loss_val) or avg_loss_val == 0:
            return 0.0 if np.isnan(avg_win_val) or avg_win_val == 0 else float("inf")
        return abs(avg_win_val / avg_loss_val)

    avg_win_val = metrics.avg_win(trades)
    avg_loss_val = abs(metrics.avg_loss(trades))

    if avg_loss_val == 0:
        return 0.0 if avg_win_val == 0 else float("inf")

    return avg_win_val / avg_loss_val


def profit_factor(trades: pd.DataFrame | pd.Series | np.ndarray) -> float:
    """Measure profit factor: Gross Profit / |Gross Loss|."""
    if not isinstance(trades, pd.DataFrame):
        normalized = _to_1d_float_array(trades)
        wins = normalized[normalized > 0].sum()
        gross_l = abs(normalized[normalized < 0].sum())
        if gross_l == 0:
            return 0.0 if wins == 0 else float("inf")
        return float(wins / gross_l)

    gross_p = returns.gross_profit(trades)
    gross_l = abs(returns.gross_loss(trades))

    if gross_l == 0:
        return 0.0 if gross_p == 0 else float("inf")

    return gross_p / gross_l


def edge_ratio(trades: pd.DataFrame) -> float:
    """
    Edge Ratio: (Avg Win / |Avg Loss|) x Win Rate.

    Combines payoff ratio with win rate
    """
    payoff = payoff_ratio(trades)
    win_pct = metrics.win_rate(trades) / 100.0

    return payoff * win_pct


def adjusted_profit_factor(trades: pd.DataFrame) -> float:
    """
    Calculate adjusted profit factor.

    Adjusted Gross Profit / |Adjusted Gross Loss|
    """
    gross_p = returns.adjusted_gross_profit(trades)
    gross_l = abs(returns.adjusted_gross_loss(trades))

    if gross_l == 0:
        return 0.0 if gross_p == 0 else float("inf")

    return gross_p / gross_l


def select_profit_factor(trades: pd.DataFrame) -> float:
    """
    Select Profit Factor.

    Select Gross Profit / |Select Gross Loss|
    """
    gross_p = returns.select_gross_profit(trades)
    gross_l = abs(returns.select_gross_loss(trades))

    if gross_l == 0:
        return 0.0 if gross_p == 0 else float("inf")

    return gross_p / gross_l


def sterling_ratio(cagr_value: float, avg_yearly_max_dd: float) -> float:
    """
    Sterling Ratio.

    User Definition:
    Return (numerator): Compound Annualized Rate of Return over last 3 years.
    Risk (denominator): Average Yearly Maximum Drawdown over last 3 years LESS an arbitrary 10%.
    Note: "Less 10%" usually implies modifying the risk denominator. If Drawdown is 20%,
    standard Sterling adds 10% safety buffer (risk=30%).
    OR it subtracts 10% (risk=10%)?
    Standard Definition: Return / |MaxDD + 10%| (Adding 10% to the drawwdown MAGNITUDE).
    Text says "less an arbitrary 10%". If DD is negative (-20%), less 10% might mean -30%? Abs(-30%) = 30%.
    Let's assume "Risk = Abs(Avg Yearly Max DD) + 10".

    Args:
        cagr_value: CAGR (percentage, e.g. 15.0)
        avg_yearly_max_dd: Average Yearly Max Drawdown (percentage, e.g. 20.0). Positive value.

    Returns:
        Sterling ratio value.
    """
    # Risk denominator
    # Assuming "less" means moving further down (more risk) or strict wording "Average ... Drawdown ... less 10%".
    # If Drawdown is a 'loss' (negative number), then "less 10%" makes it more negative (larger magnitude).
    # Since we pass in positive magnitude (e.g. 20.0 for 20%), we should ADD 10.0 to it to reflect "less 10%" in return space.
    # Risk = AvgDD + 10

    risk = avg_yearly_max_dd + 10.0

    if risk == 0:
        return 0.0 if cagr_value == 0 else float("inf")

    return float(cagr_value / risk)


def rina_index(
    select_net_profit: float, avg_drawdown: float, percent_time_in_market: float
) -> float:
    """
    RINA Index.

    User Definition:
    Select Net Profit / (Average Drawdown * Percent Time in Market)

    Args:
        select_net_profit: Net profit removing 3-sigma outliers.
        avg_drawdown: Average Drawdown (Trade Level, in Currency terms usually, or match numerator units).
                      If Numerator is currency, Denom should be currency * percent?
                      RINA is usually: Net Profit / (Avg Drawdown $ * %Time). Result is dimensionless-ish?
        percent_time_in_market: Percentage (0.0 - 100.0) or (0.0 - 1.0)?
                                Usually calculated using decimal?
                                If %Time is 50%, do we use 50 or 0.5?
                                TradeStation RINA: Net Profit / (Avg Drawdown * PercentTime/100)?
                                Or just PercentTime?
                                Let's assume standard decimal usage if "Percentage" text.
                                If Percent Time is 20%, use 0.2?
                                Users definitions often imply the labeled number.
                                Let's use 0-1 scale for time. (Percent / 100).

    Returns:
        RINA Index value.
    """
    if avg_drawdown == 0 or percent_time_in_market == 0:
        return 0.0

    # Convert percent to decimal?
    # If percent_time was passed as 50.0 (50%), use 0.5.
    # If passed as 0.5, use 0.5.
    # Check magnitude?
    time_factor = percent_time_in_market
    if time_factor > 1.0:  # Likely 0-100 scale
        time_factor = time_factor / 100.0

    denominator = avg_drawdown * time_factor

    if denominator == 0:
        return float("inf") if select_net_profit > 0 else 0.0

    return float(select_net_profit / denominator)
