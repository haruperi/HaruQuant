"""Drawdown chart plotting for backtest visualization.

This module provides functions for plotting drawdown charts:
- Underwater/drawdown plot showing drawdown over time
- Drawdown periods bar chart showing top N drawdown periods

Features:
- Filled area plot for underwater equity
- Highlight recovery periods
- Top N drawdown periods ranked by duration or magnitude
- Support for both Matplotlib and Bokeh backends
"""

from typing import Any, Dict, List, Literal, Optional, Union, cast

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.ticker import FuncFormatter

from apps.logger import logger
from apps.plotting.core import (
    BOKEH_AVAILABLE,
    _format_axis,
    _format_date_axis,
    _format_grid,
    _get_colors,
)


def _calculate_drawdown(equity: pd.Series) -> pd.Series:
    """Calculate drawdown series from equity curve.

    Args:
        equity: Equity series indexed by datetime

    Returns:
        Drawdown series as percentage (negative values)

    Example:
        >>> equity = pd.Series([100, 110, 105, 115])
        >>> dd = _calculate_drawdown(equity)
        >>> dd.iloc[-2]  # At 105, peak was 110
        -4.545...
    """
    running_max = equity.expanding().max()
    drawdown = (equity - running_max) / running_max * 100
    logger.debug(
        "Calculated drawdown series",
        extra={
            "data_points": len(equity),
            "min_drawdown": float(drawdown.min()) if len(drawdown) else 0.0,
        },
    )
    return drawdown


def _identify_drawdown_periods(
    drawdown: pd.Series,
) -> List[Dict[str, Any]]:
    """Identify distinct drawdown periods.

    Args:
        drawdown: Drawdown series (percentage)

    Returns:
        List of drawdown period dictionaries with:
        - start: Start date
        - end: End date (or current if not recovered)
        - duration: Duration in days
        - magnitude: Maximum drawdown percentage
        - recovered: Whether drawdown recovered to zero

    Example:
        >>> dd = pd.Series([0, -5, -10, -5, 0, -3, 0])
        >>> periods = _identify_drawdown_periods(dd, equity)
        >>> len(periods)
        2
    """
    periods = []
    in_drawdown = False
    period_start = None
    period_max_dd = 0

    for date, dd_value in drawdown.items():
        if dd_value < 0 and not in_drawdown:
            # Start of new drawdown period
            in_drawdown = True
            period_start = date
            period_max_dd = dd_value
        elif dd_value < 0 and in_drawdown:
            # Continuing drawdown
            period_max_dd = min(period_max_dd, dd_value)
        elif dd_value >= 0 and in_drawdown:
            # End of drawdown (recovered)
            in_drawdown = False
            period_end = date
            # Type assertion: period_start is guaranteed to be set when in_drawdown is True
            assert period_start is not None
            duration = int(
                (period_end - period_start).total_seconds() / 86400
            )  # pyright: ignore[reportOperatorIssue]

            periods.append(
                {
                    "start": period_start,
                    "end": period_end,
                    "duration": duration,
                    "magnitude": period_max_dd,
                    "recovered": True,
                }
            )

    # Handle ongoing drawdown (not recovered)
    if in_drawdown:
        period_end = drawdown.index[-1]
        # Type assertion: period_start is guaranteed to be set when in_drawdown is True
        assert period_start is not None
        duration = int(
            (period_end - period_start).total_seconds() / 86400
        )  # pyright: ignore[reportOperatorIssue]

        periods.append(
            {
                "start": period_start,
                "end": period_end,
                "duration": duration,
                "magnitude": period_max_dd,
                "recovered": False,
            }
        )

    logger.debug(
        "Identified drawdown periods",
        extra={
            "total_periods": len(periods),
            "contains_open_period": bool(periods and not periods[-1]["recovered"]),
        },
    )
    return periods


def _plot_drawdown(
    ax_or_figure: Union[Axes, Any],
    drawdown: Optional[pd.Series] = None,
    equity: Optional[pd.Series] = None,
    backend: Literal["matplotlib", "bokeh"] = "matplotlib",
    color_mode: Literal["color", "grayscale"] = "color",
    show_recovery: bool = True,
    **kwargs: Any,
) -> Union[Axes, Any]:
    """Plot underwater/drawdown chart showing drawdown over time.

    Args:
        ax_or_figure: Matplotlib axes or Bokeh figure
        drawdown: Pre-calculated drawdown series (percentage). If None, calculated from equity
        equity: Equity series (required if drawdown is None)
        backend: Plotting backend ('matplotlib' or 'bokeh')
        color_mode: Color scheme ('color' or 'grayscale')
        show_recovery: Highlight recovery periods back to zero
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes or figure

    Example:
        >>> fig, ax = plt.subplots()
        >>> equity = pd.Series([10000, 10500, 9500, 11000], index=dates)
        >>> _plot_drawdown(ax, equity=equity)
    """
    # Calculate drawdown if not provided
    if drawdown is None:
        if equity is None:
            raise ValueError("Either drawdown or equity must be provided")
        drawdown = _calculate_drawdown(equity)

    if len(drawdown) == 0:
        raise ValueError("Drawdown series is empty")

    colors = _get_colors(color_mode)
    logger.info(
        "Rendering drawdown plot",
        extra={
            "backend": backend,
            "color_mode": color_mode,
            "points": len(drawdown),
            "show_recovery": show_recovery,
        },
    )

    if backend == "matplotlib":
        axes = ax_or_figure

        # Plot filled area
        axes.fill_between(
            mdates.date2num(drawdown.index),
            0,
            np.asarray(drawdown.values),
            color=colors.get("loss", "#e74c3c"),
            alpha=kwargs.get("fill_alpha", 0.3),
            label="Drawdown",
        )

        # Plot line on top
        axes.plot(
            mdates.date2num(drawdown.index),
            np.asarray(drawdown.values),
            color=colors.get("loss", "#e74c3c"),
            linewidth=kwargs.get("linewidth", 1.5),
            alpha=0.8,
        )

        # Add zero reference line
        axes.axhline(y=0, color="black", linestyle="-", alpha=0.3, linewidth=1)

        # Highlight recovery periods if requested
        if show_recovery and equity is not None:
            periods = _identify_drawdown_periods(drawdown)
            for period in periods:
                if period["recovered"]:
                    # Shade recovery region lightly
                    recovery_start = period["start"]
                    recovery_end = period["end"]
                    axes.axvspan(
                        float(mdates.date2num(recovery_start)),
                        float(mdates.date2num(recovery_end)),
                        alpha=0.1,
                        color=colors.get("profit", "#2ecc71"),
                    )

        # Format axes
        _format_axis(
            axes,
            title=kwargs.get("title", "Underwater Equity (Drawdown)"),
            ylabel="Drawdown (%)",
        )
        _format_grid(axes)
        _format_date_axis(axes, cast(pd.DatetimeIndex, drawdown.index))

        # Format y-axis as percentage
        axes.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.1f}%"))

        # Add legend
        axes.legend(loc="lower left", fontsize=9)

        return axes

    if backend == "bokeh":
        if not BOKEH_AVAILABLE:
            raise ImportError("Bokeh is not installed. Use matplotlib backend.")

        # Import bokeh components at runtime
        from bokeh.models import (  # pylint: disable=import-outside-toplevel
            HoverTool,
            Span,
        )

        bokeh_fig: Any = ax_or_figure

        # Prepare data
        dd_data = pd.DataFrame({"date": drawdown.index, "drawdown": drawdown.values})

        # Create filled area
        bokeh_fig.varea(
            x="date",
            y1=0,
            y2="drawdown",
            source=dd_data,
            fill_color=colors.get("loss", "#e74c3c"),
            fill_alpha=0.3,
            legend_label="Drawdown",
        )

        # Plot line
        bokeh_fig.line(
            x="date",
            y="drawdown",
            source=dd_data,
            color=colors.get("loss", "#e74c3c"),
            line_width=1.5,
            alpha=0.8,
        )

        # Add hover tool
        hover = HoverTool(
            tooltips=[
                ("Date", "@date{%F}"),
                ("Drawdown", "@drawdown{0.00}%"),
            ],
            formatters={"@date": "datetime"},
        )
        bokeh_fig.add_tools(hover)

        # Add zero reference line
        zero_line = Span(
            location=0,
            dimension="width",
            line_color="black",
            line_alpha=0.3,
            line_width=1,
        )
        bokeh_fig.add_layout(zero_line)

        # Format axes
        bokeh_fig.yaxis.axis_label = "Drawdown (%)"
        bokeh_fig.xaxis.axis_label = "Date"

        return bokeh_fig

    raise ValueError(f"Unknown backend: {backend}")


def _plot_drawdown_periods(
    axes: Axes,
    drawdown: Optional[pd.Series] = None,
    equity: Optional[pd.Series] = None,
    top_n: int = 10,
    sort_by: Literal["duration", "magnitude"] = "duration",
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Axes:
    """Plot top N drawdown periods as bar chart.

    Args:
        axes: Matplotlib axes
        drawdown: Pre-calculated drawdown series. If None, calculated from equity
        equity: Equity series (required if drawdown is None)
        top_n: Number of top drawdown periods to show
        sort_by: Sort by 'duration' or 'magnitude'
        color_mode: Color scheme ('color' or 'grayscale')
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes

    Example:
        >>> fig, ax = plt.subplots()
        >>> equity = pd.Series([10000, 10500, 9500, 11000], index=dates)
        >>> _plot_drawdown_periods(ax, equity=equity, top_n=5)
    """
    # Calculate drawdown if not provided
    if drawdown is None:
        if equity is None:
            raise ValueError("Either drawdown or equity must be provided")
        drawdown = _calculate_drawdown(equity)

    # Identify drawdown periods
    periods = _identify_drawdown_periods(drawdown)
    logger.info(
        "Rendering drawdown periods plot",
        extra={
            "top_n": top_n,
            "sort_by": sort_by,
            "color_mode": color_mode,
            "has_equity": equity is not None,
            "periods_found": len(periods),
        },
    )

    if len(periods) == 0:
        # No drawdown periods, plot empty chart
        axes.text(
            0.5,
            0.5,
            "No drawdown periods",
            ha="center",
            va="center",
            transform=axes.transAxes,
            fontsize=12,
        )
        _format_axis(axes, title=kwargs.get("title", "Top Drawdown Periods"))
        return axes

    # Sort periods
    if sort_by == "duration":
        periods_sorted = sorted(periods, key=lambda x: x["duration"], reverse=True)
    else:  # magnitude
        periods_sorted = sorted(
            periods, key=lambda x: x["magnitude"]
        )  # Most negative first

    # Take top N
    periods_top = periods_sorted[:top_n]

    # Prepare data for plotting
    labels = []
    durations = []
    magnitudes = []
    colors_list: List[Union[str, tuple]] = []

    colors = _get_colors(color_mode)

    for period in periods_top:
        # Create label with date range
        label = f"{period['start'].strftime('%Y-%m-%d')}\nto\n{period['end'].strftime('%Y-%m-%d')}"
        labels.append(label)
        durations.append(period["duration"])
        magnitudes.append(abs(period["magnitude"]))

        # Color by magnitude
        if color_mode == "grayscale":
            colors_list.append(colors.get("text", "#34495e"))
        else:
            # Gradient from light to dark red based on magnitude
            magnitude_normalized = abs(period["magnitude"]) / max(
                abs(period_item["magnitude"]) for period_item in periods_top
            )
            # Interpolate between light and dark red
            light_red = np.array([1.0, 0.8, 0.8])  # Light red
            dark_red = np.array([0.8, 0.0, 0.0])  # Dark red
            color_rgb = light_red + magnitude_normalized * (dark_red - light_red)
            colors_list.append(tuple(color_rgb))

    # Create bar chart
    y_pos = np.arange(len(periods_top))

    if sort_by == "duration":
        # Plot duration as bars
        bars = axes.barh(y_pos, durations, color=colors_list, alpha=0.7)

        # Annotate with magnitude
        for bar_rect, magnitude in zip(bars, magnitudes):
            width = bar_rect.get_width()
            axes.text(
                width + max(durations) * 0.02,
                bar_rect.get_y() + bar_rect.get_height() / 2,
                f"{magnitude:.1f}%",
                ha="left",
                va="center",
                fontsize=8,
                color=colors.get("text", "#34495e"),
            )

        axes.set_xlabel("Duration (days)")
        axes.set_title(kwargs.get("title", "Top Drawdown Periods by Duration"))

    else:  # magnitude
        # Plot magnitude as bars
        bars = axes.barh(y_pos, magnitudes, color=colors_list, alpha=0.7)

        # Annotate with duration
        for bar_rect, duration in zip(bars, durations):
            width = bar_rect.get_width()
            axes.text(
                width + max(magnitudes) * 0.02,
                bar_rect.get_y() + bar_rect.get_height() / 2,
                f"{duration}d",
                ha="left",
                va="center",
                fontsize=8,
                color=colors.get("text", "#34495e"),
            )

        axes.set_xlabel("Magnitude (%)")
        axes.set_title(kwargs.get("title", "Top Drawdown Periods by Magnitude"))

    # Set y-axis labels
    axes.set_yticks(y_pos)
    axes.set_yticklabels(labels, fontsize=7)
    axes.invert_yaxis()  # Top period at the top

    _format_grid(axes, alpha=0.3)

    return axes


__all__ = [
    "_calculate_drawdown",
    "_identify_drawdown_periods",
    "_plot_drawdown",
    "_plot_drawdown_periods",
]
