"""Rolling metrics chart plotting for backtest visualization.

This module provides functions for plotting rolling performance metrics:
- Rolling volatility (annualized)
- Rolling Sharpe ratio
- Rolling Sortino ratio
- Rolling beta (vs benchmark)
- Rolling returns

Features:
- Configurable rolling windows
- Reference lines for quality zones
- Benchmark comparison
- Support for Matplotlib backend
"""

from typing import Any, Literal, Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from apps.plotting.core import (
    _format_axis,
    _format_date_axis,
    _format_grid,
    _get_colors,
)


def _plot_rolling_volatility(
    ax: Axes,
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    window: int = 30,
    annualize: bool = True,
    periods_per_year: int = 252,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Axes:
    """Plot rolling volatility over time.

    Args:
        ax: Matplotlib axes
        returns: Returns series
        benchmark_returns: Optional benchmark returns for comparison
        window: Rolling window size (default 30 periods)
        annualize: Annualize volatility (default True)
        periods_per_year: Periods per year for annualization (default 252 for daily)
        color_mode: Color scheme ('color' or 'grayscale')
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes

    Example:
        >>> fig, ax = plt.subplots()
        >>> returns = pd.Series([0.01, 0.02, -0.01], index=dates)
        >>> _plot_rolling_volatility(ax, returns, window=30)
    """
    colors = _get_colors(color_mode)

    # Calculate rolling volatility
    rolling_vol = returns.rolling(window=window).std()

    if annualize:
        rolling_vol = (
            rolling_vol * np.sqrt(periods_per_year) * 100
        )  # Convert to percentage
        ylabel = f"Rolling Volatility (%, {window}-period)"
    else:
        rolling_vol = rolling_vol * 100
        ylabel = f"Rolling Volatility (%, {window}-period)"

    # Plot strategy volatility
    ax.plot(
        mdates.date2num(rolling_vol.index),
        rolling_vol.values,
        label="Strategy",
        color=colors.get("profit", "#2ecc71"),
        linewidth=kwargs.get("linewidth", 2),
        alpha=0.9,
    )

    # Plot benchmark if provided
    if benchmark_returns is not None:
        rolling_bench_vol = benchmark_returns.rolling(window=window).std()

        if annualize:
            rolling_bench_vol = rolling_bench_vol * np.sqrt(periods_per_year) * 100
        else:
            rolling_bench_vol = rolling_bench_vol * 100

        ax.plot(
            mdates.date2num(rolling_bench_vol.index),
            rolling_bench_vol.values,
            label="Benchmark",
            color=colors.get("text", "#7f8c8d"),
            linewidth=kwargs.get("linewidth", 1.5),
            linestyle="--",
            alpha=0.7,
        )

    # Add mean line
    mean_vol = rolling_vol.mean()
    ax.axhline(
        y=mean_vol,
        color=colors.get("text", "#34495e"),
        linestyle=":",
        alpha=0.5,
        linewidth=1,
        label=f"Mean: {mean_vol:.1f}%",
    )

    # Format axes
    _format_axis(
        ax,
        title=kwargs.get("title", f"Rolling Volatility ({window}-period)"),
        ylabel=ylabel,
    )
    _format_grid(ax)
    _format_date_axis(ax, rolling_vol.index)

    # Format y-axis as percentage
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.1f}%"))

    # Add legend
    ax.legend(loc="upper left", fontsize=9)

    return ax


def _plot_rolling_sharpe(
    ax: Axes,
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    window: int = 60,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Axes:
    """Plot rolling Sharpe ratio over time.

    Args:
        ax: Matplotlib axes
        returns: Returns series
        benchmark_returns: Optional benchmark returns for comparison
        window: Rolling window size (default 60 periods)
        risk_free_rate: Risk-free rate (annualized, default 0.0)
        periods_per_year: Periods per year for annualization (default 252)
        color_mode: Color scheme ('color' or 'grayscale')
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes

    Example:
        >>> fig, ax = plt.subplots()
        >>> returns = pd.Series([0.01, 0.02, -0.01], index=dates)
        >>> _plot_rolling_sharpe(ax, returns, window=60)
    """
    colors = _get_colors(color_mode)

    # Calculate rolling Sharpe
    rolling_mean = returns.rolling(window=window).mean()
    rolling_std = returns.rolling(window=window).std()

    # Annualize
    rf_daily = risk_free_rate / periods_per_year
    sharpe = (rolling_mean - rf_daily) / rolling_std * np.sqrt(periods_per_year)

    # Plot strategy Sharpe
    ax.plot(
        mdates.date2num(sharpe.index),
        sharpe.values,
        label="Strategy",
        color=colors.get("profit", "#2ecc71"),
        linewidth=kwargs.get("linewidth", 2),
        alpha=0.9,
    )

    # Plot benchmark if provided
    if benchmark_returns is not None:
        bench_mean = benchmark_returns.rolling(window=window).mean()
        bench_std = benchmark_returns.rolling(window=window).std()
        bench_sharpe = (bench_mean - rf_daily) / bench_std * np.sqrt(periods_per_year)

        ax.plot(
            mdates.date2num(bench_sharpe.index),
            bench_sharpe.values,
            label="Benchmark",
            color=colors.get("text", "#7f8c8d"),
            linewidth=kwargs.get("linewidth", 1.5),
            linestyle="--",
            alpha=0.7,
        )

    # Add reference lines
    for level in [-2, -1, 0, 1, 2]:
        ax.axhline(
            y=level,
            color="gray",
            linestyle="--" if level == 0 else ":",
            alpha=0.3 if level == 0 else 0.2,
            linewidth=1,
        )

    # Format axes
    _format_axis(
        ax,
        title=kwargs.get("title", f"Rolling Sharpe Ratio ({window}-period)"),
        ylabel="Sharpe Ratio",
    )
    _format_grid(ax, alpha=0.3)
    _format_date_axis(ax, sharpe.index)

    # Add legend
    ax.legend(loc="upper left", fontsize=9)

    return ax


def _plot_rolling_sortino(
    ax: Axes,
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    window: int = 60,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Axes:
    """Plot rolling Sortino ratio over time.

    Args:
        ax: Matplotlib axes
        returns: Returns series
        benchmark_returns: Optional benchmark returns for comparison
        window: Rolling window size (default 60 periods)
        risk_free_rate: Risk-free rate (annualized, default 0.0)
        periods_per_year: Periods per year for annualization (default 252)
        color_mode: Color scheme ('color' or 'grayscale')
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes

    Example:
        >>> fig, ax = plt.subplots()
        >>> returns = pd.Series([0.01, 0.02, -0.01], index=dates)
        >>> _plot_rolling_sortino(ax, returns, window=60)
    """
    colors = _get_colors(color_mode)

    rf_daily = risk_free_rate / periods_per_year

    # Calculate rolling Sortino
    def rolling_sortino(window_returns):
        mean_ret = window_returns.mean()
        downside_returns = window_returns[window_returns < 0]

        if len(downside_returns) == 0:
            return np.nan

        downside_std = downside_returns.std()

        if downside_std == 0 or np.isnan(downside_std):
            return np.nan

        return (mean_ret - rf_daily) / downside_std * np.sqrt(periods_per_year)

    sortino = returns.rolling(window=window).apply(rolling_sortino, raw=False)

    # Plot strategy Sortino
    ax.plot(
        mdates.date2num(sortino.index),
        sortino.values,
        label="Strategy",
        color=colors.get("profit", "#2ecc71"),
        linewidth=kwargs.get("linewidth", 2),
        alpha=0.9,
    )

    # Plot benchmark if provided
    if benchmark_returns is not None:
        bench_sortino = benchmark_returns.rolling(window=window).apply(
            rolling_sortino, raw=False
        )

        ax.plot(
            mdates.date2num(bench_sortino.index),
            bench_sortino.values,
            label="Benchmark",
            color=colors.get("text", "#7f8c8d"),
            linewidth=kwargs.get("linewidth", 1.5),
            linestyle="--",
            alpha=0.7,
        )

    # Add reference lines
    for level in [-2, -1, 0, 1, 2]:
        ax.axhline(
            y=level,
            color="gray",
            linestyle="--" if level == 0 else ":",
            alpha=0.3 if level == 0 else 0.2,
            linewidth=1,
        )

    # Format axes
    _format_axis(
        ax,
        title=kwargs.get("title", f"Rolling Sortino Ratio ({window}-period)"),
        ylabel="Sortino Ratio",
    )
    _format_grid(ax, alpha=0.3)
    _format_date_axis(ax, sortino.index)

    # Add legend
    ax.legend(loc="upper left", fontsize=9)

    return ax


def _plot_rolling_beta(
    ax: Axes,
    returns: pd.Series,
    benchmark_returns: pd.Series,
    window: int = 60,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Axes:
    """Plot rolling beta (vs benchmark) over time.

    Args:
        ax: Matplotlib axes
        returns: Strategy returns series
        benchmark_returns: Benchmark returns series
        window: Rolling window size (default 60 periods)
        color_mode: Color scheme ('color' or 'grayscale')
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes

    Example:
        >>> fig, ax = plt.subplots()
        >>> returns = pd.Series([0.01, 0.02, -0.01], index=dates)
        >>> benchmark = pd.Series([0.008, 0.015, -0.005], index=dates)
        >>> _plot_rolling_beta(ax, returns, benchmark, window=60)
    """
    colors = _get_colors(color_mode)

    # Calculate rolling beta
    def rolling_beta_calc(idx):
        if idx < window:
            return np.nan

        strategy_window = returns.iloc[idx - window : idx]
        benchmark_window = benchmark_returns.iloc[idx - window : idx]

        covariance = np.cov(strategy_window, benchmark_window)[0, 1]
        benchmark_variance = np.var(benchmark_window)

        if benchmark_variance == 0:
            return np.nan

        return covariance / benchmark_variance

    beta = pd.Series(
        [rolling_beta_calc(i) for i in range(len(returns))],
        index=returns.index,
    )

    # Plot beta
    ax.plot(
        mdates.date2num(beta.index),
        beta.values,
        label="Rolling Beta",
        color=colors.get("profit", "#3498db"),
        linewidth=kwargs.get("linewidth", 2),
        alpha=0.9,
    )

    # Add reference line at β=1
    ax.axhline(
        y=1.0,
        color="black",
        linestyle="-",
        alpha=0.3,
        linewidth=1.5,
        label="β = 1",
    )

    # Shade areas for β>1 and β<1
    ax.axhspan(
        0,
        1,
        alpha=0.05,
        color=colors.get("profit", "#2ecc71"),
        label="β < 1 (Lower risk)",
    )
    ax.axhspan(
        1,
        beta.max() if not np.isnan(beta.max()) else 2,
        alpha=0.05,
        color=colors.get("loss", "#e74c3c"),
        label="β > 1 (Higher risk)",
    )

    # Format axes
    _format_axis(
        ax,
        title=kwargs.get("title", f"Rolling Beta vs Benchmark ({window}-period)"),
        ylabel="Beta (β)",
    )
    _format_grid(ax)
    _format_date_axis(ax, beta.index)

    # Add legend
    ax.legend(loc="upper left", fontsize=9)

    return ax


def _plot_rolling_returns(
    ax: Axes,
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    window: int = 21,
    period_label: str = "Monthly",
    annualize: bool = False,
    periods_per_year: int = 252,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Axes:
    """Plot rolling period returns over time.

    Args:
        ax: Matplotlib axes
        returns: Returns series
        benchmark_returns: Optional benchmark returns for comparison
        window: Rolling window size (default 21 for monthly with daily data)
        period_label: Label for the period (e.g., 'Monthly', 'Quarterly')
        annualize: Annualize the returns (default False)
        periods_per_year: Periods per year for annualization (default 252)
        color_mode: Color scheme ('color' or 'grayscale')
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes

    Example:
        >>> fig, ax = plt.subplots()
        >>> returns = pd.Series([0.01, 0.02, -0.01], index=dates)
        >>> _plot_rolling_returns(ax, returns, window=21, period_label="Monthly")
    """
    colors = _get_colors(color_mode)

    # Calculate rolling returns
    rolling_ret = (
        (1 + returns).rolling(window=window).apply(lambda x: x.prod() - 1, raw=False)
    )

    if annualize:
        rolling_ret = rolling_ret * (periods_per_year / window)

    # Convert to percentage
    rolling_ret = rolling_ret * 100

    # Plot strategy returns
    ax.plot(
        mdates.date2num(rolling_ret.index),
        rolling_ret.values,
        label="Strategy",
        color=colors.get("profit", "#2ecc71"),
        linewidth=kwargs.get("linewidth", 2),
        alpha=0.9,
    )

    # Plot benchmark if provided
    if benchmark_returns is not None:
        rolling_bench_ret = (
            (1 + benchmark_returns)
            .rolling(window=window)
            .apply(lambda x: x.prod() - 1, raw=False)
        )

        if annualize:
            rolling_bench_ret = rolling_bench_ret * (periods_per_year / window)

        rolling_bench_ret = rolling_bench_ret * 100

        ax.plot(
            mdates.date2num(rolling_bench_ret.index),
            rolling_bench_ret.values,
            label="Benchmark",
            color=colors.get("text", "#7f8c8d"),
            linewidth=kwargs.get("linewidth", 1.5),
            linestyle="--",
            alpha=0.7,
        )

    # Add zero reference line
    ax.axhline(y=0, color="black", linestyle="-", alpha=0.3, linewidth=1)

    # Format axes
    ann_label = " (Annualized)" if annualize else ""
    _format_axis(
        ax,
        title=kwargs.get("title", f"Rolling {period_label} Returns{ann_label}"),
        ylabel=f"{period_label} Return (%)" + ann_label,
    )
    _format_grid(ax)
    _format_date_axis(ax, rolling_ret.index)

    # Format y-axis as percentage
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.1f}%"))

    # Add legend
    ax.legend(loc="upper left", fontsize=9)

    return ax


__all__ = [
    "_plot_rolling_volatility",
    "_plot_rolling_sharpe",
    "_plot_rolling_sortino",
    "_plot_rolling_beta",
    "_plot_rolling_returns",
]
