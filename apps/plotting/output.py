"""Output and export management for backtest visualizations.

This module provides:
- File output with multiple format support (PNG, PDF, SVG, HTML)
- Browser integration for automatic HTML viewing
- Jupyter notebook integration and auto-detection
- Return object management for further customization
- Filename sanitization and standardized naming conventions

The module handles all output operations for backtest plots, ensuring
consistent and professional results across different environments.
"""

import re
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Union

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

try:
    from bokeh.io import output_notebook
    from bokeh.io import show as bokeh_show
    from bokeh.models import LayoutDOM

    BOKEH_AVAILABLE = True
except ImportError:
    BOKEH_AVAILABLE = False

from apps.logger import logger

# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

FormatType = Literal["png", "pdf", "svg", "html", "jpg", "jpeg"]
BrowserType = Literal["default", "chrome", "firefox", "safari", "edge"]
ReturnType = Union[Figure, "LayoutDOM", None]

# =============================================================================
# JUPYTER DETECTION
# =============================================================================


def is_jupyter_environment() -> bool:
    """Detect if code is running in a Jupyter notebook/lab environment.

    Returns:
        True if running in Jupyter, False otherwise.

    Examples:
        >>> if is_jupyter_environment():
        ...     print("Running in Jupyter")
    """
    try:
        # Check for IPython
        shell: str = get_ipython().__class__.__name__  # type: ignore
        return shell == "ZMQInteractiveShell"
    except NameError:
        return False  # Probably standard Python interpreter


def configure_jupyter_display(
    backend: Literal["matplotlib", "bokeh"] = "matplotlib",
) -> None:
    """Configure display settings for Jupyter environment.

    This function auto-detects Jupyter and applies appropriate display settings
    for matplotlib and Bokeh plots.

    Args:
        backend: Which plotting backend to configure ("matplotlib" or "bokeh")

    Examples:
        >>> configure_jupyter_display("matplotlib")
        >>> configure_jupyter_display("bokeh")
    """
    if not is_jupyter_environment():
        logger.debug("Not in Jupyter environment, skipping configuration")
        return

    try:
        if backend == "matplotlib":
            # Configure matplotlib for inline display
            from IPython import get_ipython

            ipython = get_ipython()
            if ipython:
                ipython.run_line_magic("matplotlib", "inline")
                logger.info("Configured matplotlib for Jupyter inline display")

                # Adjust default figure size for notebooks
                plt.rcParams["figure.figsize"] = (12, 6)
                plt.rcParams["figure.dpi"] = 100

        elif backend == "bokeh":
            if BOKEH_AVAILABLE:
                # Configure Bokeh for notebook output
                output_notebook()
                logger.info("Configured Bokeh for Jupyter notebook output")
            else:
                logger.warning("Bokeh not available, cannot configure for Jupyter")

    except Exception as e:
        logger.error(f"Failed to configure Jupyter display: {e}")


# =============================================================================
# FILENAME UTILITIES
# =============================================================================


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing invalid characters.

    Removes or replaces characters that are invalid in filenames across
    different operating systems.

    Args:
        filename: Original filename to sanitize

    Returns:
        Sanitized filename safe for all platforms

    Examples:
        >>> sanitize_filename("My Strategy: Test #1")
        'My_Strategy_Test_1'
        >>> sanitize_filename("BTCUSDT/EURUSD")
        'BTCUSDT_EURUSD'
    """
    # Remove invalid characters: \ / : * ? " < > |
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", filename)

    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(". ")

    # Replace multiple underscores with single
    sanitized = re.sub(r"_+", "_", sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    return sanitized


def generate_filename(
    strategy_name: str,
    metric: str,
    add_timestamp: bool = False,
    extension: str = "png",
) -> str:
    """Generate a standardized filename for output files.

    Follows the naming convention: strategy_name_metric_date.ext

    Args:
        strategy_name: Name of the trading strategy
        metric: Type of metric/plot (e.g., "equity", "drawdown", "returns")
        add_timestamp: Whether to add timestamp to filename
        extension: File extension (without dot)

    Returns:
        Standardized filename

    Examples:
        >>> generate_filename("MA_Cross", "equity", False, "png")
        'MA_Cross_equity.png'
        >>> generate_filename("MACD Strategy", "returns", True, "pdf")
        'MACD_Strategy_returns_20251202_143025.pdf'
    """
    # Sanitize components
    strategy = sanitize_filename(strategy_name)
    metric_clean = sanitize_filename(metric)

    # Build filename
    parts = [strategy, metric_clean]

    if add_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts.append(timestamp)

    # Join parts and add extension
    filename = "_".join(parts) + f".{extension}"

    return filename


# =============================================================================
# FILE OUTPUT
# =============================================================================


def save_figure(
    fig: Union[Figure, Any],
    filepath: Union[str, Path],
    file_format: Optional[FormatType] = None,
    dpi: int = 300,
    create_dirs: bool = True,
    overwrite: bool = True,
    tight_layout: bool = True,
    **kwargs,
) -> Path:
    """Save a matplotlib or Bokeh figure to file.

    Supports multiple output formats with automatic directory creation,
    DPI settings for raster formats, and optional overwrite confirmation.

    Args:
        fig: Matplotlib Figure or Bokeh LayoutDOM to save
        filepath: Output file path (can include or omit extension)
        file_format: Output format (png, pdf, svg, html, jpg). Auto-detected if None
        dpi: DPI for raster formats (PNG, JPG). Default 300 for publication quality
        create_dirs: Whether to create output directory if it doesn't exist
        overwrite: Whether to overwrite existing files without confirmation
        tight_layout: Whether to apply tight layout before saving
        **kwargs: Additional arguments passed to savefig() or save()

    Returns:
        Path object of saved file

    Raises:
        ValueError: If format is unsupported or figure type is invalid
        FileExistsError: If file exists and overwrite is False

    Examples:
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3], [1, 4, 9])
        >>> save_figure(fig, "output/test.png", dpi=300)
        PosixPath('output/test.png')

        >>> # Save as PDF for publication
        >>> save_figure(fig, "output/test.pdf", format="pdf")
        PosixPath('output/test.pdf')
    """
    # Convert to Path object
    output_path = Path(filepath)

    # Auto-detect format from extension if not specified
    if file_format is None:
        detected_format = output_path.suffix.lower().lstrip(".")
        if not detected_format:
            raise ValueError("No format specified and no extension in filepath")
        file_format = detected_format  # type: ignore[assignment]

    # Validate format
    valid_formats = ["png", "pdf", "svg", "html", "jpg", "jpeg"]
    if file_format not in valid_formats:
        raise ValueError(
            f"Unsupported format: {file_format}. Must be one of {valid_formats}"
        )

    # Ensure extension matches format
    if output_path.suffix.lower().lstrip(".") != file_format:
        output_path = output_path.with_suffix(f".{file_format}")

    # Create output directory if needed
    if create_dirs and output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created output directory: {output_path.parent}")

    # Check if file exists
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"File already exists: {output_path}. Set overwrite=True to replace."
        )

    # Save based on figure type
    if isinstance(fig, Figure):
        _save_matplotlib_figure(
            fig, output_path, file_format, dpi, tight_layout, **kwargs
        )
    elif BOKEH_AVAILABLE and isinstance(fig, LayoutDOM):
        _save_bokeh_figure(fig, output_path, file_format, **kwargs)
    else:
        raise ValueError(
            f"Unsupported figure type: {type(fig)}. "
            "Must be matplotlib Figure or Bokeh LayoutDOM"
        )

    return output_path


def _save_matplotlib_figure(
    fig: Figure,
    output_path: Path,
    file_format: str,
    dpi: int,
    tight_layout: bool,
    **kwargs: Any,
) -> None:
    """Save a Matplotlib figure."""
    logger.info(f"Saving matplotlib figure to {output_path}")

    # Apply tight layout
    if tight_layout:
        try:
            fig.tight_layout()
        except Exception as e:
            logger.warning(f"Failed to apply tight layout: {e}")

    # Prepare save kwargs
    save_kwargs = {
        "dpi": float(dpi) if file_format in ["png", "jpg", "jpeg"] else None,
        "bbox_inches": "tight",
        "format": file_format,
    }
    save_kwargs.update(kwargs)

    # Remove None values
    clean_save_kwargs = {k: v for k, v in save_kwargs.items() if v is not None}

    # Save figure
    fig.savefig(output_path, **clean_save_kwargs)
    logger.success(f"Saved figure to {output_path}")


def _save_bokeh_figure(
    fig: Any,
    output_path: Path,
    file_format: str,
    **kwargs: Any,
) -> None:
    """Save a Bokeh figure."""
    logger.info(f"Saving Bokeh figure to {output_path}")

    if file_format == "html":
        from bokeh.io import output_file, save

        # Configure output
        output_file(str(output_path), **kwargs)

        # Save figure
        save(fig)
        logger.success(f"Saved Bokeh figure to {output_path}")
    else:
        # Bokeh export to other formats requires additional dependencies
        logger.warning(
            f"Bokeh export to {file_format} requires selenium and additional drivers"
        )
        raise ValueError(f"Bokeh only supports HTML export. Got format: {file_format}")


def save_multiple_formats(
    fig: Union[Figure, Any],
    base_path: Union[str, Path],
    formats: list[FormatType],
    dpi: int = 300,
    **kwargs,
) -> Dict[str, Path]:
    """Save figure in multiple formats at once.

    Convenience function to export a figure to multiple file formats
    with a single call.

    Args:
        fig: Matplotlib Figure or Bokeh LayoutDOM to save
        base_path: Base output path (without extension)
        formats: List of formats to export to
        dpi: DPI for raster formats
        **kwargs: Additional arguments passed to save_figure()

    Returns:
        Dictionary mapping format to output path

    Examples:
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3])
        >>> paths = save_multiple_formats(fig, "output/chart", ["png", "pdf", "svg"])
        >>> paths
        {'png': PosixPath('output/chart.png'),
         'pdf': PosixPath('output/chart.pdf'),
         'svg': PosixPath('output/chart.svg')}
    """
    base_path = Path(base_path)
    saved_paths: Dict[str, Path] = {}

    for fmt in formats:
        output_path = base_path.with_suffix(f".{fmt}")
        try:
            saved_path = save_figure(
                fig, output_path, file_format=fmt, dpi=dpi, **kwargs
            )
            saved_paths[fmt] = saved_path
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"Failed to save {fmt} format: {exc}")

    logger.success(f"Saved figure in {len(saved_paths)} formats")
    return saved_paths


# =============================================================================
# BROWSER INTEGRATION
# =============================================================================


def open_in_browser(
    filepath: Union[str, Path],
    browser: BrowserType = "default",
    new: int = 2,
) -> bool:
    """Open an HTML file in the default or specified browser.

    Uses the webbrowser module to automatically open HTML visualization files.
    Supports file:// protocol for local files.

    Args:
        filepath: Path to HTML file to open
        browser: Browser to use ("default", "chrome", "firefox", "safari", "edge")
        new: How to open (0=same window, 1=new window, 2=new tab)

    Returns:
        True if successful, False otherwise

    Examples:
        >>> # Open in default browser
        >>> open_in_browser("output/chart.html")
        True

        >>> # Open in Chrome in new tab
        >>> open_in_browser("output/chart.html", browser="chrome", new=2)
        True
    """
    filepath = Path(filepath)

    # Check if file exists
    if not filepath.exists():
        logger.error(f"File not found: {filepath}")
        return False

    # Check if it's an HTML file
    if filepath.suffix.lower() not in [".html", ".htm"]:
        logger.warning(f"File is not HTML: {filepath}")
        return False

    # Convert to absolute path for file:// protocol
    abs_path = filepath.resolve()
    file_url = abs_path.as_uri()

    logger.info(f"Opening {filepath} in browser")

    try:
        browser_controller = _get_browser_controller(browser)

        # Open in browser
        if browser_controller:
            browser_controller.open(file_url, new=new)
            logger.success(f"Opened {filepath} in browser")
            return True
        else:
            logger.error("No browser controller available")
            return False

    except Exception as e:
        logger.error(f"Failed to open browser: {e}")
        return False


def _get_browser_controller(browser: str) -> Optional[webbrowser.BaseBrowser]:
    """Get the requested browser controller or default."""
    if browser == "default":
        return webbrowser.get()

    # Try to get specific browser
    browser_names = {
        "chrome": ["google-chrome", "chrome", "chromium"],
        "firefox": ["firefox"],
        "safari": ["safari"],
        "edge": ["microsoft-edge", "edge"],
    }

    for name in browser_names.get(browser, []):
        try:
            return webbrowser.get(name)
        except webbrowser.Error:
            continue

    logger.warning(f"Could not find {browser} browser, using default")
    try:
        return webbrowser.get()
    except webbrowser.Error:
        return None


def save_and_open(
    fig: Union[Figure, Any],
    filepath: Union[str, Path],
    browser: BrowserType = "default",
    **kwargs,
) -> Optional[Path]:
    """Save figure as HTML and automatically open in browser.

    Convenience function combining save and open operations for
    HTML visualization files.

    Args:
        fig: Matplotlib or Bokeh figure to save
        filepath: Output HTML file path
        browser: Browser to use for opening
        **kwargs: Additional arguments passed to save_figure()

    Returns:
        Path to saved file if successful, None otherwise

    Examples:
        >>> from apps.plotting.plotly_convert import to_plotly
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3])
        >>> plotly_fig = to_plotly(fig)
        >>> save_and_open(plotly_fig, "output/interactive.html")
        PosixPath('output/interactive.html')
    """
    try:
        # Save figure
        output_path = save_figure(fig, filepath, format="html", **kwargs)

        # Open in browser
        open_in_browser(output_path, browser=browser)

        return output_path

    except Exception as e:
        logger.error(f"Failed to save and open: {e}")
        return None


# =============================================================================
# RETURN OBJECT MANAGEMENT
# =============================================================================


def should_return_figure(
    show: bool = True,
    save: bool = False,
    return_fig: bool = False,
) -> bool:
    """Determine whether to return figure object based on parameters.

    This function implements the logic for deciding when to return
    plot objects for further customization.

    Args:
        show: Whether plot will be shown
        save: Whether plot will be saved
        return_fig: Explicit request to return figure

    Returns:
        True if figure should be returned, False otherwise

    Examples:
        >>> # Return for further customization
        >>> should_return_figure(show=False, save=False, return_fig=True)
        True

        >>> # Don't return if showing/saving
        >>> should_return_figure(show=True, save=True, return_fig=False)
        False
    """
    # Explicit request always honored
    if return_fig:
        return True

    # If not showing or saving, return by default
    if not show and not save:
        return True

    return False


def handle_plot_output(
    fig: Union[Figure, Any],
    show: bool = True,
    save: bool = False,
    filepath: Optional[Union[str, Path]] = None,
    return_fig: bool = False,
    open_browser: bool = False,
    **save_kwargs,
) -> Optional[ReturnType]:
    """Handle all plot output operations (show, save, return).

    This is the main orchestration function for plot output, handling
    display, file saving, and return value based on parameters.

    Args:
        fig: Matplotlib Figure or Bokeh LayoutDOM
        show: Whether to display the plot
        save: Whether to save the plot to file
        filepath: Output file path (required if save=True)
        return_fig: Whether to return the figure object
        open_browser: Whether to open HTML files in browser
        **save_kwargs: Additional arguments passed to save_figure()

    Returns:
        Figure object if should_return_figure() is True, else None

    Raises:
        ValueError: If save=True but filepath is None

    Examples:
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3])
        >>> handle_plot_output(fig, show=True, save=False)
        >>> # Shows plot, doesn't save, returns None

        >>> handle_plot_output(fig, save=True, filepath="output/test.png")
        >>> # Saves plot, returns None

        >>> result = handle_plot_output(fig, show=False, return_fig=True)
        >>> # Doesn't show, returns figure for customization
    """
    # Save if requested
    if save:
        if filepath is None:
            raise ValueError("filepath must be provided when save=True")

        saved_path = save_figure(fig, filepath, **save_kwargs)

        # Open in browser if HTML and requested
        if open_browser and saved_path.suffix.lower() in [".html", ".htm"]:
            open_in_browser(saved_path)

    # Show if requested
    if show:
        if isinstance(fig, Figure):
            plt.show()
        elif BOKEH_AVAILABLE and isinstance(fig, LayoutDOM):
            bokeh_show(fig)
        else:
            logger.warning(f"Don't know how to show figure of type {type(fig)}")

    # Determine if should return
    if should_return_figure(show, save, return_fig):
        return fig

    return None


# =============================================================================
# CONFIGURATION HELPERS
# =============================================================================


def get_output_config() -> Dict[str, Any]:
    """Get current output configuration settings.

    Returns:
        Dictionary with current output settings

    Examples:
        >>> config = get_output_config()
        >>> config['jupyter_detected']
        False
        >>> config['bokeh_available']
        True
    """
    config = {
        "jupyter_detected": is_jupyter_environment(),
        "bokeh_available": BOKEH_AVAILABLE,
        "matplotlib_backend": plt.get_backend(),
        "default_dpi": plt.rcParams.get("figure.dpi", 100),
        "default_figsize": plt.rcParams.get("figure.figsize", (6.4, 4.8)),
    }

    return config


def print_output_config() -> None:
    """Print current output configuration to console.

    Useful for debugging display issues.

    Examples:
        >>> print_output_config()
        Output Configuration:
        =====================
        Jupyter Environment: False
        Bokeh Available: True
        Matplotlib Backend: Qt5Agg
        Default DPI: 100
        Default Figure Size: (6.4, 4.8)
    """
    config = get_output_config()

    print("\nOutput Configuration:")
    print("=" * 50)
    print(f"Jupyter Environment: {config['jupyter_detected']}")
    print(f"Bokeh Available: {config['bokeh_available']}")
    print(f"Matplotlib Backend: {config['matplotlib_backend']}")
    print(f"Default DPI: {config['default_dpi']}")
    print(f"Default Figure Size: {config['default_figsize']}")
    print("=" * 50)
