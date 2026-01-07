"""Batch plotting and report generation for backtest results.

This module provides functionality for generating multiple plots at once
and creating comprehensive reports with embedded visualizations.
"""

import base64
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

# Conditional bokeh imports
if TYPE_CHECKING:
    from bokeh.models import LayoutDOM
else:
    try:
        from bokeh.models import LayoutDOM
    except ImportError:
        LayoutDOM = Any  # type: ignore

from apps.logger import logger
from apps.plotting.core import BOKEH_AVAILABLE, save_figure
from apps.plotting.distribution import _plot_distribution
from apps.plotting.drawdown import _plot_drawdown
from apps.plotting.heatmap import _plot_monthly_heatmap
from apps.plotting.main import plot
from apps.plotting.performance import _plot_cumulative_returns
from apps.plotting.rolling import _plot_rolling_sharpe
from apps.plotting.summary import (
    _plot_daily_returns,
    _plot_yearly_returns,
    plot_snapshot,
)


def plot_all(  # noqa: C901
    results: Dict[str, Any],
    output_dir: Union[str, Path] = "output/plots",
    prefix: Optional[str] = None,
    formats: Optional[List[str]] = None,
    dpi: int = 150,
    create_manifest: bool = True,
    **kwargs: Any,
) -> Dict[str, List[Path]]:
    """Generate all available plots for backtest results.

    This function creates a comprehensive set of plots and saves them to
    an organized directory structure with consistent naming conventions.

    Args:
        results: Results dictionary from Backtest.run()
        output_dir: Directory to save plots
        prefix: Optional prefix for plot filenames (e.g., strategy name)
        formats: List of formats to save (e.g., ['png', 'pdf', 'svg'])
        dpi: DPI for raster formats
        create_manifest: Whether to create an index/manifest file
        **kwargs: Additional plotting options

    Returns:
        Dictionary mapping plot names to lists of saved file paths

    Example:
        >>> bt = Backtest(data, strategy=MyStrategy, cash=10000)
        >>> results = bt.run()
        >>> saved_plots = plot_all(
        ...     results,
        ...     output_dir='output/my_strategy',
        ...     prefix='MA_Crossover',
        ...     formats=['png', 'pdf']
        ... )
        >>> print(saved_plots.keys())
        dict_keys(['main', 'equity', 'drawdown', 'returns', ...])
    """
    logger.info(f"Starting batch plot generation to {output_dir}")

    # Convert to Path and create directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Default formats
    if formats is None:
        formats = ["png"]

    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d")

    # Build filename prefix
    if prefix:
        file_prefix = f"{prefix}_{timestamp}"
    else:
        file_prefix = timestamp

    # Dictionary to store saved file paths
    saved_plots: Dict[str, List[Path]] = {}

    # Extract data for individual plots
    try:
        broker = results.get("broker")
        # strategy = results.get("strategy")  # Unused variable
        stats = results.get("stats", {})

        # 1. Main comprehensive plot
        logger.debug("Generating main plot")
        fig_main = plot(results, backend="matplotlib", **kwargs)
        saved_plots["main"] = save_figure(
            fig_main,
            output_dir / f"{file_prefix}_main",
            formats=formats,
            dpi=dpi,
        )
        plt.close(fig_main)

        # 2. Equity curve
        if broker and hasattr(broker, "equity"):
            logger.debug("Generating equity curve plot")

            # Convert equity to returns for cumulative returns plot
            equity_series = (
                broker.equity
                if isinstance(broker.equity, pd.Series)
                else pd.Series(broker.equity)
            )
            returns = equity_series.pct_change().dropna()

            # Create figure and plot
            fig_equity, axis = plt.subplots(figsize=kwargs.get("figsize", (12, 6)))
            _plot_cumulative_returns(axis, returns)
            axis.set_title("Equity Curve", fontsize=14, fontweight="bold")

            saved_plots["equity"] = save_figure(
                fig_equity,
                output_dir / f"{file_prefix}_equity",
                formats=formats,
                dpi=dpi,
            )
            plt.close(fig_equity)

        # 3. Drawdown
        if broker and hasattr(broker, "equity"):
            logger.debug("Generating drawdown plot")

            equity_series = (
                broker.equity
                if isinstance(broker.equity, pd.Series)
                else pd.Series(broker.equity)
            )

            # Create figure and plot
            fig_dd, axis = plt.subplots(figsize=kwargs.get("figsize", (12, 5)))
            _plot_drawdown(axis, equity=equity_series)
            axis.set_title("Drawdown", fontsize=14, fontweight="bold")

            saved_plots["drawdown"] = save_figure(
                fig_dd,
                output_dir / f"{file_prefix}_drawdown",
                formats=formats,
                dpi=dpi,
            )
            plt.close(fig_dd)

        # 4. Returns distribution
        if broker and hasattr(broker, "equity"):
            logger.debug("Generating returns distribution plot")

            equity_series = (
                broker.equity
                if isinstance(broker.equity, pd.Series)
                else pd.Series(broker.equity)
            )
            returns = equity_series.pct_change().dropna()

            # Create figure and plot
            fig_dist, axis = plt.subplots(figsize=kwargs.get("figsize", (10, 6)))
            _plot_distribution(axis, returns)
            axis.set_title("Returns Distribution", fontsize=14, fontweight="bold")

            saved_plots["returns_distribution"] = save_figure(
                fig_dist,
                output_dir / f"{file_prefix}_returns_distribution",
                formats=formats,
                dpi=dpi,
            )
            plt.close(fig_dist)

        # 5. Monthly heatmap
        if broker and hasattr(broker, "equity"):
            logger.debug("Generating monthly heatmap")

            equity_series = (
                broker.equity
                if isinstance(broker.equity, pd.Series)
                else pd.Series(broker.equity)
            )
            returns = equity_series.pct_change().dropna()

            # Create figure and plot
            fig_heatmap, axis = plt.subplots(figsize=kwargs.get("figsize", (12, 8)))
            _plot_monthly_heatmap(axis, returns)
            axis.set_title("Monthly Returns Heatmap", fontsize=14, fontweight="bold")

            saved_plots["monthly_heatmap"] = save_figure(
                fig_heatmap,
                output_dir / f"{file_prefix}_monthly_heatmap",
                formats=formats,
                dpi=dpi,
            )
            plt.close(fig_heatmap)

        # 6. Rolling Sharpe ratio
        if broker and hasattr(broker, "equity"):
            logger.debug("Generating rolling Sharpe ratio plot")

            # Convert equity to returns for rolling Sharpe
            equity_series = (
                broker.equity
                if isinstance(broker.equity, pd.Series)
                else pd.Series(broker.equity)
            )
            returns = equity_series.pct_change().dropna()

            # Create figure and plot
            fig_sharpe, axis = plt.subplots(figsize=kwargs.get("figsize", (12, 6)))
            _plot_rolling_sharpe(axis, returns, window=30)
            plt.title("Rolling Sharpe Ratio (30-day)")

            saved_plots["rolling_sharpe"] = save_figure(
                fig_sharpe,
                output_dir / f"{file_prefix}_rolling_sharpe",
                formats=formats,
                dpi=dpi,
            )
            plt.close(fig_sharpe)

        # 7. Yearly returns
        if broker and hasattr(broker, "equity"):
            logger.debug("Generating yearly returns plot")

            equity_series = (
                broker.equity
                if isinstance(broker.equity, pd.Series)
                else pd.Series(broker.equity)
            )
            returns = equity_series.pct_change().dropna()

            # Create figure and plot
            fig_yearly, axis = plt.subplots(figsize=kwargs.get("figsize", (10, 6)))
            _plot_yearly_returns(axis, returns)
            axis.set_title("Yearly Returns", fontsize=14, fontweight="bold")

            saved_plots["yearly_returns"] = save_figure(
                fig_yearly,
                output_dir / f"{file_prefix}_yearly_returns",
                formats=formats,
                dpi=dpi,
            )
            plt.close(fig_yearly)

        # 8. Daily returns
        if broker and hasattr(broker, "equity"):
            logger.debug("Generating daily returns plot")

            equity_series = (
                broker.equity
                if isinstance(broker.equity, pd.Series)
                else pd.Series(broker.equity)
            )
            returns = equity_series.pct_change().dropna()

            # Create figure and plot
            fig_daily, axis = plt.subplots(figsize=kwargs.get("figsize", (10, 6)))
            _plot_daily_returns(axis, returns)
            axis.set_title("Daily Returns", fontsize=14, fontweight="bold")

            saved_plots["daily_returns"] = save_figure(
                fig_daily,
                output_dir / f"{file_prefix}_daily_returns",
                formats=formats,
                dpi=dpi,
            )
            plt.close(fig_daily)

        # 9. Performance snapshot
        if stats and broker and hasattr(broker, "equity"):
            logger.debug("Generating performance snapshot")

            equity_series = (
                broker.equity
                if isinstance(broker.equity, pd.Series)
                else pd.Series(broker.equity)
            )
            returns = equity_series.pct_change().dropna()

            fig_snapshot = plot_snapshot(
                returns=returns,
                metrics=stats,
                title="Performance Snapshot",
                figsize=kwargs.get("figsize"),
                show=False,
            )
            # Don't apply tight_layout for snapshot (has colorbar)
            saved_plots["snapshot"] = save_figure(
                fig_snapshot,
                output_dir / f"{file_prefix}_snapshot",
                formats=formats,
                dpi=dpi,
                tight_layout=False,
            )
            plt.close(fig_snapshot)

        # 10. Trade analysis plots (if trades available)
        # Future enhancement: Add trade analysis plots after updating their interfaces
        # trades = results.get("trades")
        # if trades and len(trades) > 0:
        #     logger.debug("Generating trade analysis plots")
        #     ...

        # Create manifest file
        if create_manifest:
            logger.debug("Creating manifest file")
            _create_manifest(
                output_dir=output_dir,
                saved_plots=saved_plots,
                prefix=file_prefix,
                formats=formats,
            )

        logger.success(
            f"Batch plot generation complete: {len(saved_plots)} plot types, "
            f"{sum(len(paths) for paths in saved_plots.values())} total files"
        )

        return saved_plots

    except Exception as error:
        logger.error(f"Error during batch plot generation: {error}", exc_info=True)
        raise


def _create_manifest(
    output_dir: Path,
    saved_plots: Dict[str, List[Path]],
    prefix: str,
    formats: List[str],
) -> None:
    """Create a manifest file listing all generated plots.

    Args:
        output_dir: Directory containing plots
        saved_plots: Dictionary of plot names to file paths
        prefix: Filename prefix used
        formats: List of formats saved
    """
    plot_entries: Dict[str, Dict[str, List[str]]] = {}

    # Add plot information
    for plot_name, file_paths in saved_plots.items():
        plot_entries[plot_name] = {
            "files": [str(path.name) for path in file_paths],
            "full_paths": [str(path) for path in file_paths],
        }

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "prefix": prefix,
        "formats": formats,
        "output_directory": str(output_dir),
        "plots": plot_entries,
    }

    # Save manifest as JSON
    manifest_path = output_dir / f"{prefix}_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)

    logger.debug(f"Manifest saved to {manifest_path}")


def _embed_figure_html(
    fig: Figure,
    alt_text: str = "Plot",
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> str:
    """Convert matplotlib figure to base64 PNG and embed in HTML img tag.

    Args:
        fig: Matplotlib figure to embed
        alt_text: Alt text for the image tag
        width: Optional width attribute for img tag (in pixels)
        height: Optional height attribute for img tag (in pixels)

    Returns:
        HTML string with embedded image

    Example:
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3])
        >>> html = _embed_figure_html(fig, alt_text="Example plot")
        >>> with open('report.html', 'w') as f:
        ...     f.write(html)
    """
    # Save figure to BytesIO buffer
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
    buffer.seek(0)

    # Encode to base64
    img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    buffer.close()

    # Build img tag
    img_attrs = [f'alt="{alt_text}"']

    if width is not None:
        img_attrs.append(f'width="{width}"')

    if height is not None:
        img_attrs.append(f'height="{height}"')

    # Add responsive styling
    img_attrs.append('style="max-width: 100%; height: auto;"')

    img_tag = f'<img src="data:image/png;base64,{img_base64}" {" ".join(img_attrs)} />'

    return img_tag


def _bokeh_to_html(
    bokeh_figure: "LayoutDOM",
    title: Optional[str] = None,
) -> Dict[str, str]:
    """Convert Bokeh figure to HTML components.

    Args:
        bokeh_figure: Bokeh figure or layout to convert
        title: Optional title for the plot

    Returns:
        Dictionary with 'script' and 'div' keys containing HTML components

    Raises:
        ImportError: If Bokeh is not available

    Example:
        >>> from bokeh.plotting import figure
        >>> p = figure(title="Example")
        >>> p.line([1, 2, 3], [1, 2, 3])
        >>> components = _bokeh_to_html(p, title="My Plot")
        >>> html = f"<html><body>{components['div']}{components['script']}</body></html>"
    """
    if not BOKEH_AVAILABLE:
        raise ImportError("Bokeh is required for this functionality")

    # Import at runtime to avoid issues when Bokeh is not installed
    from bokeh.embed import components as bokeh_components

    # Generate script and div components
    script, div = bokeh_components(bokeh_figure)

    result = {
        "script": script,
        "div": div,
    }

    if title:
        result["title"] = title

    return result


def create_html_report(  # noqa: C901
    results: Dict[str, Any],
    output_path: Union[str, Path] = "output/report.html",
    title: str = "Backtest Report",
    include_plots: Optional[List[str]] = None,
    **kwargs: Any,  # noqa: ARG001  # pylint: disable=unused-argument
) -> Path:
    """Create comprehensive HTML report with embedded plots.

    Args:
        results: Results dictionary from Backtest.run()
        output_path: Path to save HTML report
        title: Report title
        include_plots: List of plot types to include (None = all)
        **kwargs: Additional options for plot generation

    Returns:
        Path to saved HTML report

    Example:
        >>> bt = Backtest(data, strategy=MyStrategy, cash=10000)
        >>> results = bt.run()
        >>> report_path = create_html_report(
        ...     results,
        ...     output_path='output/my_strategy_report.html',
        ...     title='MA Crossover Strategy Report'
        ... )
    """
    logger.info(f"Creating HTML report: {output_path}")

    if kwargs:
        logger.debug(
            "create_html_report received extra options: %s",
            sorted(kwargs.keys()),
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Adapter for BacktestResult object
    # -------------------------------------------------------------------------
    # If results is a BacktestResult object (has comprehensive_summary method),
    # convert it to the expected dictionary format.
    if hasattr(results, "comprehensive_summary"):
        logger.debug("Adapting BacktestResult object to dictionary format")

        # Create a simple broker-like object to hold equity series
        class ResultBroker:
            def __init__(self, equity_series: Any) -> None:
                self.equity = equity_series

        # Get summary stats
        summary_stats = results.comprehensive_summary()

        # Get equity series
        # Try _get_equity_series first (internal method)
        if hasattr(results, "_get_equity_series"):
            equity = results._get_equity_series()
        # Fallback to reconstructing from equity_curve
        elif hasattr(results, "equity_curve"):
            curve = results.equity_curve
            if curve:
                times = [p.timestamp for p in curve]
                values = [p.equity for p in curve]
                equity = pd.Series(values, index=pd.DatetimeIndex(times))
            else:
                equity = pd.Series(dtype=float)
        else:
            equity = pd.Series(dtype=float)

        # Create adapted dictionary
        results_dict: Dict[str, Any] = {
            "stats": summary_stats,
            "broker": ResultBroker(equity),
            "strategy": getattr(results, "strategy_name", "Unknown Strategy"),
        }

        # Use the adapted dictionary
        results = results_dict

    # Extract stats
    stats = results.get("stats", {})

    # Start building HTML
    html_parts = []

    # HTML header
    html_parts.append(
        f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                         'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 5px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .plot-container {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .plot-title {{
            font-size: 1.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        .timestamp {{
            color: #95a5a6;
            font-size: 0.9em;
            text-align: right;
            margin-top: 30px;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
"""
    )

    # Add statistics section
    if stats:
        html_parts.append("<h2>Performance Statistics</h2>")
        html_parts.append('<div class="stats-grid">')

        # Key metrics to display
        key_metrics = [
            ("Total Return", "Total Return [%]", "{:.2f}%"),
            ("Sharpe Ratio", "Sharpe Ratio", "{:.2f}"),
            ("Max Drawdown", "Max. Drawdown [%]", "{:.2f}%"),
            ("Win Rate", "Win Rate [%]", "{:.2f}%"),
            ("Number of Trades", "# Trades", "{:.0f}"),
            ("Avg Trade", "Avg. Trade [%]", "{:.2f}%"),
        ]

        for label, stat_key, fmt in key_metrics:
            value = stats.get(stat_key, "N/A")
            if isinstance(value, (int, float)):
                formatted_value = fmt.format(value)
            else:
                formatted_value = str(value)

            html_parts.append(
                f"""
                <div class="stat-card">
                    <div class="stat-label">{label}</div>
                    <div class="stat-value">{formatted_value}</div>
                </div>
                """
            )

        html_parts.append("</div>")

    # Generate and embed plots
    html_parts.append("<h2>Visualizations</h2>")

    # Define plot types and their generation functions
    plot_specs = []

    if include_plots is None or "main" in include_plots:
        plot_specs.append(("Main Chart", lambda: plot(results, backend="matplotlib")))

    if (
        (include_plots is None or "equity" in include_plots)
        and results.get("broker")
        and hasattr(results["broker"], "equity")
    ):

        def plot_equity():
            equity_series = results["broker"].equity
            if not isinstance(equity_series, pd.Series):
                equity_series = pd.Series(equity_series)
            returns = equity_series.pct_change().dropna()

            fig, axis = plt.subplots(figsize=(12, 6))
            _plot_cumulative_returns(axis, returns)
            axis.set_title("Equity Curve", fontsize=14, fontweight="bold")
            return fig

        plot_specs.append(("Equity Curve", plot_equity))

    if (
        (include_plots is None or "drawdown" in include_plots)
        and results.get("broker")
        and hasattr(results["broker"], "equity")
    ):

        def plot_dd():
            equity_series = results["broker"].equity
            if not isinstance(equity_series, pd.Series):
                equity_series = pd.Series(equity_series)

            fig, axis = plt.subplots(figsize=(12, 5))
            _plot_drawdown(axis, equity=equity_series)
            axis.set_title("Drawdown", fontsize=14, fontweight="bold")
            return fig

        plot_specs.append(("Drawdown", plot_dd))

    if (
        (include_plots is None or "monthly_heatmap" in include_plots)
        and results.get("broker")
        and hasattr(results["broker"], "equity")
    ):

        def plot_heatmap():
            equity_series = results["broker"].equity
            if not isinstance(equity_series, pd.Series):
                equity_series = pd.Series(equity_series)
            returns = equity_series.pct_change().dropna()

            fig, axis = plt.subplots(figsize=(12, 8))
            _plot_monthly_heatmap(axis, returns)
            axis.set_title("Monthly Returns", fontsize=14, fontweight="bold")
            return fig

        plot_specs.append(("Monthly Returns Heatmap", plot_heatmap))

    # Generate and embed each plot
    for plot_title, plot_func in plot_specs:
        try:
            fig = plot_func()
            html_img = _embed_figure_html(fig, alt_text=plot_title)

            html_parts.append(
                f"""
                <div class="plot-container">
                    <div class="plot-title">{plot_title}</div>
                    {html_img}
                </div>
                """
            )

            plt.close(fig)

        except (ValueError, KeyError, AttributeError) as error:
            logger.warning(f"Failed to generate plot '{plot_title}': {error}")

    # HTML footer
    html_parts.append(
        """
    <div class="timestamp">
        Report generated by HaruQuant Trading System
    </div>
</body>
</html>
"""
    )

    # Write HTML file
    html_content = "\n".join(html_parts)
    output_path.write_text(html_content, encoding="utf-8")

    logger.success(f"HTML report saved to {output_path}")

    return output_path
