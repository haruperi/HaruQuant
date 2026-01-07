"""Convenience wrapper functions for common plotting operations.

This module provides simplified interfaces to plotting functions with
consistent parameter handling across all visualization types.
"""

from pathlib import Path
from typing import Any, Literal, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from apps.logger import logger
from apps.plotting.core import save_figure
from apps.plotting.distribution import _plot_distribution
from apps.plotting.drawdown import _plot_drawdown
from apps.plotting.heatmap import _plot_monthly_heatmap
from apps.plotting.performance import _plot_cumulative_returns
from apps.plotting.rolling import _plot_rolling_sharpe
from apps.plotting.summary import _plot_daily_returns, _plot_yearly_returns


def plot_returns(
    equity: Union[np.ndarray, pd.Series],
    figsize: Optional[Tuple[float, float]] = None,
    title: Optional[str] = None,
    savefig: Optional[Union[str, Path]] = None,
    show: bool = True,
    grayscale: bool = False,
    benchmark: Optional[Union[np.ndarray, pd.Series]] = None,
    **kwargs: Any,
) -> Figure:
    """Plot cumulative returns curve.

    Convenience wrapper for _plot_cumulative_returns with consistent interface.

    Args:
        equity: Equity curve array or series
        figsize: Figure size as (width, height) in inches
        title: Custom title for the plot
        savefig: Path to save figure (if provided)
        show: Whether to display the figure
        grayscale: Use grayscale colors instead of color
        benchmark: Optional benchmark equity curve for comparison
        **kwargs: Additional arguments passed to _plot_cumulative_returns

    Returns:
        Matplotlib Figure object

    Example:
        >>> equity = np.array([10000, 10100, 10200, 10150, 10300])
        >>> fig = plot_returns(equity, title="My Strategy Returns")
        >>> plt.show()
    """
    if title is None:
        title = "Cumulative Returns"

    # Convert equity to returns
    equity_series = equity if isinstance(equity, pd.Series) else pd.Series(equity)
    returns = equity_series.pct_change().dropna()

    # Convert benchmark if provided
    benchmark_returns = None
    if benchmark is not None:
        benchmark_series = (
            benchmark if isinstance(benchmark, pd.Series) else pd.Series(benchmark)
        )
        benchmark_returns = benchmark_series.pct_change().dropna()

    # Create figure
    if figsize is None:
        figsize = (12, 6)

    fig, ax = plt.subplots(figsize=figsize)

    # Plot using the performance module function
    color_mode: Literal["color", "grayscale"] = "grayscale" if grayscale else "color"
    _plot_cumulative_returns(
        ax,
        returns,
        benchmark_returns=benchmark_returns,
        color_mode=color_mode,
        **kwargs,
    )

    # Set title
    ax.set_title(title, fontsize=14, fontweight="bold")

    if savefig:
        save_figure(fig, savefig)
        logger.info(f"Returns plot saved to {savefig}")

    if show:
        plt.show()

    return fig


def plot_drawdown(
    equity: Union[np.ndarray, pd.Series],
    figsize: Optional[Tuple[float, float]] = None,
    title: Optional[str] = None,
    savefig: Optional[Union[str, Path]] = None,
    show: bool = True,
    grayscale: bool = False,
    **kwargs: Any,
) -> Figure:
    """Plot drawdown chart.

    Convenience wrapper for _plot_drawdown with consistent interface.

    Args:
        equity: Equity curve array or series
        figsize: Figure size as (width, height) in inches
        title: Custom title for the plot
        savefig: Path to save figure (if provided)
        show: Whether to display the figure
        grayscale: Use grayscale colors instead of color
        **kwargs: Additional arguments passed to _plot_drawdown

    Returns:
        Matplotlib Figure object

    Example:
        >>> equity = np.array([10000, 10100, 10200, 10150, 10300])
        >>> fig = plot_drawdown(equity, title="Strategy Drawdown")
        >>> plt.show()
    """
    if title is None:
        title = "Drawdown"

    # Convert to series if needed
    equity_series = equity if isinstance(equity, pd.Series) else pd.Series(equity)

    # Create figure
    if figsize is None:
        figsize = (12, 5)

    fig, ax = plt.subplots(figsize=figsize)

    # Plot using the drawdown module function
    color_mode: Literal["color", "grayscale"] = "grayscale" if grayscale else "color"
    _plot_drawdown(
        ax,
        equity=equity_series,
        color_mode=color_mode,
        **kwargs,
    )

    # Set title
    ax.set_title(title, fontsize=14, fontweight="bold")

    if savefig:
        save_figure(fig, savefig)
        logger.info(f"Drawdown plot saved to {savefig}")

    if show:
        plt.show()

    return fig


def plot_monthly_heatmap(
    equity: Union[np.ndarray, pd.Series],
    figsize: Optional[Tuple[float, float]] = None,
    title: Optional[str] = None,
    savefig: Optional[Union[str, Path]] = None,
    show: bool = True,
    grayscale: bool = False,
    **kwargs: Any,
) -> Figure:
    """Plot monthly returns heatmap.

    Convenience wrapper for _plot_monthly_heatmap with consistent interface.

    Args:
        equity: Equity curve array or series
        figsize: Figure size as (width, height) in inches
        title: Custom title for the plot
        savefig: Path to save figure (if provided)
        show: Whether to display the figure
        grayscale: Use grayscale colors instead of color
        **kwargs: Additional arguments passed to _plot_monthly_heatmap

    Returns:
        Matplotlib Figure object

    Example:
        >>> equity = pd.Series([...], index=pd.date_range('2024-01-01', periods=365))
        >>> fig = plot_monthly_heatmap(equity, title="Monthly Performance")
        >>> plt.show()
    """
    if title is None:
        title = "Monthly Returns Heatmap"

    # Convert to series if needed
    equity_series = equity if isinstance(equity, pd.Series) else pd.Series(equity)
    returns = equity_series.pct_change().dropna()

    # Create figure
    if figsize is None:
        figsize = (12, 8)

    fig, ax = plt.subplots(figsize=figsize)

    # Plot using the heatmap module function
    color_mode: Literal["color", "grayscale"] = "grayscale" if grayscale else "color"
    _plot_monthly_heatmap(
        ax,
        returns,
        color_mode=color_mode,
        **kwargs,
    )

    # Set title
    ax.set_title(title, fontsize=14, fontweight="bold")

    if savefig:
        save_figure(fig, savefig)
        logger.info(f"Monthly heatmap saved to {savefig}")

    if show:
        plt.show()

    return fig


def plot_rolling_sharpe(
    equity: Union[np.ndarray, pd.Series],
    window: int = 30,
    periods_per_year: int = 252,
    figsize: Optional[Tuple[float, float]] = None,
    title: Optional[str] = None,
    savefig: Optional[Union[str, Path]] = None,
    show: bool = True,
    grayscale: bool = False,
    **kwargs: Any,
) -> Figure:
    """Plot rolling Sharpe ratio.

    Convenience wrapper for _plot_rolling_sharpe with consistent interface.

    Args:
        equity: Equity curve array or series
        window: Rolling window size in periods
        periods_per_year: Number of periods per year for annualization
        figsize: Figure size as (width, height) in inches
        title: Custom title for the plot
        savefig: Path to save figure (if provided)
        show: Whether to display the figure
        grayscale: Use grayscale colors instead of color
        **kwargs: Additional arguments passed to _plot_rolling_sharpe

    Returns:
        Matplotlib Figure object

    Example:
        >>> equity = np.array([10000, 10100, 10200, 10150, 10300])
        >>> fig = plot_rolling_sharpe(equity, window=30, title="30-Day Rolling Sharpe")
        >>> plt.show()
    """
    if title is None:
        title = f"Rolling Sharpe Ratio ({window}-period)"

    # Convert equity to returns
    equity_series = equity if isinstance(equity, pd.Series) else pd.Series(equity)
    returns = equity_series.pct_change().dropna()

    # Create figure
    if figsize is None:
        figsize = (12, 6)

    fig, ax = plt.subplots(figsize=figsize)

    # Plot using the rolling module function
    color_mode: Literal["color", "grayscale"] = "grayscale" if grayscale else "color"
    _plot_rolling_sharpe(
        ax,
        returns,
        window=window,
        periods_per_year=periods_per_year,
        color_mode=color_mode,
        title=title,
        **kwargs,
    )

    if savefig:
        save_figure(fig, savefig)
        logger.info(f"Rolling Sharpe plot saved to {savefig}")

    if show:
        plt.show()

    return fig


def plot_yearly_returns(
    equity: Union[np.ndarray, pd.Series],
    figsize: Optional[Tuple[float, float]] = None,
    title: Optional[str] = None,
    savefig: Optional[Union[str, Path]] = None,
    show: bool = True,
    grayscale: bool = False,
    **kwargs: Any,
) -> Figure:
    """Plot yearly returns bar chart.

    Convenience wrapper for _plot_yearly_returns with consistent interface.

    Args:
        equity: Equity curve array or series
        figsize: Figure size as (width, height) in inches
        title: Custom title for the plot
        savefig: Path to save figure (if provided)
        show: Whether to display the figure
        grayscale: Use grayscale colors instead of color
        **kwargs: Additional arguments passed to _plot_yearly_returns

    Returns:
        Matplotlib Figure object

    Example:
        >>> equity = pd.Series([...], index=pd.date_range('2020-01-01', periods=1000))
        >>> fig = plot_yearly_returns(equity, title="Annual Performance")
        >>> plt.show()
    """
    if title is None:
        title = "Yearly Returns"

    # Convert to series if needed
    equity_series = equity if isinstance(equity, pd.Series) else pd.Series(equity)
    returns = equity_series.pct_change().dropna()

    # Create figure
    if figsize is None:
        figsize = (10, 6)

    fig, ax = plt.subplots(figsize=figsize)

    # Plot using the summary module function
    color_mode: Literal["color", "grayscale"] = "grayscale" if grayscale else "color"
    _plot_yearly_returns(
        ax,
        returns,
        color_mode=color_mode,
        **kwargs,
    )

    # Set title
    ax.set_title(title, fontsize=14, fontweight="bold")

    if savefig:
        save_figure(fig, savefig)
        logger.info(f"Yearly returns plot saved to {savefig}")

    if show:
        plt.show()

    return fig


def plot_daily_returns(
    equity: Union[np.ndarray, pd.Series],
    figsize: Optional[Tuple[float, float]] = None,
    title: Optional[str] = None,
    savefig: Optional[Union[str, Path]] = None,
    show: bool = True,
    grayscale: bool = False,
    **kwargs: Any,
) -> Figure:
    """Plot daily returns histogram.

    Convenience wrapper for _plot_daily_returns with consistent interface.

    Args:
        equity: Equity curve array or series
        figsize: Figure size as (width, height) in inches
        title: Custom title for the plot
        savefig: Path to save figure (if provided)
        show: Whether to display the figure
        grayscale: Use grayscale colors instead of color
        **kwargs: Additional arguments passed to _plot_daily_returns

    Returns:
        Matplotlib Figure object

    Example:
        >>> equity = pd.Series([...], index=pd.date_range('2024-01-01', periods=100))
        >>> fig = plot_daily_returns(equity, title="Daily Return Distribution")
        >>> plt.show()
    """
    if title is None:
        title = "Daily Returns"

    # Convert to series if needed
    equity_series = equity if isinstance(equity, pd.Series) else pd.Series(equity)
    returns = equity_series.pct_change().dropna()

    # Create figure
    if figsize is None:
        figsize = (10, 6)

    fig, ax = plt.subplots(figsize=figsize)

    # Plot using the summary module function
    color_mode: Literal["color", "grayscale"] = "grayscale" if grayscale else "color"
    _plot_daily_returns(
        ax,
        returns,
        color_mode=color_mode,
        **kwargs,
    )

    # Set title
    ax.set_title(title, fontsize=14, fontweight="bold")

    if savefig:
        save_figure(fig, savefig)
        logger.info(f"Daily returns plot saved to {savefig}")

    if show:
        plt.show()

    return fig


def plot_distribution(
    equity: Union[np.ndarray, pd.Series],
    figsize: Optional[Tuple[float, float]] = None,
    title: Optional[str] = None,
    savefig: Optional[Union[str, Path]] = None,
    show: bool = True,
    grayscale: bool = False,
    **kwargs: Any,
) -> Figure:
    """Plot returns distribution with histogram and KDE.

    Convenience wrapper for _plot_distribution with consistent interface.

    Args:
        equity: Equity curve array or series
        figsize: Figure size as (width, height) in inches
        title: Custom title for the plot
        savefig: Path to save figure (if provided)
        show: Whether to display the figure
        grayscale: Use grayscale colors instead of color
        **kwargs: Additional arguments passed to _plot_distribution

    Returns:
        Matplotlib Figure object

    Example:
        >>> equity = np.array([10000, 10100, 10200, 10150, 10300])
        >>> fig = plot_distribution(equity, title="Return Distribution Analysis")
        >>> plt.show()
    """
    if title is None:
        title = "Returns Distribution"

    # Convert to series if needed
    equity_series = equity if isinstance(equity, pd.Series) else pd.Series(equity)
    returns = equity_series.pct_change().dropna()

    # Create figure
    if figsize is None:
        figsize = (10, 6)

    fig, ax = plt.subplots(figsize=figsize)

    # Plot using the distribution module function
    color_mode: Literal["color", "grayscale"] = "grayscale" if grayscale else "color"
    _plot_distribution(
        ax,
        returns,
        color_mode=color_mode,
        **kwargs,
    )

    # Set title
    ax.set_title(title, fontsize=14, fontweight="bold")

    if savefig:
        save_figure(fig, savefig)
        logger.info(f"Distribution plot saved to {savefig}")

    if show:
        plt.show()

    return fig
