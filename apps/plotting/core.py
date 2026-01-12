"""Core plotting configuration and utilities.

This module provides:
- Matplotlib and Seaborn default configurations
- Color schemes for trading visualizations
- Axis and legend formatters
- Backend management utilities
- Figure creation and cleanup helpers

The module configures sensible defaults for creating professional-quality
trading charts and performance visualizations.
"""

import contextlib
import gc
import os
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union, cast

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from apps.logger import logger

OutputCallable = Optional[Callable[..., None]]
output_file: OutputCallable = None
output_notebook: OutputCallable = None

try:
    from bokeh.io import output_file as bokeh_output_file
    from bokeh.io import output_notebook as bokeh_output_notebook

    output_file = bokeh_output_file
    output_notebook = bokeh_output_notebook
    BOKEH_AVAILABLE = True
except ImportError:
    BOKEH_AVAILABLE = False
    logger.warning(
        "Bokeh import failed; interactive plotting disabled",
        exc_info=True,
    )
    warnings.warn(
        "Bokeh not available. Interactive plotting will be limited.", stacklevel=2
    )


# =============================================================================
# COLOR SCHEMES
# =============================================================================

# FlatUI color palette (modern, vibrant colors)
FLATUI_COLORS = {
    "turquoise": "#1abc9c",
    "emerald": "#2ecc71",
    "peter_river": "#3498db",
    "amethyst": "#9b59b6",
    "wet_asphalt": "#34495e",
    "green_sea": "#16a085",
    "nephritis": "#27ae60",
    "belize_hole": "#2980b9",
    "wisteria": "#8e44ad",
    "midnight_blue": "#2c3e50",
    "sun_flower": "#f1c40f",
    "carrot": "#e67e22",
    "alizarin": "#e74c3c",
    "clouds": "#ecf0f1",
    "concrete": "#95a5a6",
    "orange": "#f39c12",
    "pumpkin": "#d35400",
    "pomegranate": "#c0392b",
    "silver": "#bdc3c7",
    "asbestos": "#7f8c8d",
}

# Grayscale palette for monochrome charts
GRAYSCALE_COLORS = {
    "dark": "#2d2d2d",
    "medium_dark": "#5a5a5a",
    "medium": "#8a8a8a",
    "medium_light": "#b5b5b5",
    "light": "#e0e0e0",
}

# Trading-specific colors
TRADING_COLORS = {
    "profit": "#2ecc71",  # Green
    "loss": "#e74c3c",  # Red
    "long_entry": "#27ae60",  # Dark green
    "short_entry": "#e67e22",  # Orange
    "long_exit": "#3498db",  # Blue
    "short_exit": "#9b59b6",  # Purple
    "candle_up": "#2ecc71",  # Green
    "candle_down": "#e74c3c",  # Red
    "volume_up": "#2ecc71",  # Green
    "volume_down": "#e74c3c",  # Red
    "neutral": "#95a5a6",  # Gray
}

# Default color sequence for multiple lines
DEFAULT_COLOR_SEQUENCE = [
    FLATUI_COLORS["peter_river"],
    FLATUI_COLORS["emerald"],
    FLATUI_COLORS["amethyst"],
    FLATUI_COLORS["carrot"],
    FLATUI_COLORS["alizarin"],
    FLATUI_COLORS["sun_flower"],
]


def _get_colors(mode: Literal["color", "grayscale"] = "color") -> Dict[str, str]:
    """Get color palette based on mode.

    Args:
        mode: Color mode - 'color' for full colors, 'grayscale' for monochrome

    Returns:
        Dictionary mapping color names to hex codes
    """
    if mode == "grayscale":
        return {
            **GRAYSCALE_COLORS,
            "profit": GRAYSCALE_COLORS["dark"],
            "loss": GRAYSCALE_COLORS["medium_dark"],
            "long_entry": GRAYSCALE_COLORS["dark"],
            "short_entry": GRAYSCALE_COLORS["medium_dark"],
            "long_exit": GRAYSCALE_COLORS["medium"],
            "short_exit": GRAYSCALE_COLORS["medium_light"],
            "candle_up": GRAYSCALE_COLORS["medium_dark"],
            "candle_down": GRAYSCALE_COLORS["medium_light"],
            "volume_up": GRAYSCALE_COLORS["medium_dark"],
            "volume_down": GRAYSCALE_COLORS["medium_light"],
            "neutral": GRAYSCALE_COLORS["medium"],
        }

    return TRADING_COLORS


# =============================================================================
# MATPLOTLIB CONFIGURATION
# =============================================================================


def configure_matplotlib(
    dpi: int = 100,
    figsize: Tuple[float, float] = (12, 8),
    style: str = "seaborn-v0_8-darkgrid",
) -> None:
    """Configure matplotlib with sensible defaults for trading charts.

    Args:
        dpi: Dots per inch for figure resolution
        figsize: Default figure size (width, height) in inches
        style: Matplotlib style to use
    """
    logger.debug(
        "Configuring matplotlib (dpi=%s, figsize=%s, style=%s)",
        dpi,
        figsize,
        style,
    )

    # Set figure defaults
    plt.rcParams["figure.dpi"] = dpi
    plt.rcParams["figure.figsize"] = figsize
    plt.rcParams["savefig.dpi"] = dpi
    plt.rcParams["savefig.bbox"] = "tight"
    plt.rcParams["savefig.pad_inches"] = 0.1

    # Font configuration
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [
        "DejaVu Sans",
        "Arial",
        "Helvetica",
        "Liberation Sans",
        "Bitstream Vera Sans",
        "sans-serif",
    ]
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.titlesize"] = 12
    plt.rcParams["axes.labelsize"] = 10
    plt.rcParams["xtick.labelsize"] = 9
    plt.rcParams["ytick.labelsize"] = 9
    plt.rcParams["legend.fontsize"] = 9

    # Line and marker defaults
    plt.rcParams["lines.linewidth"] = 1.5
    plt.rcParams["lines.markersize"] = 6
    plt.rcParams["lines.markeredgewidth"] = 0.5

    # Grid configuration
    plt.rcParams["grid.alpha"] = 0.3
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["grid.linewidth"] = 0.5

    # Axes configuration
    plt.rcParams["axes.grid"] = True
    plt.rcParams["axes.axisbelow"] = True
    plt.rcParams["axes.edgecolor"] = "#333333"
    plt.rcParams["axes.linewidth"] = 1.0
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False

    # Legend configuration
    plt.rcParams["legend.frameon"] = True
    plt.rcParams["legend.framealpha"] = 0.9
    plt.rcParams["legend.edgecolor"] = "#cccccc"
    plt.rcParams["legend.fancybox"] = True

    # Set style if available
    try:
        plt.style.use(style)
    except (OSError, ValueError):
        warnings.warn(f"Style '{style}' not available, using default", stacklevel=2)


def configure_seaborn(
    context: Literal["paper", "notebook", "talk", "poster"] = "notebook",
    palette: str = "deep",
) -> None:
    """Configure seaborn with sensible defaults.

    Args:
        context: Seaborn context for scaling plot elements
        palette: Color palette name
    """
    logger.debug("Configuring seaborn context=%s palette=%s", context, palette)
    sns.set_context(context)
    sns.set_palette(palette)

    # Additional aesthetic parameters
    sns.set_style(
        "darkgrid",
        {
            "axes.facecolor": "#f9f9f9",
            "grid.color": "#e0e0e0",
            "grid.linestyle": "--",
            "axes.edgecolor": "#333333",
            "axes.linewidth": 1.0,
        },
    )


# =============================================================================
# AXIS FORMATTERS
# =============================================================================


class PercentageFormatter(mticker.Formatter):
    """Format values as percentages."""

    def __init__(self, decimals: int = 1, scale: float = 100.0):
        """Initialize formatter.

        Args:
            decimals: Number of decimal places
            scale: Multiplier for converting to percentage (default 100.0)
        """
        self.decimals = decimals
        self.scale = scale

    def __call__(self, x: float, pos: Optional[int] = None) -> str:
        """Format value as percentage."""
        return f"{x * self.scale:.{self.decimals}f}%"


class CurrencyFormatter(mticker.Formatter):
    """Format values as currency."""

    def __init__(self, symbol: str = "$", decimals: int = 0):
        """Initialize formatter.

        Args:
            symbol: Currency symbol
            decimals: Number of decimal places
        """
        self.symbol = symbol
        self.decimals = decimals

    def __call__(self, x: float, pos: Optional[int] = None) -> str:
        """Format value as currency."""
        if abs(x) >= 1_000_000:
            return f"{self.symbol}{x / 1_000_000:.1f}M"
        if abs(x) >= 1_000:
            return f"{self.symbol}{x / 1_000:.1f}K"
        return f"{self.symbol}{x:.{self.decimals}f}"


class CompactNumberFormatter(mticker.Formatter):
    """Format large numbers compactly (K, M, B)."""

    def __call__(self, x: float, pos: Optional[int] = None) -> str:
        """Format number compactly."""
        if abs(x) >= 1_000_000_000:
            return f"{x / 1_000_000_000:.1f}B"
        if abs(x) >= 1_000_000:
            return f"{x / 1_000_000:.1f}M"
        if abs(x) >= 1_000:
            return f"{x / 1_000:.1f}K"
        return f"{x:.0f}"


# =============================================================================
# FORMATTING UTILITIES
# =============================================================================


def _format_axis(
    axes_obj: Axes,
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title_fontsize: int = 12,
    label_fontsize: int = 10,
) -> None:
    """Format axis with consistent styling.

    Args:
        axes_obj: Matplotlib axes object
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        title_fontsize: Font size for title
        label_fontsize: Font size for labels
    """
    if title:
        axes_obj.set_title(title, fontsize=title_fontsize, fontweight="bold", pad=10)
    if xlabel:
        axes_obj.set_xlabel(xlabel, fontsize=label_fontsize)
    if ylabel:
        axes_obj.set_ylabel(ylabel, fontsize=label_fontsize)

    # Remove top and right spines
    axes_obj.spines["top"].set_visible(False)
    axes_obj.spines["right"].set_visible(False)


def _format_grid(axes_obj: Axes, alpha: float = 0.3, linestyle: str = "--") -> None:
    """Format grid with consistent styling.

    Args:
        axes_obj: Matplotlib axes object
        alpha: Grid transparency
        linestyle: Grid line style
    """
    axes_obj.grid(True, alpha=alpha, linestyle=linestyle, linewidth=0.5)
    axes_obj.set_axisbelow(True)


def _format_legend(
    axes_obj: Axes,
    loc: str = "best",
    frameon: bool = True,
    framealpha: float = 0.9,
    edgecolor: str = "#cccccc",
) -> None:
    """Format legend with consistent styling.

    Args:
        axes_obj: Matplotlib axes object
        loc: Legend location
        frameon: Whether to draw frame
        framealpha: Frame transparency
        edgecolor: Frame edge color
    """
    legend = axes_obj.legend(
        loc=loc,
        frameon=frameon,
        framealpha=framealpha,
        edgecolor=edgecolor,
        fancybox=True,
    )
    if legend:
        legend.get_frame().set_linewidth(0.5)


def _format_date_axis(
    axes_obj: Axes,
    data_index: pd.DatetimeIndex,
    num_ticks: int = 6,
) -> None:
    """Format x-axis for datetime data.

    Args:
        axes_obj: Matplotlib axes object
        data_index: Datetime index from data
        num_ticks: Approximate number of ticks to show
    """
    # Use appropriate date formatting based on data range
    date_range = (data_index.max() - data_index.min()).days

    if date_range <= 1:  # Intraday
        date_format = "%H:%M"
    elif date_range <= 30:  # Up to 1 month
        date_format = "%b %d"
    elif date_range <= 365:  # Up to 1 year
        date_format = "%b %Y"
    else:  # Multi-year
        date_format = "%Y"

    from matplotlib.dates import AutoDateLocator, DateFormatter

    axes_obj.xaxis.set_major_formatter(DateFormatter(date_format))
    locator = AutoDateLocator(
        minticks=max(2, num_ticks // 2),
        maxticks=max(3, num_ticks),
    )
    axes_obj.xaxis.set_major_locator(locator)

    # Rotate labels for better readability
    plt.setp(axes_obj.xaxis.get_majorticklabels(), rotation=45, ha="right")


def _add_watermark(
    axes_obj: Axes,
    text: str = "HaruQuant",
    alpha: float = 0.1,
    fontsize: int = 40,
    color: str = "gray",
) -> None:
    """Add watermark to plot.

    Args:
        axes_obj: Matplotlib axes object
        text: Watermark text
        alpha: Transparency
        fontsize: Font size
        color: Text color
    """
    axes_obj.text(
        0.5,
        0.5,
        text,
        transform=axes_obj.transAxes,
        fontsize=fontsize,
        color=color,
        alpha=alpha,
        ha="center",
        va="center",
        rotation=30,
        zorder=0,
    )


# =============================================================================
# BACKEND MANAGEMENT
# =============================================================================


def _get_backend() -> str:
    """Detect current environment and return appropriate backend.

    Returns:
        Backend name ('inline', 'Agg', 'TkAgg', etc.)
    """
    # Check if running in Jupyter
    try:
        shell = get_ipython().__class__.__name__  # type: ignore
        if shell == "ZMQInteractiveShell":  # Jupyter notebook
            return "inline"
        if shell == "TerminalInteractiveShell":  # IPython terminal
            return "TkAgg"
    except NameError:
        pass  # Not in IPython/Jupyter

    # Check if DISPLAY is available (Unix)
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        return "Agg"  # No display available, use non-interactive

    # Default to current backend
    return cast(str, matplotlib.get_backend())


@contextlib.contextmanager
def _backend_context(backend: str):
    """Context manager for temporarily switching matplotlib backend.

    Args:
        backend: Backend name to use

    Yields:
        None

    Example:
        with _backend_context('Agg'):
            plt.figure()
            plt.plot([1, 2, 3])
            plt.savefig('plot.png')
    """
    original_backend = matplotlib.get_backend()

    try:
        matplotlib.use(backend, force=True)
        yield
    finally:
        matplotlib.use(original_backend, force=True)


def configure_bokeh(
    plot_width: int = 1200,
    plot_height: int = 600,
    theme: Literal[
        "caliber", "dark_minimal", "light_minimal", "night_sky", "contrast"
    ] = "caliber",
) -> Dict[str, Any]:
    """Configure Bokeh with sensible defaults for interactive plots.

    Args:
        plot_width: Default plot width in pixels
        plot_height: Default plot height in pixels
        theme: Bokeh theme name

    Returns:
        Dictionary of default Bokeh configuration
    """
    if not BOKEH_AVAILABLE:
        logger.warning("Bokeh configuration requested but library unavailable")
        warnings.warn("Bokeh not available", stacklevel=2)
        return {}

    config = {
        "plot_width": plot_width,
        "plot_height": plot_height,
        "tools": "pan,wheel_zoom,box_zoom,reset,save",
        "active_drag": "pan",
        "active_scroll": "wheel_zoom",
        "toolbar_location": "above",
        "sizing_mode": "stretch_width",
    }

    # Apply theme if curdoc is available
    try:
        from bokeh.io import curdoc

        curdoc().theme = theme
        logger.debug("Applied Bokeh theme %s", theme)
    except (RuntimeError, ValueError, AttributeError):
        logger.debug("Unable to apply Bokeh theme %s", theme, exc_info=True)

    return config


def setup_bokeh_output(
    mode: Literal["notebook", "file"] = "notebook",
    filename: Optional[str] = None,
) -> None:
    """Set up Bokeh output mode.

    Args:
        mode: Output mode - 'notebook' for Jupyter, 'file' for HTML
        filename: Output filename (required if mode='file')
    """
    if not BOKEH_AVAILABLE:
        logger.warning("setup_bokeh_output requested but Bokeh unavailable")
        warnings.warn("Bokeh not available", stacklevel=2)
        return

    if mode == "notebook":
        if output_notebook is None:
            raise RuntimeError("Bokeh notebook output is unavailable")
        logger.info("Setting up Bokeh output in notebook mode")
        output_notebook()
        return

    if mode == "file":
        if not filename:
            raise ValueError("filename required for file output mode")
        if output_file is None:
            raise RuntimeError("Bokeh file output is unavailable")
        logger.info("Setting up Bokeh output file at %s", filename)
        output_file(filename)
        return

    raise ValueError(f"Invalid mode: {mode}")


# =============================================================================
# FIGURE MANAGEMENT
# =============================================================================


def _create_figure(
    nrows: int = 1,
    ncols: int = 1,
    figsize: Optional[Tuple[float, float]] = None,
    dpi: Optional[int] = None,
    **subplot_kw,
) -> Tuple[Figure, Union[Axes, np.ndarray]]:
    """Create matplotlib figure with consistent styling.

    Args:
        nrows: Number of subplot rows
        ncols: Number of subplot columns
        figsize: Figure size (width, height) in inches
        dpi: Figure DPI
        **subplot_kw: Additional arguments for subplots

    Returns:
        Tuple of (figure, axes)
    """
    if figsize is None:
        figsize = plt.rcParams["figure.figsize"]
    if dpi is None:
        dpi = plt.rcParams["figure.dpi"]

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, dpi=dpi, **subplot_kw)
    fig.tight_layout(pad=2.0)

    return fig, axes


def _cleanup_figure(fig: Optional[Figure] = None) -> None:
    """Clean up matplotlib figure to free memory.

    Args:
        fig: Figure to close (if None, closes all figures)
    """
    if fig is not None:
        plt.close(fig)
    else:
        plt.close("all")

    gc.collect()


def save_figure(
    fig: Figure,
    filepath: Union[str, Path],
    formats: Optional[List[str]] = None,
    dpi: Optional[int] = None,
    tight_layout: bool = True,
    **savefig_kw,
) -> List[Path]:
    """Save figure to file(s).

    Args:
        fig: Matplotlib figure to save
        filepath: Output file path (without extension if multiple formats)
        formats: List of formats to save (e.g., ['png', 'pdf', 'svg'])
        dpi: DPI for raster formats
        tight_layout: Apply tight layout before saving
        **savefig_kw: Additional arguments for savefig

    Returns:
        List of saved file paths

    Example:
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        save_figure(fig, 'output/plot', formats=['png', 'pdf'])
    """
    filepath = Path(filepath)

    # Default to PNG if no formats specified
    if formats is None:
        formats = ["png"]

    # Create directory if it doesn't exist
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Apply tight layout
    if tight_layout:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message=".*constrained_layout not applied.*"
            )
            warnings.filterwarnings("ignore", message=".*tight_layout not applied.*")
            with contextlib.suppress(Exception):
                fig.tight_layout()

    # Default DPI
    if dpi is None:
        dpi = plt.rcParams["savefig.dpi"]

    saved_files = []

    for fmt in formats:
        # Construct output path
        if filepath.suffix:
            output_path = filepath.with_suffix(f".{fmt}")
        else:
            output_path = Path(f"{filepath}.{fmt}")

        # Save figure
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message=".*constrained_layout not applied.*"
            )
            warnings.filterwarnings("ignore", message=".*tight_layout not applied.*")
            try:
                fig.savefig(
                    output_path,
                    dpi=dpi,
                    bbox_inches="tight",
                    **savefig_kw,
                )
            except Exception as e:
                logger.warning(f"Failed to save figure {output_path}: {e}")

        saved_files.append(output_path)

    return saved_files


# =============================================================================
# INITIALIZATION
# =============================================================================


def initialize_plotting(
    matplotlib_dpi: int = 100,
    matplotlib_figsize: Tuple[float, float] = (12, 8),
    seaborn_context: Literal["paper", "notebook", "talk", "poster"] = "notebook",
    bokeh_width: int = 1200,
    bokeh_height: int = 600,
) -> None:
    """Initialize all plotting libraries with consistent defaults.

    Args:
        matplotlib_dpi: Matplotlib figure DPI
        matplotlib_figsize: Default figure size (width, height) in inches
        seaborn_context: Seaborn context for scaling
        bokeh_width: Default Bokeh plot width in pixels
        bokeh_height: Default Bokeh plot height in pixels
    """
    logger.info("Initializing plotting stack")
    configure_matplotlib(dpi=matplotlib_dpi, figsize=matplotlib_figsize)
    configure_seaborn(context=seaborn_context)

    if BOKEH_AVAILABLE:
        logger.debug(
            "Configuring Bokeh plot_width=%s plot_height=%s",
            bokeh_width,
            bokeh_height,
        )
        configure_bokeh(plot_width=bokeh_width, plot_height=bokeh_height)


# Initialize on import
initialize_plotting()
