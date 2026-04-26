"""
Risk-adjusted performance ratios.

Focus: reward vs volatility vs downside

This module provides various metrics to evaluate strategy performance relative to risk.
It includes classical ratios (Sharpe, Sortino, Calmar), modern specialized ratios (Omega, Kappa, RINA),
and trade-based performance relations.

Summary of Methods:
------------------
Utility Helpers:
    - win_rate_fraction: Win rate on a 0-1 scale.

Classical Risk-Adjusted Ratios:
    - sharpe_ratio: Excess return per unit of volatility.
    - annualized_sharpe_ratio: Sharpe ratio scaled to yearly terms.
    - sortino_ratio: Excess return per unit of downside volatility.
    - calmar_ratio: CAGR divided by maximum drawdown.
    - information_ratio: Excess return per unit of tracking error.

Modern & Specialized Ratios:
    - fouse_ratio: Risk-adjusted return considering risk tolerance.
    - upside_potential_ratio: Upside potential relative to downside risk.
    - omega_ratio: Probability-weighted ratio of gains vs losses.
    - gain_to_pain_ratio: Total returns relative to absolute negative returns.
    - kappa_ratio: Generalization of Sortino using higher moments.
    - sterling_ratio: CAGR relative to average yearly max drawdown.
    - rina_index: Select net profit relative to time-adjusted drawdown.

Trade-Based Performance Ratios:
    - profit_factor: Gross Profit / |Gross Loss|.
    - payoff_ratio: |Avg Win| / |Avg Loss|.
    - edge_ratio: (Avg Win / |Avg Loss|) x Win Rate.
    - profit_to_mae_ratio: Efficiency of profit capture relative to adverse excursion.
    - mfe_to_mae_ratio: Favorable excursion vs adverse excursion.
    - return_over_drawdown: Total return / max trade drawdown.
    - expectancy_over_variance: Stability of the trading edge.

Net Profit Performance Relations:
    - net_profit_as_percent_of_largest_loss
    - net_profit_as_percent_of_max_trade_drawdown
    - net_profit_as_percent_of_max_strategy_drawdown
    - select_net_profit_as_percent_of_largest_loss
    - select_net_profit_as_percent_of_max_trade_drawdown
    - select_net_profit_as_percent_of_max_strategy_drawdown
    - adjusted_net_profit_as_percent_of_largest_loss
    - adjusted_net_profit_as_percent_of_max_trade_drawdown
    - adjusted_net_profit_as_percent_of_max_strategy_drawdown

Advanced Profit Factors:
    - adjusted_profit_factor: Adjusted Gross Profit / |Adjusted Gross Loss|.
    - select_profit_factor: Select Gross Profit / |Select Gross Loss|.

Expectancy & Edge:
    - expectancy: Expected value per trade.
    - expectancy_r: Expectancy in terms of R-multiples.
"""

import numpy as np
import pandas as pd

from . import drawdowns, metrics, returns


# =========================================================================
# Utility Helpers
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
# Classical Risk-Adjusted Ratios
# =========================================================================


def sharpe_ratio(
    returns_in: pd.Series | np.ndarray, risk_free_rate: float = 0.0, annualize: bool = True
) -> float:
    """
    Sharpe Ratio - excess return per unit of volatility.
    """
    normalized = _to_1d_float_array(returns_in)

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
    Annualized Sharpe Ratio from monthly inputs.
    """
    monthly_sharpe = sharpe_ratio(
        monthly_returns, risk_free_rate_monthly, annualize=False
    )
    return float(monthly_sharpe * np.sqrt(12))


def sortino_ratio(
    returns_in: pd.Series | np.ndarray, target_return: float = 0.0, annualize: bool = True
) -> float:
    """
    Sortino Ratio - excess return per unit of downside volatility.
    """
    normalized = _to_1d_float_array(returns_in)

    if len(normalized) < 2:
        return 0.0

    excess_returns = normalized - target_return
    mean_excess = excess_returns.mean()

    # Lower Partial Moment (LPM) order 2 for downside risk
    deviations = normalized - target_return
    downside_deviations = deviations[deviations < 0]

    sum_sq_diff = (downside_deviations**2).sum()
    n = len(normalized)
    downside_risk = np.sqrt(sum_sq_diff / n)

    if downside_risk == 0:
        return float("inf") if mean_excess > 0 else 0.0

    sortino = mean_excess / downside_risk

    if annualize:
        sortino = sortino * np.sqrt(12)

    return float(sortino)


def calmar_ratio(
    cagr_value: float | pd.Series | np.ndarray,
    max_dd: float | None = None,
    periods_per_year: int = 252,
) -> float:
    """
    Calmar Ratio - CAGR divided by maximum drawdown.
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
    returns_in: pd.Series,
    benchmark_returns: pd.Series,
    annualize: bool = True,
    periods_per_year: int = 252,
) -> float:
    """
    Information Ratio - excess return per unit of tracking error.
    """
    if len(returns_in) < 2 or len(benchmark_returns) < 2:
        return 0.0

    aligned_returns = pd.DataFrame(
        {"strategy": returns_in, "benchmark": benchmark_returns}
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
        ir = ir * np.sqrt(periods_per_year)

    return float(ir)


# =========================================================================
# Modern & Specialized Ratios
# =========================================================================


def fouse_ratio(
    monthly_returns: pd.Series,
    risk_tolerance: float,
    risk_free_rate_monthly: float = 0.0,
) -> float:
    """
    Fouse Ratio (Fouse DD Index). Formula: rc - rt * dd^2
    """
    if len(monthly_returns) == 0:
        return 0.0

    growth_factors = 1 + monthly_returns
    rc = growth_factors.prod() ** (1 / len(monthly_returns)) - 1

    target = risk_free_rate_monthly
    deviations = monthly_returns - target
    downside_deviations = deviations[deviations < 0]
    sum_sq_diff = (downside_deviations**2).sum()
    n = len(monthly_returns)
    dd = np.sqrt(sum_sq_diff / n)

    fouse = rc - (risk_tolerance * (dd**2))
    return float(fouse)


def upside_potential_ratio(returns_in: pd.Series, target: float = 0.0) -> float:
    """
    Upside Potential Ratio - upside potential / downside risk.
    """
    if len(returns_in) < 2:
        return 0.0

    deviations = returns_in - target
    downside_deviations = deviations[deviations < 0]
    sum_sq_diff_down = (downside_deviations**2).sum()
    n = len(returns_in)
    downside_risk = np.sqrt(sum_sq_diff_down / n)

    upside_deviations = deviations[deviations > 0]
    sum_diff_up = upside_deviations.sum()
    upside_potential = sum_diff_up / n

    if downside_risk == 0:
        return float("inf") if upside_potential > 0 else 0.0

    return float(upside_potential / downside_risk)


def omega_ratio(returns_in: pd.Series, threshold: float = 0.0) -> float:
    """
    Omega Ratio - probability-weighted ratio of gains vs losses.
    """
    if len(returns_in) == 0:
        return 0.0

    gains = returns_in[returns_in > threshold] - threshold
    losses = threshold - returns_in[returns_in < threshold]

    sum_gains = gains.sum()
    sum_losses = losses.sum()

    if sum_losses == 0:
        return float("inf") if sum_gains > 0 else 1.0

    return float(sum_gains / sum_losses)


def gain_to_pain_ratio(returns_in: pd.Series) -> float:
    """
    Gain-to-Pain Ratio - sum of returns / sum of absolute negative returns.
    """
    if len(returns_in) == 0:
        return 0.0

    sum_returns = returns_in.sum()
    sum_negative = abs(returns_in[returns_in < 0].sum())

    if sum_negative == 0:
        return float("inf") if sum_returns > 0 else 0.0

    return float(sum_returns / sum_negative)


def kappa_ratio(returns_in: pd.Series, target: float = 0.0, order: int = 3) -> float:
    """
    Kappa Ratio - generalization of Sortino using higher moments.
    """
    if len(returns_in) < 2:
        return 0.0

    excess_returns = returns_in - target
    mean_excess = excess_returns.mean()
    downside_returns = excess_returns[excess_returns < 0]

    if len(downside_returns) == 0:
        return float("inf") if mean_excess > 0 else 0.0

    lpm = (abs(downside_returns) ** order).mean() ** (1 / order)
    if lpm == 0:
        return 0.0

    return float(mean_excess / lpm)


def sterling_ratio(cagr_value: float, avg_yearly_max_dd: float) -> float:
    """
    Sterling Ratio. Formula: CAGR / (AvgYearlyMaxDD + 10%)
    """
    risk = avg_yearly_max_dd + 10.0
    if risk == 0:
        return 0.0 if cagr_value == 0 else float("inf")
    return float(cagr_value / risk)


def rina_index(
    select_net_profit: float, avg_drawdown: float, percent_time_in_market: float
) -> float:
    """
    RINA Index: Select Net Profit / (Average Drawdown * Percent Time in Market)
    """
    if avg_drawdown == 0 or percent_time_in_market == 0:
        return 0.0

    time_factor = percent_time_in_market
    if time_factor > 1.0:
        time_factor = time_factor / 100.0

    denominator = avg_drawdown * time_factor
    if denominator == 0:
        return float("inf") if select_net_profit > 0 else 0.0

    return float(select_net_profit / denominator)


# =========================================================================
# Trade-Based Performance Ratios
# =========================================================================


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


def edge_ratio(trades: pd.DataFrame) -> float:
    """Edge Ratio: (Avg Win / |Avg Loss|) x Win Rate."""
    payoff = payoff_ratio(trades)
    win_pct = metrics.win_rate(trades) / 100.0
    return payoff * win_pct


def profit_to_mae_ratio(trades: pd.DataFrame) -> float:
    """Profit-to-MAE Ratio - measures efficiency of profit capture."""
    if len(trades) == 0 or "profit_loss" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0

    valid_trades = trades[trades["mae_usd"] > 0]
    if len(valid_trades) == 0:
        return 0.0

    ratio = valid_trades["profit_loss"] / valid_trades["mae_usd"]
    return float(ratio.mean())


def mfe_to_mae_ratio(trades: pd.DataFrame) -> float:
    """MFE-to-MAE Ratio - favorable excursion vs adverse excursion."""
    if len(trades) == 0 or "mfe_usd" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0

    valid_trades = trades[trades["mae_usd"] > 0]
    if len(valid_trades) == 0:
        return 0.0

    ratio = valid_trades["mfe_usd"] / valid_trades["mae_usd"]
    return float(ratio.mean())


def return_over_drawdown(trades: pd.DataFrame) -> float:
    """Return-over-Drawdown Ratio - total return / max trade drawdown."""
    if len(trades) == 0:
        return 0.0

    total_ret = trades["profit_loss"].sum()
    max_dd = drawdowns.max_close_to_close_drawdown(trades)

    if max_dd == 0:
        return float("inf") if total_ret > 0 else 0.0

    return float(total_ret / max_dd)


def expectancy_over_variance(trades: pd.DataFrame) -> float:
    """Expectancy-over-Variance Ratio - stability of edge."""
    if len(trades) == 0:
        return 0.0

    expectancy_val = trades["profit_loss"].mean()
    variance = trades["profit_loss"].var()

    if variance == 0:
        return 0.0

    return float(expectancy_val / np.sqrt(variance))


# =========================================================================
# Net Profit Performance Relations
# =========================================================================


def net_profit_as_percent_of_largest_loss(trades: pd.DataFrame) -> float:
    """(Net Profit / |Largest Loss|) * 100"""
    if len(trades) == 0:
        return 0.0
    net_p = returns.net_profit(trades)
    largest_l = abs(metrics.largest_loss(trades))
    if largest_l == 0:
        return float("inf") if net_p > 0 else 0.0
    return float((net_p / largest_l) * 100.0)


def net_profit_as_percent_of_max_trade_drawdown(trades: pd.DataFrame) -> float:
    """(Net Profit / Max Trade Drawdown) * 100"""
    if len(trades) == 0:
        return 0.0
    net_p = returns.net_profit(trades)
    max_dd = drawdowns.max_close_to_close_drawdown(trades)
    if max_dd == 0:
        return float("inf") if net_p > 0 else 0.0
    return float((net_p / max_dd) * 100.0)


def net_profit_as_percent_of_max_strategy_drawdown(
    net_profit_val: float, max_strategy_drawdown: float
) -> float:
    """(Net Profit / Max Strategy Drawdown) * 100"""
    if max_strategy_drawdown == 0:
        return float("inf") if net_profit_val > 0 else 0.0
    return float((net_profit_val / max_strategy_drawdown) * 100.0)


def select_net_profit_as_percent_of_largest_loss(trades: pd.DataFrame) -> float:
    """(Select Net Profit / |Largest Loss|) * 100"""
    if len(trades) == 0:
        return 0.0
    sel_net = returns.select_net_profit(trades)
    largest_l = abs(metrics.largest_loss(trades))
    if largest_l == 0:
        return float("inf") if sel_net > 0 else 0.0
    return float((sel_net / largest_l) * 100.0)


def select_net_profit_as_percent_of_max_trade_drawdown(trades: pd.DataFrame) -> float:
    """(Select Net Profit / Max Trade Drawdown) * 100"""
    if len(trades) == 0:
        return 0.0
    sel_net = returns.select_net_profit(trades)
    max_dd = drawdowns.max_close_to_close_drawdown(trades)
    if max_dd == 0:
        return float("inf") if sel_net > 0 else 0.0
    return float((sel_net / max_dd) * 100.0)


def select_net_profit_as_percent_of_max_strategy_drawdown(
    select_net_profit_val: float, max_strategy_drawdown: float
) -> float:
    """(Select Net Profit / Max Strategy Drawdown) * 100"""
    if max_strategy_drawdown == 0:
        return float("inf") if select_net_profit_val > 0 else 0.0
    return float((select_net_profit_val / max_strategy_drawdown) * 100.0)


def adjusted_net_profit_as_percent_of_largest_loss(trades: pd.DataFrame) -> float:
    """(Adjusted Net Profit / |Largest Loss|) * 100"""
    if len(trades) == 0:
        return 0.0
    adj_net = returns.adjusted_net_profit(trades)
    largest_l = abs(metrics.largest_loss(trades))
    if largest_l == 0:
        return float("inf") if adj_net > 0 else 0.0
    return float((adj_net / largest_l) * 100.0)


def adjusted_net_profit_as_percent_of_max_trade_drawdown(trades: pd.DataFrame) -> float:
    """(Adjusted Net Profit / Max Trade Drawdown) * 100"""
    if len(trades) == 0:
        return 0.0
    adj_net = returns.adjusted_net_profit(trades)
    max_dd = drawdowns.max_close_to_close_drawdown(trades)
    if max_dd == 0:
        return float("inf") if adj_net > 0 else 0.0
    return float((adj_net / max_dd) * 100.0)


def adjusted_net_profit_as_percent_of_max_strategy_drawdown(
    adjusted_net_profit_val: float, max_strategy_drawdown: float
) -> float:
    """(Adjusted Net Profit / Max Strategy Drawdown) * 100"""
    if max_strategy_drawdown == 0:
        return float("inf") if adjusted_net_profit_val > 0 else 0.0
    return float((adjusted_net_profit_val / max_strategy_drawdown) * 100.0)


# =========================================================================
# Advanced Profit Factors
# =========================================================================


def adjusted_profit_factor(trades: pd.DataFrame) -> float:
    """Adjusted Gross Profit / |Adjusted Gross Loss|"""
    gross_p = returns.adjusted_gross_profit(trades)
    gross_l = abs(returns.adjusted_gross_loss(trades))
    if gross_l == 0:
        return 0.0 if gross_p == 0 else float("inf")
    return gross_p / gross_l


def select_profit_factor(trades: pd.DataFrame) -> float:
    """Select Gross Profit / |Select Gross Loss|"""
    gross_p = returns.select_gross_profit(trades)
    gross_l = abs(returns.select_gross_loss(trades))
    if gross_l == 0:
        return 0.0 if gross_p == 0 else float("inf")
    return gross_p / gross_l


# =========================================================================
# Expectancy & Edge
# =========================================================================


def expectancy(trades: pd.DataFrame) -> float:
    """(Win% x Avg Win) + (Loss% x Avg Loss)"""
    if not isinstance(trades, pd.DataFrame):
        return _expectancy_1d(trades)

    win_pct = metrics.win_rate(trades) / 100.0
    loss_pct = metrics.loss_rate(trades) / 100.0
    avg_win_val = metrics.avg_win(trades)
    avg_loss_val = metrics.avg_loss(trades)

    return (win_pct * avg_win_val) + (loss_pct * avg_loss_val)


def expectancy_r(trades: pd.DataFrame) -> float:
    """(Win% x Avg R Win) + (Loss% x Avg R Loss)"""
    if len(trades) == 0 or "r_multiple" not in trades.columns:
        return 0.0

    win_pct = metrics.win_rate(trades) / 100.0
    loss_pct = metrics.loss_rate(trades) / 100.0

    winners = trades[trades["profit_loss"] > 0]
    losers = trades[trades["profit_loss"] < 0]

    avg_r_win = winners["r_multiple"].mean() if len(winners) > 0 else 0.0
    avg_r_loss = losers["r_multiple"].mean() if len(losers) > 0 else 0.0

    return (win_pct * avg_r_win) + (loss_pct * avg_r_loss)
