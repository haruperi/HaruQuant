"""Plotting module for backtest results visualization.

This package provides comprehensive plotting capabilities for backtesting results,
including:
- Interactive charts with Bokeh
- Static charts with Matplotlib
- Performance metrics visualization
- Trade analysis plots
- Optimization heatmaps

The module is organized as:
- core: Base configuration and utilities
- charts: Individual chart components (to be implemented)
- layouts: Multi-panel layouts (to be implemented)
"""

from apps.plotting.batch import (
    _bokeh_to_html,
    _embed_figure_html,
    create_html_report,
    plot_all,
)
from apps.plotting.core import (
    BOKEH_AVAILABLE,
    DEFAULT_COLOR_SEQUENCE,
    FLATUI_COLORS,
    GRAYSCALE_COLORS,
    TRADING_COLORS,
    CompactNumberFormatter,
    CurrencyFormatter,
    PercentageFormatter,
    _add_watermark,
    _backend_context,
    _cleanup_figure,
    _create_figure,
    _format_axis,
    _format_date_axis,
    _format_grid,
    _format_legend,
    _get_backend,
    _get_colors,
    configure_bokeh,
    configure_matplotlib,
    configure_seaborn,
    initialize_plotting,
    save_figure,
    setup_bokeh_output,
)
from apps.plotting.distribution import _plot_distribution, _plot_histogram, _plot_qq
from apps.plotting.heatmap import (
    _plot_correlation_heatmap,
    _plot_monthly_heatmap,
    plot_heatmaps,
)
from apps.plotting.interactive import (
    add_drawdown_hover,
    add_equity_hover,
    add_indicator_hover,
    add_linked_crosshair,
    add_ohlc_hover,
    add_pan_zoom_tools,
    add_range_selector,
    add_trade_hover,
    apply_standard_tools,
    configure_interactive_legend,
    create_legend_toggles,
    create_linked_chart_layout,
    create_range_selector_layout,
    customize_hover_css,
    sync_zoom_across_figures,
)
from apps.plotting.main import plot
from apps.plotting.output import (
    configure_jupyter_display,
    generate_filename,
    get_output_config,
    handle_plot_output,
    is_jupyter_environment,
    open_in_browser,
    print_output_config,
    sanitize_filename,
    save_and_open,
    save_multiple_formats,
    should_return_figure,
)
from apps.plotting.plotly_convert import (
    PLOTLY_AVAILABLE,
    convert_and_save,
    create_plotly_candlestick,
    create_plotly_time_series,
    save_plotly_html,
    to_plotly,
)
from apps.plotting.summary import (
    _plot_daily_returns,
    _plot_yearly_returns,
    plot_snapshot,
)
from apps.plotting.themes import (
    THEMES,
    ThemeContext,
    add_logo,
    add_watermark,
    apply_theme_to_figure,
    create_custom_theme,
    get_current_theme,
    get_line_colors,
    get_theme_colors,
    initialize_theme,
    list_themes,
    load_theme_preference,
    reset_theme,
    save_theme_preference,
    set_color_palette,
    set_custom_font,
    set_theme,
)
from apps.plotting.trades import (
    _plot_trade_durations,
    _plot_trade_scatter,
    _plot_trade_sizes,
    _plot_win_loss_streaks,
)
from apps.plotting.wrappers import (
    plot_daily_returns,
    plot_distribution,
    plot_drawdown,
    plot_monthly_heatmap,
    plot_returns,
    plot_rolling_sharpe,
    plot_yearly_returns,
)

__all__ = [
    # Main plotting function
    "plot",
    # Batch plotting and reports
    "plot_all",
    "create_html_report",
    "_embed_figure_html",
    "_bokeh_to_html",
    # Plotly conversion
    "to_plotly",
    "save_plotly_html",
    "convert_and_save",
    "create_plotly_time_series",
    "create_plotly_candlestick",
    "PLOTLY_AVAILABLE",
    # Output and export management
    "save_multiple_formats",
    "save_and_open",
    "open_in_browser",
    "handle_plot_output",
    "should_return_figure",
    "generate_filename",
    "sanitize_filename",
    "is_jupyter_environment",
    "configure_jupyter_display",
    "get_output_config",
    "print_output_config",
    # Theme and styling
    "set_theme",
    "get_current_theme",
    "reset_theme",
    "list_themes",
    "ThemeContext",
    "apply_theme_to_figure",
    "create_custom_theme",
    "set_color_palette",
    "set_custom_font",
    "add_watermark",
    "add_logo",
    "get_theme_colors",
    "get_line_colors",
    "initialize_theme",
    "save_theme_preference",
    "load_theme_preference",
    "THEMES",
    # Summary functions
    "plot_snapshot",
    "_plot_yearly_returns",
    "_plot_daily_returns",
    # Heatmap functions
    "_plot_monthly_heatmap",
    "plot_heatmaps",
    "_plot_correlation_heatmap",
    # Distribution functions
    "_plot_histogram",
    "_plot_qq",
    "_plot_distribution",
    # Trade analysis functions
    "_plot_trade_durations",
    "_plot_trade_sizes",
    "_plot_trade_scatter",
    "_plot_win_loss_streaks",
    # Convenience wrappers
    "plot_returns",
    "plot_drawdown",
    "plot_monthly_heatmap",
    "plot_rolling_sharpe",
    "plot_yearly_returns",
    "plot_daily_returns",
    "plot_distribution",
    # Interactive tools (Bokeh)
    "add_linked_crosshair",
    "add_pan_zoom_tools",
    "sync_zoom_across_figures",
    "add_ohlc_hover",
    "add_equity_hover",
    "add_indicator_hover",
    "add_trade_hover",
    "add_drawdown_hover",
    "customize_hover_css",
    "configure_interactive_legend",
    "create_legend_toggles",
    "add_range_selector",
    "create_range_selector_layout",
    "apply_standard_tools",
    "create_linked_chart_layout",
    # Configuration functions
    "initialize_plotting",
    "configure_matplotlib",
    "configure_seaborn",
    "configure_bokeh",
    "setup_bokeh_output",
    # Color schemes
    "FLATUI_COLORS",
    "GRAYSCALE_COLORS",
    "TRADING_COLORS",
    "DEFAULT_COLOR_SEQUENCE",
    "_get_colors",
    # Formatters
    "PercentageFormatter",
    "CurrencyFormatter",
    "CompactNumberFormatter",
    # Formatting utilities
    "_format_axis",
    "_format_grid",
    "_format_legend",
    "_format_date_axis",
    "_add_watermark",
    # Backend management
    "_get_backend",
    "_backend_context",
    # Figure management
    "_create_figure",
    "_cleanup_figure",
    "save_figure",
    # Constants
    "BOKEH_AVAILABLE",
]

# Package metadata
__version__ = "1.0.0"
__author__ = "HaruQuant Team"
