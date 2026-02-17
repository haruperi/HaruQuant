"""Plotly conversion utilities for matplotlib figures.

This module provides functionality to convert matplotlib figures to interactive
Plotly charts, preserving styling, annotations, and layout while adding
web-based interactivity.
"""

import warnings
from typing import Any, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from apps.utils.logger import logger

# Check for plotly availability
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    warnings.warn(
        "Plotly not available. Install with: pip install plotly",
        stacklevel=2,
    )


def to_plotly(
    fig: Figure,
    preserve_layout: bool = True,
    add_rangeslider: bool = False,
    hover_template: Optional[str] = None,
    theme: str = "plotly_white",
    **kwargs: Any,
) -> "go.Figure":
    """Convert matplotlib figure to interactive Plotly figure.

    This function extracts data and styling from a matplotlib figure and
    recreates it as an interactive Plotly chart. Not all matplotlib features
    can be perfectly converted, but most common plots are supported.

    Args:
        fig: Matplotlib figure to convert
        preserve_layout: Attempt to preserve matplotlib layout settings
        add_rangeslider: Add range slider for time series plots
        hover_template: Custom hover template (None = auto-generate)
        theme: Plotly template/theme to use
        **kwargs: Additional arguments passed to Plotly figure

    Returns:
        Interactive Plotly figure

    Raises:
        ImportError: If Plotly is not installed
        ValueError: If figure cannot be converted

    Example:
        >>> import matplotlib.pyplot as plt
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3], [1, 4, 2])
        >>> plotly_fig = to_plotly(fig)
        >>> plotly_fig.show()

    Note:
        Some matplotlib features may not convert perfectly:
        - Complex annotations
        - Custom colormaps (approximated)
        - 3D plots (not supported)
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("Plotly is not installed. Install with: pip install plotly")

    logger.debug("Converting matplotlib figure to Plotly")

    # Get all axes from the figure
    axes_list = fig.get_axes()

    if not axes_list:
        raise ValueError("Figure contains no axes to convert")

    # Create Plotly figure with subplots if needed
    n_axes = len(axes_list)

    if n_axes == 1:
        plotly_fig = go.Figure()
        _convert_axes(axes_list[0], plotly_fig, hover_template=hover_template)
    else:
        # Determine subplot layout
        rows, cols = _determine_subplot_layout(n_axes)

        plotly_fig = make_subplots(
            rows=rows,
            cols=cols,
            subplot_titles=[ax.get_title() for ax in axes_list],
            **kwargs.get("subplot_kwargs", {}),
        )

        # Convert each axis
        for idx, ax in enumerate(axes_list, 1):
            row = (idx - 1) // cols + 1
            col = (idx - 1) % cols + 1
            _convert_axes(
                ax,
                plotly_fig,
                row=row,
                col=col,
                hover_template=hover_template,
            )

    # Apply theme
    plotly_fig.update_layout(template=theme)

    # Preserve layout if requested
    if preserve_layout:
        _preserve_matplotlib_layout(fig, plotly_fig)

    # Add range slider for time series
    if add_rangeslider:
        plotly_fig.update_xaxes(rangeslider_visible=True)

    # Update general layout
    plotly_fig.update_layout(
        showlegend=True,
        hovermode="closest",
        **kwargs.get("layout_kwargs", {}),
    )

    logger.success("Matplotlib figure converted to Plotly successfully")

    return plotly_fig


def _convert_axes(
    ax: Axes,
    plotly_fig: "go.Figure",
    row: Optional[int] = None,
    col: Optional[int] = None,
    hover_template: Optional[str] = None,
) -> None:
    """Convert a single matplotlib axes to Plotly traces.

    Args:
        ax: Matplotlib axes to convert
        plotly_fig: Plotly figure to add traces to
        row: Subplot row (None for single plot)
        col: Subplot column (None for single plot)
        hover_template: Custom hover template
    """
    # Extract all line plots
    for line in ax.get_lines():
        _add_line_trace(line, plotly_fig, row, col, hover_template)

    # Extract bar plots
    for patch in ax.patches:
        if hasattr(patch, "get_height"):  # Bar plot
            _add_bar_from_patch(patch, plotly_fig, row, col)

    # Extract scatter plots
    for collection in ax.collections:
        _add_scatter_trace(collection, plotly_fig, row, col, hover_template)

    # Set axis labels and title
    if row is None or col is None:
        plotly_fig.update_xaxes(title_text=ax.get_xlabel())
        plotly_fig.update_yaxes(title_text=ax.get_ylabel())
        if ax.get_title():
            plotly_fig.update_layout(title=ax.get_title())
    else:
        plotly_fig.update_xaxes(title_text=ax.get_xlabel(), row=row, col=col)
        plotly_fig.update_yaxes(title_text=ax.get_ylabel(), row=row, col=col)


def _convert_color_to_plotly(color: Any) -> str:
    """Convert matplotlib color to Plotly-compatible RGB string.

    Args:
        color: Matplotlib color (can be tuple, string, etc.)

    Returns:
        RGB string in format 'rgb(r,g,b)'
    """
    import matplotlib.colors as mcolors

    # If already a string, check if it's a valid format
    if isinstance(color, str):
        return color

    # Convert to RGBA
    rgba = mcolors.to_rgba(color)

    # Convert to RGB string (0-255 range)
    r = int(rgba[0] * 255)
    g = int(rgba[1] * 255)
    b = int(rgba[2] * 255)

    return f"rgb({r},{g},{b})"


def _add_line_trace(
    line: Any,
    plotly_fig: "go.Figure",
    row: Optional[int],
    col: Optional[int],
    hover_template: Optional[str],
) -> None:
    """Add a line plot trace to Plotly figure."""
    xdata = line.get_xdata()
    ydata = line.get_ydata()
    label = line.get_label()

    # Skip if label starts with underscore (internal matplotlib)
    if label and label.startswith("_"):
        label = None

    # Get line properties
    color = line.get_color()
    linewidth = line.get_linewidth()
    linestyle = line.get_linestyle()

    # Convert color to RGB string format
    color_str = _convert_color_to_plotly(color)

    # Convert linestyle
    dash_map = {
        "-": "solid",
        "--": "dash",
        "-.": "dashdot",
        ":": "dot",
    }
    dash = dash_map.get(linestyle, "solid")

    trace = go.Scatter(
        x=xdata,
        y=ydata,
        mode="lines",
        name=label,
        line={"color": color_str, "width": linewidth, "dash": dash},
        hovertemplate=hover_template,
    )

    plotly_fig.add_trace(trace, row=row, col=col)


def _add_bar_from_patch(
    patch: Any,
    plotly_fig: "go.Figure",
    row: Optional[int],
    col: Optional[int],
) -> None:
    """Add bar plot from matplotlib patch (not fully implemented)."""
    # This is a simplified version - full conversion would need more logic
    # to aggregate all patches into bar traces
    pass


def _add_scatter_trace(
    collection: Any,
    plotly_fig: "go.Figure",
    row: Optional[int],
    col: Optional[int],
    hover_template: Optional[str],
) -> None:
    """Add scatter plot trace to Plotly figure."""
    # PathCollection (from scatter plots)
    if hasattr(collection, "get_offsets"):
        offsets = collection.get_offsets()
        if len(offsets) > 0:
            xdata = offsets[:, 0]
            ydata = offsets[:, 1]

            # Get scatter properties
            sizes = collection.get_sizes()
            colors = collection.get_facecolors()

            # Convert color to Plotly format
            if len(colors) > 0:
                color_str = _convert_color_to_plotly(colors[0])
            else:
                color_str = "blue"

            trace = go.Scatter(
                x=xdata,
                y=ydata,
                mode="markers",
                marker={
                    "size": sizes[0] if len(sizes) > 0 else 6,
                    "color": color_str,
                },
                hovertemplate=hover_template,
            )

            plotly_fig.add_trace(trace, row=row, col=col)


def _determine_subplot_layout(n_axes: int) -> Tuple[int, int]:
    """Determine optimal subplot grid layout.

    Args:
        n_axes: Number of axes/subplots

    Returns:
        Tuple of (rows, cols)
    """
    if n_axes <= 1:
        return 1, 1
    elif n_axes == 2:
        return 2, 1
    elif n_axes <= 4:
        return 2, 2
    elif n_axes <= 6:
        return 2, 3
    elif n_axes <= 9:
        return 3, 3
    else:
        # For many subplots, use a more square layout
        rows = int(np.ceil(np.sqrt(n_axes)))
        cols = int(np.ceil(n_axes / rows))
        return rows, cols


def _preserve_matplotlib_layout(mpl_fig: Figure, plotly_fig: "go.Figure") -> None:
    """Preserve matplotlib layout settings in Plotly figure.

    Args:
        mpl_fig: Original matplotlib figure
        plotly_fig: Plotly figure to update
    """
    # Get matplotlib figure size
    width, height = mpl_fig.get_size_inches()

    # Convert to pixels (assuming 100 DPI)
    plotly_fig.update_layout(
        width=int(width * 100),
        height=int(height * 100),
    )


def save_plotly_html(
    plotly_fig: "go.Figure",
    filepath: str,
    include_plotlyjs: Union[bool, str] = "cdn",
    auto_open: bool = False,
) -> None:
    """Save Plotly figure as standalone HTML file.

    Args:
        plotly_fig: Plotly figure to save
        filepath: Output filepath (.html extension)
        include_plotlyjs: How to include plotly.js library
            - 'cdn': Link to CDN (smaller file, requires internet)
            - True: Embed full library (larger file, works offline)
            - False: Don't include (requires plotly.js loaded separately)
        auto_open: Automatically open in browser after saving

    Example:
        >>> save_plotly_html(fig, 'output/chart.html', auto_open=True)
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("Plotly is not installed")

    logger.info(f"Saving Plotly figure to {filepath}")

    # Ensure .html extension
    if not filepath.endswith(".html"):
        filepath = f"{filepath}.html"

    # Save figure
    plotly_fig.write_html(
        filepath,
        include_plotlyjs=include_plotlyjs,
        auto_open=auto_open,
    )

    logger.success(f"Plotly figure saved to {filepath}")


def convert_and_save(
    mpl_fig: Figure,
    filepath: str,
    auto_open: bool = False,
    **kwargs: Any,
) -> "go.Figure":
    """Convert matplotlib figure to Plotly and save as HTML.

    Convenience function that combines conversion and saving.

    Args:
        mpl_fig: Matplotlib figure to convert
        filepath: Output filepath for HTML
        auto_open: Open in browser after saving
        **kwargs: Additional arguments for to_plotly()

    Returns:
        Converted Plotly figure

    Example:
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3], [1, 4, 2])
        >>> plotly_fig = convert_and_save(
        ...     fig,
        ...     'output/interactive.html',
        ...     auto_open=True
        ... )
    """
    # Convert to Plotly
    plotly_fig = to_plotly(mpl_fig, **kwargs)

    # Save as HTML
    save_plotly_html(plotly_fig, filepath, auto_open=auto_open)

    return plotly_fig


def create_plotly_time_series(
    data: pd.DataFrame,
    y_columns: Union[str, List[str]],
    x_column: Optional[str] = None,
    title: str = "Time Series",
    rangeslider: bool = True,
    **kwargs: Any,
) -> "go.Figure":
    """Create interactive time series plot with Plotly.

    Args:
        data: DataFrame with time series data
        y_columns: Column name(s) to plot on y-axis
        x_column: Column name for x-axis (None = use index)
        title: Plot title
        rangeslider: Add interactive range slider
        **kwargs: Additional layout arguments

    Returns:
        Interactive Plotly figure

    Example:
        >>> df = pd.DataFrame({
        ...     'date': pd.date_range('2024-01-01', periods=100),
        ...     'equity': np.cumsum(np.random.randn(100))
        ... })
        >>> fig = create_plotly_time_series(
        ...     df, y_columns='equity', x_column='date'
        ... )
        >>> fig.show()
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("Plotly is not installed")

    # Create figure
    fig = go.Figure()

    # Get x data
    if x_column:
        x_data = data[x_column]
    else:
        x_data = data.index

    # Add traces for each y column
    if isinstance(y_columns, str):
        y_columns = [y_columns]

    for col in y_columns:
        fig.add_trace(
            go.Scatter(
                x=x_data,
                y=data[col],
                mode="lines",
                name=col,
            )
        )

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title=x_column or "Index",
        yaxis_title="Value",
        hovermode="x unified",
        **kwargs,
    )

    # Add range slider
    if rangeslider:
        fig.update_xaxes(rangeslider_visible=True)

    return fig


def create_plotly_candlestick(
    data: pd.DataFrame,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: Optional[str] = "volume",
    title: str = "Candlestick Chart",
    **kwargs: Any,
) -> "go.Figure":
    """Create interactive candlestick chart with Plotly.

    Args:
        data: DataFrame with OHLCV data
        open_col: Column name for open prices
        high_col: Column name for high prices
        low_col: Column name for low prices
        close_col: Column name for close prices
        volume_col: Column name for volume (None to exclude)
        title: Chart title
        **kwargs: Additional layout arguments

    Returns:
        Interactive Plotly figure with candlestick chart

    Example:
        >>> fig = create_plotly_candlestick(ohlcv_data)
        >>> fig.show()
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("Plotly is not installed")

    # Create subplots if volume is included
    if volume_col and volume_col in data.columns:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(title, "Volume"),
            row_heights=[0.7, 0.3],
        )

        # Add candlestick
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data[open_col],
                high=data[high_col],
                low=data[low_col],
                close=data[close_col],
                name="OHLC",
            ),
            row=1,
            col=1,
        )

        # Add volume bars
        colors = [
            "green" if data[close_col].iloc[i] >= data[open_col].iloc[i] else "red"
            for i in range(len(data))
        ]

        fig.add_trace(
            go.Bar(
                x=data.index,
                y=data[volume_col],
                name="Volume",
                marker_color=colors,
            ),
            row=2,
            col=1,
        )

    else:
        # Candlestick only
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=data.index,
                    open=data[open_col],
                    high=data[high_col],
                    low=data[low_col],
                    close=data[close_col],
                )
            ]
        )
        fig.update_layout(title=title)

    # Update layout
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        **kwargs,
    )

    return fig


__all__ = [
    "PLOTLY_AVAILABLE",
    "to_plotly",
    "save_plotly_html",
    "convert_and_save",
    "create_plotly_time_series",
    "create_plotly_candlestick",
]

