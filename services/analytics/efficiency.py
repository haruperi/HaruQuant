"""
Summary:
-------
HaruQuant Efficiency & Resource Analytics.
Analysis of how effectively a strategy converts capital, time, and risk into returns.
This module provides institutional-grade metrics for capital deployment efficiency, 
time-weighted returns, and execution capture (MFE/MAE efficiency).

Summary of Methods:
------------------
Capital & Risk Efficiency:
    - avg_trade_notional_efficiency: Return per unit of capital deployed per trade.
    - return_per_r_risk: Net profit divided by total R-multiple risk.
    - risk_adjusted_efficiency: Profit relative to absolute adverse excursion (MAE).

Time & Frequency Efficiency:
    - time_efficiency: Return per hour of market exposure.
    - return_per_unit_time: Annualized return per unit of calendar time.
    - profit_per_day: Average dollar profit per calendar day.
    - return_per_trade: Mean P&L percentage per trade.

Execution Capture Efficiency:
    - mfe_efficiency: Percentage of peak profit (MFE) realized at close.
    - mae_efficiency: Ability to recover from adverse movement (MAE).
    - profit_per_pip_risk: Reward-to-risk based on price movement.
    - mae_efficiency: Ratio of actual loss to maximum adverse excursion.
    - exit_efficiency: Combined measure of capturing wins and containing losses.
    - win_efficiency: Aggregate percentage of potential profit captured across all winners.
    - loss_containment_efficiency: Measure of how well realized losses stayed above the absolute valley.

Sizing Efficiency:
    - position_size_efficiency: Correlation between position size and trade outcome.
"""

from typing import Optional
import numpy as np
import pandas as pd

from . import common
from .common import (
    EPSILON, get_closed_trades, get_r_multiples, 
    time_in_market_duration, percent_time_in_market
)


# =========================================================================
# Capital Efficiency Metrics
# =========================================================================


def capital_efficiency(
    trades: pd.DataFrame,
    contract_size: float = 100000.0,
) -> float:
    """
    Return per unit of nominal capital deployed (Average Trade Notional Efficiency).
    
    Formula: Total Net Profit / Average Absolute Notional Exposure.
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns or "size" not in data.columns:
        return 0.0

    total_profit = data["profit_loss"].sum()
    # Use absolute size to handle short positions correctly
    avg_nominal = data["size"].abs().mean() * contract_size

    if avg_nominal < EPSILON:
        return 0.0

    return float(total_profit / avg_nominal)


def avg_trade_notional_efficiency(
    trades: pd.DataFrame,
    contract_size: float = 100000.0,
) -> float:
    """Alias for capital_efficiency; clearer semantic name."""
    return capital_efficiency(trades, contract_size)


def return_per_unit_mae(trades: pd.DataFrame) -> float:
    """
    Total return relative to absolute adverse excursion (MAE) experienced.
    
    Formula: Net Profit / Sum(|MAE_USD|).
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns or "mae_usd" not in data.columns:
        return 0.0

    total_profit = data["profit_loss"].sum()
    total_mae = data["mae_usd"].abs().sum()

    if total_mae < EPSILON:
        return float("inf") if total_profit > EPSILON else 0.0

    return float(total_profit / total_mae)


def risk_adjusted_efficiency(trades: pd.DataFrame) -> float:
    """
    Return relative to total defined initial risk (R).
    
    Formula: Net Profit / Sum(|Initial Risk Amount|).
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns:
        return 0.0

    # Support multiple risk column names
    risk_col = next(
        (col for col in ["initial_risk_amount", "initial_risk", "initial_risk_usd"] if col in data.columns),
        None,
    )
    
    if not risk_col:
        return 0.0

    total_profit = data["profit_loss"].sum()
    total_risk = data[risk_col].abs().sum()

    if total_risk < EPSILON:
        return float("inf") if total_profit > EPSILON else 0.0

    return float(total_profit / total_risk)


def avg_return_per_risk_unit(trades: pd.DataFrame) -> float:
    """
    Average R-multiple per closed trade.
    Equivalent to average normalized return per unit risk.
    """
    r = get_r_multiples(trades)
    if r.empty:
        return 0.0
    return float(r.mean())


# =========================================================================
# Time & Frequency Efficiency
# =========================================================================


def return_per_trade_hour(trades: pd.DataFrame) -> float:
    """
    Net Profit per hour spent in active trades (sum of all trade-hours).
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns or "time_in_trade" not in data.columns:
        return 0.0

    total_profit = data["profit_loss"].sum()
    total_trade_hours = data["time_in_trade"].sum()

    if total_trade_hours == 0:
        return 0.0

    return float(total_profit / total_trade_hours)


def return_per_market_hour(
    trades: pd.DataFrame, 
    end_time: Optional[pd.Timestamp] = None
) -> float:
    """
    Net Profit per hour where at least one trade was open (merged market time).
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns:
        return 0.0

    total_profit = data["profit_loss"].sum()
    market_time = time_in_market_duration(data, end_time)
    market_hours = market_time.total_seconds() / 3600.0

    if market_hours == 0:
        return 0.0

    return float(total_profit / market_hours)


def trades_per_day(
    trades: pd.DataFrame,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> float:
    """
    Average number of closed trades per calendar day in the test period.
    """
    data = get_closed_trades(trades)
    if data.empty or "open_time" not in data.columns or "close_time" not in data.columns:
        return 0.0

    # Ensure clean timestamps
    open_times = pd.to_datetime(data["open_time"])
    close_times = pd.to_datetime(data["close_time"])

    t_start = start_time if start_time else open_times.min()
    t_end = end_time if end_time else close_times.max()

    if pd.isna(t_start) or pd.isna(t_end) or t_end <= t_start:
        return 0.0

    total_days = (t_end - t_start).total_seconds() / 86400.0
    return float(len(data) / total_days) if total_days > 0 else 0.0


def return_per_calendar_day(
    trades: pd.DataFrame,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> float:
    """
    Net Profit per calendar day in the test period.
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns:
        return 0.0
    if "open_time" not in data.columns or "close_time" not in data.columns:
        return 0.0

    total_profit = data["profit_loss"].sum()
    
    # Ensure clean timestamps
    open_times = pd.to_datetime(data["open_time"])
    close_times = pd.to_datetime(data["close_time"])

    t_start = start_time if start_time else open_times.min()
    t_end = end_time if end_time else close_times.max()

    if pd.isna(t_start) or pd.isna(t_end) or t_end <= t_start:
        return 0.0

    total_days = (t_end - t_start).total_seconds() / 86400.0
    return float(total_profit / total_days) if total_days > 0 else 0.0


def profit_per_trade_per_day(
    trades: pd.DataFrame,
    start_time: Optional[pd.Timestamp] = None,
    end_time: Optional[pd.Timestamp] = None,
) -> float:
    """
    Net profit normalized by both number of trades and calendar days.
    Useful for comparing strategies with different trade frequencies.
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns:
        return 0.0

    tpd = trades_per_day(data, start_time, end_time)
    if tpd <= 0:
        return 0.0

    avg_trade = data["profit_loss"].mean()
    return float(avg_trade * tpd)


# =========================================================================
# Execution & Capture Efficiency
# =========================================================================


def mfe_efficiency(trades: pd.DataFrame) -> float:
    """
    Average percentage of MFE captured by winning trades.
    Returns fraction, e.g. 0.65 = 65%.
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns or "mfe_usd" not in data.columns:
        return 0.0

    winners = data[data["profit_loss"] > EPSILON]
    if winners.empty:
        return 0.0

    pnl = winners["profit_loss"].astype(float)
    mfe = winners["mfe_usd"].astype(float).clip(lower=0.0)

    # Avoid division by zero
    valid = mfe > EPSILON
    if not valid.any():
        return 0.0

    # Efficiency per trade capped at 100%
    eff = pnl[valid] / mfe[valid]
    eff = eff.clip(lower=0.0, upper=1.0)
    
    return float(eff.mean())


def aggregate_mfe_capture_ratio(trades: pd.DataFrame) -> float:
    """
    Aggregate MFE capture ratio for winning trades.
    Formula: Sum(winning PnL) / Sum(winning MFE).
    Returns fraction, e.g. 0.65 = 65%.
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns or "mfe_usd" not in data.columns:
        return 0.0

    winners = data[data["profit_loss"] > EPSILON]
    if winners.empty:
        return 0.0

    total_profit = winners["profit_loss"].sum()
    total_mfe = winners["mfe_usd"].astype(float).clip(lower=0.0).sum()

    if total_mfe <= EPSILON:
        return 0.0

    return float(max(0.0, min(1.0, total_profit / total_mfe)))


def profit_per_pip_risk(trades: pd.DataFrame) -> float:
    """Reward-to-risk based on price movement (Profit Pips / |MAE Pips|)."""
    data = get_closed_trades(trades)
    if data.empty:
        return 0.0
        
    profit_col = None
    for col in ["profit_loss_pips", "profit_pips", "pips"]:
        if col in data.columns:
            profit_col = col
            break
            
    mae_col = None
    for col in ["mae_pips", "mae_points"]:
        if col in data.columns:
            mae_col = col
            break
            
    if not profit_col or not mae_col:
        return 0.0
    
    total_profit_pips = data[profit_col].sum()
    total_mae_pips = data[mae_col].abs().sum()
    
    if total_mae_pips < EPSILON:
        return 0.0
        
    return float(total_profit_pips / total_mae_pips)


def mae_efficiency(trades: pd.DataFrame) -> float:
    """
    Average realized-loss-to-MAE ratio for losing trades.
    Returns fraction, e.g. 0.70 = loss captured 70% of adverse excursion.
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns or "mae_usd" not in data.columns:
        return 0.0

    losers = data[data["profit_loss"] < -EPSILON]
    if losers.empty:
        return 0.0

    loss = losers["profit_loss"].abs().astype(float)
    mae = losers["mae_usd"].abs().astype(float)

    valid = mae > EPSILON
    if not valid.any():
        return 0.0

    # Efficiency per trade: |P&L| / |MAE|
    eff = loss[valid] / mae[valid]
    eff = eff.clip(lower=0.0, upper=1.0)
    
    return float(eff.mean())


def exit_efficiency(trades: pd.DataFrame) -> float:
    """
    Combined measure of capturing wins and containing losses (0-1).
    """
    mfe_eff = max(0.0, min(1.0, mfe_efficiency(trades)))
    
    # MAE containment: 1 - mae_efficiency (how much 'heat' was avoided)
    # This is slightly simplified but common.
    mae_eff_val = mae_efficiency(trades)
    mae_containment = max(0.0, min(1.0, 1.0 - mae_eff_val))
    
    return float((mfe_eff + mae_containment) / 2.0)


def loss_containment_efficiency(trades: pd.DataFrame) -> float:
    """
    Average measure of how well realized losses stayed above their absolute valley (MAE).
    (1 - (|Loss| / |MAE|)) * 100
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns or "mae_usd" not in data.columns:
        return 0.0

    losers = data[data["profit_loss"] < -EPSILON]
    if losers.empty:
        return 100.0

    pnl = losers["profit_loss"].abs()
    mae = losers["mae_usd"].abs()

    valid = mae > EPSILON
    if not valid.any():
        return 100.0

    # Per-trade containment
    containment = 1.0 - (pnl[valid] / mae[valid])
    # Clip to [0, 1] - sometimes slippage makes pnl > mae, but that's an edge case
    containment = containment.clip(lower=0.0, upper=1.0)
    
    return float(containment.mean() * 100.0)


def aggregate_loss_containment_efficiency(trades: pd.DataFrame) -> float:
    """
    Aggregate loss containment for losing trades.
    Formula: (1 - Sum(|Loss|) / Sum(|MAE|)) * 100.
    """
    data = get_closed_trades(trades)
    if data.empty or "profit_loss" not in data.columns or "mae_usd" not in data.columns:
        return 0.0

    losers = data[data["profit_loss"] < -EPSILON]
    if losers.empty:
        return 100.0

    total_loss = losers["profit_loss"].abs().sum()
    total_mae = losers["mae_usd"].abs().sum()

    if total_mae <= EPSILON:
        return 100.0

    containment = 1.0 - (total_loss / total_mae)
    containment = max(0.0, min(1.0, containment))

    return float(containment * 100.0)


# =========================================================================
# Sizing Efficiency
# =========================================================================


def position_size_efficiency(trades: pd.DataFrame) -> float:
    """
    Correlation between absolute position size and normalized trade outcome (R-multiple).
    Measures if larger sizes are correctly aligned with better opportunities.
    """
    data = get_closed_trades(trades)
    if data.empty:
        return 0.0
        
    size_col = None
    for col in ["size", "volume", "quantity"]:
        if col in data.columns:
            size_col = col
            break
            
    if not size_col:
        return 0.0

    r_multiples = get_r_multiples(data)
    if r_multiples.empty:
        # Fallback to normalized P&L correlation
        pnl = data["profit_loss"].astype(float)
        size = data[size_col].abs()
        if pnl.std() < EPSILON or size.std() < EPSILON:
            return 0.0
        return float(size.corr(pnl))

    size = data.loc[r_multiples.index, size_col].abs()
    if size.std() < EPSILON or r_multiples.std() < EPSILON:
        return 0.0

    return float(size.corr(r_multiples))
