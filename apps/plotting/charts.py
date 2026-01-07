"""Price chart components for backtest visualization.

This module provides chart components for plotting OHLC data, volume, and line charts
using both Matplotlib and Bokeh backends. It includes:

- OHLC/Candlestick charts with both backends
- Line charts for equity curves and indicators
- Volume charts with price direction coloring
- Hover tooltips and interactive features (Bokeh)
- Proper axis formatting and styling

The functions in this module are typically called by the main plot() function
but can also be used standalone for custom visualizations.
"""

from typing import TYPE_CHECKING, Any, Literal, Optional, Union

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle

from apps.plotting.core import (
    BOKEH_AVAILABLE,
    CompactNumberFormatter,
    _format_axis,
    _format_date_axis,
    _format_grid,
    _get_colors,
)

if TYPE_CHECKING or BOKEH_AVAILABLE:
    from bokeh.models import (
        CrosshairTool,
        HoverTool,
        NumeralTickFormatter,
        PanTool,
        ResetTool,
        WheelZoomTool,
    )
    from bokeh.plotting import figure as bokeh_figure


def _plot_ohlc_bokeh(
    data: pd.DataFrame,
    width: int = 1200,
    height: int = 400,
    title: str = "Price Chart",
    show_volume: bool = False,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Any:
    """Plot OHLC/Candlestick chart using Bokeh.

    Creates an interactive candlestick chart with hover tooltips, crosshair,
    and pan/zoom tools.

    Args:
        data: DataFrame with OHLC data (Open, High, Low, Close columns)
              Index should be datetime
        width: Figure width in pixels
        height: Figure height in pixels
        title: Chart title
        show_volume: Whether to show volume bars below price chart
        color_mode: Color mode ("color" or "grayscale")
        **kwargs: Additional Bokeh figure parameters

    Returns:
        Bokeh figure object

    Raises:
        ImportError: If Bokeh is not installed
        ValueError: If required columns are missing

    Example:
        >>> data = pd.DataFrame({
        ...     'Open': [100, 102, 101],
        ...     'High': [103, 104, 105],
        ...     'Low': [99, 101, 100],
        ...     'Close': [102, 103, 104]
        ... }, index=pd.date_range('2024-01-01', periods=3))
        >>> fig = _plot_ohlc_bokeh(data)
    """
    if not BOKEH_AVAILABLE:
        raise ImportError(
            "Bokeh is required for interactive plots. "
            "Install with: pip install bokeh"
        )

    # Validate required columns
    required_cols = ["Open", "High", "Low", "Close"]
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Get colors
    colors = _get_colors(mode=color_mode)

    # Prepare data
    df = data.copy()
    df["Date"] = df.index

    # Determine candle colors (green for up, red for down)
    df["Color"] = np.where(
        df["Close"] >= df["Open"],
        colors["candle_up"],
        colors["candle_down"],
    )

    # Create figure
    p = bokeh_figure(
        width=width,
        height=height,
        title=title,
        x_axis_type="datetime",
        toolbar_location="above",
        **kwargs,
    )

    # Plot candlestick wicks (high-low lines)
    p.segment(
        x0="Date",
        y0="Low",
        x1="Date",
        y1="High",
        color="Color",
        line_width=1,
        source=df,
    )

    # Plot candlestick bodies
    # Calculate body width (80% of bar spacing)
    if len(df) > 1:
        avg_spacing = (df.index[-1] - df.index[0]) / len(df)
        body_width = avg_spacing * 0.8
    else:
        body_width = pd.Timedelta(hours=12)  # Default width

    p.vbar(
        x="Date",
        width=body_width,
        top="Open",
        bottom="Close",
        fill_color="Color",
        line_color="Color",
        source=df,
    )

    # Add hover tool with OHLC values
    hover = HoverTool(
        tooltips=[
            ("Date", "@Date{%F}"),
            ("Open", "@Open{0,0.00}"),
            ("High", "@High{0,0.00}"),
            ("Low", "@Low{0,0.00}"),
            ("Close", "@Close{0,0.00}"),
            ("Change", "@Change{0.00%}"),
        ],
        formatters={"@Date": "datetime"},
        mode="vline",
    )

    # Calculate price change percentage
    df["Change"] = (df["Close"] - df["Open"]) / df["Open"]

    p.add_tools(hover)

    # Add interactive tools
    p.add_tools(CrosshairTool())
    p.add_tools(PanTool())
    p.add_tools(WheelZoomTool())
    p.add_tools(ResetTool())

    # Format axes
    p.xaxis.axis_label = "Date"
    p.yaxis.axis_label = "Price"

    # Use numeral formatter for price axis (currency format)
    p.yaxis.formatter = NumeralTickFormatter(format="$0,0.00")

    return p


def _plot_ohlc_matplotlib(
    ax: Axes,
    data: pd.DataFrame,
    color_mode: Literal["color", "grayscale"] = "color",
    show_grid: bool = True,
    **kwargs: Any,
) -> Axes:
    """Plot OHLC/Candlestick chart using Matplotlib.

    Creates a static candlestick chart with proper formatting and styling.

    Args:
        ax: Matplotlib axes to plot on
        data: DataFrame with OHLC data (Open, High, Low, Close columns)
              Index should be datetime
        color_mode: Color mode ("color" or "grayscale")
        show_grid: Whether to show grid lines
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes object

    Raises:
        ValueError: If required columns are missing

    Example:
        >>> fig, ax = plt.subplots()
        >>> data = pd.DataFrame({
        ...     'Open': [100, 102, 101],
        ...     'High': [103, 104, 105],
        ...     'Low': [99, 101, 100],
        ...     'Close': [102, 103, 104]
        ... }, index=pd.date_range('2024-01-01', periods=3))
        >>> _plot_ohlc_matplotlib(ax, data)
    """
    # Validate required columns
    required_cols = ["Open", "High", "Low", "Close"]
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Get colors
    colors = _get_colors(mode=color_mode)

    # Prepare data
    df = data.copy()

    # Calculate bar width (80% of average spacing)
    if len(df) > 1:
        # Convert dates to numbers for plotting
        dates_numeric = mdates.date2num(df.index)
        avg_spacing = (dates_numeric[-1] - dates_numeric[0]) / len(df)
        width = avg_spacing * 0.8
    else:
        width = 0.8

    # Plot candlesticks
    for _idx, (date, row) in enumerate(df.iterrows()):
        # Convert date to numeric for plotting
        x = mdates.date2num(date)

        # Determine color
        color = (
            colors["candle_up"]
            if row["Close"] >= row["Open"]
            else colors["candle_down"]
        )

        # Plot high-low line (wick)
        ax.plot(
            [x, x],
            [row["Low"], row["High"]],
            color=color,
            linewidth=1,
            solid_capstyle="round",
        )

        # Plot open-close rectangle (body)
        body_height = abs(row["Close"] - row["Open"])
        body_bottom = min(row["Open"], row["Close"])

        rect = Rectangle(
            (float(x - width / 2), float(body_bottom)),
            float(width),
            float(body_height),
            facecolor=color,
            edgecolor=color,
            linewidth=1,
        )
        ax.add_patch(rect)

    # Format date axis
    _format_date_axis(ax, pd.DatetimeIndex(df.index))

    # Format axes
    _format_axis(
        ax,
        title=kwargs.get("title", "Price Chart"),
        xlabel="Date",
        ylabel="Price",
    )

    # Format grid
    if show_grid:
        _format_grid(ax)

    # Set y-axis limits with some padding
    y_min = df["Low"].min()
    y_max = df["High"].max()
    y_range = y_max - y_min
    ax.set_ylim(y_min - 0.05 * y_range, y_max + 0.05 * y_range)

    return ax


def _plot_line(  # noqa: C901
    ax_or_figure: Union[Axes, Any],
    data: Union[pd.Series, np.ndarray],
    dates: Optional[pd.DatetimeIndex] = None,
    label: Optional[str] = None,
    color: Optional[str] = None,
    style: str = "-",
    backend: Literal["matplotlib", "bokeh"] = "matplotlib",
    **kwargs: Any,
) -> Union[Axes, Any]:
    """Plot line chart for equity curves, indicators, etc.

    Supports both Matplotlib and Bokeh backends for consistent line plotting.

    Args:
        ax_or_figure: Matplotlib axes or Bokeh figure
        data: Series or array of values to plot
        dates: DatetimeIndex for x-axis (if data is ndarray)
        label: Line label for legend
        color: Line color (hex or named color)
        style: Line style ("-", "--", "-.", ":")
        backend: Backend to use ("matplotlib" or "bokeh")
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes or figure object

    Raises:
        ValueError: If dates is None when data is ndarray
        ValueError: If unsupported backend is specified

    Example:
        >>> fig, ax = plt.subplots()
        >>> equity = pd.Series([10000, 10500, 10800],
        ...                    index=pd.date_range('2024-01-01', periods=3))
        >>> _plot_line(ax, equity, label='Equity', color='blue')
    """
    if backend == "matplotlib":
        ax = ax_or_figure

        # Prepare data
        if isinstance(data, pd.Series):
            x = data.index
            y = data.values
        else:
            if dates is None:
                raise ValueError("dates must be provided when data is ndarray")
            x = dates
            y = data

        # Plot line
        line_kwargs = {
            "label": label,
            "color": color,
            "linestyle": style,
            "linewidth": kwargs.get("linewidth", 2),
            "alpha": kwargs.get("alpha", 1.0),
        }

        ax.plot(np.asarray(x), np.asarray(y), **line_kwargs)

        return ax

    elif backend == "bokeh":
        if not BOKEH_AVAILABLE:
            raise ImportError("Bokeh is required for interactive plots")

        p: Any = ax_or_figure

        # Prepare data
        if isinstance(data, pd.Series):
            x = data.index
            y = data.values
        else:
            if dates is None:
                raise ValueError("dates must be provided when data is ndarray")
            x = dates
            y = data

        # Plot line
        line_kwargs = {
            "legend_label": label,
            "color": color or "blue",
            "line_width": kwargs.get("line_width", 2),
            "alpha": kwargs.get("alpha", 1.0),
        }

        # Convert line style
        if style == "--":
            line_kwargs["line_dash"] = "dashed"
        elif style == "-.":
            line_kwargs["line_dash"] = "dashdot"
        elif style == ":":
            line_kwargs["line_dash"] = "dotted"

        p.line(np.asarray(x), np.asarray(y), **line_kwargs)

        # Add hover tool if requested
        if kwargs.get("hover", True):
            hover = HoverTool(
                tooltips=[
                    ("Date", "@x{%F}"),
                    ("Value", "@y{0,0.00}"),
                ],
                formatters={"@x": "datetime"},
            )
            p.add_tools(hover)

        return p

    else:
        raise ValueError(f"Unsupported backend: {backend}")


def _plot_volume_bokeh(
    data: pd.DataFrame,
    width: int = 1200,
    height: int = 150,
    color_mode: Literal["color", "grayscale"] = "color",
    link_to: Optional[Any] = None,
    **kwargs: Any,
) -> Any:
    """Plot volume bar chart using Bokeh.

    Creates an interactive volume chart with bars colored by price direction.

    Args:
        data: DataFrame with Volume and OHLC columns
              Index should be datetime
        width: Figure width in pixels
        height: Figure height in pixels (typically 1/4 of price chart)
        color_mode: Color mode ("color" or "grayscale")
        link_to: Bokeh figure to link x-axis with (for synchronized zooming)
        **kwargs: Additional Bokeh figure parameters

    Returns:
        Bokeh figure object

    Raises:
        ImportError: If Bokeh is not installed
        ValueError: If required columns are missing

    Example:
        >>> data = pd.DataFrame({
        ...     'Open': [100, 102],
        ...     'Close': [102, 101],
        ...     'Volume': [1000000, 1500000]
        ... }, index=pd.date_range('2024-01-01', periods=2))
        >>> fig = _plot_volume_bokeh(data)
    """
    if not BOKEH_AVAILABLE:
        raise ImportError("Bokeh is required for interactive plots")

    # Validate required columns
    if "Volume" not in data.columns:
        raise ValueError("Volume column is required")

    # Get colors
    colors = _get_colors(mode=color_mode)

    # Prepare data
    df = data.copy()
    df["Date"] = df.index

    # Determine bar colors (green for up days, red for down days)
    if "Open" in df.columns and "Close" in df.columns:
        df["Color"] = np.where(
            df["Close"] >= df["Open"],
            colors["volume_up"],
            colors["volume_down"],
        )
    else:
        df["Color"] = colors["neutral"]

    # Create figure
    fig_kwargs = {
        "width": width,
        "height": height,
        "title": "Volume",
        "x_axis_type": "datetime",
        "toolbar_location": None,  # Share toolbar with main chart
    }

    # Link x-axis if requested
    if link_to is not None:
        fig_kwargs["x_range"] = link_to.x_range

    p = bokeh_figure(**fig_kwargs, **kwargs)

    # Calculate bar width
    if len(df) > 1:
        avg_spacing = (df.index[-1] - df.index[0]) / len(df)
        bar_width = avg_spacing * 0.8
    else:
        bar_width = pd.Timedelta(hours=12)

    # Plot volume bars
    p.vbar(
        x="Date",
        width=bar_width,
        top="Volume",
        bottom=0,
        fill_color="Color",
        line_color="Color",
        source=df,
    )

    # Add hover tool
    hover = HoverTool(
        tooltips=[
            ("Date", "@Date{%F}"),
            ("Volume", "@Volume{0,0}"),
        ],
        formatters={"@Date": "datetime"},
    )
    p.add_tools(hover)

    # Format axes
    p.xaxis.axis_label = "Date"
    p.yaxis.axis_label = "Volume"

    # Use compact number formatter for volume axis
    p.yaxis.formatter = NumeralTickFormatter(format="0.0a")

    return p


def _plot_volume_matplotlib(
    ax: Axes,
    data: pd.DataFrame,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Axes:
    """Plot volume bar chart using Matplotlib.

    Creates a static volume chart with bars colored by price direction.

    Args:
        ax: Matplotlib axes to plot on
        data: DataFrame with Volume and OHLC columns
              Index should be datetime
        color_mode: Color mode ("color" or "grayscale")
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes object

    Raises:
        ValueError: If Volume column is missing

    Example:
        >>> fig, ax = plt.subplots()
        >>> data = pd.DataFrame({
        ...     'Open': [100, 102],
        ...     'Close': [102, 101],
        ...     'Volume': [1000000, 1500000]
        ... }, index=pd.date_range('2024-01-01', periods=2))
        >>> _plot_volume_matplotlib(ax, data)
    """
    # Validate required columns
    if "Volume" not in data.columns:
        raise ValueError("Volume column is required")

    # Get colors
    colors = _get_colors(mode=color_mode)

    # Prepare data
    df = data.copy()

    # Determine bar colors
    if "Open" in df.columns and "Close" in df.columns:
        bar_colors = [
            colors["volume_up"] if close >= open_price else colors["volume_down"]
            for open_price, close in zip(df["Open"], df["Close"])
        ]
    else:
        bar_colors = [colors["neutral"]] * len(df)

    # Calculate bar width
    if len(df) > 1:
        dates_numeric = mdates.date2num(df.index)
        avg_spacing = (dates_numeric[-1] - dates_numeric[0]) / len(df)
        width = avg_spacing * 0.8
    else:
        width = 0.8

    # Convert dates to numeric for plotting
    x = mdates.date2num(df.index)

    # Plot volume bars
    ax.bar(
        x,
        df["Volume"],
        width=width,
        color=bar_colors,
        edgecolor=bar_colors,
        linewidth=0.5,
    )

    # Format date axis
    _format_date_axis(ax, pd.DatetimeIndex(df.index))

    # Format axes
    _format_axis(
        ax,
        title=kwargs.get("title", "Volume"),
        xlabel="Date",
        ylabel="Volume",
    )

    # Format y-axis to use compact notation
    ax.yaxis.set_major_formatter(CompactNumberFormatter())

    # Set y-axis to start at 0
    ax.set_ylim(bottom=0)

    return ax


__all__ = [
    "_plot_ohlc_bokeh",
    "_plot_ohlc_matplotlib",
    "_plot_line",
    "_plot_volume_bokeh",
    "_plot_volume_matplotlib",
]
