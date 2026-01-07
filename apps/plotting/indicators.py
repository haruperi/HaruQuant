"""Indicator overlay plotting for backtest visualization.

This module provides functions for plotting technical indicators on charts.
Supports both overlay indicators (on price chart) and panel indicators
(in separate subplots).

Features:
- Automatic indicator classification (overlay vs panel)
- Overlay indicators: moving averages, Bollinger Bands, etc.
- Panel indicators: RSI, MACD, Stochastic, etc.
- Multi-line indicator support
- Reference levels for oscillators
- Filled areas (e.g., between Bollinger Bands)
"""

from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes

from apps.plotting.core import (
    DEFAULT_COLOR_SEQUENCE,
    _format_axis,
    _format_date_axis,
    _format_grid,
)

# Common overlay indicators
OVERLAY_INDICATORS = {
    "sma",
    "ema",
    "wma",
    "dema",
    "tema",
    "kama",
    "bb",
    "bbands",
    "bollinger",
    "kc",
    "keltner",
    "dc",
    "donchian",
    "sar",
    "parabolic",
    "supertrend",
    "vwap",
    "pivot",
}

# Common panel indicators
PANEL_INDICATORS = {
    "rsi",
    "macd",
    "stoch",
    "stochastic",
    "cci",
    "adx",
    "atr",
    "obv",
    "mfi",
    "williams",
    "roc",
    "momentum",
    "tsi",
    "uo",
    "ao",
}


def _classify_indicator(
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Classify indicator as overlay or panel based on name and metadata.

    Args:
        name: Indicator name
        metadata: Optional metadata dictionary with plot hints

    Returns:
        Tuple of (plot_type, style_hints) where:
        - plot_type is "overlay" or "panel"
        - style_hints contains color, linestyle, etc.

    Example:
        >>> _classify_indicator("sma_20")
        ('overlay', {'color': None, 'linestyle': '-'})
        >>> _classify_indicator("rsi")
        ('panel', {'color': None, 'linestyle': '-', 'levels': [30, 70]})
    """
    # Check metadata first if available
    if metadata and "plot_type" in metadata:
        plot_type = metadata["plot_type"]
        style_hints = metadata.get("style", {})
    else:
        # Classify based on name
        name_lower = name.lower()

        # Check for known overlay indicators
        is_overlay = any(ind in name_lower for ind in OVERLAY_INDICATORS)

        if is_overlay:
            plot_type = "overlay"
            style_hints = {"linestyle": "-"}
        else:
            # Check for known panel indicators
            is_panel = any(ind in name_lower for ind in PANEL_INDICATORS)

            if is_panel:
                plot_type = "panel"
                style_hints = {"linestyle": "-"}

                # Add reference levels for oscillators
                if "rsi" in name_lower:
                    style_hints["levels"] = [30, 70]
                    style_hints["range"] = [0, 100]
                elif "stoch" in name_lower:
                    style_hints["levels"] = [20, 80]
                    style_hints["range"] = [0, 100]
                elif "cci" in name_lower:
                    style_hints["levels"] = [-100, 100]
                elif "williams" in name_lower:
                    style_hints["levels"] = [-20, -80]
                    style_hints["range"] = [-100, 0]
            else:
                # Default to overlay for unknown indicators
                plot_type = "overlay"
                style_hints = {"linestyle": "-"}

    return plot_type, style_hints


def _plot_overlay_indicators(
    ax: Axes,
    indicators: Dict[str, Union[pd.Series, pd.DataFrame]],
    color_sequence: Optional[List[str]] = None,
    show_legend: bool = True,
    **kwargs: Any,
) -> Axes:
    """Plot overlay indicators on price chart.

    Args:
        ax: Matplotlib axes to plot on
        indicators: Dictionary mapping indicator names to data
        color_sequence: List of colors to cycle through
        show_legend: Whether to add indicators to legend
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes object

    Example:
        >>> fig, ax = plt.subplots()
        >>> indicators = {
        ...     'SMA_20': pd.Series([100, 101, 102]),
        ...     'SMA_50': pd.Series([99, 100, 101])
        ... }
        >>> _plot_overlay_indicators(ax, indicators)
    """
    if not indicators:
        return ax

    # Use default color sequence if not provided
    if color_sequence is None:
        color_sequence = DEFAULT_COLOR_SEQUENCE

    for color_idx, (name, data) in enumerate(indicators.items()):
        # Classify indicator to get style hints
        _, style_hints = _classify_indicator(name)

        # Get color
        color = (
            style_hints.get("color") or color_sequence[color_idx % len(color_sequence)]
        )

        # Get line style
        linestyle = style_hints.get("linestyle", "-")

        # Handle multi-series indicators (e.g., Bollinger Bands)
        if isinstance(data, pd.DataFrame):
            # Plot each column
            for col in data.columns:
                label = f"{name}_{col}" if show_legend else None
                ax.plot(
                    mdates.date2num(data.index),
                    data[col],
                    label=label,
                    color=color,
                    linestyle=linestyle,
                    alpha=kwargs.get("alpha", 0.7),
                    linewidth=kwargs.get("linewidth", 1.5),
                )

            # Add filled area for bands (if applicable)
            if len(data.columns) >= 2 and any(
                x in name.lower() for x in ["bb", "bollinger", "keltner", "donchian"]
            ):
                ax.fill_between(
                    mdates.date2num(data.index),
                    data.iloc[:, 0],  # Lower band
                    data.iloc[:, -1],  # Upper band
                    alpha=kwargs.get("fill_alpha", 0.1),
                    color=color,
                )

        else:
            # Single series indicator
            label = name if show_legend else None
            ax.plot(
                mdates.date2num(data.index),
                data.values,
                label=label,
                color=color,
                linestyle=linestyle,
                alpha=kwargs.get("alpha", 0.8),
                linewidth=kwargs.get("linewidth", 1.5),
            )

    return ax


def _plot_panel_indicators(
    indicators: Dict[str, Union[pd.Series, pd.DataFrame]],
    dates: pd.DatetimeIndex,
    figsize: Optional[Tuple[float, float]] = None,
    sharex: Optional[Axes] = None,
    **kwargs: Any,
) -> Tuple[plt.Figure, List[Axes]]:
    """Plot panel indicators in separate subplots.

    Args:
        indicators: Dictionary mapping indicator names to data
        dates: DatetimeIndex for x-axis
        figsize: Figure size (width, height)
        sharex: Axes to share x-axis with
        **kwargs: Additional plotting parameters

    Returns:
        Tuple of (figure, list of axes)

    Example:
        >>> indicators = {'RSI': pd.Series([50, 60, 70])}
        >>> dates = pd.date_range('2024-01-01', periods=3)
        >>> fig, axes = _plot_panel_indicators(indicators, dates)
    """
    if not indicators:
        return None, []

    n_indicators = len(indicators)

    # Create figure with subplots
    if figsize is None:
        figsize = (12, 3 * n_indicators)

    fig, axes = plt.subplots(
        n_indicators,
        1,
        figsize=figsize,
        sharex=sharex is not None,
    )

    # Ensure axes is a list
    if n_indicators == 1:
        axes = [axes]

    color_sequence = DEFAULT_COLOR_SEQUENCE
    for idx, (name, data) in enumerate(indicators.items()):
        _plot_single_panel_indicator(
            ax=axes[idx],
            name=name,
            data=data,
            dates=dates,
            color_sequence=color_sequence,
            color_idx=idx,
            is_last_subplot=(idx == n_indicators - 1),
            **kwargs,
        )

    plt.tight_layout()

    return fig, axes


def _plot_single_panel_indicator(
    ax: Axes,
    name: str,
    data: Union[pd.Series, pd.DataFrame],
    dates: pd.DatetimeIndex,
    color_sequence: List[str],
    color_idx: int,
    is_last_subplot: bool,
    **kwargs: Any,
) -> None:
    """Plot a single panel indicator on specific axes."""
    # Classify indicator to get style hints
    _, style_hints = _classify_indicator(name)

    # Get color
    color = style_hints.get("color") or color_sequence[color_idx % len(color_sequence)]

    # Handle multi-series indicators (e.g., MACD with signal and histogram)
    if isinstance(data, pd.DataFrame):
        # Determine base color index for columns - behaves as original logic
        # Original: color_idx incremented before inner loop
        base_color_idx = color_idx + 1

        for col_idx, col in enumerate(data.columns):
            col_color = color_sequence[(base_color_idx + col_idx) % len(color_sequence)]

            # Check if this is a histogram column (for MACD)
            if "hist" in col.lower():
                # Plot as bar chart
                ax.bar(
                    mdates.date2num(data.index),
                    data[col],
                    width=kwargs.get("bar_width", 0.8),
                    color=col_color,
                    alpha=0.3,
                    label=col,
                )
            else:
                # Plot as line
                ax.plot(
                    mdates.date2num(data.index),
                    data[col],
                    label=col,
                    color=col_color,
                    linewidth=kwargs.get("linewidth", 1.5),
                )
    else:
        # Single series indicator
        ax.plot(
            mdates.date2num(data.index),
            data.values,
            label=name,
            color=color,
            linewidth=kwargs.get("linewidth", 1.5),
        )

    # Add reference levels if specified
    if "levels" in style_hints:
        for level in style_hints["levels"]:
            ax.axhline(
                y=level,
                color="gray",
                linestyle="--",
                alpha=0.5,
                linewidth=1,
            )

    # Add zero line for centered oscillators
    if style_hints.get("zero_line", False) or any(
        x in name.lower() for x in ["macd", "momentum", "roc", "cci"]
    ):
        ax.axhline(y=0, color="black", linestyle="-", alpha=0.3, linewidth=1)

    # Set y-axis range if specified
    if "range" in style_hints:
        ax.set_ylim(style_hints["range"])

    # Format axes
    _format_axis(ax, title=name, ylabel=name)
    _format_grid(ax)

    # Format date axis for the last subplot
    if is_last_subplot:
        _format_date_axis(ax, dates)
    else:
        ax.set_xlabel("")

    # Add legend
    ax.legend(loc="upper left", fontsize=8)


def _create_indicator_subplot(
    main_ax: Axes,
    indicator_name: str,
    indicator_data: Union[pd.Series, pd.DataFrame],
    height_ratio: float = 0.3,
    **kwargs: Any,
) -> Axes:
    """Create a subplot for a single indicator below the main chart.

    Args:
        main_ax: Main chart axes
        indicator_name: Name of the indicator
        indicator_data: Indicator data (Series or DataFrame)
        height_ratio: Height of indicator panel relative to main chart
        **kwargs: Additional plotting parameters

    Returns:
        New axes for the indicator

    Example:
        >>> fig, ax = plt.subplots()
        >>> rsi = pd.Series([50, 60, 70])
        >>> indicator_ax = _create_indicator_subplot(ax, 'RSI', rsi)
    """
    # Get figure from main axes
    fig = main_ax.figure

    # Get position of main axes
    pos = main_ax.get_position()

    # Calculate new positions
    main_height = pos.height * (1 / (1 + height_ratio))
    indicator_height = pos.height * (height_ratio / (1 + height_ratio))

    # Adjust main axes
    main_ax.set_position([pos.x0, pos.y0 + indicator_height, pos.width, main_height])

    # Create new axes for indicator
    indicator_ax = fig.add_axes([pos.x0, pos.y0, pos.width, indicator_height])

    # Classify indicator
    _, style_hints = _classify_indicator(indicator_name)

    # Plot indicator
    if isinstance(indicator_data, pd.DataFrame):
        for col in indicator_data.columns:
            indicator_ax.plot(
                mdates.date2num(indicator_data.index),
                indicator_data[col],
                label=col,
                linewidth=kwargs.get("linewidth", 1.5),
            )
    else:
        indicator_ax.plot(
            mdates.date2num(indicator_data.index),
            indicator_data.values,
            label=indicator_name,
            linewidth=kwargs.get("linewidth", 1.5),
        )

    # Add reference levels
    if "levels" in style_hints:
        for level in style_hints["levels"]:
            indicator_ax.axhline(
                y=level,
                color="gray",
                linestyle="--",
                alpha=0.5,
                linewidth=1,
            )

    # Add zero line if appropriate
    if style_hints.get("zero_line", False) or any(
        x in indicator_name.lower() for x in ["macd", "momentum", "roc"]
    ):
        indicator_ax.axhline(y=0, color="black", linestyle="-", alpha=0.3, linewidth=1)

    # Format axes
    _format_axis(indicator_ax, title=indicator_name, ylabel=indicator_name)
    _format_grid(indicator_ax)
    _format_date_axis(indicator_ax, indicator_data.index)

    # Share x-axis with main chart
    indicator_ax.sharex(main_ax)

    # Add legend
    indicator_ax.legend(loc="upper left", fontsize=8)

    return indicator_ax


__all__ = [
    "_classify_indicator",
    "_plot_overlay_indicators",
    "_plot_panel_indicators",
    "_create_indicator_subplot",
]
