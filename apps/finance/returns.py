"""
Return calculations & period-based analysis.

Focus: equity growth, compounding, time normalization
"""

from typing import Optional

import numpy as np
import pandas as pd

from . import drawdowns

# =========================================================================
# Basic Returns & Benchmarks
# =========================================================================


def buy_and_hold_return(price_data: pd.Series) -> float:
    """
    Buy & Hold Return.

    Return achieved if asset was bought at start and held to end.

    Args:
        price_data: Series of asset prices (e.g., Close prices)

    Returns:
        Percentage return (0.0 - 100.0+)
    """
    if len(price_data) < 2:
        return 0.0

    start_price = float(price_data.iloc[0])
    end_price = float(price_data.iloc[-1])

    if start_price == 0:
        return 0.0

    return ((end_price - start_price) / start_price) * 100.0


def buy_and_hold_cagr(price_data: pd.Series) -> float:
    """Buy & Hold CAGR."""
    # Create a dummy equity curve matching the price
    if len(price_data) < 2:
        return 0.0
    return cagr(price_data)


def total_return(equity: pd.Series) -> float:
    """
    Total return from equity curve.

    Args:
        equity: Equity series

    Returns:
        Total return in currency units
    """
    if len(equity) == 0:
        return 0.0
    return float(equity.iloc[-1] - equity.iloc[0])


def net_profit(trades: pd.DataFrame) -> float:
    """Net profit from all trades."""
    if len(trades) == 0:
        return 0.0
    return float(trades["profit_loss"].sum())


def gross_profit(trades: pd.DataFrame) -> float:
    """Gross profit (sum of winning trades)."""
    if len(trades) == 0:
        return 0.0
    return float(trades[trades["profit_loss"] > 0]["profit_loss"].sum())


def gross_loss(trades: pd.DataFrame) -> float:
    """Gross loss (sum of losing trades, negative value)."""
    if len(trades) == 0:
        return 0.0
    return float(trades[trades["profit_loss"] < 0]["profit_loss"].sum())


# =========================================================================
# Equity Curve Generation
# =========================================================================


def equity_curve(trades: pd.DataFrame, initial_balance: float) -> pd.Series:
    """
    Generate equity curve from trades.

    Args:
        trades: Trades DataFrame
        initial_balance: Starting balance

    Returns:
        Series with cumulative equity indexed by close_time
    """
    if len(trades) == 0:
        return pd.Series([initial_balance])

    # Sort by close time
    sorted_trades = trades.sort_values("close_time")

    # Cumulative P&L
    cumulative_pnl = sorted_trades["profit_loss"].cumsum()
    equity_series = initial_balance + cumulative_pnl

    # Set index to close time
    equity_series.index = sorted_trades["close_time"]

    # Add initial point
    if len(sorted_trades) > 0:
        first_time = sorted_trades.iloc[0]["open_time"]
        equity_series = pd.concat(
            [pd.Series([initial_balance], index=[first_time]), equity_series]
        )

    return equity_series


def balance_curve(trades: pd.DataFrame, initial_balance: float) -> pd.Series:
    """
    Generate balance curve (realized P&L only).

    Same as equity_curve for closed trades
    """
    return equity_curve(trades, initial_balance)


def returns_series(equity_curve: pd.Series) -> pd.Series:
    """
    Calculate returns series from equity curve.

    Returns:
        Series of percentage returns
    """
    if len(equity_curve) < 2:
        return pd.Series(dtype=float)

    return equity_curve.pct_change().dropna()


def log_returns_series(equity_curve: pd.Series) -> pd.Series:
    """
    Calculate log returns series from equity curve.

    Returns:
        Series of log returns
    """
    if len(equity_curve) < 2:
        return pd.Series(dtype=float)

    return np.log(equity_curve / equity_curve.shift(1)).dropna()


# =========================================================================
# Period-Based Returns
# =========================================================================


def daily_returns(equity_curve: pd.Series) -> pd.Series:
    """
    Resample equity curve to daily returns.

    Args:
        equity_curve: Equity series with datetime index

    Returns:
        Daily returns series
    """
    if len(equity_curve) < 2:
        return pd.Series(dtype=float)

    daily_equity = equity_curve.resample("D").last().dropna()
    return daily_equity.pct_change().dropna()


def weekly_returns(equity_curve: pd.Series) -> pd.Series:
    """Resample equity curve to weekly returns."""
    if len(equity_curve) < 2:
        return pd.Series(dtype=float)

    weekly_equity = equity_curve.resample("W").last().dropna()
    return weekly_equity.pct_change().dropna()


def monthly_returns(equity_curve: pd.Series) -> pd.Series:
    """Resample equity curve to monthly returns."""
    if len(equity_curve) < 2:
        return pd.Series(dtype=float)

    monthly_equity = equity_curve.resample("ME").last().dropna()
    return monthly_equity.pct_change().dropna()


def annual_returns(equity_curve: pd.Series) -> pd.Series:
    """Resample equity curve to annual returns."""
    if len(equity_curve) < 2:
        return pd.Series(dtype=float)

    annual_equity = equity_curve.resample("YE").last().dropna()
    return annual_equity.pct_change().dropna()


# =========================================================================
# Compounding Metrics
# =========================================================================


def compound_monthly_growth_rate(equity_curve: pd.Series) -> float:
    """
    Compound Monthly Growth Rate (CMGR).

    Equivalent to CAGR but for monthly periods.
    """
    if len(equity_curve) < 2:
        return 0.0

    start_value = equity_curve.iloc[0]
    end_value = equity_curve.iloc[-1]

    if start_value <= 0:
        return 0.0

    # Calculate months
    start_date = equity_curve.index[0]
    end_date = equity_curve.index[-1]
    # More accurate month diff
    days = (end_date - start_date).total_seconds() / (24 * 3600)
    months = days / 30.44  # Average days in month

    if months == 0:
        return 0.0

    # CMGR = (End/Start)^(1/months) - 1
    cmgr_value = (end_value / start_value) ** (1 / months) - 1

    return float(cmgr_value * 100)


def avg_monthly_return(equity_curve: pd.Series) -> float:
    """
    Average Monthly Return.

    Arithmetic mean of monthly returns.
    """
    m_ret = monthly_returns(equity_curve)
    if len(m_ret) == 0:
        return 0.0
    return float(m_ret.mean() * 100)


def monthly_return_stddev(equity_curve: pd.Series) -> float:
    """Calculate standard deviation of monthly returns."""
    m_ret = monthly_returns(equity_curve)
    if len(m_ret) < 2:
        return 0.0
    return float(m_ret.std() * 100)


def cagr(equity_curve: pd.Series) -> float:
    """
    Compound Annual Growth Rate.

    Args:
        equity_curve: Equity series with datetime index

    Returns:
        CAGR as percentage
    """
    if len(equity_curve) < 2:
        return 0.0

    start_value = equity_curve.iloc[0]
    end_value = equity_curve.iloc[-1]

    if start_value <= 0:
        return 0.0

    # Calculate years
    start_date = equity_curve.index[0]
    end_date = equity_curve.index[-1]
    years = (end_date - start_date).total_seconds() / (365.25 * 24 * 3600)

    if years == 0:
        return 0.0

    # CAGR = (End/Start)^(1/years) - 1
    cagr_value = (end_value / start_value) ** (1 / years) - 1

    return float(cagr_value * 100)


def annualized_return(
    returns: pd.Series, periods_per_year: Optional[int] = None
) -> float:
    """
    Calculate annualized return from returns series.

    Args:
        returns: Returns series
        periods_per_year: Number of periods per year (auto-detected if None)

    Returns:
        Annualized return as percentage
    """
    if len(returns) == 0:
        return 0.0

    # Auto-detect periods per year if not provided
    if periods_per_year is None:
        if isinstance(returns.index, pd.DatetimeIndex):
            # Estimate based on index frequency
            mean_diff = (returns.index[-1] - returns.index[0]) / len(returns)
            days_per_period = mean_diff.total_seconds() / (24 * 3600)

            if days_per_period < 2:
                periods_per_year = 252  # Daily
            elif days_per_period < 8:
                periods_per_year = 52  # Weekly
            elif days_per_period < 35:
                periods_per_year = 12  # Monthly
            else:
                periods_per_year = 1  # Yearly
        else:
            periods_per_year = 252  # Default to daily

    # Geometric mean return
    mean_return = returns.mean()

    # Annualize
    annualized = (1 + mean_return) ** periods_per_year - 1

    return float(annualized * 100)


def geometric_mean_return(returns: pd.Series) -> float:
    """
    Calculate geometric mean return.

    Args:
        returns: Returns series (as decimals, e.g., 0.01 for 1%)

    Returns:
        Geometric mean return
    """
    if len(returns) == 0:
        return 0.0

    # Convert to growth factors
    growth_factors = 1 + returns

    # Geometric mean: (product of all factors)^(1/n) - 1
    geometric_mean = growth_factors.prod() ** (1 / len(returns)) - 1

    return float(geometric_mean)


# =========================================================================
# Stability
# =========================================================================


def return_volatility(returns: pd.Series) -> float:
    """
    Calculate return volatility (standard deviation).

    Args:
        returns: Returns series

    Returns:
        Standard deviation of returns
    """
    if len(returns) < 2:
        return 0.0
    return float(returns.std())


def downside_return_volatility(returns: pd.Series, target: float = 0.0) -> float:
    """
    Calculate downside volatility (semi-deviation).

    Only considers returns below target

    Args:
        returns: Returns series
        target: Target return (default 0)

    Returns:
        Downside standard deviation
    """
    if len(returns) < 2:
        return 0.0

    downside_returns = returns[returns < target]

    if len(downside_returns) == 0:
        return 0.0

    return float(downside_returns.std())


def return_skewness(returns: pd.Series) -> float:
    """
    Calculate skewness of returns distribution.

    - Negative: More extreme losses than gains
    - Positive: More extreme gains than losses
    - Zero: Symmetric

    Args:
        returns: Returns series

    Returns:
        Skewness value
    """
    if len(returns) < 3:
        return 0.0
    return float(returns.skew())


def return_kurtosis(returns: pd.Series) -> float:
    """
    Calculate kurtosis of returns distribution.

    Measures "tailedness" of distribution
    - High kurtosis: Fat tails (more extreme events)
    - Low kurtosis: Thin tails (fewer extreme events)

    Args:
        returns: Returns series

    Returns:
        Excess kurtosis value
    """
    if len(returns) < 4:
        return 0.0
    return float(returns.kurtosis())


# =========================================================================
# Adjusted & Select Metrics (Trade-Based)
# =========================================================================


def adjusted_gross_profit(trades: pd.DataFrame) -> float:
    """
    Calculate Adjusted Gross Profit.

    (N_Winning_Trades - Sqrt(N_Winning_Trades)) * Avg_Winning_Trade
    """
    winners = trades[trades["profit_loss"] > 0]
    n_winners = len(winners)

    if n_winners == 0:
        return 0.0

    avg_win_val = float(winners["profit_loss"].mean())
    adjusted_n = n_winners - np.sqrt(n_winners)

    return float(adjusted_n * avg_win_val)


def adjusted_gross_loss(trades: pd.DataFrame) -> float:
    """
    Calculate Adjusted Gross Loss.

    (N_Losing_Trades + Sqrt(N_Losing_Trades)) * Avg_Losing_Trade

    (Note: Since Avg_Losing_Trade is negative, increasing the count by sqrt(N)
    makes the result more negative, effectively 'increasing' the loss magnitude)
    """
    losers = trades[trades["profit_loss"] < 0]
    n_losers = len(losers)

    if n_losers == 0:
        return 0.0

    avg_loss_val = float(losers["profit_loss"].mean())
    adjusted_n = n_losers + np.sqrt(n_losers)

    return float(adjusted_n * avg_loss_val)


def adjusted_net_profit(trades: pd.DataFrame) -> float:
    """
    Calculate Adjusted Net Profit.

    The difference between the adjusted gross loss and the adjusted gross profit.
    """
    return adjusted_gross_profit(trades) + adjusted_gross_loss(trades)


def _remove_outliers(trades: pd.DataFrame, sigma: float = 3.0) -> pd.DataFrame:
    """
    Remove trades that are outliers.

    Helper to remove trades that are more than `sigma` standard deviations
    away from the mean profit/loss.
    """
    if len(trades) < 2:
        return trades

    mean = trades["profit_loss"].mean()
    std = trades["profit_loss"].std()

    if std == 0:
        return trades

    lower_bound = mean - (sigma * std)
    upper_bound = mean + (sigma * std)

    # Keep trades within [mean - 3std, mean + 3std]
    mask = (trades["profit_loss"] >= lower_bound) & (
        trades["profit_loss"] <= upper_bound
    )
    return trades[mask]


def select_net_profit(trades: pd.DataFrame) -> float:
    """
    Select Net Profit.

    Net Profit with outlier trades removed.
    A trade is an outlier if its PnL is > 3 std devs from the mean.
    """
    if len(trades) == 0:
        return 0.0

    filtered = _remove_outliers(trades, sigma=3.0)
    return float(filtered["profit_loss"].sum())


def select_gross_profit(trades: pd.DataFrame) -> float:
    """
    Select Gross Profit.

    Gross Profit consisting only of non-outlier trades.
    """
    if len(trades) == 0:
        return 0.0

    # Filter global outliers, then sum the positive ones remaining.
    filtered = _remove_outliers(trades, sigma=3.0)

    winners = filtered[filtered["profit_loss"] > 0]
    return float(winners["profit_loss"].sum())


def select_gross_loss(trades: pd.DataFrame) -> float:
    """
    Select Gross Loss.

    Gross Loss consisting only of non-outlier trades.
    """
    if len(trades) == 0:
        return 0.0

    filtered = _remove_outliers(trades, sigma=3.0)

    losers = filtered[filtered["profit_loss"] < 0]
    return float(losers["profit_loss"].sum())


# =========================================================================
# Return Ratios
# =========================================================================


def return_on_max_strategy_drawdown(equity_curve: pd.Series) -> float:
    """
    Return on Max Strategy Drawdown.

    Total Return / Max Strategy Drawdown.
    """
    dd = drawdowns.max_strategy_drawdown(equity_curve)
    if dd == 0:
        return 0.0

    tot_ret = total_return(equity_curve)
    return tot_ret / dd


def return_on_max_close_to_close_drawdown(trades: pd.DataFrame) -> float:
    """
    Return on Max Close To Close Drawdown.

    Net Profit / Max Close To Close Drawdown.
    """
    dd = drawdowns.max_close_to_close_drawdown(trades)
    if dd == 0:
        return 0.0

    profit = net_profit(trades)
    return profit / dd


def return_on_account(trades: pd.DataFrame) -> float:
    """
    Return on Account.

    Net Profit / Account Size Required.
    """
    return return_on_max_close_to_close_drawdown(trades)


def return_on_initial_capital(trades: pd.DataFrame, initial_capital: float) -> float:
    """
    Return on Initial Capital.

    Net Profit / Initial Capital.
    """
    if initial_capital == 0:
        return 0.0

    profit = net_profit(trades)
    return profit / initial_capital
