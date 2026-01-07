"""Main plotting module for backtest results visualization.

This module provides the primary plot() function that creates comprehensive
visualizations of backtest results, including:
- OHLC/Candlestick charts
- Equity curves
- Trade markers (entry/exit points)
- Volume bars
- Drawdown plots
- Performance metrics

The plotting system supports both Matplotlib (static) and Bokeh (interactive)
backends, with automatic layout management and data preparation.
"""

import warnings
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from apps.plotting.core import (
    TRADING_COLORS,
    _create_figure,
    _format_axis,
    _format_date_axis,
    _format_grid,
    _format_legend,
    save_figure,
)


def plot(
    results: Dict[str, Any],
    filename: Optional[str] = None,
    plot_width: int = 1200,
    plot_height: int = 800,
    plot_equity: bool = True,
    plot_returns: bool = False,
    plot_drawdown: bool = False,
    plot_trades: bool = True,
    plot_indicators: bool = False,
    show_legend: bool = True,
    backend: str = "matplotlib",
    figsize: Optional[Tuple[float, float]] = None,
    **kwargs: Any,
) -> Union[Figure, Any]:
    """Plot backtest results with comprehensive visualizations.

    This is the main entry point for plotting backtest results. It creates
    a multi-panel chart showing price data, equity curve, trades, and other
    relevant information.

    Args:
        results: Results dictionary from Backtest.run() containing:
            - 'broker': Broker instance with equity and trade data
            - 'strategy': Strategy instance with data and indicators
            - 'equity': Equity curve array
            - 'trades': Tuple of closed trades
            - 'stats': Statistics dictionary
        filename: Optional output filename for saving the plot
        plot_width: Plot width in pixels (for Bokeh) or inches (for matplotlib)
        plot_height: Plot height in pixels (for Bokeh) or inches (for matplotlib)
        plot_equity: Whether to plot equity curve
        plot_returns: Whether to plot returns distribution
        plot_drawdown: Whether to plot drawdown chart
        plot_trades: Whether to plot trade entry/exit markers
        plot_indicators: Whether to plot strategy indicators
        show_legend: Whether to show legend
        backend: Plotting backend ('matplotlib' or 'bokeh')
        figsize: Figure size as (width, height) in inches (overrides plot_width/height)
        **kwargs: Additional plotting options

    Returns:
        Matplotlib Figure or Bokeh figure object

    Raises:
        ValueError: If results dict is missing required keys
        ValueError: If backend is not supported

    Example:
        >>> bt = Backtest(data, strategy=MyStrategy, cash=10000)
        >>> results = bt.run()
        >>> fig = plot(results, filename='backtest_results.png')
    """
    # Validate results
    if not isinstance(results, dict):
        raise ValueError("results must be a dictionary")

    required_keys = {"broker", "strategy"}
    missing_keys = required_keys - set(results.keys())
    if missing_keys:
        raise ValueError(f"results missing required keys: {missing_keys}")

    # Validate backend
    if backend not in ("matplotlib", "bokeh"):
        raise ValueError(f"Unsupported backend: {backend}. Use 'matplotlib' or 'bokeh'")

    # Extract data from results
    data_dict = _extract_data(results)

    # Determine plot layout
    panels = _determine_layout(
        plot_equity=plot_equity,
        plot_returns=plot_returns,
        plot_drawdown=plot_drawdown,
        has_ohlc=data_dict["ohlc"] is not None,
    )

    # Create plots based on backend
    if backend == "matplotlib":
        fig = _plot_matplotlib(
            data_dict=data_dict,
            panels=panels,
            plot_trades=plot_trades,
            plot_indicators=plot_indicators,
            show_legend=show_legend,
            figsize=figsize,
            **kwargs,
        )

        # Save if filename provided
        if filename:
            save_figure(fig, filename)

        return fig
    else:  # bokeh
        warnings.warn(
            "Bokeh backend not yet fully implemented, falling back to matplotlib",
            stacklevel=2,
        )
        return plot(results, filename, backend="matplotlib", **kwargs)


def _extract_data(results: Dict[str, Any]) -> Dict[str, Any]:
    """Extract plotting data from results dictionary.

    Args:
        results: Results from Backtest.run()

    Returns:
        Dictionary containing extracted data:
            - ohlc: OHLC DataFrame (if available)
            - equity: Equity curve array
            - dates: DatetimeIndex
            - trades: List of trade dictionaries
            - indicators: Dictionary of indicator data
            - drawdown: Drawdown series (if available)
    """
    broker = results["broker"]
    strategy = results["strategy"]

    # Extract OHLC data from strategy's data object
    ohlc = None
    dates = None
    if hasattr(strategy, "data") and hasattr(strategy.data, "df"):
        df = strategy.data.df
        if all(col in df.columns for col in ["Open", "High", "Low", "Close"]):
            ohlc = df[["Open", "High", "Low", "Close"]]
            if "Volume" in df.columns:
                ohlc = df[["Open", "High", "Low", "Close", "Volume"]]
            dates = df.index

    # Extract equity curve
    equity = broker.equity if hasattr(broker, "equity") else None

    # Extract trades
    trades_list = []
    if hasattr(broker, "closed_trades"):
        for trade in broker.closed_trades:
            trades_list.append(
                {
                    "entry_time": trade.entry_time,
                    "exit_time": trade.exit_time,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "size": trade.size,
                    "pl": trade.pl,
                    "pl_pct": trade.pl_pct,
                    "is_long": trade.is_long,
                }
            )

    # Extract indicators (if requested)
    indicators = {}
    if hasattr(strategy, "_indicators"):
        for ind in strategy._indicators:
            if hasattr(ind, "name"):
                indicators[ind.name] = ind

    # Calculate drawdown if we have equity
    drawdown = None
    if equity is not None and len(equity) > 0:
        equity_series = pd.Series(equity)
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max

    return {
        "ohlc": ohlc,
        "equity": equity,
        "dates": dates,
        "trades": trades_list,
        "indicators": indicators,
        "drawdown": drawdown,
    }


def _determine_layout(
    plot_equity: bool,
    plot_returns: bool,
    plot_drawdown: bool,
    has_ohlc: bool,
) -> List[str]:
    """Determine which panels to plot based on parameters.

    Args:
        plot_equity: Whether to include equity panel
        plot_returns: Whether to include returns panel
        plot_drawdown: Whether to include drawdown panel
        has_ohlc: Whether OHLC data is available

    Returns:
        List of panel names in order from top to bottom
    """
    panels = []

    if has_ohlc:
        panels.append("ohlc")

    if plot_equity:
        panels.append("equity")

    if plot_drawdown:
        panels.append("drawdown")

    if plot_returns:
        panels.append("returns")

    # If no panels specified and no OHLC, at least show equity
    if not panels:
        panels.append("equity")

    return panels


def _plot_matplotlib(
    data_dict: Dict[str, Any],
    panels: List[str],
    plot_trades: bool,
    plot_indicators: bool,
    show_legend: bool,
    figsize: Optional[Tuple[float, float]],
    **kwargs: Any,
) -> Figure:
    """Create matplotlib visualization of backtest results.

    Args:
        data_dict: Extracted data dictionary
        panels: List of panels to plot
        plot_trades: Whether to plot trade markers
        plot_indicators: Whether to plot indicators
        show_legend: Whether to show legend
        figsize: Figure size (width, height) in inches
        **kwargs: Additional plotting options

    Returns:
        Matplotlib Figure object
    """
    num_panels = len(panels)

    # Calculate height ratios
    height_ratios = _calculate_height_ratios(panels)

    # Determine figure size
    if figsize is None:
        width = 14
        height = 4 * num_panels
        figsize = (width, height)

    # Create figure with subplots
    fig, axes = _create_figure(
        nrows=num_panels,
        ncols=1,
        figsize=figsize,
        sharex=True,
        gridspec_kw={"height_ratios": height_ratios},
    )

    # Handle single subplot case
    if num_panels == 1:
        axes = [axes]

    # Plot each panel
    for idx, panel_name in enumerate(panels):
        ax = axes[idx]

        if panel_name == "ohlc":
            _plot_ohlc_panel(
                ax, data_dict, plot_trades, plot_indicators, show_legend, **kwargs
            )
        elif panel_name == "equity":
            _plot_equity_panel(ax, data_dict, show_legend, **kwargs)
        elif panel_name == "drawdown":
            _plot_drawdown_panel(ax, data_dict, **kwargs)
        elif panel_name == "returns":
            _plot_returns_panel(ax, data_dict, **kwargs)

        # Format date axis for bottom panel
        if idx == num_panels - 1 and data_dict["dates"] is not None:
            _format_date_axis(ax, data_dict["dates"])

    fig.tight_layout()
    return fig


def _calculate_height_ratios(panels: List[str]) -> List[float]:
    """Calculate height ratios for subplot panels.

    Args:
        panels: List of panel names

    Returns:
        List of height ratios summing to appropriate total
    """
    ratios = []
    for panel in panels:
        if panel == "ohlc":
            ratios.append(3.0)  # OHLC gets most space
        elif panel == "equity":
            ratios.append(1.5)  # Equity gets moderate space
        elif panel == "drawdown":
            ratios.append(1.0)  # Drawdown gets less space
        elif panel == "returns":
            ratios.append(1.5)  # Returns histogram needs moderate space
        else:
            ratios.append(1.0)  # Default

    return ratios


def _plot_ohlc_panel(
    ax: plt.Axes,
    data_dict: Dict[str, Any],
    plot_trades: bool,
    plot_indicators: bool,
    show_legend: bool,
    **kwargs: Any,
) -> None:
    """Plot OHLC/candlestick panel.

    Args:
        ax: Matplotlib axes
        data_dict: Data dictionary
        plot_trades: Whether to plot trade markers
        plot_indicators: Whether to plot indicators
        show_legend: Whether to show legend
        **kwargs: Additional options
    """
    ohlc = data_dict["ohlc"]
    dates = data_dict["dates"]

    if ohlc is None or dates is None:
        return

    # Simple line chart for close prices (candlesticks require more complex rendering)
    ax.plot(
        dates,
        ohlc["Close"],
        color=TRADING_COLORS["neutral"],
        linewidth=1.5,
        label="Close",
    )

    # Plot trade markers if requested
    if plot_trades and data_dict["trades"]:
        _plot_trade_markers(ax, data_dict["trades"])

    _format_axis(ax, title="Price Chart", ylabel="Price")
    _format_grid(ax)

    if show_legend:
        _format_legend(ax)


def _plot_trade_markers(ax: plt.Axes, trades: List[Dict[str, Any]]) -> None:
    """Plot trade entry and exit markers on price chart.

    Args:
        ax: Matplotlib axes
        trades: List of trade dictionaries
    """
    entry_long_times = []
    entry_long_prices = []
    entry_short_times = []
    entry_short_prices = []
    exit_profit_times = []
    exit_profit_prices = []
    exit_loss_times = []
    exit_loss_prices = []

    for trade in trades:
        # Entry markers
        if trade["is_long"]:
            entry_long_times.append(trade["entry_time"])
            entry_long_prices.append(trade["entry_price"])
        else:
            entry_short_times.append(trade["entry_time"])
            entry_short_prices.append(trade["entry_price"])

        # Exit markers
        if trade["pl"] > 0:
            exit_profit_times.append(trade["exit_time"])
            exit_profit_prices.append(trade["exit_price"])
        else:
            exit_loss_times.append(trade["exit_time"])
            exit_loss_prices.append(trade["exit_price"])

    # Plot entry markers
    if entry_long_times:
        ax.scatter(
            entry_long_times,
            entry_long_prices,
            marker="^",
            color=TRADING_COLORS["long_entry"],
            s=100,
            label="Long Entry",
            zorder=5,
        )

    if entry_short_times:
        ax.scatter(
            entry_short_times,
            entry_short_prices,
            marker="v",
            color=TRADING_COLORS["short_entry"],
            s=100,
            label="Short Entry",
            zorder=5,
        )

    # Plot exit markers
    if exit_profit_times:
        ax.scatter(
            exit_profit_times,
            exit_profit_prices,
            marker="o",
            color=TRADING_COLORS["profit"],
            s=80,
            label="Profitable Exit",
            zorder=5,
            alpha=0.7,
        )

    if exit_loss_times:
        ax.scatter(
            exit_loss_times,
            exit_loss_prices,
            marker="o",
            color=TRADING_COLORS["loss"],
            s=80,
            label="Loss Exit",
            zorder=5,
            alpha=0.7,
        )


def _plot_equity_panel(
    ax: plt.Axes,
    data_dict: Dict[str, Any],
    show_legend: bool,
    **kwargs: Any,
) -> None:
    """Plot equity curve panel.

    Args:
        ax: Matplotlib axes
        data_dict: Data dictionary
        show_legend: Whether to show legend
        **kwargs: Additional options
    """
    equity = data_dict["equity"]
    dates = data_dict["dates"]

    if equity is None:
        return

    # Use dates if available, otherwise use index
    x_values = dates if dates is not None else np.arange(len(equity))

    ax.plot(
        x_values,
        equity,
        color=TRADING_COLORS["profit"],
        linewidth=2,
        label="Equity",
    )

    # Fill area under curve
    if dates is not None:
        if isinstance(equity, pd.Series):
            baseline = equity.iloc[0]
        elif hasattr(equity, "__getitem__"):
            baseline = equity[0]
        else:
            baseline = equity
        ax.fill_between(
            x_values,
            equity,
            baseline,
            alpha=0.1,
            color=TRADING_COLORS["profit"],
        )

    _format_axis(ax, title="Portfolio Equity", ylabel="Equity ($)")
    _format_grid(ax)

    if show_legend:
        _format_legend(ax)


def _plot_drawdown_panel(
    ax: plt.Axes,
    data_dict: Dict[str, Any],
    **kwargs: Any,
) -> None:
    """Plot drawdown (underwater) panel.

    Args:
        ax: Matplotlib axes
        data_dict: Data dictionary
        **kwargs: Additional options
    """
    drawdown = data_dict["drawdown"]
    dates = data_dict["dates"]

    if drawdown is None:
        return

    # Use dates if available, otherwise use index
    x_values = dates if dates is not None else np.arange(len(drawdown))

    ax.fill_between(
        x_values,
        drawdown * 100,  # Convert to percentage
        0,
        color=TRADING_COLORS["loss"],
        alpha=0.3,
    )
    ax.plot(
        x_values,
        drawdown * 100,
        color=TRADING_COLORS["loss"],
        linewidth=1.5,
    )
    ax.axhline(0, color="black", linewidth=0.5)

    _format_axis(ax, title="Drawdown", ylabel="Drawdown (%)")
    _format_grid(ax)


def _plot_returns_panel(
    ax: plt.Axes,
    data_dict: Dict[str, Any],
    **kwargs: Any,
) -> None:
    """Plot returns distribution panel.

    Args:
        ax: Matplotlib axes
        data_dict: Data dictionary
        **kwargs: Additional options
    """
    equity = data_dict["equity"]

    if equity is None or len(equity) < 2:
        return

    # Calculate returns
    returns = np.diff(equity) / equity[:-1]

    # Plot histogram
    n, bins, patches = ax.hist(returns, bins=30, edgecolor="black", alpha=0.7)

    # Color bars by positive/negative
    for i, patch in enumerate(patches):
        if bins[i] < 0:
            patch.set_facecolor(TRADING_COLORS["loss"])
        else:
            patch.set_facecolor(TRADING_COLORS["profit"])

    ax.axvline(0, color="black", linewidth=1)

    _format_axis(ax, title="Returns Distribution", xlabel="Return", ylabel="Frequency")
    _format_grid(ax)


__all__ = ["plot"]
