"""
Summary:
-------
HaruQuant Risk-Adjusted Performance Ratios.
Reward vs volatility vs downside analysis.
This module implements institutional-grade risk-adjusted ratios (Sharpe, Sortino, Calmar), 
modern specialized indices (Omega, Kappa, Tail Ratio), and trade-based efficiency metrics.

Summary of Methods:
------------------
Volatility-Adjusted Ratios:
    - sharpe_ratio: Excess return per unit of total risk.
    - information_ratio: Active return per unit of active risk (Tracking Error).

Downside-Adjusted Ratios:
    - sortino_ratio: Excess return per unit of downside risk.
    - calmar_ratio: Annualized return per unit of max drawdown.
    - sterling_ratio: Return relative to average drawdown.
    - burke_ratio: Return relative to square root of squared drawdowns.

Threshold & Tail Ratios:
    - omega_ratio: Gain-to-loss ratio relative to a target return.
    - kappa_ratio (Kappa 1, 2, 3): Standardized downside risk measures.
    - tail_ratio: Ratio of right-tail (95th) to left-tail (5th) returns.
"""

import numpy as np
import pandas as pd

from . import common, drawdowns, returns
from .common import EPSILON, _to_1d_float_array


# =========================================================================
# Local Trade Helpers (to avoid circular dependency with metrics.py)
# =========================================================================


def _closed_pnl(trades: pd.DataFrame) -> pd.Series:
    """Helper to get realized P&L series from a trade frame."""
    data = common.get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns:
        return pd.Series(dtype=float)
    return data["profit_loss"].astype(float)


def _avg_win(trades: pd.DataFrame) -> float:
    """Mean profit of winning trades."""
    pnl = _closed_pnl(trades)
    wins = pnl[pnl > EPSILON]
    return float(wins.mean()) if not wins.empty else 0.0


def _avg_loss(trades: pd.DataFrame) -> float:
    """Mean loss of losing trades."""
    pnl = _closed_pnl(trades)
    losses = pnl[pnl < -EPSILON]
    return float(losses.mean()) if not losses.empty else 0.0


def _win_rate(trades: pd.DataFrame) -> float:
    """Win rate fraction (0-1)."""
    pnl = _closed_pnl(trades)
    if pnl.empty:
        return 0.0
    return float((pnl > EPSILON).mean())


def _loss_rate(trades: pd.DataFrame) -> float:
    """Loss rate fraction (0-1)."""
    pnl = _closed_pnl(trades)
    if pnl.empty:
        return 0.0
    return float((pnl < -EPSILON).mean())


def _largest_loss(trades: pd.DataFrame) -> float:
    """Maximum loss from a single trade."""
    pnl = _closed_pnl(trades)
    return float(pnl.min()) if not pnl.empty else 0.0


# =========================================================================
# Utility Helpers
# =========================================================================


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
    return float(np.mean(normalized > EPSILON))


def _avg_win_loss_1d(values) -> tuple[float, float]:
    """Calculate mean winning and losing outcomes from 1D numeric input."""
    normalized = _to_1d_float_array(values)
    wins = normalized[normalized > EPSILON]
    losses = normalized[normalized < -EPSILON]
    avg_win = float(np.mean(wins)) if len(wins) else float("nan")
    avg_loss = float(np.mean(losses)) if len(losses) else float("nan")
    return avg_win, avg_loss


# =========================================================================
# Classical Risk-Adjusted Ratios
# =========================================================================


def sharpe_ratio(
    returns_in: pd.Series | np.ndarray,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    annualize: bool = True,
) -> float:
    """
    Sharpe Ratio - excess return per unit of volatility.
    
    Uses simple periodic risk-free conversion: rf / periods_per_year.
    """
    normalized = _to_1d_float_array(returns_in)

    if len(normalized) < 2:
        return 0.0

    period_rf = risk_free_rate / periods_per_year
    excess_returns = normalized - period_rf

    std_excess = excess_returns.std(ddof=1)
    if std_excess == 0:
        return 0.0

    sharpe = excess_returns.mean() / std_excess

    if annualize:
        sharpe *= np.sqrt(periods_per_year)

    return float(sharpe)


def annualized_sharpe_ratio(
    monthly_returns: pd.Series, risk_free_rate_monthly: float = 0.0
) -> float:
    """
    Annualized Sharpe Ratio from monthly inputs.
    """
    normalized = _to_1d_float_array(monthly_returns)

    if len(normalized) < 2:
        return 0.0

    excess = normalized - risk_free_rate_monthly
    std = excess.std(ddof=1)

    if std == 0:
        return 0.0

    return float((excess.mean() / std) * np.sqrt(12))


def sortino_ratio(
    returns_in: pd.Series | np.ndarray,
    target_return: float = 0.0,
    periods_per_year: int = 252,
    annualize: bool = True,
) -> float:
    """
    Sortino Ratio - excess return per unit of downside volatility.
    
    Target return is handled as a per-period target (e.g. 0.0).
    """
    normalized = _to_1d_float_array(returns_in)

    if len(normalized) < 2:
        return 0.0

    excess_returns = normalized - target_return
    mean_excess = excess_returns.mean()

    # Downside risk calculated using the full-period denominator
    downside_diffs = np.minimum(normalized - target_return, 0.0)
    downside_risk = np.sqrt(np.mean(downside_diffs**2))

    if downside_risk == 0:
        return float("inf") if mean_excess > 0 else 0.0

    sortino = mean_excess / downside_risk

    if annualize:
        sortino *= np.sqrt(periods_per_year)

    return float(sortino)


def calmar_ratio(
    cagr_value: float | pd.Series | np.ndarray,
    max_dd: float | None = None,
    periods_per_year: int = 252,
) -> float:
    """
    Calmar Ratio = annualized return percentage / max drawdown percentage.
    """
    if max_dd is None and not np.isscalar(cagr_value):
        normalized = _to_1d_float_array(cagr_value)
        if len(normalized) < 2:
            return 0.0

        annual_return_pct = returns.annualized_return(
            pd.Series(normalized),
            periods_per_year=periods_per_year,
        )
        drawdown_pct = abs(drawdowns.max_drawdown(normalized)) * 100.0

        if drawdown_pct == 0:
            return float("inf") if annual_return_pct > 0 else 0.0

        return float(annual_return_pct / drawdown_pct)

    if max_dd is None:
        raise ValueError("max_dd is required when cagr_value is scalar")

    if max_dd == 0:
        return float("inf") if cagr_value > 0 else 0.0

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
    monthly_returns: pd.Series | np.ndarray,
    risk_tolerance: float,
    risk_free_rate_monthly: float = 0.0,
) -> float:
    """
    Fouse Ratio (Fouse DD Index). Formula: rc - rt * dd^2
    """
    normalized = _to_1d_float_array(monthly_returns)
    if len(normalized) == 0:
        return 0.0

    growth_factors = 1 + normalized
    rc = growth_factors.prod() ** (1 / len(normalized)) - 1

    target = risk_free_rate_monthly
    deviations = normalized - target
    downside_deviations = np.minimum(deviations, 0.0)
    dd = np.sqrt(np.mean(downside_deviations**2))

    fouse = rc - (risk_tolerance * (dd**2))
    return float(fouse)


def upside_potential_ratio(returns_in: pd.Series, target: float = 0.0) -> float:
    """
    Upside Potential Ratio - upside potential / downside risk.
    """
    normalized = _to_1d_float_array(returns_in)
    if len(normalized) < 2:
        return 0.0

    deviations = normalized - target
    
    # Downside Risk
    downside_diffs = np.minimum(deviations, 0.0)
    downside_risk = np.sqrt(np.mean(downside_diffs**2))

    # Upside Potential
    upside_potential = np.mean(np.maximum(deviations, 0.0))

    if downside_risk == 0:
        return float("inf") if upside_potential > 0 else 0.0

    return float(upside_potential / downside_risk)


def omega_ratio(returns_in: pd.Series, threshold: float = 0.0) -> float:
    """
    Omega Ratio - probability-weighted ratio of gains vs losses.
    """
    normalized = _to_1d_float_array(returns_in)
    if len(normalized) == 0:
        return 0.0

    gains = np.maximum(normalized - threshold, 0.0)
    losses = np.maximum(threshold - normalized, 0.0)

    sum_gains = np.sum(gains)
    sum_losses = np.sum(losses)

    if sum_losses == 0:
        return float("inf") if sum_gains > 0 else 1.0

    return float(sum_gains / sum_losses)


def gain_to_pain_ratio(returns_in: pd.Series) -> float:
    """
    Gain-to-Pain Ratio - sum of returns / sum of absolute negative returns.
    """
    normalized = _to_1d_float_array(returns_in)
    if len(normalized) == 0:
        return 0.0

    sum_returns = np.sum(normalized)
    sum_negative = np.abs(np.sum(normalized[normalized < 0]))

    if sum_negative == 0:
        return float("inf") if sum_returns > 0 else 0.0

    return float(sum_returns / sum_negative)


def kappa_ratio(returns_in: pd.Series | np.ndarray, target: float = 0.0, order: int = 3) -> float:
    """
    Kappa Ratio - generalization of Sortino using higher moments.
    """
    normalized = _to_1d_float_array(returns_in)
    if len(normalized) < 2:
        return 0.0

    mean_excess = np.mean(normalized - target)
    
    # Lower Partial Moment (LPM) calculation including all observations
    shortfall = np.maximum(target - normalized, 0.0)
    lpm = np.mean(shortfall ** order) ** (1.0 / order)
    
    if lpm == 0:
        return float("inf") if mean_excess > 0 else 0.0

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
        wins = normalized[normalized > EPSILON].sum()
        gross_l = np.abs(normalized[normalized < -EPSILON].sum())
        if gross_l == 0:
            return float("inf") if wins > EPSILON else 0.0
        return float(wins / gross_l)

    gross_p = returns.gross_profit(trades)
    gross_l = np.abs(returns.gross_loss(trades))

    if gross_l == 0:
        return float("inf") if gross_p > EPSILON else 0.0

    return float(gross_p / gross_l)


def payoff_ratio(trades: pd.DataFrame | pd.Series | np.ndarray) -> float:
    """Measure payoff ratio: |Avg Win| / |Avg Loss|."""
    if not isinstance(trades, pd.DataFrame):
        avg_win_val, avg_loss_val = _avg_win_loss_1d(trades)
        if np.isnan(avg_loss_val) or avg_loss_val == 0:
            return float("inf") if not np.isnan(avg_win_val) and avg_win_val != 0 else 0.0
        return float(np.abs(avg_win_val / avg_loss_val))

    avg_win_val = _avg_win(trades)
    avg_loss_val = np.abs(_avg_loss(trades))

    if avg_loss_val == 0:
        return float("inf") if avg_win_val > EPSILON else 0.0

    return float(avg_win_val / avg_loss_val)


def edge_ratio(trades: pd.DataFrame) -> float:
    """Edge Ratio: (Avg Win / |Avg Loss|) x Win Rate."""
    payoff = payoff_ratio(trades)
    win_pct = _win_rate(trades)
    return float(payoff * win_pct)


def profit_to_mae_ratio(trades: pd.DataFrame) -> float:
    """Profit-to-MAE Ratio - measures efficiency of profit capture."""
    if trades.empty or "profit_loss" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0

    data = common.get_closed_trades(trades)
    if data.empty:
        return 0.0

    pnl = data["profit_loss"].astype(float).values
    mae = np.abs(data["mae_usd"].astype(float).values)

    valid = mae > EPSILON
    if not valid.any():
        return 0.0

    return float((pnl[valid] / mae[valid]).mean())


def mfe_to_mae_ratio(trades: pd.DataFrame) -> float:
    """MFE-to-MAE Ratio - favorable excursion vs adverse excursion."""
    if trades.empty or "mfe_usd" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0

    data = common.get_closed_trades(trades)
    if data.empty:
        return 0.0

    mfe = np.maximum(data["mfe_usd"].astype(float).values, 0.0)
    mae = np.abs(data["mae_usd"].astype(float).values)

    valid = mae > EPSILON
    if not valid.any():
        return 0.0

    return float((mfe[valid] / mae[valid]).mean())


def return_over_drawdown(trades: pd.DataFrame) -> float:
    """Return-over-Drawdown Ratio - total return / max trade drawdown."""
    if trades.empty:
        return 0.0

    total_ret = returns.net_profit(trades)
    max_dd = drawdowns.max_close_to_close_drawdown(trades)

    if max_dd == 0:
        return float("inf") if total_ret > EPSILON else 0.0

    return float(total_ret / max_dd)


def expectancy_over_std(trades: pd.DataFrame) -> float:
    """Expectancy-over-Std Ratio - stability of edge (Expectancy / Standard Deviation)."""
    data = common.get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns:
        return 0.0

    pnl = data["profit_loss"].astype(float)
    expectancy_val = pnl.mean()
    std_dev = pnl.std()

    if std_dev == 0:
        return 0.0

    return float(expectancy_val / std_dev)


# =========================================================================
# Net Profit Performance Relations
# =========================================================================


def net_profit_as_percent_of_largest_loss(trades: pd.DataFrame) -> float:
    """(Net Profit / |Largest Loss|) * 100"""
    if trades.empty:
        return 0.0
    net_p = returns.net_profit(trades)
    largest_l = np.abs(_largest_loss(trades))
    if largest_l == 0:
        return float("inf") if net_p > EPSILON else 0.0
    return float((net_p / largest_l) * 100.0)


def net_profit_as_percent_of_max_trade_drawdown(trades: pd.DataFrame) -> float:
    """(Net Profit / Max Trade Drawdown) * 100"""
    if trades.empty:
        return 0.0
    net_p = returns.net_profit(trades)
    max_dd = drawdowns.max_close_to_close_drawdown(trades)
    if max_dd == 0:
        return float("inf") if net_p > EPSILON else 0.0
    return float((net_p / max_dd) * 100.0)


def net_profit_as_percent_of_max_strategy_drawdown(
    net_profit_val: float, max_strategy_drawdown: float
) -> float:
    """(Net Profit / Max Strategy Drawdown) * 100"""
    if max_strategy_drawdown == 0:
        return float("inf") if net_profit_val > EPSILON else 0.0
    return float((net_profit_val / max_strategy_drawdown) * 100.0)


def select_net_profit_as_percent_of_largest_loss(trades: pd.DataFrame) -> float:
    """(Select Net Profit / |Largest Loss|) * 100"""
    if trades.empty:
        return 0.0
    sel_net = returns.select_net_profit(trades)
    largest_l = np.abs(_largest_loss(trades))
    if largest_l == 0:
        return float("inf") if sel_net > EPSILON else 0.0
    return float((sel_net / largest_l) * 100.0)


def select_net_profit_as_percent_of_max_trade_drawdown(trades: pd.DataFrame) -> float:
    """(Select Net Profit / Max Trade Drawdown) * 100"""
    if trades.empty:
        return 0.0
    sel_net = returns.select_net_profit(trades)
    max_dd = drawdowns.max_close_to_close_drawdown(trades)
    if max_dd == 0:
        return float("inf") if sel_net > EPSILON else 0.0
    return float((sel_net / max_dd) * 100.0)


def select_net_profit_as_percent_of_max_strategy_drawdown(
    select_net_profit_val: float, max_strategy_drawdown: float
) -> float:
    """(Select Net Profit / Max Strategy Drawdown) * 100"""
    if max_strategy_drawdown == 0:
        return float("inf") if select_net_profit_val > EPSILON else 0.0
    return float((select_net_profit_val / max_strategy_drawdown) * 100.0)


def adjusted_net_profit_as_percent_of_largest_loss(trades: pd.DataFrame) -> float:
    """(Adjusted Net Profit / |Largest Loss|) * 100"""
    if trades.empty:
        return 0.0
    adj_net = returns.adjusted_net_profit(trades)
    largest_l = np.abs(_largest_loss(trades))
    if largest_l == 0:
        return float("inf") if adj_net > EPSILON else 0.0
    return float((adj_net / largest_l) * 100.0)


def adjusted_net_profit_as_percent_of_max_trade_drawdown(trades: pd.DataFrame) -> float:
    """(Adjusted Net Profit / Max Trade Drawdown) * 100"""
    if trades.empty:
        return 0.0
    adj_net = returns.adjusted_net_profit(trades)
    max_dd = drawdowns.max_close_to_close_drawdown(trades)
    if max_dd == 0:
        return float("inf") if adj_net > EPSILON else 0.0
    return float((adj_net / max_dd) * 100.0)


def adjusted_net_profit_as_percent_of_max_strategy_drawdown(
    adjusted_net_profit_val: float, max_strategy_drawdown: float
) -> float:
    """(Adjusted Net Profit / Max Strategy Drawdown) * 100"""
    if max_strategy_drawdown == 0:
        return float("inf") if adjusted_net_profit_val > EPSILON else 0.0
    return float((adjusted_net_profit_val / max_strategy_drawdown) * 100.0)


# =========================================================================
# Advanced Profit Factors
# =========================================================================


def adjusted_profit_factor(trades: pd.DataFrame) -> float:
    """Adjusted Gross Profit / |Adjusted Gross Loss|"""
    gross_p = returns.adjusted_gross_profit(trades)
    gross_l = np.abs(returns.adjusted_gross_loss(trades))
    if gross_l == 0:
        return float("inf") if gross_p > EPSILON else 0.0
    return float(gross_p / gross_l)


def select_profit_factor(trades: pd.DataFrame) -> float:
    """Select Gross Profit / |Select Gross Loss|"""
    gross_p = returns.select_gross_profit(trades)
    gross_l = np.abs(returns.select_gross_loss(trades))
    if gross_l == 0:
        return float("inf") if gross_p > EPSILON else 0.0
    return float(gross_p / gross_l)


# =========================================================================
# Expectancy & Edge
# =========================================================================


def expectancy(trades: pd.DataFrame | pd.Series | np.ndarray) -> float:
    """(Win% x Avg Win) + (Loss% x Avg Loss)"""
    if not isinstance(trades, pd.DataFrame):
        return _expectancy_1d(trades)

    win_pct = _win_rate(trades)
    loss_pct = _loss_rate(trades)
    avg_win_val = _avg_win(trades)
    avg_loss_val = _avg_loss(trades)

    return float((win_pct * avg_win_val) + (loss_pct * avg_loss_val))


def expectancy_r(r_multiples: pd.Series | np.ndarray) -> float:
    """Average R-multiple value."""
    r = _to_1d_float_array(r_multiples)
    if len(r) == 0:
        return 0.0
    return float(np.mean(r))
