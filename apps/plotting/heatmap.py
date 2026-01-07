"""Heatmap plotting functions for backtest visualization.

This module provides heatmap visualizations for:
- Monthly returns calendar (QuantStats-style)
- Optimization parameter analysis
- Correlation matrices

Features:
- Monthly returns heatmap with YTD column
- 2D parameter optimization heatmaps
- Correlation heatmaps for multiple strategies
- Support for both color and grayscale modes
- Customizable colormaps and annotations
"""

from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from apps.plotting.core import BOKEH_AVAILABLE, _format_axis


def _plot_monthly_heatmap(
    ax: Axes,
    returns: pd.Series,
    color_mode: Literal["color", "grayscale"] = "color",
    cmap: Optional[str] = None,
    annot_decimals: int = 1,
    show_ytd: bool = True,
    **kwargs: Any,
) -> None:
    """Plot monthly returns heatmap (QuantStats-style).

    Creates a calendar-style heatmap with years as rows and months as columns,
    showing monthly returns with color-coded cells.

    Args:
        ax: Matplotlib axes to plot on
        returns: Returns series (daily or any frequency)
                Index should be datetime
        color_mode: 'color' for full colors, 'grayscale' for monochrome
        cmap: Colormap name (default: 'RdYlGn' for color, 'Greys' for grayscale)
        annot_decimals: Number of decimal places for annotations
        show_ytd: Include YTD (year-to-date) column
        **kwargs: Additional arguments for seaborn heatmap

    Returns:
        None

    Example:
        >>> fig, ax = plt.subplots(figsize=(12, 6))
        >>> _plot_monthly_heatmap(ax, returns)
    """
    # Convert returns to monthly
    if not isinstance(returns.index, pd.DatetimeIndex):
        raise ValueError("Returns index must be DatetimeIndex")

    # Resample to monthly returns (compound returns within each month)
    monthly_returns = (1 + returns).resample("ME").prod() - 1

    # Ensure we have a DatetimeIndex after resampling
    dt_index = pd.DatetimeIndex(monthly_returns.index)

    # Create pivot table: years as rows, months as columns
    monthly_table = pd.DataFrame(
        {
            "Year": dt_index.year,
            "Month": dt_index.month,
            "Return": monthly_returns.values,
        }
    )

    pivot_table = monthly_table.pivot(index="Year", columns="Month", values="Return")

    # Add YTD column if requested
    if show_ytd:
        # Calculate YTD returns for each year
        ytd_returns = []
        for year in pivot_table.index:
            year_returns = monthly_returns[dt_index.year == year]
            ytd = (1 + year_returns).prod() - 1
            ytd_returns.append(ytd)
        pivot_table["YTD"] = ytd_returns

    # Convert to percentage
    pivot_table = pivot_table * 100

    # Rename columns to month names
    month_names = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    column_mapping: Dict[Union[int, str], str] = {
        i + 1: month_names[i] for i in range(12)
    }
    if show_ytd:
        column_mapping["YTD"] = "YTD"
    pivot_table = pivot_table.rename(columns=column_mapping)

    # Select colormap
    if cmap is None:
        if color_mode == "grayscale":
            cmap = "Greys"
        else:
            cmap = "RdYlGn"

    # Create heatmap
    # Center colormap at 0 for diverging effect
    vmax = max(abs(pivot_table.min().min()), abs(pivot_table.max().max()))
    vmin = -vmax

    # Format annotations
    annot_data = pivot_table.map(
        lambda x: f"{x:.{annot_decimals}f}" if pd.notna(x) else ""
    )

    sns.heatmap(
        pivot_table,
        annot=annot_data,
        fmt="",
        cmap=cmap,
        center=0,
        vmin=vmin,
        vmax=vmax,
        cbar_kws={"label": "Return (%)"},
        linewidths=0.5,
        linecolor="white",
        ax=ax,
        **kwargs,
    )

    # Format axes
    _format_axis(ax, title="Monthly Returns Heatmap", xlabel="", ylabel="Year")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)


def plot_heatmaps(
    optimization_results: pd.DataFrame,
    metric_column: str = "sharpe_ratio",
    param_columns: Optional[List[str]] = None,
    backend: Literal["matplotlib", "bokeh"] = "matplotlib",
    color_mode: Literal["color", "grayscale"] = "color",
    cmap: Optional[str] = None,
    figsize: Tuple[float, float] = (12, 10),
    save_path: Optional[str] = None,
    open_browser: bool = False,
    show_marginals: bool = False,
    **kwargs: Any,
) -> Optional[Union[Figure, Any]]:
    """Plot optimization heatmaps for parameter analysis.

    Creates 2D heatmaps for each pair of optimization parameters,
    showing how the target metric varies across parameter combinations.

    Args:
        optimization_results: DataFrame with optimization results
                            Must contain parameter columns and metric column
        metric_column: Name of column containing optimization metric
        param_columns: List of parameter column names to analyze
                      If None, auto-detect numeric columns (excluding metric)
        backend: 'matplotlib' for static plots, 'bokeh' for interactive
        color_mode: 'color' for full colors, 'grayscale' for monochrome
        cmap: Colormap name (default: 'viridis' for color, 'Greys' for grayscale)
        figsize: Figure size (width, height) in inches
        save_path: Path to save figure (extension determines format)
        open_browser: Open HTML file in browser (Bokeh only)
        show_marginals: Show 1D marginal distributions on plot margins
                       (matplotlib only, shows how each parameter affects metric)
        **kwargs: Additional arguments for plotting functions

    Returns:
        Figure object (matplotlib) or Bokeh layout (bokeh), or None if saved

    Example:
        >>> results = pd.DataFrame({
        ...     'param1': [1, 2, 3, 1, 2, 3],
        ...     'param2': [10, 10, 10, 20, 20, 20],
        ...     'sharpe_ratio': [0.5, 1.2, 0.8, 1.5, 2.0, 1.3]
        ... })
        >>> plot_heatmaps(results, metric_column='sharpe_ratio', show_marginals=True)
    """
    # Validate inputs
    if metric_column not in optimization_results.columns:
        raise ValueError(f"Metric column '{metric_column}' not found in results")

    # Auto-detect parameter columns if not provided
    if param_columns is None:
        # Get all numeric columns except the metric
        numeric_cols = optimization_results.select_dtypes(
            include=[np.number]
        ).columns.tolist()
        param_columns = [col for col in numeric_cols if col != metric_column]

    if len(param_columns) < 2:
        raise ValueError("Need at least 2 parameter columns for heatmap")

    # Select colormap
    if cmap is None:
        if color_mode == "grayscale":
            cmap = "Greys"
        else:
            cmap = "viridis"

    if backend == "matplotlib":
        return _plot_optimization_heatmaps_matplotlib(
            optimization_results,
            metric_column,
            param_columns,
            cmap,
            figsize,
            save_path,
            show_marginals,
            **kwargs,
        )
    elif backend == "bokeh":
        if not BOKEH_AVAILABLE:
            raise ImportError("Bokeh not available. Install with: pip install bokeh")
        return _plot_optimization_heatmaps_bokeh(
            optimization_results,
            metric_column,
            param_columns,
            cmap,
            save_path,
            open_browser,
            **kwargs,
        )
    else:
        raise ValueError(f"Invalid backend: {backend}")


def _plot_optimization_heatmaps_matplotlib(
    optimization_results: pd.DataFrame,
    metric_column: str,
    param_columns: List[str],
    cmap: str,
    figsize: Tuple[float, float],
    save_path: Optional[str],
    show_marginals: bool = False,
    **kwargs: Any,
) -> Optional[Figure]:
    """Plot optimization heatmaps using matplotlib.

    Internal function for matplotlib backend with optional marginal distributions.
    """
    from matplotlib.gridspec import GridSpec

    # Calculate number of parameter pairs
    n_params = len(param_columns)
    n_pairs = (n_params * (n_params - 1)) // 2

    if n_pairs == 0:
        raise ValueError("Need at least 2 parameters for pairwise heatmaps")

    if not show_marginals:
        # Original simple grid layout without marginals
        ncols = min(3, n_pairs)
        nrows = (n_pairs + ncols - 1) // ncols

        fig, axes = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False)
        axes = axes.flatten()

        # Create heatmap for each parameter pair
        pair_idx = 0
        for i in range(n_params):
            for j in range(i + 1, n_params):
                param1 = param_columns[i]
                param2 = param_columns[j]

                # Create pivot table
                pivot = optimization_results.pivot_table(
                    values=metric_column, index=param2, columns=param1, aggfunc="mean"
                )

                # Plot heatmap
                ax = axes[pair_idx]
                sns.heatmap(
                    pivot,
                    cmap=cmap,
                    annot=True,
                    fmt=".2f",
                    cbar_kws={"label": metric_column},
                    linewidths=0.5,
                    ax=ax,
                    **kwargs,
                )

                _format_axis(
                    ax,
                    title=f"{metric_column} vs {param1} & {param2}",
                    xlabel=param1,
                    ylabel=param2,
                )

                pair_idx += 1

        # Hide unused subplots
        for idx in range(pair_idx, len(axes)):
            axes[idx].set_visible(False)

        fig.tight_layout()

    else:
        # Enhanced layout with marginal distributions
        # Each heatmap gets marginal plots on top and right
        ncols = min(2, n_pairs)  # Reduce columns when showing marginals
        nrows = (n_pairs + ncols - 1) // ncols

        # Adjust figure size for marginals
        fig = plt.figure(figsize=(figsize[0], figsize[1] * 1.2))

        pair_idx = 0
        for i in range(n_params):
            for j in range(i + 1, n_params):
                param1 = param_columns[i]
                param2 = param_columns[j]

                # Calculate subplot position
                row = pair_idx // ncols
                col = pair_idx % ncols

                # Create gridspec for this subplot with marginals
                # Layout: [top marginal] [main heatmap] [right marginal]
                gs = GridSpec(
                    nrows * 4,
                    ncols * 4,
                    figure=fig,
                    hspace=0.4,
                    wspace=0.4,
                )

                # Define subplot regions
                main_row_start = row * 4 + 1
                main_row_end = row * 4 + 4
                main_col_start = col * 4
                main_col_end = col * 4 + 3

                top_row = row * 4
                right_col = col * 4 + 3

                # Create axes
                ax_main = fig.add_subplot(
                    gs[main_row_start:main_row_end, main_col_start:main_col_end]
                )
                ax_top = fig.add_subplot(
                    gs[top_row, main_col_start:main_col_end], sharex=ax_main
                )
                ax_right = fig.add_subplot(
                    gs[main_row_start:main_row_end, right_col], sharey=ax_main
                )

                # Create pivot table
                pivot = optimization_results.pivot_table(
                    values=metric_column, index=param2, columns=param1, aggfunc="mean"
                )

                # Plot main heatmap
                sns.heatmap(
                    pivot,
                    cmap=cmap,
                    annot=True,
                    fmt=".2f",
                    cbar_kws={"label": metric_column},
                    linewidths=0.5,
                    ax=ax_main,
                    **kwargs,
                )

                ax_main.set_title(f"{metric_column} vs {param1} & {param2}")
                ax_main.set_xlabel(param1)
                ax_main.set_ylabel(param2)

                # Calculate marginal distributions (average across other parameter)
                # Top marginal: average metric for each param1 value
                marginal_param1 = optimization_results.groupby(param1)[
                    metric_column
                ].mean()

                # Right marginal: average metric for each param2 value
                marginal_param2 = optimization_results.groupby(param2)[
                    metric_column
                ].mean()

                # Plot top marginal (param1 effect)
                ax_top.plot(
                    marginal_param1.index,
                    marginal_param1.values,
                    marker="o",
                    linewidth=2,
                    markersize=6,
                    color="#3498db",
                )
                ax_top.fill_between(
                    marginal_param1.index,
                    marginal_param1.values,
                    alpha=0.3,
                    color="#3498db",
                )
                ax_top.set_ylabel(f"Avg {metric_column}", fontsize=8)
                ax_top.tick_params(labelbottom=False, labelsize=8)
                ax_top.grid(True, alpha=0.3)
                ax_top.spines["top"].set_visible(False)
                ax_top.spines["right"].set_visible(False)

                # Plot right marginal (param2 effect)
                ax_right.plot(
                    marginal_param2.values,
                    marginal_param2.index,
                    marker="o",
                    linewidth=2,
                    markersize=6,
                    color="#e74c3c",
                )
                ax_right.fill_betweenx(
                    marginal_param2.index,
                    marginal_param2.values,
                    alpha=0.3,
                    color="#e74c3c",
                )
                ax_right.set_xlabel(f"Avg {metric_column}", fontsize=8)
                ax_right.tick_params(labelleft=False, labelsize=8)
                ax_right.grid(True, alpha=0.3)
                ax_right.spines["top"].set_visible(False)
                ax_right.spines["right"].set_visible(False)

                pair_idx += 1

    # Save if path provided
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return None

    return fig


def _plot_optimization_heatmaps_bokeh(
    optimization_results: pd.DataFrame,
    metric_column: str,
    param_columns: List[str],
    cmap: str,
    save_path: Optional[str],
    open_browser: bool,
    **kwargs: Any,
) -> Any:
    """Plot optimization heatmaps using Bokeh.

    Internal function for Bokeh backend with interactive features.
    """
    from typing import cast

    from bokeh.io import output_file, save, show
    from bokeh.layouts import gridplot
    from bokeh.models import ColorBar, HoverTool, LinearColorMapper
    from bokeh.plotting import figure
    from bokeh.transform import transform

    # Calculate number of parameter pairs
    n_params = len(param_columns)
    plots = []

    # Create heatmap for each parameter pair
    for i in range(n_params):
        for j in range(i + 1, n_params):
            param1 = param_columns[i]
            param2 = param_columns[j]

            # Create pivot table
            pivot = optimization_results.pivot_table(
                values=metric_column, index=param2, columns=param1, aggfunc="mean"
            )

            # Prepare data for Bokeh
            param1_values = pivot.columns.tolist()
            param2_values = pivot.index.tolist()

            # Create meshgrid for heatmap
            data = []
            for _, p2_val in enumerate(param2_values):
                for _, p1_val in enumerate(param1_values):
                    metric_val = pivot.loc[p2_val, p1_val]
                    if pd.notna(metric_val):
                        data.append(
                            {
                                param1: p1_val,
                                param2: p2_val,
                                metric_column: metric_val,
                            }
                        )

            source_df = pd.DataFrame(data)

            # Create figure
            p = figure(
                title=f"{metric_column} vs {param1} & {param2}",
                x_axis_label=param1,
                y_axis_label=param2,
                width=400,
                height=400,
                toolbar_location="above",
                tools="hover,pan,wheel_zoom,box_zoom,reset,save",
            )

            # Create color mapper
            mapper = LinearColorMapper(
                palette="Viridis256",
                low=source_df[metric_column].min(),
                high=source_df[metric_column].max(),
            )

            # Plot rectangles for heatmap
            p.rect(
                x=param1,
                y=param2,
                width=1,
                height=1,
                source=source_df,
                fill_color=transform(metric_column, mapper),
                line_color=None,
            )

            # Configure hover tool
            hover = cast(HoverTool, p.select_one({"type": HoverTool}))
            hover.tooltips = [
                (param1, f"@{{{param1}}}"),
                (param2, f"@{{{param2}}}"),
                (metric_column, f"@{{{metric_column}}}{{0.00}}"),
            ]

            # Add color bar
            color_bar = ColorBar(
                color_mapper=mapper, width=8, location=(0, 0), title=metric_column
            )
            p.add_layout(color_bar, "right")

            plots.append(p)

    # Arrange in grid
    grid = gridplot(plots, ncols=3, sizing_mode="scale_width")

    # Save or show
    if save_path:
        output_file(save_path)
        save(grid)
        if open_browser:
            import webbrowser

            webbrowser.open(f"file://{save_path}")
    else:
        show(grid)

    return grid


def _plot_correlation_heatmap(
    ax: Axes,
    returns: Union[pd.DataFrame, Dict[str, pd.Series]],
    color_mode: Literal["color", "grayscale"] = "color",
    cmap: Optional[str] = None,
    annot: bool = True,
    mask_upper: bool = False,
    **kwargs: Any,
) -> None:
    """Plot correlation heatmap for multiple strategies or assets.

    Creates a heatmap showing correlation coefficients between different
    return series (strategies, assets, etc.).

    Args:
        ax: Matplotlib axes to plot on
        returns: DataFrame with returns for multiple strategies/assets
                (each column is a strategy/asset) OR
                Dictionary mapping strategy names to return series
        color_mode: 'color' for full colors, 'grayscale' for monochrome
        cmap: Colormap name (default: 'coolwarm' for color, 'Greys' for grayscale)
        annot: Show correlation coefficients in cells
        mask_upper: Mask upper triangle of correlation matrix
        **kwargs: Additional arguments for seaborn heatmap

    Returns:
        None

    Example:
        >>> returns_df = pd.DataFrame({
        ...     'Strategy A': [0.01, -0.02, 0.03],
        ...     'Strategy B': [0.02, -0.01, 0.02],
        ...     'Strategy C': [-0.01, 0.01, 0.04]
        ... })
        >>> fig, ax = plt.subplots(figsize=(8, 6))
        >>> _plot_correlation_heatmap(ax, returns_df)
    """
    # Convert dict to DataFrame if needed
    if isinstance(returns, dict):
        returns = pd.DataFrame(returns)

    # Calculate correlation matrix
    corr_matrix = returns.corr()

    # Create mask for upper triangle if requested
    mask = None
    if mask_upper:
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)

    # Select colormap
    if cmap is None:
        if color_mode == "grayscale":
            cmap = "Greys"
        else:
            cmap = "coolwarm"

    # Create heatmap
    sns.heatmap(
        corr_matrix,
        annot=annot,
        fmt=".2f",
        cmap=cmap,
        center=0,
        vmin=-1,
        vmax=1,
        square=True,
        linewidths=0.5,
        cbar_kws={"label": "Correlation"},
        mask=mask,
        ax=ax,
        **kwargs,
    )

    # Format axes
    _format_axis(ax, title="Correlation Heatmap", xlabel="", ylabel="")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)


__all__ = [
    "_plot_monthly_heatmap",
    "plot_heatmaps",
    "_plot_correlation_heatmap",
]
