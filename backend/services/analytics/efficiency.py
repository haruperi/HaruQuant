"""
Capital and time efficiency metrics.

Focus: how effectively the strategy converts resources (capital, time, risk) into returns.

This module provides metrics to evaluate the "yield" of a strategy relative to various constraints.
It includes capital deployment efficiency, time-based returns (per hour, per day), 
and execution capture metrics (MFE/MAE efficiency).

Summary of Methods:
------------------
Capital Efficiency:
    - capital_efficiency: Return per unit of capital deployed.
    - return_per_unit_risk: Return relative to absolute adverse excursion (MAE).
    - risk_adjusted_efficiency: Return relative to defined initial risk.

Time & Frequency Efficiency:
    - time_efficiency: Return per hour spent in active trades.
    - return_per_unit_time: Return per hour of total calendar time.
    - trades_per_day: Average trading frequency.
    - return_per_trade_opportunity: Return per calendar day.
    - return_per_trade: Average arithmetic mean P&L per closed trade.

Execution & Capturing Efficiency:
    - mfe_efficiency: Percentage of maximum favorable excursion captured as profit.
    - mae_efficiency: Ratio of actual loss to maximum adverse excursion.
    - exit_efficiency: Combined measure of capturing wins and containing losses.
    - win_efficiency: Aggregate percentage of potential profit captured across all winners.
    - loss_containment_efficiency: Measure of how well realized losses stayed above the absolute valley.

Sizing Efficiency:
    - position_size_efficiency: Correlation between position size and trade outcome.
"""

from typing import Optional

import pandas as pd


# =========================================================================
# Capital Efficiency
# =========================================================================


def capital_efficiency(trades: pd.DataFrame) -> float:
    """Return per unit of capital deployed (estimated position value)."""
    if len(trades) == 0 or "profit_loss" not in trades.columns or "size" not in trades.columns:
        return 0.0
    total_ret = trades["profit_loss"].sum()
    avg_pos_val = trades["size"].mean() * 100000
    return float(total_ret / avg_pos_val) if avg_pos_val != 0 else 0.0


def return_per_unit_risk(trades: pd.DataFrame) -> float:
    """Return per unit of adverse movement (MAE)."""
    if len(trades) == 0 or "profit_loss" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0
    total_mae = trades["mae_usd"].sum()
    return float(trades["profit_loss"].sum() / total_mae) if total_mae != 0 else 0.0


def risk_adjusted_efficiency(trades: pd.DataFrame) -> float:
    """Return per unit of initial risk defined at entry."""
    if len(trades) == 0 or "profit_loss" not in trades.columns or "initial_risk_usd" not in trades.columns:
        return 0.0
    valid = trades[trades["initial_risk_usd"] > 0]
    total_risk = valid["initial_risk_usd"].sum()
    return float(valid["profit_loss"].sum() / total_risk) if total_risk != 0 else 0.0


# =========================================================================
# Time & Frequency Efficiency
# =========================================================================


def time_efficiency(trades: pd.DataFrame) -> float:
    """Return per hour spent actively in market."""
    if len(trades) == 0 or "profit_loss" not in trades.columns or "time_in_trade" not in trades.columns:
        return 0.0
    total_time = trades["time_in_trade"].sum()
    return float(trades["profit_loss"].sum() / total_time) if total_time != 0 else 0.0


def return_per_unit_time(trades: pd.DataFrame, total_time_hours: Optional[float] = None) -> float:
    """Return per hour of total calendar time (start to end)."""
    if len(trades) == 0 or "profit_loss" not in trades.columns:
        return 0.0
    if total_time_hours is None:
        if "open_time" not in trades.columns or "close_time" not in trades.columns:
            return 0.0
        total_time_hours = (trades["close_time"].max() - trades["open_time"].min()).total_seconds() / 3600
    if total_time_hours == 0: return 0.0
    return float(trades["profit_loss"].sum() / total_time_hours)


def trades_per_day(trades: pd.DataFrame) -> float:
    """Average number of trade executions per calendar day."""
    if len(trades) == 0 or "open_time" not in trades.columns or "close_time" not in trades.columns:
        return 0.0
    total_days = (trades["close_time"].max() - trades["open_time"].min()).total_seconds() / 86400
    return float(len(trades) / total_days) if total_days != 0 else 0.0


def return_per_trade_opportunity(trades: pd.DataFrame, total_days: Optional[float] = None) -> float:
    """Return per calendar day from start to end."""
    if len(trades) == 0 or "profit_loss" not in trades.columns:
        return 0.0
    if total_days is None:
        if "open_time" not in trades.columns or "close_time" not in trades.columns:
            return 0.0
        total_days = (trades["close_time"].max() - trades["open_time"].min()).total_seconds() / 86400
    return float(trades["profit_loss"].sum() / total_days) if total_days != 0 else 0.0


def return_per_trade(trades: pd.DataFrame) -> float:
    """Average arithmetic mean profit per closed trade."""
    if len(trades) == 0 or "profit_loss" not in trades.columns:
        return 0.0
    return float(trades["profit_loss"].mean())


# =========================================================================
# Execution & Capturing Efficiency
# =========================================================================


def mfe_efficiency(trades: pd.DataFrame) -> float:
    """Mean ratio of realized profit to maximum favorable excursion (winners)."""
    if len(trades) == 0 or "profit_loss" not in trades.columns or "mfe_usd" not in trades.columns:
        return 0.0
    winners = trades[(trades["profit_loss"] > 0) & (trades["mfe_usd"] > 0)]
    return float((winners["profit_loss"] / winners["mfe_usd"]).mean()) if len(winners) > 0 else 0.0


def mae_efficiency(trades: pd.DataFrame) -> float:
    """Mean ratio of realized loss to maximum adverse excursion (losers)."""
    if len(trades) == 0 or "profit_loss" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0
    losers = trades[(trades["profit_loss"] < 0) & (trades["mae_usd"] > 0)]
    return float((abs(losers["profit_loss"]) / losers["mae_usd"]).mean()) if len(losers) > 0 else 0.0


def exit_efficiency(trades: pd.DataFrame) -> float:
    """Combined capture efficiency across both winners and losers."""
    mfe_eff = mfe_efficiency(trades)
    mae_eff = mae_efficiency(trades)
    mae_inv = 1.0 - mae_eff if mae_eff > 0 else 0.0
    return float((mfe_eff + mae_inv) / 2)


def win_efficiency(trades: pd.DataFrame) -> float:
    """Aggregate percentage of cumulative MFE captured as profit."""
    if len(trades) == 0 or "profit_loss" not in trades.columns or "mfe_usd" not in trades.columns:
        return 0.0
    winners = trades[trades["profit_loss"] > 0]
    pot_p = winners["mfe_usd"].sum()
    return float((winners["profit_loss"].sum() / pot_p) * 100) if pot_p != 0 else 0.0


def loss_containment_efficiency(trades: pd.DataFrame) -> float:
    """Measure of how well realized losses were contained above the valley (MAE)."""
    if len(trades) == 0 or "profit_loss" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0
    losers = trades[trades["profit_loss"] < 0]
    if len(losers) == 0: return 100.0
    pot_l = losers["mae_usd"].sum()
    if pot_l == 0: return 100.0
    containment = (1 - (abs(losers["profit_loss"].sum()) / pot_l)) * 100
    return float(max(0.0, containment))


# =========================================================================
# Sizing Efficiency
# =========================================================================


def position_size_efficiency(trades: pd.DataFrame) -> float:
    """Correlation between trade position size and trade profit outcome."""
    if len(trades) < 2 or "size" not in trades.columns or "profit_loss" not in trades.columns:
        return 0.0
    corr = trades["size"].corr(trades["profit_loss"])
    return float(corr) if not pd.isna(corr) else 0.0
