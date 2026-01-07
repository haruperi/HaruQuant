"""Theme and styling management for backtest visualizations.

This module provides:
- Pre-defined themes (light, dark, grayscale, print)
- Theme application and management
- Custom styling support
- Watermark and logo functionality
- Theme persistence

The module allows users to customize the appearance of all plots
with consistent, professional themes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Tuple, Union, cast

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

from apps.logger import logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from bokeh.themes import Theme as BokehTheme

try:
    from bokeh.themes import Theme as runtime_bokeh_theme

    BOKEH_AVAILABLE = True
except ImportError:
    runtime_bokeh_theme: Optional[Any] = None  # type: ignore[no-redef]
    BOKEH_AVAILABLE = False

# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

ThemeType = Literal["light", "dark", "grayscale", "print", "professional"]

# =============================================================================
# THEME DEFINITIONS
# =============================================================================

# Light theme (default) - bright, colorful, modern
LIGHT_THEME: Dict[str, Any] = {
    "name": "light",
    "description": "Bright, colorful theme for screens",
    "matplotlib": {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#cccccc",
        "axes.labelcolor": "#333333",
        "axes.grid": True,
        "grid.color": "#e0e0e0",
        "grid.linestyle": "-",
        "grid.linewidth": 0.5,
        "grid.alpha": 0.5,
        "text.color": "#333333",
        "xtick.color": "#666666",
        "ytick.color": "#666666",
        "legend.facecolor": "#ffffff",
        "legend.edgecolor": "#cccccc",
        "legend.framealpha": 0.9,
    },
    "colors": {
        "profit": "#2ecc71",  # Green
        "loss": "#e74c3c",  # Red
        "long": "#27ae60",  # Dark green
        "short": "#e67e22",  # Orange
        "neutral": "#95a5a6",  # Gray
        "primary": "#3498db",  # Blue
        "secondary": "#9b59b6",  # Purple
        "accent": "#f1c40f",  # Yellow
        "background": "#ffffff",  # White
        "text": "#333333",  # Dark gray
    },
    "line_colors": [
        "#3498db",  # Blue
        "#2ecc71",  # Green
        "#9b59b6",  # Purple
        "#e67e22",  # Orange
        "#e74c3c",  # Red
        "#f1c40f",  # Yellow
    ],
}

# Dark theme - easy on eyes, modern
DARK_THEME: Dict[str, Any] = {
    "name": "dark",
    "description": "Dark theme for reduced eye strain",
    "matplotlib": {
        "figure.facecolor": "#1e1e1e",
        "axes.facecolor": "#2d2d2d",
        "axes.edgecolor": "#555555",
        "axes.labelcolor": "#e0e0e0",
        "axes.grid": True,
        "grid.color": "#404040",
        "grid.linestyle": "-",
        "grid.linewidth": 0.5,
        "grid.alpha": 0.5,
        "text.color": "#e0e0e0",
        "xtick.color": "#b0b0b0",
        "ytick.color": "#b0b0b0",
        "legend.facecolor": "#2d2d2d",
        "legend.edgecolor": "#555555",
        "legend.framealpha": 0.9,
    },
    "colors": {
        "profit": "#4ade80",  # Lighter green
        "loss": "#f87171",  # Lighter red
        "long": "#22c55e",  # Green
        "short": "#fb923c",  # Orange
        "neutral": "#9ca3af",  # Gray
        "primary": "#60a5fa",  # Light blue
        "secondary": "#c084fc",  # Light purple
        "accent": "#fbbf24",  # Yellow
        "background": "#1e1e1e",  # Dark gray
        "text": "#e0e0e0",  # Light gray
    },
    "line_colors": [
        "#60a5fa",  # Light blue
        "#4ade80",  # Light green
        "#c084fc",  # Light purple
        "#fb923c",  # Light orange
        "#f87171",  # Light red
        "#fbbf24",  # Yellow
    ],
}

# Grayscale theme - for presentations, reports
GRAYSCALE_THEME: Dict[str, Any] = {
    "name": "grayscale",
    "description": "Grayscale theme for professional reports",
    "matplotlib": {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#888888",
        "axes.labelcolor": "#000000",
        "axes.grid": True,
        "grid.color": "#d0d0d0",
        "grid.linestyle": "-",
        "grid.linewidth": 0.5,
        "grid.alpha": 0.5,
        "text.color": "#000000",
        "xtick.color": "#444444",
        "ytick.color": "#444444",
        "legend.facecolor": "#ffffff",
        "legend.edgecolor": "#888888",
        "legend.framealpha": 0.9,
    },
    "colors": {
        "profit": "#2d2d2d",  # Dark gray
        "loss": "#7a7a7a",  # Medium gray
        "long": "#1a1a1a",  # Very dark
        "short": "#5a5a5a",  # Medium dark
        "neutral": "#b0b0b0",  # Light gray
        "primary": "#444444",  # Dark gray
        "secondary": "#6a6a6a",  # Medium gray
        "accent": "#8a8a8a",  # Light medium gray
        "background": "#ffffff",  # White
        "text": "#000000",  # Black
    },
    "line_colors": [
        "#000000",  # Black
        "#333333",  # Very dark gray
        "#555555",  # Dark gray
        "#777777",  # Medium gray
        "#999999",  # Medium light gray
        "#bbbbbb",  # Light gray
    ],
}

# Print theme - optimized for printing
PRINT_THEME: Dict[str, Any] = {
    "name": "print",
    "description": "Optimized for black and white printing",
    "matplotlib": {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#000000",
        "axes.labelcolor": "#000000",
        "axes.grid": True,
        "grid.color": "#c0c0c0",
        "grid.linestyle": ":",
        "grid.linewidth": 0.5,
        "grid.alpha": 0.7,
        "text.color": "#000000",
        "xtick.color": "#000000",
        "ytick.color": "#000000",
        "legend.facecolor": "#ffffff",
        "legend.edgecolor": "#000000",
        "legend.framealpha": 1.0,
        "lines.linewidth": 1.5,
        "lines.markersize": 6,
    },
    "colors": {
        "profit": "#000000",  # Black
        "loss": "#666666",  # Dark gray
        "long": "#000000",  # Black
        "short": "#444444",  # Dark gray
        "neutral": "#888888",  # Medium gray
        "primary": "#000000",  # Black
        "secondary": "#555555",  # Dark gray
        "accent": "#777777",  # Medium gray
        "background": "#ffffff",  # White
        "text": "#000000",  # Black
    },
    "line_colors": [
        "#000000",  # Black (solid)
        "#2d2d2d",  # Very dark
        "#4a4a4a",  # Dark
        "#676767",  # Medium dark
        "#848484",  # Medium
        "#a1a1a1",  # Light
    ],
}

# Professional theme - grayscale variant for reports
PROFESSIONAL_THEME: Dict[str, Any] = {
    **GRAYSCALE_THEME,
    "name": "professional",
    "description": "Professional grayscale theme for reports",
}

# Theme registry
THEMES: Dict[str, Dict[str, Any]] = {
    "light": LIGHT_THEME,
    "dark": DARK_THEME,
    "grayscale": GRAYSCALE_THEME,
    "print": PRINT_THEME,
    "professional": PROFESSIONAL_THEME,
}

# Current active theme
_CURRENT_THEME: Dict[str, Any] = LIGHT_THEME
_THEME_STACK: list = []  # For temporary theme contexts

# =============================================================================
# THEME MANAGEMENT
# =============================================================================


def set_theme(theme: ThemeType = "light", persist: bool = False) -> None:
    """Set the global plotting theme.

    This applies the theme to matplotlib's rcParams, affecting all
    subsequent plots until changed.

    Args:
        theme: Theme name ('light', 'dark', 'grayscale', 'print')
        persist: Whether to save theme preference to config file

    Examples:
        >>> set_theme("dark")
        >>> # All subsequent plots will use dark theme
        >>> set_theme("print", persist=True)
        >>> # Switch to print theme and save preference
    """
    global _CURRENT_THEME  # pylint: disable=global-statement

    if theme not in THEMES:
        raise ValueError(f"Unknown theme: {theme}. Available: {list(THEMES.keys())}")

    _CURRENT_THEME = THEMES[theme]
    logger.info(f"Setting theme: {theme}")

    # Apply matplotlib settings
    mpl_settings = cast(Dict[str, Any], _CURRENT_THEME["matplotlib"])
    for key, value in mpl_settings.items():
        plt.rcParams[key] = value

    # Save preference if requested
    if persist:
        save_theme_preference(theme)
        logger.success(f"Theme '{theme}' saved as default")


def get_current_theme() -> Dict[str, Any]:
    """Get the currently active theme.

    Returns:
        Dictionary containing theme configuration

    Examples:
        >>> theme = get_current_theme()
        >>> print(theme['name'])
        'light'
        >>> colors = theme['colors']
    """
    return _CURRENT_THEME


def reset_theme() -> None:
    """Reset theme to default (light).

    Examples:
        >>> set_theme("dark")
        >>> reset_theme()  # Back to light theme
    """
    set_theme("light")
    logger.info("Theme reset to default (light)")


def list_themes() -> Dict[str, str]:
    """List all available themes with descriptions.

    Returns:
        Dictionary mapping theme names to descriptions

    Examples:
        >>> themes = list_themes()
        >>> for name, desc in themes.items():
        ...     print(f"{name}: {desc}")
    """
    return {name: cast(str, theme["description"]) for name, theme in THEMES.items()}


# =============================================================================
# THEME CONTEXT MANAGER
# =============================================================================


class ThemeContext:  # pylint: disable=too-few-public-methods
    """Context manager for temporary theme changes.

    Allows using a different theme temporarily without changing
    the global theme.

    Examples:
        >>> with ThemeContext("print"):
        ...     plot_equity_curve(data)  # Uses print theme
        >>> # Back to original theme
    """

    def __init__(self, theme: ThemeType):
        """Initialize theme context.

        Args:
            theme: Theme to use temporarily
        """
        self.theme: ThemeType = theme
        self.previous_theme: Optional[Dict[str, Any]] = None

    def __enter__(self) -> "ThemeContext":
        """Enter context - save current theme and apply new one."""
        # pylint: disable=global-variable-not-assigned
        global _THEME_STACK  # noqa: F824

        # Save current theme
        self.previous_theme = _CURRENT_THEME.copy()
        _THEME_STACK.append(self.previous_theme)

        # Apply new theme
        set_theme(self.theme)
        logger.debug(f"Entered theme context: {self.theme}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore previous theme."""
        # pylint: disable=global-variable-not-assigned
        global _CURRENT_THEME, _THEME_STACK  # noqa: F824

        # Restore previous theme
        if _THEME_STACK:
            _CURRENT_THEME = _THEME_STACK.pop()

            # Reapply matplotlib settings
            mpl_settings = cast(Dict[str, Any], _CURRENT_THEME["matplotlib"])
            for key, value in mpl_settings.items():
                plt.rcParams[key] = value

        return False


# =============================================================================
# THEME APPLICATION
# =============================================================================


def apply_theme_to_figure(
    fig: Figure,
    theme: Optional[ThemeType] = None,
) -> None:
    """Apply theme styling to an existing figure.

    This applies theme colors to an already-created figure,
    useful for theming figures created elsewhere.

    Args:
        fig: Matplotlib figure to theme
        theme: Theme to apply (uses current theme if None)

    Examples:
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3])
        >>> apply_theme_to_figure(fig, "dark")
    """
    if theme is not None:
        theme_config = THEMES.get(theme, _CURRENT_THEME)
    else:
        theme_config = _CURRENT_THEME

    # Apply figure background
    fig.patch.set_facecolor(theme_config["matplotlib"]["figure.facecolor"])

    # Apply to all axes
    for axis in fig.axes:
        axis.set_facecolor(theme_config["matplotlib"]["axes.facecolor"])
        axis.spines["top"].set_color(theme_config["matplotlib"]["axes.edgecolor"])
        axis.spines["bottom"].set_color(theme_config["matplotlib"]["axes.edgecolor"])
        axis.spines["left"].set_color(theme_config["matplotlib"]["axes.edgecolor"])
        axis.spines["right"].set_color(theme_config["matplotlib"]["axes.edgecolor"])

        # Update tick colors
        axis.tick_params(
            colors=theme_config["matplotlib"]["xtick.color"],
            which="both",
        )

        # Update labels
        axis.xaxis.label.set_color(theme_config["matplotlib"]["axes.labelcolor"])
        axis.yaxis.label.set_color(theme_config["matplotlib"]["axes.labelcolor"])
        axis.title.set_color(theme_config["matplotlib"]["text.color"])

        # Update grid
        if theme_config["matplotlib"]["axes.grid"]:
            axis.grid(
                True,
                color=theme_config["matplotlib"]["grid.color"],
                linestyle=theme_config["matplotlib"]["grid.linestyle"],
                linewidth=theme_config["matplotlib"]["grid.linewidth"],
                alpha=theme_config["matplotlib"]["grid.alpha"],
            )

    logger.debug(f"Applied theme '{theme_config['name']}' to figure")


# =============================================================================
# CUSTOM STYLING
# =============================================================================


def load_custom_stylesheet(filepath: Union[str, Path]) -> None:
    """Load a custom matplotlib stylesheet.

    Args:
        filepath: Path to matplotlib style file (.mplstyle)

    Examples:
        >>> load_custom_stylesheet("my_custom_style.mplstyle")
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Stylesheet not found: {filepath}")

    plt.style.use(str(filepath))
    logger.success(f"Loaded custom stylesheet: {filepath}")


def create_custom_theme(
    name: str,
    base_theme: ThemeType = "light",
    color_overrides: Optional[Dict[str, str]] = None,
    matplotlib_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a custom theme based on an existing theme.

    Args:
        name: Name for the custom theme
        base_theme: Base theme to start from
        color_overrides: Dictionary of color overrides
        matplotlib_overrides: Dictionary of matplotlib rcParams overrides

    Returns:
        Custom theme dictionary

    Examples:
        >>> custom = create_custom_theme(
        ...     "my_theme",
        ...     base_theme="dark",
        ...     color_overrides={"profit": "#00ff00"},
        ...     matplotlib_overrides={"grid.alpha": 0.3}
        ... )
        >>> THEMES["my_theme"] = custom
        >>> set_theme("my_theme")
    """
    base = THEMES[base_theme].copy()

    custom_theme = {
        "name": name,
        "description": f"Custom theme based on {base_theme}",
        "matplotlib": cast(Dict[str, Any], base["matplotlib"]).copy(),
        "colors": cast(Dict[str, str], base["colors"]).copy(),
        "line_colors": cast(list[str], base["line_colors"]).copy(),
    }

    # Apply color overrides
    if color_overrides:
        colors_dict = cast(Dict[str, str], custom_theme["colors"])
        colors_dict.update(color_overrides)

    # Apply matplotlib overrides
    if matplotlib_overrides:
        mpl_dict = cast(Dict[str, Any], custom_theme["matplotlib"])
        mpl_dict.update(matplotlib_overrides)

    logger.success(f"Created custom theme: {name}")
    return custom_theme


def set_color_palette(colors: list[str]) -> None:
    """Set custom color palette for line plots.

    Args:
        colors: List of color hex codes

    Examples:
        >>> set_color_palette(["#ff0000", "#00ff00", "#0000ff"])
    """
    global _CURRENT_THEME  # noqa: F824  # pylint: disable=global-variable-not-assigned

    _CURRENT_THEME["line_colors"] = colors
    logger.info(f"Updated color palette with {len(colors)} colors")


def set_custom_font(
    family: str = "sans-serif",
    size: int = 10,
    weight: str = "normal",
) -> None:
    """Set custom font for all plots.

    Args:
        family: Font family name
        size: Font size in points
        weight: Font weight ('normal', 'bold', etc.)

    Examples:
        >>> set_custom_font("Arial", 12, "bold")
        >>> set_custom_font("DejaVu Sans Mono", 10)
    """
    plt.rcParams["font.family"] = family
    plt.rcParams["font.size"] = size
    plt.rcParams["font.weight"] = weight

    logger.info(f"Set custom font: {family} ({size}pt, {weight})")


# =============================================================================
# WATERMARKS AND LOGOS
# =============================================================================


def add_watermark(
    fig: Figure,
    text: str,
    position: Tuple[float, float] = (0.5, 0.5),
    alpha: float = 0.1,
    fontsize: int = 60,
    rotation: float = 30,
    color: Optional[str] = None,
) -> None:
    """Add a watermark text to a figure.

    Args:
        fig: Matplotlib figure
        text: Watermark text
        position: Position as (x, y) in figure coordinates (0-1)
        alpha: Transparency (0=invisible, 1=opaque)
        fontsize: Font size
        rotation: Rotation angle in degrees
        color: Text color (uses theme text color if None)

    Examples:
        >>> fig, ax = plt.subplots()
        >>> add_watermark(fig, "CONFIDENTIAL")
        >>> add_watermark(fig, "DRAFT", position=(0.8, 0.2), alpha=0.3)
    """
    if color is None:
        color = _CURRENT_THEME["colors"]["text"]

    fig.text(
        position[0],
        position[1],
        text,
        fontsize=fontsize,
        color=color,
        alpha=alpha,
        ha="center",
        va="center",
        rotation=rotation,
        transform=fig.transFigure,
        zorder=1000,
    )

    logger.debug(f"Added watermark: {text}")


def add_logo(
    fig: Figure,
    logo_path: Union[str, Path],
    position: Tuple[float, float] = (0.95, 0.05),
    zoom: float = 0.1,
    alpha: float = 1.0,
) -> None:
    """Add a logo image to a figure.

    Args:
        fig: Matplotlib figure
        logo_path: Path to logo image file
        position: Position as (x, y) in figure coordinates (0-1)
        zoom: Size scaling factor
        alpha: Transparency (0=invisible, 1=opaque)

    Examples:
        >>> fig, ax = plt.subplots()
        >>> add_logo(fig, "company_logo.png", position=(0.95, 0.05))
    """
    logo_path = Path(logo_path)

    if not logo_path.exists():
        logger.warning(f"Logo file not found: {logo_path}")
        return

    try:
        # Convert to array
        img_array = plt.imread(logo_path)

        # Create image box
        imagebox = OffsetImage(img_array, zoom=zoom, alpha=alpha)

        # Add to figure
        annotation_box = AnnotationBbox(
            imagebox,
            position,
            xycoords="figure fraction",
            frameon=False,
            box_alignment=(1, 0),
        )

        fig.add_artist(annotation_box)
        logger.debug(f"Added logo from: {logo_path}")

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Failed to add logo: {exc}")


# =============================================================================
# THEME PERSISTENCE
# =============================================================================


def get_theme_config_path() -> Path:
    """Get path to theme configuration file.

    Returns:
        Path to theme config JSON file
    """
    # Store in user's config directory
    config_dir = Path.home() / ".haruquant"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "plot_theme.json"


def save_theme_preference(theme: ThemeType) -> None:
    """Save theme preference to config file.

    Args:
        theme: Theme name to save as default

    Examples:
        >>> save_theme_preference("dark")
    """
    config_path = get_theme_config_path()

    config = {"default_theme": theme}

    try:
        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=2)

        logger.success(f"Saved theme preference: {theme}")

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Failed to save theme preference: {exc}")


def load_theme_preference() -> Optional[ThemeType]:
    """Load saved theme preference from config file.

    Returns:
        Saved theme name, or None if not found

    Examples:
        >>> theme = load_theme_preference()
        >>> if theme:
        ...     set_theme(theme)
    """
    config_path = get_theme_config_path()

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = json.load(file)

        theme = config.get("default_theme")

        if theme and theme in THEMES:
            logger.info(f"Loaded theme preference: {theme}")
            return cast(ThemeType, theme)

        logger.warning(f"Invalid theme in config: {theme}")
        return None

    except Exception as exc:  # pylint: disable=broad-except
        logger.error(f"Failed to load theme preference: {exc}")
        return None


def initialize_theme() -> None:
    """Initialize theme system.

    Loads saved preference if available, otherwise uses default.

    Examples:
        >>> initialize_theme()  # Called automatically on import
    """
    saved_theme = load_theme_preference()

    if saved_theme:
        set_theme(saved_theme)
        logger.info(f"Initialized with saved theme: {saved_theme}")
    else:
        set_theme("light")
        logger.info("Initialized with default theme: light")


# =============================================================================
# BOKEH THEME SUPPORT (if available)
# =============================================================================

if BOKEH_AVAILABLE:

    def get_bokeh_theme(theme: ThemeType = "light") -> "BokehTheme":
        """Get Bokeh theme configuration.

        Args:
            theme: Theme name

        Returns:
            Bokeh Theme object

        Examples:
            >>> if BOKEH_AVAILABLE:
            ...     bokeh_theme = get_bokeh_theme("dark")
            ...     curdoc().theme = bokeh_theme
        """
        theme_config = THEMES.get(theme, LIGHT_THEME)

        colors_dict = cast(Dict[str, str], theme_config["colors"])
        mpl_dict = cast(Dict[str, Any], theme_config["matplotlib"])

        bokeh_config = {
            "attrs": {
                "Figure": {
                    "background_fill_color": colors_dict["background"],
                    "border_fill_color": colors_dict["background"],
                    "outline_line_color": mpl_dict["axes.edgecolor"],
                },
                "Grid": {
                    "grid_line_color": mpl_dict["grid.color"],
                    "grid_line_alpha": mpl_dict["grid.alpha"],
                },
                "Axis": {
                    "axis_line_color": mpl_dict["axes.edgecolor"],
                    "major_tick_line_color": mpl_dict["xtick.color"],
                    "major_label_text_color": mpl_dict["xtick.color"],
                    "axis_label_text_color": mpl_dict["axes.labelcolor"],
                },
                "Legend": {
                    "background_fill_color": mpl_dict["legend.facecolor"],
                    "background_fill_alpha": mpl_dict["legend.framealpha"],
                    "border_line_color": mpl_dict["legend.edgecolor"],
                },
                "Title": {
                    "text_color": colors_dict["text"],
                },
            }
        }

        # runtime_bokeh_theme is guaranteed to be not None here (inside BOKEH_AVAILABLE block)
        assert runtime_bokeh_theme is not None
        return runtime_bokeh_theme(json=bokeh_config)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_theme_colors(theme: Optional[ThemeType] = None) -> Dict[str, str]:
    """Get color dictionary for a theme.

    Args:
        theme: Theme name (uses current theme if None)

    Returns:
        Dictionary of theme colors

    Examples:
        >>> colors = get_theme_colors("dark")
        >>> profit_color = colors["profit"]
    """
    if theme is not None:
        return cast(Dict[str, str], THEMES[theme]["colors"])

    return cast(Dict[str, str], _CURRENT_THEME["colors"])


def get_line_colors(
    theme: Optional[ThemeType] = None, num_colors: int = 6
) -> list[str]:
    """Get list of line colors for a theme.

    Args:
        theme: Theme name (uses current theme if None)
        num_colors: Number of colors to return

    Returns:
        List of color hex codes

    Examples:
        >>> colors = get_line_colors("light", num_colors=3)
        >>> # Returns first 3 colors from light theme
    """
    if theme is not None:
        colors = cast(list[str], THEMES[theme]["line_colors"])
    else:
        colors = cast(list[str], _CURRENT_THEME["line_colors"])

    # Cycle through colors if num_colors > available
    if num_colors <= len(colors):
        return colors[:num_colors]

    # Repeat colors to reach num_colors
    full_cycles = num_colors // len(colors)
    remainder = num_colors % len(colors)
    return colors * full_cycles + colors[:remainder]
