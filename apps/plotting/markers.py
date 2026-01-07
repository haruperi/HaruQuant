"""Trade markers and annotations for backtest visualization.

This module provides functions for plotting trade entry/exit markers and
annotations on price charts. It supports both Matplotlib and Bokeh backends.

Features:
- Entry markers with different shapes for long/short positions
- Exit markers colored by profit/loss
- Trade connection lines showing entry-to-exit paths
- Hover tooltips with trade details (Bokeh)
- Customizable marker sizes and colors
"""

from typing import Any, Dict, List, Literal, Union

import matplotlib.dates as mdates
from matplotlib.axes import Axes

from apps.plotting.core import BOKEH_AVAILABLE, _get_colors

if BOKEH_AVAILABLE:
    from bokeh.models import ColumnDataSource, HoverTool


def _plot_entry_markers(
    ax_or_figure: Union[Axes, Any],
    trades: List[Dict[str, Any]],
    backend: Literal["matplotlib", "bokeh"] = "matplotlib",
    marker_size: int = 100,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Union[Axes, Any]:
    """Plot trade entry markers on price chart.

    Plots entry points with different markers for long/short positions:
    - Long entries: green upward triangle
    - Short entries: orange/red downward triangle

    Args:
        ax_or_figure: Matplotlib axes or Bokeh figure
        trades: List of trade dictionaries with entry information
        backend: Backend to use ("matplotlib" or "bokeh")
        marker_size: Size of markers in points
        color_mode: Color mode ("color" or "grayscale")
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes or figure object

    Raises:
        ValueError: If unsupported backend is specified

    Example:
        >>> fig, ax = plt.subplots()
        >>> trades = [
        ...     {'entry_time': pd.Timestamp('2024-01-01'),
        ...      'entry_price': 100.0,
        ...      'is_long': True,
        ...      'size': 10}
        ... ]
        >>> _plot_entry_markers(ax, trades)
    """
    if not trades:
        return ax_or_figure

    # Get colors
    colors = _get_colors(mode=color_mode)

    # Separate long and short entries
    long_entries = [t for t in trades if t.get("is_long", True)]
    short_entries = [t for t in trades if not t.get("is_long", True)]

    if backend == "matplotlib":
        ax = ax_or_figure

        # Plot long entries (green upward triangles)
        if long_entries:
            entry_times = [t["entry_time"] for t in long_entries]
            entry_prices = [t["entry_price"] for t in long_entries]
            entry_times_num = mdates.date2num(entry_times)

            ax.scatter(
                entry_times_num,
                entry_prices,
                marker="^",
                s=marker_size,
                color=colors["long_entry"],
                edgecolors="white",
                linewidths=1,
                zorder=10,
                label=kwargs.get("long_label", "Long Entry"),
            )

        # Plot short entries (orange/red downward triangles)
        if short_entries:
            entry_times = [t["entry_time"] for t in short_entries]
            entry_prices = [t["entry_price"] for t in short_entries]
            entry_times_num = mdates.date2num(entry_times)

            ax.scatter(
                entry_times_num,
                entry_prices,
                marker="v",
                s=marker_size,
                color=colors["short_entry"],
                edgecolors="white",
                linewidths=1,
                zorder=10,
                label=kwargs.get("short_label", "Short Entry"),
            )

        return ax

    elif backend == "bokeh":
        if not BOKEH_AVAILABLE:
            raise ImportError("Bokeh is required for interactive plots")

        p = ax_or_figure

        # Plot long entries
        if long_entries:
            long_data = {
                "entry_time": [t["entry_time"] for t in long_entries],
                "entry_price": [t["entry_price"] for t in long_entries],
                "size": [t.get("size", 0) for t in long_entries],
                "tag": [t.get("entry_tag", "N/A") for t in long_entries],
            }
            source = ColumnDataSource(long_data)

            p.triangle(
                x="entry_time",
                y="entry_price",
                size=marker_size / 10,
                color=colors["long_entry"],
                line_color="white",
                line_width=1,
                source=source,
                legend_label="Long Entry",
            )

            # Add hover tool
            hover = HoverTool(
                tooltips=[
                    ("Type", "Long Entry"),
                    ("Time", "@entry_time{%F %T}"),
                    ("Price", "@entry_price{0,0.00}"),
                    ("Size", "@size{0,0.00}"),
                    ("Tag", "@tag"),
                ],
                formatters={"@entry_time": "datetime"},
                mode="mouse",
            )
            p.add_tools(hover)

        # Plot short entries
        if short_entries:
            short_data = {
                "entry_time": [t["entry_time"] for t in short_entries],
                "entry_price": [t["entry_price"] for t in short_entries],
                "size": [t.get("size", 0) for t in short_entries],
                "tag": [t.get("entry_tag", "N/A") for t in short_entries],
            }
            source = ColumnDataSource(short_data)

            p.inverted_triangle(
                x="entry_time",
                y="entry_price",
                size=marker_size / 10,
                color=colors["short_entry"],
                line_color="white",
                line_width=1,
                source=source,
                legend_label="Short Entry",
            )

            # Add hover tool
            hover = HoverTool(
                tooltips=[
                    ("Type", "Short Entry"),
                    ("Time", "@entry_time{%F %T}"),
                    ("Price", "@entry_price{0,0.00}"),
                    ("Size", "@size{0,0.00}"),
                    ("Tag", "@tag"),
                ],
                formatters={"@entry_time": "datetime"},
                mode="mouse",
            )
            p.add_tools(hover)

        return p

    else:
        raise ValueError(f"Unsupported backend: {backend}")


def _plot_exit_markers(
    ax_or_figure: Union[Axes, Any],
    trades: List[Dict[str, Any]],
    backend: Literal["matplotlib", "bokeh"] = "matplotlib",
    marker_size: int = 100,
    size_by_pl: bool = False,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Union[Axes, Any]:
    """Plot trade exit markers on price chart.

    Plots exit points as circles colored by profit/loss:
    - Profitable exits: green circles
    - Losing exits: red circles

    Args:
        ax_or_figure: Matplotlib axes or Bokeh figure
        trades: List of trade dictionaries with exit information
        backend: Backend to use ("matplotlib" or "bokeh")
        marker_size: Base size of markers in points
        size_by_pl: Whether to scale marker size by P&L magnitude
        color_mode: Color mode ("color" or "grayscale")
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes or figure object

    Raises:
        ValueError: If unsupported backend is specified

    Example:
        >>> fig, ax = plt.subplots()
        >>> trades = [
        ...     {'exit_time': pd.Timestamp('2024-01-05'),
        ...      'exit_price': 105.0,
        ...      'pl': 50.0,
        ...      'pl_pct': 0.05}
        ... ]
        >>> _plot_exit_markers(ax, trades)
    """
    if not trades:
        return ax_or_figure

    # Get colors
    colors = _get_colors(mode=color_mode)

    # Separate profitable and losing exits
    profit_exits = [t for t in trades if t.get("pl", 0) >= 0]
    loss_exits = [t for t in trades if t.get("pl", 0) < 0]

    if backend == "matplotlib":
        return _plot_exit_markers_matplotlib(
            ax_or_figure,
            profit_exits,
            loss_exits,
            colors,
            marker_size,
            size_by_pl,
            **kwargs,
        )

    elif backend == "bokeh":
        return _plot_exit_markers_bokeh(
            ax_or_figure,
            profit_exits,
            loss_exits,
            colors,
            marker_size,
            size_by_pl,
        )

    else:
        raise ValueError(f"Unsupported backend: {backend}")


def _plot_exit_markers_matplotlib(
    ax: Axes,
    profit_exits: List[Dict[str, Any]],
    loss_exits: List[Dict[str, Any]],
    colors: Dict[str, Any],
    marker_size: int,
    size_by_pl: bool,
    **kwargs: Any,
) -> Axes:
    """Plot exit markers using Matplotlib."""
    # Plot profitable exits (green circles)
    if profit_exits:
        exit_times = [t["exit_time"] for t in profit_exits]
        exit_prices = [t["exit_price"] for t in profit_exits]
        exit_times_num = mdates.date2num(exit_times)

        # Calculate marker sizes if size_by_pl is enabled
        sizes: Union[int, List[float]]
        if size_by_pl:
            pl_values = [abs(t.get("pl_pct", 0)) for t in profit_exits]
            max_pl = max(pl_values) if pl_values else 1
            sizes = [marker_size * (1 + pl / max_pl) for pl in pl_values]
        else:
            sizes = marker_size

        ax.scatter(
            exit_times_num,
            exit_prices,
            marker="o",
            s=sizes,
            color=colors["profit"],
            edgecolors="white",
            linewidths=1,
            zorder=10,
            label=kwargs.get("profit_label", "Profit Exit"),
        )

    # Plot losing exits (red circles)
    if loss_exits:
        exit_times = [t["exit_time"] for t in loss_exits]
        exit_prices = [t["exit_price"] for t in loss_exits]
        exit_times_num = mdates.date2num(exit_times)

        # Calculate marker sizes if size_by_pl is enabled
        if size_by_pl:
            pl_values = [abs(t.get("pl_pct", 0)) for t in loss_exits]
            max_pl = max(pl_values) if pl_values else 1
            sizes = [marker_size * (1 + pl / max_pl) for pl in pl_values]
        else:
            sizes = marker_size

        ax.scatter(
            exit_times_num,
            exit_prices,
            marker="o",
            s=sizes,
            color=colors["loss"],
            edgecolors="white",
            linewidths=1,
            zorder=10,
            label=kwargs.get("loss_label", "Loss Exit"),
        )

    return ax


def _plot_exit_markers_bokeh(
    p: Any,
    profit_exits: List[Dict[str, Any]],
    loss_exits: List[Dict[str, Any]],
    colors: Dict[str, Any],
    marker_size: int,
    size_by_pl: bool,
) -> Any:
    """Plot exit markers using Bokeh."""
    if not BOKEH_AVAILABLE:
        raise ImportError("Bokeh is required for interactive plots")

    # Plot profitable exits
    if profit_exits:
        profit_data = {
            "exit_time": [t["exit_time"] for t in profit_exits],
            "exit_price": [t["exit_price"] for t in profit_exits],
            "pl": [t.get("pl", 0) for t in profit_exits],
            "pl_pct": [t.get("pl_pct", 0) * 100 for t in profit_exits],
            "duration": [
                str(t.get("exit_time") - t.get("entry_time", t.get("exit_time")))
                for t in profit_exits
            ],
            "tag": [t.get("exit_tag", "N/A") for t in profit_exits],
        }

        # Calculate sizes if needed
        size_field: Union[str, float]
        if size_by_pl:
            pl_values = [abs(t.get("pl_pct", 0)) for t in profit_exits]
            max_pl = max(pl_values) if pl_values else 1
            profit_data["size"] = [
                (marker_size / 10) * (1 + pl / max_pl) for pl in pl_values
            ]
            size_field = "size"
        else:
            size_field = marker_size / 10

        source = ColumnDataSource(profit_data)

        p.circle(
            x="exit_time",
            y="exit_price",
            size=size_field,
            color=colors["profit"],
            line_color="white",
            line_width=1,
            source=source,
            legend_label="Profit Exit",
        )

        # Add hover tool
        hover = HoverTool(
            tooltips=[
                ("Type", "Profit Exit"),
                ("Time", "@exit_time{%F %T}"),
                ("Price", "@exit_price{0,0.00}"),
                ("P&L", "$@pl{0,0.00}"),
                ("P&L %", "@pl_pct{0.00}%"),
                ("Duration", "@duration"),
                ("Tag", "@tag"),
            ],
            formatters={"@exit_time": "datetime"},
            mode="mouse",
        )
        p.add_tools(hover)

    # Plot losing exits
    if loss_exits:
        loss_data = {
            "exit_time": [t["exit_time"] for t in loss_exits],
            "exit_price": [t["exit_price"] for t in loss_exits],
            "pl": [t.get("pl", 0) for t in loss_exits],
            "pl_pct": [t.get("pl_pct", 0) * 100 for t in loss_exits],
            "duration": [
                str(t.get("exit_time") - t.get("entry_time", t.get("exit_time")))
                for t in loss_exits
            ],
            "tag": [t.get("exit_tag", "N/A") for t in loss_exits],
        }

        # Calculate sizes if needed
        if size_by_pl:
            pl_values = [abs(t.get("pl_pct", 0)) for t in loss_exits]
            max_pl = max(pl_values) if pl_values else 1
            loss_data["size"] = [
                (marker_size / 10) * (1 + pl / max_pl) for pl in pl_values
            ]
            size_field = "size"
        else:
            size_field = marker_size / 10

        source = ColumnDataSource(loss_data)

        p.circle(
            x="exit_time",
            y="exit_price",
            size=size_field,
            color=colors["loss"],
            line_color="white",
            line_width=1,
            source=source,
            legend_label="Loss Exit",
        )

        # Add hover tool
        hover = HoverTool(
            tooltips=[
                ("Type", "Loss Exit"),
                ("Time", "@exit_time{%F %T}"),
                ("Price", "@exit_price{0,0.00}"),
                ("P&L", "$@pl{0,0.00}"),
                ("P&L %", "@pl_pct{0.00}%"),
                ("Duration", "@duration"),
                ("Tag", "@tag"),
            ],
            formatters={"@exit_time": "datetime"},
            mode="mouse",
        )
        p.add_tools(hover)

    return p


def _plot_trade_lines(
    ax_or_figure: Union[Axes, Any],
    trades: List[Dict[str, Any]],
    backend: Literal["matplotlib", "bokeh"] = "matplotlib",
    color_mode: Literal["color", "grayscale"] = "color",
    line_style: str = "--",
    alpha: float = 0.3,
    **kwargs: Any,
) -> Union[Axes, Any]:
    """Plot lines connecting trade entries to exits.

    Draws lines from entry to exit points, colored by profit/loss.
    Useful for visualizing trade duration and outcome.

    Args:
        ax_or_figure: Matplotlib axes or Bokeh figure
        trades: List of trade dictionaries with entry and exit information
        backend: Backend to use ("matplotlib" or "bokeh")
        color_mode: Color mode ("color" or "grayscale")
        line_style: Line style ("--", "-.", ":", "-")
        alpha: Line transparency (0-1)
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes or figure object

    Raises:
        ValueError: If unsupported backend is specified

    Example:
        >>> fig, ax = plt.subplots()
        >>> trades = [
        ...     {'entry_time': pd.Timestamp('2024-01-01'),
        ...      'entry_price': 100.0,
        ...      'exit_time': pd.Timestamp('2024-01-05'),
        ...      'exit_price': 105.0,
        ...      'pl': 50.0}
        ... ]
        >>> _plot_trade_lines(ax, trades)
    """
    if not trades:
        return ax_or_figure

    # Get colors
    colors = _get_colors(mode=color_mode)

    if backend == "matplotlib":
        return _plot_trade_lines_matplotlib(
            ax_or_figure, trades, colors, line_style, alpha, **kwargs
        )

    elif backend == "bokeh":
        return _plot_trade_lines_bokeh(
            ax_or_figure, trades, colors, line_style, alpha, **kwargs
        )

    else:
        raise ValueError(f"Unsupported backend: {backend}")


def _plot_trade_lines_matplotlib(
    ax: Axes,
    trades: List[Dict[str, Any]],
    colors: Dict[str, Any],
    line_style: str,
    alpha: float,
    **kwargs: Any,
) -> Axes:
    """Plot trade lines using Matplotlib."""
    for trade in trades:
        # Skip if missing required data
        if not all(
            k in trade for k in ["entry_time", "entry_price", "exit_time", "exit_price"]
        ):
            continue

        # Determine color based on P&L
        pl = trade.get("pl", 0)
        color = colors["profit"] if pl >= 0 else colors["loss"]

        # Convert times to numeric
        entry_time = mdates.date2num(trade["entry_time"])
        exit_time = mdates.date2num(trade["exit_time"])

        # Plot line
        ax.plot(
            [entry_time, exit_time],
            [trade["entry_price"], trade["exit_price"]],
            linestyle=line_style,
            color=color,
            alpha=alpha,
            linewidth=kwargs.get("linewidth", 1),
            zorder=5,
        )

    return ax


def _plot_trade_lines_bokeh(
    p: Any,
    trades: List[Dict[str, Any]],
    colors: Dict[str, Any],
    line_style: str,
    alpha: float,
    **kwargs: Any,
) -> Any:
    """Plot trade lines using Bokeh."""
    if not BOKEH_AVAILABLE:
        raise ImportError("Bokeh is required for interactive plots")

    # Separate profitable and losing trades
    profit_trades = [t for t in trades if t.get("pl", 0) >= 0]
    loss_trades = [t for t in trades if t.get("pl", 0) < 0]

    # Convert line style
    bokeh_dash = "solid"
    if line_style == "--":
        bokeh_dash = "dashed"
    elif line_style == "-.":
        bokeh_dash = "dashdot"
    elif line_style == ":":
        bokeh_dash = "dotted"

    # Plot profit trade lines
    for trade in profit_trades:
        if not all(
            k in trade for k in ["entry_time", "entry_price", "exit_time", "exit_price"]
        ):
            continue

        p.line(
            [trade["entry_time"], trade["exit_time"]],
            [trade["entry_price"], trade["exit_price"]],
            line_dash=bokeh_dash,
            line_color=colors["profit"],
            line_alpha=alpha,
            line_width=kwargs.get("line_width", 1),
        )

    # Plot loss trade lines
    for trade in loss_trades:
        if not all(
            k in trade for k in ["entry_time", "entry_price", "exit_time", "exit_price"]
        ):
            continue

        p.line(
            [trade["entry_time"], trade["exit_time"]],
            [trade["entry_price"], trade["exit_price"]],
            line_dash=bokeh_dash,
            line_color=colors["loss"],
            line_alpha=alpha,
            line_width=kwargs.get("line_width", 1),
        )

    return p


__all__ = [
    "_plot_entry_markers",
    "_plot_exit_markers",
    "_plot_trade_lines",
]
