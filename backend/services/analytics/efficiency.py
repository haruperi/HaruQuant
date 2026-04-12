"""
Capital and time efficiency metrics.

How efficiently the strategy converts risk → return
"""

from typing import Optional

import pandas as pd

# =========================================================================
# Capital Efficiency
# =========================================================================


def capital_efficiency(trades: pd.DataFrame) -> float:
    """
    Capital efficiency - return per unit of capital deployed.

    Args:
        trades: Trades DataFrame

    Returns:
        Capital efficiency ratio
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns or "size" not in trades.columns:
        return 0.0

    total_return = trades["profit_loss"].sum()

    # Estimate capital deployed (simplified)
    # In reality, this should account for margin and leverage
    avg_position_value = trades["size"].mean() * 100000  # Standard lot

    if avg_position_value == 0:
        return 0.0

    return float(total_return / avg_position_value)


def return_per_unit_risk(trades: pd.DataFrame) -> float:
    """
    Return per unit of risk (using MAE).

    Measures how efficiently the strategy captures returns
    relative to adverse price movements

    Args:
        trades: Trades DataFrame

    Returns:
        Return / MAE ratio
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0

    total_return = trades["profit_loss"].sum()
    total_mae = trades["mae_usd"].sum()

    if total_mae == 0:
        return 0.0

    return float(total_return / total_mae)


# =========================================================================
# Time Efficiency
# =========================================================================


def time_efficiency(trades: pd.DataFrame) -> float:
    """
    Time efficiency - return per hour in market.

    Args:
        trades: Trades DataFrame

    Returns:
        Return per hour
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns or "time_in_trade" not in trades.columns:
        return 0.0

    total_return = trades["profit_loss"].sum()
    total_time = trades["time_in_trade"].sum()

    if total_time == 0:
        return 0.0

    return float(total_return / total_time)


def return_per_trade(trades: pd.DataFrame) -> float:
    """
    Average return per trade.

    Args:
        trades: Trades DataFrame

    Returns:
        Average return per trade
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns:
        return 0.0

    return float(trades["profit_loss"].mean())


def return_per_unit_time(
    trades: pd.DataFrame, total_time_hours: Optional[float] = None
) -> float:
    """
    Return per unit of calendar time (not just time in market).

    Args:
        trades: Trades DataFrame
        total_time_hours: Total calendar time in hours (auto-calculated if None)

    Returns:
        Return per hour of calendar time
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns:
        return 0.0

    total_return = trades["profit_loss"].sum()

    if total_time_hours is None:
        # Calculate from first open to last close
        if "open_time" not in trades.columns or "close_time" not in trades.columns:
            return 0.0

        first_open = trades["open_time"].min()
        last_close = trades["close_time"].max()

        total_time_hours = (last_close - first_open).total_seconds() / 3600

    if total_time_hours == 0:
        return 0.0

    return float(total_return / total_time_hours)


# =========================================================================
# Trade Execution Efficiency
# =========================================================================


def mfe_efficiency(trades: pd.DataFrame) -> float:
    """
    MFE efficiency - how much of favorable move was captured.

    Ratio of actual profit to maximum favorable excursion

    Args:
        trades: Trades DataFrame

    Returns:
        MFE efficiency ratio (0-1)
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns or "mfe_usd" not in trades.columns:
        return 0.0

    # Only consider winning trades for this metric
    winners = trades[trades["profit_loss"] > 0]

    if len(winners) == 0:
        return 0.0

    # Filter out zero MFE
    valid_winners = winners[winners["mfe_usd"] > 0]

    if len(valid_winners) == 0:
        return 0.0

    efficiency_ratios = valid_winners["profit_loss"] / valid_winners["mfe_usd"]

    return float(efficiency_ratios.mean())


def mae_efficiency(trades: pd.DataFrame) -> float:
    """
    MAE efficiency - how well losses were contained.

    For losing trades, ratio of actual loss to MAE
    Lower is better (means stopped out before max adverse move)

    Args:
        trades: Trades DataFrame

    Returns:
        MAE efficiency ratio
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0

    # Only consider losing trades
    losers = trades[trades["profit_loss"] < 0]

    if len(losers) == 0:
        return 0.0

    # Filter out zero MAE
    valid_losers = losers[losers["mae_usd"] > 0]

    if len(valid_losers) == 0:
        return 0.0

    # Use absolute values
    efficiency_ratios = abs(valid_losers["profit_loss"]) / valid_losers["mae_usd"]

    return float(efficiency_ratios.mean())


def exit_efficiency(trades: pd.DataFrame) -> float:
    """
    Exit efficiency - average of MFE and (1 - MAE) efficiency.

    Combines both win capture and loss containment

    Args:
        trades: Trades DataFrame

    Returns:
        Overall exit efficiency
    """
    mfe_eff = mfe_efficiency(trades)
    mae_eff = mae_efficiency(trades)

    # For MAE, lower is better, so we invert it
    mae_eff_inverted = 1.0 - mae_eff if mae_eff > 0 else 0.0

    # Average of both
    return float((mfe_eff + mae_eff_inverted) / 2)


# =========================================================================
# Position Sizing Efficiency
# =========================================================================


def position_size_efficiency(trades: pd.DataFrame) -> float:
    """
    Position sizing efficiency.

    Measures if larger positions correlate with better outcomes

    Args:
        trades: Trades DataFrame

    Returns:
        Correlation between position size and profit
    """
    if len(trades) == 0:
        return 0.0

    if "size" not in trades.columns or "profit_loss" not in trades.columns:
        return 0.0

    if len(trades) < 2:
        return 0.0

    correlation = trades["size"].corr(trades["profit_loss"])

    return float(correlation) if not pd.isna(correlation) else 0.0


def risk_adjusted_efficiency(trades: pd.DataFrame) -> float:
    """
    Risk-adjusted efficiency - return per unit of initial risk.

    Args:
        trades: Trades DataFrame

    Returns:
        Return / initial risk ratio
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns or "initial_risk_usd" not in trades.columns:
        return 0.0

    # Filter trades with defined risk
    trades_with_risk = trades[trades["initial_risk_usd"] > 0]

    if len(trades_with_risk) == 0:
        return 0.0

    total_return = trades_with_risk["profit_loss"].sum()
    total_risk = trades_with_risk["initial_risk_usd"].sum()

    if total_risk == 0:
        return 0.0

    return float(total_return / total_risk)


# =========================================================================
# Trade Frequency Efficiency
# =========================================================================


def trades_per_day(trades: pd.DataFrame) -> float:
    """
    Average number of trades per day.

    Args:
        trades: Trades DataFrame

    Returns:
        Trades per day
    """
    if len(trades) == 0:
        return 0.0

    if "open_time" not in trades.columns or "close_time" not in trades.columns:
        return 0.0

    first_open = trades["open_time"].min()
    last_close = trades["close_time"].max()

    total_days = (last_close - first_open).total_seconds() / (24 * 3600)

    if total_days == 0:
        return 0.0

    return float(len(trades) / total_days)


def return_per_trade_opportunity(
    trades: pd.DataFrame, total_days: Optional[float] = None
) -> float:
    """
    Return per trading opportunity (calendar day).

    Args:
        trades: Trades DataFrame
        total_days: Total calendar days (auto-calculated if None)

    Returns:
        Return per day
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns:
        return 0.0

    total_return = trades["profit_loss"].sum()

    if total_days is None:
        if "open_time" not in trades.columns or "close_time" not in trades.columns:
            return 0.0

        first_open = trades["open_time"].min()
        last_close = trades["close_time"].max()

        total_days = (last_close - first_open).total_seconds() / (24 * 3600)

    if total_days == 0:
        return 0.0

    return float(total_return / total_days)


# =========================================================================
# Win/Loss Efficiency
# =========================================================================


def win_efficiency(trades: pd.DataFrame) -> float:
    """
    Win efficiency - percentage of potential profit captured.

    Compares actual wins to potential wins (based on MFE)

    Args:
        trades: Trades DataFrame

    Returns:
        Win efficiency percentage (0-100)
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns or "mfe_usd" not in trades.columns:
        return 0.0

    winners = trades[trades["profit_loss"] > 0]

    if len(winners) == 0:
        return 0.0

    actual_profit = winners["profit_loss"].sum()
    potential_profit = winners["mfe_usd"].sum()

    if potential_profit == 0:
        return 0.0

    return float((actual_profit / potential_profit) * 100)


def loss_containment_efficiency(trades: pd.DataFrame) -> float:
    """
    Loss containment efficiency.

    How well losses are contained relative to MAE
    Higher is better

    Args:
        trades: Trades DataFrame

    Returns:
        Loss containment efficiency percentage (0-100)
    """
    if len(trades) == 0:
        return 0.0

    if "profit_loss" not in trades.columns or "mae_usd" not in trades.columns:
        return 0.0

    losers = trades[trades["profit_loss"] < 0]

    if len(losers) == 0:
        return 100.0  # No losses = perfect containment

    actual_loss = abs(losers["profit_loss"].sum())
    potential_loss = losers["mae_usd"].sum()

    if potential_loss == 0:
        return 100.0

    # Lower actual loss vs potential = higher efficiency
    containment = (1 - (actual_loss / potential_loss)) * 100

    return float(max(0.0, containment))
