"""Performance summary plotting functions for backtest visualization.

This module provides comprehensive summary visualizations including:
- Snapshot/tearsheet summaries with multiple panels
- Yearly returns bar charts
- Daily returns charts with volatility bands

Features:
- Multi-panel snapshot layouts (2x2 or 3x2 grids)
- Yearly aggregated returns with benchmark comparison
- Daily returns visualization with statistical bands
- Grayscale mode support
- Customizable figure sizes and styling
"""

from typing import Any, Dict, Literal, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .core import _format_axis, _format_date_axis, _format_grid, _get_colors

# Import other plotting functions for snapshot
from .distribution import _plot_histogram
from .drawdown import _plot_drawdown
from .heatmap import _plot_monthly_heatmap
from .performance import _plot_cumulative_returns
from .rolling import _plot_rolling_sharpe


def _get_snapshot_layout_params(
    layout: str,
) -> Tuple[int, int, Tuple[float, float]]:
    """Get layout parameters based on layout name."""
    if layout == "2x2":
        return 2, 2, (14, 10)
    elif layout == "3x2":
        return 3, 2, (14, 14)
    elif layout == "2x3":
        return 2, 3, (18, 10)
    else:
        raise ValueError(f"Invalid layout: {layout}. Must be '2x2', '3x2', or '2x3'")


def plot_snapshot(
    returns: pd.Series,
    metrics: Optional[Dict[str, Any]] = None,
    benchmark_returns: Optional[pd.Series] = None,
    layout: Literal["2x2", "3x2", "2x3"] = "3x2",
    color_mode: Literal["color", "grayscale"] = "color",
    figsize: Optional[Tuple[float, float]] = None,
    title: Optional[str] = None,
    save_path: Optional[str] = None,
    show: bool = True,
    **kwargs: Any,
) -> Figure:
    """Create a comprehensive snapshot/tearsheet summary of backtest performance.

    Creates a multi-panel visualization combining:
    - Cumulative returns chart
    - Key metrics table
    - Returns distribution histogram
    - Monthly returns heatmap
    - Drawdown chart (optional)
    - Rolling Sharpe ratio (optional)

    Args:
        returns: Returns series (not cumulative)
        metrics: Dictionary of key performance metrics to display
        benchmark_returns: Optional benchmark returns for comparison
        layout: Grid layout - '2x2', '3x2', or '2x3'
        color_mode: 'color' for full colors, 'grayscale' for monochrome
        figsize: Figure size (width, height) in inches
        title: Overall title for the snapshot
        save_path: Path to save figure (if None, not saved)
        show: Whether to display the figure
        **kwargs: Additional arguments

    Returns:
        Matplotlib Figure object

    Example:
        >>> snapshot_fig = plot_snapshot(
        ...     returns=strategy_returns,
        ...     metrics={'Sharpe': 1.5, 'Max DD': -0.15},
        ...     layout='3x2'
        ... )
    """
    # colors = _get_colors(color_mode)  # Unused

    # Determine layout dimensions
    nrows, ncols, default_figsize = _get_snapshot_layout_params(layout)

    if figsize is None:
        figsize = default_figsize

    # Create figure with subplots
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    gs = fig.add_gridspec(nrows, ncols, hspace=0.3, wspace=0.3)

    # Add overall title
    if title:
        fig.suptitle(title, fontsize=16, fontweight="bold", y=0.995)
    else:
        # Default title with date range
        start_date = returns.index[0].strftime("%Y-%m-%d")
        end_date = returns.index[-1].strftime("%Y-%m-%d")
        fig.suptitle(
            f"Performance Summary ({start_date} to {end_date})",
            fontsize=16,
            fontweight="bold",
            y=0.995,
        )

    # Panel 1: Cumulative Returns
    ax1 = fig.add_subplot(gs[0, :])  # Top row, full width
    _plot_cumulative_returns(
        ax1,
        returns,
        benchmark_returns=benchmark_returns,
        backend="matplotlib",
        color_mode=color_mode,
        start_at_zero=True,
    )
    _format_axis(ax1, title="Cumulative Returns", ylabel="Return (%)")
    _format_grid(ax1)

    # Panel 2: Key Metrics Table
    ax2 = fig.add_subplot(gs[1, 0])
    _plot_metrics_table(ax2, metrics or {}, color_mode=color_mode)

    # Panel 3: Returns Distribution
    ax3 = fig.add_subplot(gs[1, 1])
    _plot_histogram(
        ax3,
        returns,
        bins=50,
        show_normal=True,
        show_stats=True,
        color_mode=color_mode,
    )
    _format_axis(ax3, title="Returns Distribution", xlabel="Return", ylabel="Frequency")
    _format_grid(ax3)

    # Panel 4: Monthly Returns Heatmap
    if nrows >= 3:
        ax4 = fig.add_subplot(gs[2, :])  # Bottom row, full width
        _plot_monthly_heatmap(
            ax4,
            returns,
            color_mode=color_mode,
            show_ytd=True,
        )

    # Optional panels for 3x2 or 2x3 layouts
    if layout == "3x2" and nrows >= 3:
        # Add drawdown chart if we have space
        # (Already used row 2 for heatmap, could add more if needed)
        pass
    elif layout == "2x3" and ncols >= 3:
        # Panel 5: Drawdown
        ax5 = fig.add_subplot(gs[0, 2])
        cumulative_returns = (1 + returns).cumprod()
        equity = cumulative_returns * 100000  # Assume $100k starting
        _plot_drawdown(
            ax5,
            equity,
            backend="matplotlib",
            color_mode=color_mode,
        )
        _format_axis(ax5, title="Drawdown", ylabel="Drawdown (%)")
        _format_grid(ax5)

        # Panel 6: Rolling Sharpe
        ax6 = fig.add_subplot(gs[1, 2])
        _plot_rolling_sharpe(
            ax6,
            returns,
            window=60,
            backend="matplotlib",
            color_mode=color_mode,
        )
        _format_axis(ax6, title="Rolling Sharpe (60-day)", ylabel="Sharpe Ratio")
        _format_grid(ax6)

    # Save if requested
    if save_path:
        from .core import save_figure

        save_figure(fig, save_path, formats=["png"], dpi=150)

    # Show if requested
    if show:
        plt.show()

    return fig


def _format_metric_value(value: Any) -> str:
    """Format metric value for display in table."""
    if isinstance(value, (int, float)):
        if abs(value) < 1 and value != 0:
            return f"{value:.4f}"
        elif abs(value) < 100:
            return f"{value:.2f}"
        else:
            return f"{value:,.0f}"
    return str(value)


def _plot_metrics_table(
    ax: Axes,
    metrics: Dict[str, Any],
    color_mode: Literal["color", "grayscale"] = "color",
) -> None:
    """Plot key metrics as a formatted table.

    Args:
        ax: Matplotlib axes to plot on
        metrics: Dictionary of metric names and values
        color_mode: Color mode for styling
    """
    # colors = _get_colors(color_mode)  # Unused

    # Hide axes
    ax.axis("off")

    if not metrics:
        ax.text(
            0.5,
            0.5,
            "No metrics provided",
            ha="center",
            va="center",
            fontsize=12,
            color="gray",
        )
        return

    # Prepare table data
    table_data = []
    # Prepare table data
    table_data = [[key, _format_metric_value(value)] for key, value in metrics.items()]

    # Create table
    table = ax.table(
        cellText=table_data,
        colLabels=["Metric", "Value"],
        cellLoc="left",
        loc="center",
        colWidths=[0.6, 0.4],
    )

    # Style table
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    # Color header
    for i in range(2):
        cell = table[(0, i)]
        if color_mode == "color":
            cell.set_facecolor("#3498db")
            cell.set_text_props(weight="bold", color="white")
        else:
            cell.set_facecolor("#5a5a5a")
            cell.set_text_props(weight="bold", color="white")

    # Alternate row colors
    for i in range(1, len(table_data) + 1):
        for j in range(2):
            cell = table[(i, j)]
            if i % 2 == 0:
                cell.set_facecolor("#f9f9f9")
            else:
                cell.set_facecolor("white")

    ax.set_title("Key Metrics", fontsize=12, fontweight="bold", pad=10)


def _plot_yearly_returns(
    ax: Axes,
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    color_mode: Literal["color", "grayscale"] = "color",
    show_values: bool = True,
    show_average: bool = True,
    **kwargs: Any,
) -> None:
    """Plot yearly aggregated returns as a bar chart.

    Creates a bar chart showing annual returns, optionally compared with
    a benchmark. Bars are colored by positive/negative returns.

    Args:
        ax: Matplotlib axes to plot on
        returns: Returns series (not cumulative)
        benchmark_returns: Optional benchmark returns for comparison
        color_mode: 'color' for full colors, 'grayscale' for monochrome
        show_values: Show return values on top of bars
        show_average: Add horizontal line showing average return
        **kwargs: Additional arguments

    Example:
        >>> fig, ax = plt.subplots()
        >>> _plot_yearly_returns(ax, returns, show_average=True)
    """
    colors = _get_colors(color_mode)

    # Aggregate returns by year
    yearly_returns = returns.resample("YE").apply(lambda x: (1 + x).prod() - 1)

    # Extract year from datetime index and create new series with year index
    years_int = yearly_returns.index.year
    yearly_returns = pd.Series(yearly_returns.values, index=years_int)

    # Prepare data for plotting
    years = yearly_returns.index.astype(str)
    values = yearly_returns.values * 100  # Convert to percentage

    # Determine bar colors
    bar_colors = [colors["profit"] if v >= 0 else colors["loss"] for v in values]

    # Plot strategy returns
    x_pos = np.arange(len(years))
    width = 0.35 if benchmark_returns is not None else 0.6

    bars1 = ax.bar(
        x_pos if benchmark_returns is None else x_pos - width / 2,
        values,
        width,
        color=bar_colors,
        alpha=0.8,
        label="Strategy",
        edgecolor="black",
        linewidth=0.5,
    )

    # Plot benchmark returns if provided
    if benchmark_returns is not None:
        bench_yearly = benchmark_returns.resample("YE").apply(
            lambda x: (1 + x).prod() - 1
        )
        # Extract year from datetime index and create new series with year index
        bench_years_int = bench_yearly.index.year
        bench_yearly = pd.Series(bench_yearly.values, index=bench_years_int)
        bench_values = bench_yearly.values * 100

        bench_colors = [
            colors["profit"] if v >= 0 else colors["loss"] for v in bench_values
        ]

        # bars2 unused
        ax.bar(
            x_pos + width / 2,
            bench_values,
            width,
            color=bench_colors,
            alpha=0.5,
            label="Benchmark",
            edgecolor="black",
            linewidth=0.5,
        )

    # Add value labels on bars
    if show_values:
        for bar, value in zip(bars1, values):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + (1 if height >= 0 else -1),
                f"{value:.1f}%",
                ha="center",
                va="bottom" if height >= 0 else "top",
                fontsize=8,
                fontweight="bold",
            )

    # Add average line
    if show_average:
        avg_return = np.mean(values)
        ax.axhline(
            float(avg_return),
            color=colors["neutral"],
            linestyle="--",
            linewidth=1.5,
            alpha=0.7,
            label=f"Average ({avg_return:.1f}%)",
        )

    # Add zero reference line
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.3)

    # Format axes
    ax.set_xticks(x_pos)
    ax.set_xticklabels(years, rotation=45, ha="right")
    ax.set_ylabel("Annual Return (%)", fontsize=10)
    ax.set_xlabel("Year", fontsize=10)

    # Add legend
    ax.legend(loc="best", frameon=True, framealpha=0.9)

    # Grid
    _format_grid(ax)


def _plot_daily_returns(
    ax: Axes,
    returns: pd.Series,
    color_mode: Literal["color", "grayscale"] = "color",
    plot_type: Literal["bar", "scatter"] = "bar",
    smooth: bool = False,
    smooth_window: int = 20,
    show_bands: bool = True,
    num_std: float = 2.0,
    **kwargs: Any,
) -> None:
    """Plot daily returns as bars or scatter with optional volatility bands.

    Creates a visualization of daily returns with:
    - Bar or scatter plot of returns
    - Zero reference line
    - Optional moving average smoothing
    - Optional ±N standard deviation bands

    Args:
        ax: Matplotlib axes to plot on
        returns: Returns series (daily)
        color_mode: 'color' for full colors, 'grayscale' for monochrome
        plot_type: 'bar' for bar chart, 'scatter' for scatter plot
        smooth: Apply moving average smoothing
        smooth_window: Window size for moving average
        show_bands: Show ±N standard deviation bands
        num_std: Number of standard deviations for bands
        **kwargs: Additional arguments

    Example:
        >>> fig, ax = plt.subplots()
        >>> _plot_daily_returns(ax, returns, show_bands=True, num_std=2)
    """
    colors = _get_colors(color_mode)

    # Convert to percentage
    returns_pct = returns * 100

    # Determine colors for each return
    point_colors = [colors["profit"] if r >= 0 else colors["loss"] for r in returns_pct]

    # Plot based on type
    if plot_type == "bar":
        ax.bar(
            returns_pct.index,
            returns_pct.values,
            color=point_colors,
            alpha=0.6,
            width=1.0,
            edgecolor="none",
        )
    elif plot_type == "scatter":
        ax.scatter(
            returns_pct.index,
            returns_pct.values,
            c=point_colors,
            alpha=0.6,
            s=10,
            edgecolors="none",
        )
    else:
        raise ValueError(f"Invalid plot_type: {plot_type}")

    # Add zero reference line
    ax.axhline(0, color="black", linewidth=1, alpha=0.5, linestyle="-")

    # Add smoothed line if requested
    if smooth and len(returns_pct) >= smooth_window:
        smoothed = returns_pct.rolling(window=smooth_window, center=True).mean()
        ax.plot(
            smoothed.index,
            smoothed.values,
            color=colors["neutral"] if color_mode == "grayscale" else "#2c3e50",
            linewidth=2,
            alpha=0.8,
            label=f"{smooth_window}-day MA",
        )

    # Add volatility bands if requested
    if show_bands:
        # Calculate rolling standard deviation
        rolling_std = returns_pct.rolling(window=smooth_window or 20).std()

        # Upper and lower bands
        upper_band = num_std * rolling_std
        lower_band = -num_std * rolling_std

        ax.fill_between(
            returns_pct.index,
            upper_band,
            lower_band,
            alpha=0.15,
            color=colors["neutral"],
            label=f"±{num_std}σ bands",
        )

        # Plot band lines
        ax.plot(
            returns_pct.index,
            upper_band,
            color=colors["neutral"],
            linewidth=1,
            alpha=0.5,
            linestyle="--",
        )
        ax.plot(
            returns_pct.index,
            lower_band,
            color=colors["neutral"],
            linewidth=1,
            alpha=0.5,
            linestyle="--",
        )

    # Format axes
    ax.set_ylabel("Daily Return (%)", fontsize=10)
    ax.set_xlabel("Date", fontsize=10)

    # Format date axis
    if isinstance(returns_pct.index, pd.DatetimeIndex):
        _format_date_axis(ax, returns_pct.index)

    # Add legend if we have smoothing or bands
    if smooth or show_bands:
        ax.legend(loc="best", frameon=True, framealpha=0.9, fontsize=8)

    # Grid
    _format_grid(ax)


__all__ = [
    "plot_snapshot",
    "_plot_yearly_returns",
    "_plot_daily_returns",
]
