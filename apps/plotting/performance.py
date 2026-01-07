"""Performance and equity chart plotting for backtest visualization.

This module provides functions for plotting equity curves, cumulative returns,
P&L charts, and returns distributions.

Features:
- Equity curve with optional benchmark comparison
- Cumulative returns chart
- Per-trade P&L bar chart with cumulative overlay
- Returns distribution histogram with normal curve
- Support for both Matplotlib and Bokeh backends
"""

from typing import Any, Dict, List, Literal, Optional, Union

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from apps.plotting.core import (
    BOKEH_AVAILABLE,
    _format_axis,
    _format_date_axis,
    _format_grid,
    _get_colors,
)

if BOKEH_AVAILABLE:
    from bokeh.models import HoverTool, NumeralTickFormatter, Span


def _plot_equity_curve(
    ax_or_figure: Union[Axes, Any],
    equity: pd.Series,
    benchmark: Optional[pd.Series] = None,
    backend: Literal["matplotlib", "bokeh"] = "matplotlib",
    color_mode: Literal["color", "grayscale"] = "color",
    smooth: bool = False,
    smooth_window: int = 5,
    **kwargs: Any,
) -> Union[Axes, Any]:
    """Plot equity curve showing account value over time.

    Args:
        ax_or_figure: Matplotlib axes or Bokeh figure
        equity: Equity series indexed by datetime
        benchmark: Optional benchmark equity series
        backend: Plotting backend ('matplotlib' or 'bokeh')
        color_mode: Color scheme ('color' or 'grayscale')
        smooth: Apply rolling average smoothing
        smooth_window: Window size for smoothing
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes or figure

    Example:
        >>> fig, ax = plt.subplots()
        >>> equity = pd.Series([10000, 10500, 11000], index=dates)
        >>> _plot_equity_curve(ax, equity)
    """
    # Validate input
    if len(equity) == 0:
        raise ValueError("Equity series is empty")

    colors = _get_colors(color_mode)

    # Apply smoothing if requested
    if smooth and len(equity) > smooth_window:
        equity_plot = equity.rolling(window=smooth_window, center=True).mean()
    else:
        equity_plot = equity

    if backend == "matplotlib":
        ax = ax_or_figure

        # Plot main equity curve
        ax.plot(
            mdates.date2num(equity_plot.index),
            equity_plot.values,
            label="Strategy",
            color=colors.get("profit", "#2ecc71"),
            linewidth=kwargs.get("linewidth", 2),
            alpha=kwargs.get("alpha", 0.9),
        )

        # Plot benchmark if provided
        if benchmark is not None:
            # Normalize benchmark to same starting point as strategy
            normalized_benchmark = benchmark * (equity.iloc[0] / benchmark.iloc[0])

            if smooth and len(normalized_benchmark) > smooth_window:
                benchmark_plot = normalized_benchmark.rolling(
                    window=smooth_window, center=True
                ).mean()
            else:
                benchmark_plot = normalized_benchmark

            ax.plot(
                mdates.date2num(benchmark_plot.index),
                benchmark_plot.values,
                label="Benchmark",
                color=colors.get("text", "#7f8c8d"),
                linewidth=kwargs.get("linewidth", 1.5),
                linestyle="--",
                alpha=0.7,
            )

        # Format axes
        _format_axis(
            ax,
            title=kwargs.get("title", "Equity Curve"),
            ylabel="Portfolio Value ($)",
        )
        _format_grid(ax)
        _format_date_axis(ax, equity_plot.index)

        # Add legend
        ax.legend(loc="upper left", fontsize=9)

        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

        return ax

    elif backend == "bokeh":
        if not BOKEH_AVAILABLE:
            raise ImportError("Bokeh is not installed. Use matplotlib backend.")

        p = ax_or_figure

        # Prepare data for Bokeh
        strategy_data = pd.DataFrame(
            {
                "date": equity_plot.index,
                "equity": equity_plot.values,
                "return_pct": (
                    (equity_plot - equity.iloc[0]) / equity.iloc[0] * 100
                ).values,
            }
        )

        # Plot main equity curve
        p.line(
            x="date",
            y="equity",
            source=strategy_data,
            legend_label="Strategy",
            color=colors.get("profit", "#2ecc71"),
            line_width=2,
            alpha=0.9,
        )

        # Add hover tool
        hover = HoverTool(
            tooltips=[
                ("Date", "@date{%F}"),
                ("Equity", "$@equity{0,0.00}"),
                ("Return", "@return_pct{0.00}%"),
            ],
            formatters={"@date": "datetime"},
        )
        p.add_tools(hover)

        # Plot benchmark if provided
        if benchmark is not None:
            normalized_benchmark = benchmark * (equity.iloc[0] / benchmark.iloc[0])

            if smooth and len(normalized_benchmark) > smooth_window:
                benchmark_plot = normalized_benchmark.rolling(
                    window=smooth_window, center=True
                ).mean()
            else:
                benchmark_plot = normalized_benchmark

            benchmark_data = pd.DataFrame(
                {"date": benchmark_plot.index, "equity": benchmark_plot.values}
            )

            p.line(
                x="date",
                y="equity",
                source=benchmark_data,
                legend_label="Benchmark",
                color=colors.get("text", "#7f8c8d"),
                line_width=1.5,
                line_dash="dashed",
                alpha=0.7,
            )

        # Format axes
        p.yaxis.formatter = NumeralTickFormatter(format="$0,0")
        p.yaxis.axis_label = "Portfolio Value ($)"
        p.xaxis.axis_label = "Date"

        return p

    else:
        raise ValueError(f"Unknown backend: {backend}")


def _plot_cumulative_returns(
    ax_or_figure: Union[Axes, Any],
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    backend: Literal["matplotlib", "bokeh"] = "matplotlib",
    color_mode: Literal["color", "grayscale"] = "color",
    start_at_zero: bool = True,
    **kwargs: Any,
) -> Union[Axes, Any]:
    """Plot cumulative returns over time.

    Args:
        ax_or_figure: Matplotlib axes or Bokeh figure
        returns: Returns series (not cumulative)
        benchmark_returns: Optional benchmark returns series
        backend: Plotting backend ('matplotlib' or 'bokeh')
        color_mode: Color scheme ('color' or 'grayscale')
        start_at_zero: Start y-axis at 0% (True) or 100% (False)
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes or figure

    Example:
        >>> fig, ax = plt.subplots()
        >>> returns = pd.Series([0.01, 0.02, -0.01], index=dates)
        >>> _plot_cumulative_returns(ax, returns)
    """
    colors = _get_colors(color_mode)

    # Calculate cumulative returns
    if start_at_zero:
        cum_returns = (1 + returns).cumprod() - 1
        multiplier = 100  # Convert to percentage
    else:
        cum_returns = (1 + returns).cumprod()
        multiplier = 100  # Convert to percentage for display

    if backend == "matplotlib":
        ax = ax_or_figure

        # Plot cumulative returns
        ax.plot(
            mdates.date2num(cum_returns.index),
            cum_returns.values * multiplier,
            label="Strategy",
            color=colors.get("profit", "#2ecc71"),
            linewidth=kwargs.get("linewidth", 2),
            alpha=kwargs.get("alpha", 0.9),
        )

        # Plot benchmark if provided
        if benchmark_returns is not None:
            if start_at_zero:
                cum_bench = (1 + benchmark_returns).cumprod() - 1
            else:
                cum_bench = (1 + benchmark_returns).cumprod()

            ax.plot(
                mdates.date2num(cum_bench.index),
                cum_bench.values * multiplier,
                label="Benchmark",
                color=colors.get("text", "#7f8c8d"),
                linewidth=kwargs.get("linewidth", 1.5),
                linestyle="--",
                alpha=0.7,
            )

        # Add zero reference line
        ax.axhline(
            y=0 if start_at_zero else 100,
            color="black",
            linestyle="-",
            alpha=0.3,
            linewidth=1,
        )

        # Format axes
        _format_axis(
            ax,
            title=kwargs.get("title", "Cumulative Returns"),
            ylabel="Cumulative Return (%)",
        )
        _format_grid(ax)
        _format_date_axis(ax, cum_returns.index)

        # Add legend
        ax.legend(loc="upper left", fontsize=9)

        # Format y-axis as percentage
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.1f}%"))

        return ax

    elif backend == "bokeh":
        if not BOKEH_AVAILABLE:
            raise ImportError("Bokeh is not installed. Use matplotlib backend.")

        p = ax_or_figure

        # Prepare data
        strategy_data = pd.DataFrame(
            {
                "date": cum_returns.index,
                "cum_return": cum_returns.values * multiplier,
            }
        )

        # Plot cumulative returns
        p.line(
            x="date",
            y="cum_return",
            source=strategy_data,
            legend_label="Strategy",
            color=colors.get("profit", "#2ecc71"),
            line_width=2,
            alpha=0.9,
        )

        # Add hover tool
        hover = HoverTool(
            tooltips=[
                ("Date", "@date{%F}"),
                ("Cum. Return", "@cum_return{0.00}%"),
            ],
            formatters={"@date": "datetime"},
        )
        p.add_tools(hover)

        # Plot benchmark if provided
        if benchmark_returns is not None:
            if start_at_zero:
                cum_bench = (1 + benchmark_returns).cumprod() - 1
            else:
                cum_bench = (1 + benchmark_returns).cumprod()

            benchmark_data = pd.DataFrame(
                {"date": cum_bench.index, "cum_return": cum_bench.values * multiplier}
            )

            p.line(
                x="date",
                y="cum_return",
                source=benchmark_data,
                legend_label="Benchmark",
                color=colors.get("text", "#7f8c8d"),
                line_width=1.5,
                line_dash="dashed",
                alpha=0.7,
            )

        # Add zero reference line
        zero_line = Span(
            location=0 if start_at_zero else 100,
            dimension="width",
            line_color="black",
            line_alpha=0.3,
            line_width=1,
        )
        p.add_layout(zero_line)

        # Format axes
        p.yaxis.axis_label = "Cumulative Return (%)"
        p.xaxis.axis_label = "Date"

        return p

    else:
        raise ValueError(f"Unknown backend: {backend}")


def _plot_pl(
    ax_or_figure: Union[Axes, Any],
    trades: List[Dict[str, Any]],
    backend: Literal["matplotlib", "bokeh"] = "matplotlib",
    color_mode: Literal["color", "grayscale"] = "color",
    by_date: bool = True,
    show_cumulative: bool = True,
    **kwargs: Any,
) -> Union[Axes, Any]:
    """Plot per-trade P&L as bars with optional cumulative line.

    Args:
        ax_or_figure: Matplotlib axes or Bokeh figure
        trades: List of trade dictionaries with 'pl' and 'exit_time'
        backend: Plotting backend ('matplotlib' or 'bokeh')
        color_mode: Color scheme ('color' or 'grayscale')
        by_date: X-axis by exit date (True) or trade number (False)
        show_cumulative: Show cumulative P&L line overlay
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes or figure

    Example:
        >>> trades = [{'pl': 100, 'exit_time': date1}, {'pl': -50, 'exit_time': date2}]
        >>> _plot_pl(ax, trades)
    """
    if not trades:
        return ax_or_figure

    if backend == "matplotlib":
        return _plot_pl_matplotlib(
            ax_or_figure,
            trades,
            color_mode=color_mode,
            by_date=by_date,
            show_cumulative=show_cumulative,
            **kwargs,
        )
    elif backend == "bokeh":
        if not BOKEH_AVAILABLE:
            raise ImportError("Bokeh is not installed. Use matplotlib backend.")
        return _plot_pl_bokeh(
            ax_or_figure,
            trades,
            color_mode=color_mode,
            by_date=by_date,
            show_cumulative=show_cumulative,
            **kwargs,
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _plot_pl_matplotlib(
    ax: Axes,
    trades: List[Dict[str, Any]],
    color_mode: Literal["color", "grayscale"] = "color",
    by_date: bool = True,
    show_cumulative: bool = True,
    **kwargs: Any,
) -> Axes:
    """Plot P&L using Matplotlib."""
    colors = _get_colors(color_mode)

    # Extract P&L and dates
    pls = np.array([t.get("pl", 0) for t in trades])
    exit_times = [t.get("exit_time") for t in trades]

    # Cumulative P&L
    cum_pl = np.cumsum(pls)

    if by_date:
        x_values = mdates.date2num(exit_times)
        bar_width = kwargs.get("bar_width", 0.8)
    else:
        x_values = np.arange(len(pls))
        bar_width = kwargs.get("bar_width", 0.8)

    # Plot bars
    bar_colors = [
        (colors.get("profit", "#2ecc71") if pl >= 0 else colors.get("loss", "#e74c3c"))
        for pl in pls
    ]

    ax.bar(
        x_values,
        pls,
        width=bar_width,
        color=bar_colors,
        alpha=0.7,
        label="Trade P&L",
    )

    # Plot cumulative line if requested
    if show_cumulative:
        ax2 = ax.twinx()
        ax2.plot(
            x_values,
            cum_pl,
            color=colors.get("text", "#34495e"),
            linewidth=2,
            marker="o",
            markersize=4,
            label="Cumulative P&L",
            alpha=0.8,
        )
        ax2.set_ylabel("Cumulative P&L ($)", color=colors.get("text", "#34495e"))
        ax2.tick_params(axis="y", labelcolor=colors.get("text", "#34495e"))
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))
        ax2.legend(loc="upper right", fontsize=9)

    # Add zero reference line
    ax.axhline(y=0, color="black", linestyle="-", alpha=0.3, linewidth=1)

    # Format axes
    if by_date:
        _format_date_axis(ax, pd.DatetimeIndex(exit_times))
        ax.set_xlabel("Exit Date")
    else:
        ax.set_xlabel("Trade Number")

    _format_axis(ax, title=kwargs.get("title", "Trade P&L"), ylabel="P&L ($)")
    _format_grid(ax, alpha=0.3)

    # Format y-axis as currency
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

    # Add legend for bars
    ax.legend(loc="upper left", fontsize=9)

    return ax


def _plot_pl_bokeh(
    p: Any,
    trades: List[Dict[str, Any]],
    color_mode: Literal["color", "grayscale"] = "color",
    by_date: bool = True,
    show_cumulative: bool = True,
    **kwargs: Any,
) -> Any:
    """Plot P&L using Bokeh."""
    colors = _get_colors(color_mode)

    # Extract P&L and dates
    pls = np.array([t.get("pl", 0) for t in trades])
    exit_times = [t.get("exit_time") for t in trades]
    cum_pl = np.cumsum(pls)

    # Prepare data
    if by_date:
        x_values = exit_times
    else:
        x_values = list(range(len(pls)))

    pl_data = pd.DataFrame(
        {
            "x": x_values,
            "pl": pls,
            "cum_pl": cum_pl,
            "color": [
                (
                    colors.get("profit", "#2ecc71")
                    if pl >= 0
                    else colors.get("loss", "#e74c3c")
                )
                for pl in pls
            ],
            "trade_num": list(range(1, len(pls) + 1)),
        }
    )

    # Plot bars
    p.vbar(
        x="x",
        top="pl",
        width=kwargs.get("bar_width", 0.8),
        source=pl_data,
        color="color",
        alpha=0.7,
        legend_label="Trade P&L",
    )

    # Add hover tool
    hover = HoverTool(
        tooltips=[
            ("Trade", "@trade_num"),
            ("P&L", "$@pl{0,0.00}"),
            ("Cumulative", "$@cum_pl{0,0.00}"),
        ]
    )
    p.add_tools(hover)

    # Plot cumulative line if requested
    if show_cumulative:
        p.line(
            x="x",
            y="cum_pl",
            source=pl_data,
            color=colors.get("text", "#34495e"),
            line_width=2,
            legend_label="Cumulative P&L",
            alpha=0.8,
        )

    # Add zero reference line
    zero_line = Span(
        location=0,
        dimension="width",
        line_color="black",
        line_alpha=0.3,
        line_width=1,
    )
    p.add_layout(zero_line)

    # Format axes
    p.yaxis.formatter = NumeralTickFormatter(format="$0,0")
    p.yaxis.axis_label = "P&L ($)"

    if by_date:
        p.xaxis.axis_label = "Exit Date"
    else:
        p.xaxis.axis_label = "Trade Number"

    return p


def _plot_returns_distribution(
    ax: Axes,
    returns: pd.Series,
    bins: int = 50,
    show_normal: bool = True,
    show_stats: bool = True,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Axes:
    """Plot histogram of returns with optional normal distribution overlay.

    Args:
        ax: Matplotlib axes
        returns: Returns series
        bins: Number of histogram bins
        show_normal: Overlay normal distribution curve
        show_stats: Show mean and std dev lines
        color_mode: Color scheme ('color' or 'grayscale')
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes

    Example:
        >>> fig, ax = plt.subplots()
        >>> returns = pd.Series([0.01, 0.02, -0.01, 0.015])
        >>> _plot_returns_distribution(ax, returns)
    """
    colors = _get_colors(color_mode)

    # Convert to percentage
    returns_pct = returns * 100

    # Create histogram
    n, bins_edges, patches = ax.hist(
        returns_pct,
        bins=bins,
        density=True,
        alpha=0.7,
        edgecolor="black",
        linewidth=0.5,
    )

    # Color bars by positive/negative
    for i, patch in enumerate(patches):
        if bins_edges[i] < 0:
            patch.set_facecolor(colors.get("loss", "#e74c3c"))
        else:
            patch.set_facecolor(colors.get("profit", "#2ecc71"))

    # Overlay normal distribution if requested
    if show_normal:
        mu = returns_pct.mean()
        sigma = returns_pct.std()

        x = np.linspace(returns_pct.min(), returns_pct.max(), 100)
        # Calculate normal distribution PDF manually
        y = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

        ax.plot(
            x,
            y,
            color=colors.get("text", "#34495e"),
            linewidth=2,
            linestyle="--",
            label="Normal Distribution",
            alpha=0.8,
        )

    # Show statistics lines if requested
    if show_stats:
        mu = returns_pct.mean()
        sigma = returns_pct.std()

        # Mean line
        ax.axvline(
            mu,
            color=colors.get("text", "#34495e"),
            linestyle="-",
            linewidth=2,
            label=f"Mean: {mu:.2f}%",
            alpha=0.7,
        )

        # Std dev lines
        ax.axvline(
            mu + sigma,
            color=colors.get("text", "#7f8c8d"),
            linestyle=":",
            linewidth=1.5,
            label=f"±1σ: {sigma:.2f}%",
            alpha=0.6,
        )
        ax.axvline(
            mu - sigma,
            color=colors.get("text", "#7f8c8d"),
            linestyle=":",
            linewidth=1.5,
            alpha=0.6,
        )

    # Add summary statistics as text annotation
    if show_stats:
        stats_text = (
            f"Mean: {returns_pct.mean():.2f}%\n"
            f"Std Dev: {returns_pct.std():.2f}%\n"
            f"Skew: {returns_pct.skew():.2f}\n"
            f"Kurtosis: {returns_pct.kurtosis():.2f}"
        )
        ax.text(
            0.02,
            0.98,
            stats_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="top",
            bbox={
                "boxstyle": "round",
                "facecolor": "white",
                "alpha": 0.8,
                "edgecolor": colors.get("text", "#7f8c8d"),
            },
        )

    # Format axes
    _format_axis(
        ax,
        title=kwargs.get("title", "Returns Distribution"),
        xlabel="Return (%)",
        ylabel="Density",
    )
    _format_grid(ax, alpha=0.3)

    # Add legend
    if show_normal or show_stats:
        ax.legend(loc="upper right", fontsize=9)

    return ax


__all__ = [
    "_plot_equity_curve",
    "_plot_cumulative_returns",
    "_plot_pl",
    "_plot_returns_distribution",
]
