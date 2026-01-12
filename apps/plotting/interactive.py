"""Interactive plotting utilities using Bokeh.

This module provides interactive plotting capabilities including:
- Linked crosshairs across multiple charts
- Pan, zoom, and selection tools
- Customized hover tooltips
- Interactive legends with toggles
- Range selector for time-based data

All functions are designed to enhance user interactivity with Bokeh charts.
"""

import warnings
from typing import Any, List, Literal, Optional, Tuple

import numpy as np

try:
    from bokeh.layouts import column, gridplot, row
    from bokeh.models import (
        BoxZoomTool,
        CrosshairTool,
        HoverTool,
        PanTool,
        RangeTool,
        ResetTool,
        WheelZoomTool,
    )
    from bokeh.models.widgets import CheckboxGroup
    from bokeh.plotting import figure

    BOKEH_AVAILABLE = True
except ImportError:
    BOKEH_AVAILABLE = False
    warnings.warn(
        "Bokeh not available. Interactive plotting features disabled.", stacklevel=2
    )

from apps.logger import logger

# =============================================================================
# CROSSHAIR TOOL
# =============================================================================


def add_linked_crosshair(
    figures: List[Any],
    dimensions: Literal["both", "width", "height"] = "both",
    line_color: str = "#999999",
    line_alpha: float = 0.8,
    line_width: int = 1,
) -> None:
    """Add linked crosshair across multiple Bokeh figures.

    The crosshair synchronizes across all figures, showing values at the cursor
    position in all linked charts simultaneously.

    Args:
        figures: List of Bokeh figure objects to link
        dimensions: Which dimensions to sync - 'both', 'width' (x-axis), or 'height' (y-axis)
        line_color: Color of crosshair lines
        line_alpha: Transparency of crosshair lines (0-1)
        line_width: Width of crosshair lines in pixels

    Examples:
        >>> fig1 = figure(title="Price")
        >>> fig2 = figure(title="Volume")
        >>> add_linked_crosshair([fig1, fig2])
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - crosshair not added")
        return

    if not figures:
        logger.warning("No figures provided for linked crosshair")
        return

    logger.debug(f"Adding linked crosshair to {len(figures)} figures")

    # Create crosshair tool with specified properties
    crosshair = CrosshairTool(
        dimensions=dimensions,
        line_color=line_color,
        line_alpha=line_alpha,
        line_width=line_width,
    )

    # Add crosshair to all figures
    for fig in figures:
        if hasattr(fig, "add_tools"):
            fig.add_tools(crosshair)
        else:
            logger.warning(f"Figure {fig} does not support add_tools()")

    logger.success(f"Linked crosshair added to {len(figures)} figures")


# =============================================================================
# PAN & ZOOM TOOLS
# =============================================================================


def add_pan_zoom_tools(
    fig: Any,
    enable_pan: bool = True,
    enable_wheel_zoom: bool = True,
    enable_box_zoom: bool = True,
    enable_reset: bool = True,
    dimensions: Literal["both", "width", "height"] = "both",
) -> None:
    """Add pan and zoom tools to a Bokeh figure.

    Args:
        fig: Bokeh figure object
        enable_pan: Enable pan tool for dragging the view
        enable_wheel_zoom: Enable mouse wheel zoom
        enable_box_zoom: Enable box selection zoom
        enable_reset: Enable reset tool to restore original view
        dimensions: Which dimensions to enable for tools

    Examples:
        >>> fig = figure(title="Equity Curve")
        >>> add_pan_zoom_tools(fig, dimensions="width")  # Only horizontal pan/zoom
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - pan/zoom tools not added")
        return

    if fig is None:
        logger.warning("Figure is None - pan/zoom tools not added")
        return

    logger.debug(
        f"Adding pan/zoom tools to figure: {getattr(fig, 'title', 'Untitled')}"
    )

    tools = []
    active_drag = None
    active_scroll = None

    if enable_pan:
        pan = PanTool(dimensions=dimensions)
        tools.append(pan)
        active_drag = pan

    if enable_wheel_zoom:
        wheel_zoom = WheelZoomTool(dimensions=dimensions)
        tools.append(wheel_zoom)
        active_scroll = wheel_zoom

    if enable_box_zoom:
        box_zoom = BoxZoomTool(dimensions=dimensions)
        tools.append(box_zoom)

    if enable_reset:
        reset = ResetTool()
        tools.append(reset)

    # Add all tools to figure
    if tools:
        fig.add_tools(*tools)
        # Set active tools after adding them
        if active_drag:
            fig.toolbar.active_drag = active_drag
        if active_scroll:
            fig.toolbar.active_scroll = active_scroll
        logger.success(f"Added {len(tools)} pan/zoom tools to figure")


def sync_zoom_across_figures(
    figures: List[Any], sync_x: bool = True, sync_y: bool = False
) -> None:
    """Synchronize zoom across multiple Bokeh figures.

    Args:
        figures: List of Bokeh figures to synchronize
        sync_x: Synchronize x-axis range
        sync_y: Synchronize y-axis range

    Examples:
        >>> fig1 = figure(x_axis_type="datetime")
        >>> fig2 = figure(x_axis_type="datetime")
        >>> sync_zoom_across_figures([fig1, fig2], sync_x=True)
    """
    if not BOKEH_AVAILABLE or not figures:
        return

    logger.debug(f"Synchronizing zoom across {len(figures)} figures")

    # Link x-axis ranges
    if sync_x and len(figures) > 1:
        base_x_range = figures[0].x_range
        for fig in figures[1:]:
            fig.x_range = base_x_range

    # Link y-axis ranges
    if sync_y and len(figures) > 1:
        base_y_range = figures[0].y_range
        for fig in figures[1:]:
            fig.y_range = base_y_range

    logger.success("Zoom synchronization configured")


# =============================================================================
# HOVER TOOLTIPS
# =============================================================================


def add_ohlc_hover(
    fig: Any,
    date_format: str = "%Y-%m-%d",
    value_format: str = "0,0.00",
) -> HoverTool:
    """Add hover tooltip for OHLC candlestick chart.

    Args:
        fig: Bokeh figure object
        date_format: Format string for date display
        value_format: Format string for price values

    Returns:
        HoverTool object added to the figure

    Examples:
        >>> fig = figure(x_axis_type="datetime")
        >>> hover = add_ohlc_hover(fig)
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - hover tooltip not added")
        return None

    tooltips = [
        ("Date", f"@date{{{date_format}}}"),
        ("Open", f"@open{{{value_format}}}"),
        ("High", f"@high{{{value_format}}}"),
        ("Low", f"@low{{{value_format}}}"),
        ("Close", f"@close{{{value_format}}}"),
        ("Volume", "@volume{0,0}"),
    ]

    hover = HoverTool(tooltips=tooltips, formatters={"@date": "datetime"})
    fig.add_tools(hover)

    logger.debug("OHLC hover tooltip added")
    return hover


def add_equity_hover(
    fig: Any,
    date_format: str = "%Y-%m-%d",
    value_format: str = "0,0.00",
    show_returns: bool = True,
) -> HoverTool:
    """Add hover tooltip for equity curve.

    Args:
        fig: Bokeh figure object
        date_format: Format string for date display
        value_format: Format string for equity values
        show_returns: Include return percentage in tooltip

    Returns:
        HoverTool object added to the figure

    Examples:
        >>> fig = figure(x_axis_type="datetime")
        >>> hover = add_equity_hover(fig, show_returns=True)
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - hover tooltip not added")
        return None

    tooltips = [
        ("Date", f"@x{{{date_format}}}"),
        ("Equity", f"@y{{{value_format}}}"),
    ]

    if show_returns:
        tooltips.append(("Return", "@returns{0.00%}"))

    hover = HoverTool(tooltips=tooltips, formatters={"@x": "datetime"})
    fig.add_tools(hover)

    logger.debug("Equity hover tooltip added")
    return hover


def add_indicator_hover(
    fig: Any,
    indicator_name: str,
    date_format: str = "%Y-%m-%d",
    value_format: str = "0.00",
) -> HoverTool:
    """Add hover tooltip for technical indicator.

    Args:
        fig: Bokeh figure object
        indicator_name: Name of the indicator to display
        date_format: Format string for date display
        value_format: Format string for indicator values

    Returns:
        HoverTool object added to the figure

    Examples:
        >>> fig = figure(x_axis_type="datetime")
        >>> hover = add_indicator_hover(fig, "RSI")
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - hover tooltip not added")
        return None

    tooltips = [
        ("Date", f"@x{{{date_format}}}"),
        (indicator_name, f"@y{{{value_format}}}"),
    ]

    hover = HoverTool(tooltips=tooltips, formatters={"@x": "datetime"})
    fig.add_tools(hover)

    logger.debug(f"{indicator_name} hover tooltip added")
    return hover


def add_trade_hover(
    fig: Any,
    date_format: str = "%Y-%m-%d",
    value_format: str = "0,0.00",
) -> HoverTool:
    """Add hover tooltip for trade markers.

    Args:
        fig: Bokeh figure object
        date_format: Format string for date display
        value_format: Format string for price values

    Returns:
        HoverTool object added to the figure

    Examples:
        >>> fig = figure(x_axis_type="datetime")
        >>> hover = add_trade_hover(fig)
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - hover tooltip not added")
        return None

    tooltips = [
        ("Date", f"@date{{{date_format}}}"),
        ("Type", "@trade_type"),
        ("Price", f"@price{{{value_format}}}"),
        ("Size", "@size{0,0.0000}"),
        ("P&L", f"@pnl{{{value_format}}}"),
    ]

    hover = HoverTool(tooltips=tooltips, formatters={"@date": "datetime"})
    fig.add_tools(hover)

    logger.debug("Trade hover tooltip added")
    return hover


def add_drawdown_hover(
    fig: Any,
    date_format: str = "%Y-%m-%d",
    show_duration: bool = True,
) -> HoverTool:
    """Add hover tooltip for drawdown chart.

    Args:
        fig: Bokeh figure object
        date_format: Format string for date display
        show_duration: Include drawdown duration in tooltip

    Returns:
        HoverTool object added to the figure

    Examples:
        >>> fig = figure(x_axis_type="datetime")
        >>> hover = add_drawdown_hover(fig, show_duration=True)
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - hover tooltip not added")
        return None

    tooltips = [
        ("Date", f"@x{{{date_format}}}"),
        ("Drawdown", "@y{0.00%}"),
    ]

    if show_duration:
        tooltips.append(("Duration", "@duration days"))

    hover = HoverTool(tooltips=tooltips, formatters={"@x": "datetime"})
    fig.add_tools(hover)

    logger.debug("Drawdown hover tooltip added")
    return hover


def customize_hover_css(
    background_color: str = "#f7f7f7",
    border_color: str = "#cccccc",
    font_size: str = "12px",
    padding: str = "10px",
) -> str:
    """Generate custom CSS for hover tooltips.

    Args:
        background_color: Background color of tooltip
        border_color: Border color of tooltip
        font_size: Font size for tooltip text
        padding: Padding inside tooltip

    Returns:
        CSS string for tooltip styling

    Examples:
        >>> css = customize_hover_css(background_color="#ffffff")
    """
    css = f"""
    .bk-tooltip {{
        background-color: {background_color} !important;
        border: 1px solid {border_color} !important;
        font-size: {font_size} !important;
        padding: {padding} !important;
        border-radius: 4px !important;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important;
    }}
    .bk-tooltip > div {{
        padding: 2px 0 !important;
    }}
    """
    return css


# =============================================================================
# INTERACTIVE LEGEND
# =============================================================================


def configure_interactive_legend(
    fig: Any,
    location: Literal[
        "top_left",
        "top_center",
        "top_right",
        "center_left",
        "center",
        "center_right",
        "bottom_left",
        "bottom_center",
        "bottom_right",
    ] = "top_right",
    click_policy: Literal["hide", "mute"] = "hide",
    background_fill_alpha: float = 0.8,
    border_line_color: str = "#cccccc",
) -> None:
    """Configure interactive legend for a Bokeh figure.

    Args:
        fig: Bokeh figure object
        location: Position of the legend
        click_policy: Behavior when clicking legend items - 'hide' or 'mute'
        background_fill_alpha: Transparency of legend background (0-1)
        border_line_color: Color of legend border

    Examples:
        >>> fig = figure()
        >>> fig.line(x, y, legend_label="Series 1")
        >>> configure_interactive_legend(fig, click_policy="hide")
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - legend not configured")
        return

    if not hasattr(fig, "legend"):
        logger.warning("Figure has no legend to configure")
        return

    # Check if legend is actually empty
    if not fig.legend and hasattr(fig, "renderers"):
        # Try to find if any renderers have legend labels/fields to know if it's worth warning
        # But mostly, if fig.legend is empty list, we can't set properties on it easily in some versions
        # or it just warns.
        # Let's check if the legend property works.
        # In newer Bokeh, fig.legend returns a list of Legend objects.
        # If accessing it creates one, we might be fine, but the warning says "zero legends added".
        return

    try:
        fig.legend.location = location
        fig.legend.click_policy = click_policy
        fig.legend.background_fill_alpha = background_fill_alpha
        fig.legend.border_line_color = border_line_color
        fig.legend.label_text_font_size = "10pt"
        fig.legend.spacing = 5
        fig.legend.padding = 10

        logger.debug(
            f"Interactive legend configured at {location} with {click_policy} policy"
        )
    except Exception as e:
        # Catch errors if legend doesn't exist or properties fail
        logger.debug(f"Could not configure legend: {e}")


def create_legend_toggles(
    series_names: List[str], active_by_default: Optional[List[int]] = None
) -> CheckboxGroup:
    """Create checkbox widgets for toggling plot series.

    Args:
        series_names: List of series names to create toggles for
        active_by_default: Indices of series that should be active initially

    Returns:
        CheckboxGroup widget

    Examples:
        >>> toggles = create_legend_toggles(["MA20", "MA50", "MA200"])
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - toggles not created")
        return None

    if active_by_default is None:
        active_by_default = list(range(len(series_names)))

    checkbox = CheckboxGroup(labels=series_names, active=active_by_default)

    logger.debug(f"Created toggles for {len(series_names)} series")
    return checkbox


# =============================================================================
# RANGE SELECTOR
# =============================================================================


def add_range_selector(
    main_fig: Any,
    data_source: Any,
    height: int = 100,
    y_column: str = "close",
    x_column: str = "date",
) -> Tuple[Any, Any]:
    """Add a range selector tool with mini chart.

    The range selector displays a small overview chart showing the full data range,
    with a draggable selection box that updates the main chart's visible range.

    Args:
        main_fig: Main Bokeh figure to control
        data_source: ColumnDataSource with the data
        height: Height of the range selector chart in pixels
        y_column: Column name to plot in the range selector
        x_column: Column name for x-axis (default: "date")

    Returns:
        Tuple of (range_selector_figure, range_tool)

    Examples:
        >>> from bokeh.models import ColumnDataSource
        >>> source = ColumnDataSource(data=dict(x=dates, close=prices))
        >>> main_fig = figure(x_axis_type="datetime")
        >>> selector_fig, range_tool = add_range_selector(main_fig, source)
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - range selector not added")
        return None, None

    # Create small figure for range selection
    select_fig = figure(
        height=height,
        width=main_fig.width if hasattr(main_fig, "width") else 1200,
        y_range=main_fig.y_range,
        x_axis_type="datetime",
        y_axis_type=None,
        tools="",
        toolbar_location=None,
        background_fill_color="#efefef",
    )

    # Plot data in selector
    select_fig.line(x_column, y_column, source=data_source, line_color="#3498db")

    # Create range tool
    range_tool = RangeTool(x_range=main_fig.x_range)
    range_tool.overlay.fill_color = "navy"
    range_tool.overlay.fill_alpha = 0.2

    # Add range tool to selector
    select_fig.add_tools(range_tool)
    # Note: RangeTool doesn't need to be set as active_multi
    # It's automatically active when added

    logger.success("Range selector added")
    return select_fig, range_tool


def create_range_selector_layout(
    main_fig: Any,
    data_source: Any,
    selector_height: int = 100,
    y_column: str = "close",
) -> Any:
    """Create a layout combining main figure with range selector.

    Args:
        main_fig: Main Bokeh figure
        data_source: ColumnDataSource with the data
        selector_height: Height of range selector in pixels
        y_column: Column to plot in range selector

    Returns:
        Bokeh column layout with main figure and selector

    Examples:
        >>> from bokeh.models import ColumnDataSource
        >>> source = ColumnDataSource(data=dict(x=dates, close=prices))
        >>> fig = figure(x_axis_type="datetime")
        >>> layout = create_range_selector_layout(fig, source)
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - layout not created")
        return None

    # If main_fig is a layout (e.g. Column), find the first figure to link to
    target_fig = main_fig
    if not hasattr(target_fig, "y_range") and hasattr(target_fig, "children"):
        for child in target_fig.children:
            if hasattr(child, "y_range"):
                target_fig = child
                break

    # Verify we have a valid figure to link to
    if not hasattr(target_fig, "y_range"):
        logger.warning(
            "Cannot add range selector: input object has no y_range and no suitable child figure found"
        )
        return main_fig

    selector_fig, _ = add_range_selector(
        target_fig, data_source, height=selector_height, y_column=y_column
    )

    if selector_fig is None:
        return main_fig

    layout = column(main_fig, selector_fig)
    logger.success("Range selector layout created")
    return layout


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def apply_standard_tools(
    fig: Any,
    enable_crosshair: bool = True,
    enable_hover: bool = True,
    hover_type: Literal["ohlc", "equity", "indicator", "trade", "drawdown"] = "equity",
    enable_pan_zoom: bool = True,
) -> None:
    """Apply standard set of interactive tools to a figure.

    This is a convenience function that applies commonly used tools in one call.

    Args:
        fig: Bokeh figure object
        enable_crosshair: Add crosshair tool
        enable_hover: Add hover tooltip
        hover_type: Type of hover tooltip to add
        enable_pan_zoom: Add pan and zoom tools

    Examples:
        >>> fig = figure(x_axis_type="datetime")
        >>> apply_standard_tools(fig, hover_type="equity")
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh not available - tools not applied")
        return

    logger.info(
        f"Applying standard tools to figure: {getattr(fig, 'title', 'Untitled')}"
    )

    # Add pan and zoom tools
    if enable_pan_zoom:
        add_pan_zoom_tools(fig)

    # Add crosshair
    if enable_crosshair:
        add_linked_crosshair([fig])

    # Add hover tooltip based on type
    if enable_hover:
        if hover_type == "ohlc":
            add_ohlc_hover(fig)
        elif hover_type == "equity":
            add_equity_hover(fig)
        elif hover_type == "indicator":
            add_indicator_hover(fig, "Indicator")
        elif hover_type == "trade":
            add_trade_hover(fig)
        elif hover_type == "drawdown":
            add_drawdown_hover(fig)

    logger.success("Standard tools applied successfully")


def create_linked_chart_layout(
    figures: List[Any],
    layout_type: Literal["column", "row", "grid"] = "column",
    sync_x_zoom: bool = True,
    add_crosshair: bool = True,
) -> Any:
    """Create a layout of linked charts with synchronized tools.

    Args:
        figures: List of Bokeh figures to link
        layout_type: Type of layout - 'column', 'row', or 'grid'
        sync_x_zoom: Synchronize x-axis zoom across charts
        add_crosshair: Add linked crosshair across charts

    Returns:
        Bokeh layout object

    Examples:
        >>> fig1 = figure(title="Price")
        >>> fig2 = figure(title="Volume")
        >>> layout = create_linked_chart_layout([fig1, fig2], sync_x_zoom=True)
    """
    if not BOKEH_AVAILABLE or not figures:
        logger.warning("Cannot create linked layout - Bokeh unavailable or no figures")
        return None

    logger.info(f"Creating linked {layout_type} layout with {len(figures)} figures")

    # Synchronize zoom if requested
    if sync_x_zoom:
        sync_zoom_across_figures(figures, sync_x=True)

    # Add linked crosshair if requested
    if add_crosshair:
        add_linked_crosshair(figures)

    # Create layout based on type
    if layout_type == "column":
        layout = column(*figures)
    elif layout_type == "row":
        layout = row(*figures)
    elif layout_type == "grid":
        # Determine grid dimensions
        n = len(figures)
        ncols = int(np.ceil(np.sqrt(n)))
        nrows = int(np.ceil(n / ncols))

        # Pad figures list to fill grid
        grid_figures = figures + [None] * (nrows * ncols - n)

        # Create grid
        grid = [grid_figures[i * ncols : (i + 1) * ncols] for i in range(nrows)]
        layout = gridplot(grid)
    else:
        logger.error(f"Unknown layout type: {layout_type}")
        return None

    logger.success(f"Linked {layout_type} layout created successfully")
    return layout


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Crosshair
    "add_linked_crosshair",
    # Pan & Zoom
    "add_pan_zoom_tools",
    "sync_zoom_across_figures",
    # Hover tooltips
    "add_ohlc_hover",
    "add_equity_hover",
    "add_indicator_hover",
    "add_trade_hover",
    "add_drawdown_hover",
    "customize_hover_css",
    # Interactive legend
    "configure_interactive_legend",
    "create_legend_toggles",
    # Range selector
    "add_range_selector",
    "create_range_selector_layout",
    # Utilities
    "apply_standard_tools",
    "create_linked_chart_layout",
]
