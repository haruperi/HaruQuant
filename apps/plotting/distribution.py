"""Distribution and statistical plotting for backtest returns analysis.

This module provides advanced statistical visualization functions for analyzing
returns distributions, including:
- Enhanced histograms with statistical overlays
- Q-Q plots for normality assessment
- KDE plots with percentile markers

Features:
- Multiple bin sizing algorithms (Freedman-Diaconis, Sturges, Scott)
- Normal distribution fitting and overlay
- Statistical annotations (mean, median, std dev, skew, kurtosis)
- Percentile markers and VaR/CVaR visualization
- Support for matplotlib and Bokeh backends
"""

from typing import Any, Iterable, List, Literal, Optional, cast

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from scipy import stats

from apps.logger import logger
from apps.plotting.core import _format_axis, _format_grid, _get_colors


def _calculate_optimal_bins(
    data: pd.Series,
    method: Literal["auto", "fd", "sturges", "scott", "sqrt"] = "auto",
) -> int:
    """Calculate optimal number of bins for histogram."""
    n = len(data)

    if method in ("auto", "fd"):
        # Freedman-Diaconis rule: bin_width = 2 * IQR / n^(1/3)
        quantiles = np.asarray(np.percentile(data, [75, 25]), dtype=float)
        q75 = float(quantiles[0])
        q25 = float(quantiles[1])
        iqr = q75 - q25
        if iqr > 0:
            bin_width = 2 * iqr / (n ** (1 / 3))
            bins = int(np.ceil((data.max() - data.min()) / bin_width))
        else:
            bins = int(np.sqrt(n))
    elif method == "sturges":
        # Sturges' formula: bins = 1 + log2(n)
        bins = int(np.ceil(np.log2(n) + 1))
    elif method == "scott":
        # Scott's rule: bin_width = 3.5 * std / n^(1/3)
        std = data.std()
        if std > 0:
            bin_width = 3.5 * std / (n ** (1 / 3))
            bins = int(np.ceil((data.max() - data.min()) / bin_width))
        else:
            bins = int(np.sqrt(n))
    else:  # sqrt
        bins = int(np.ceil(np.sqrt(n)))

    # Ensure reasonable bounds
    return max(10, min(bins, 100))


def _plot_histogram(  # noqa: C901
    ax_or_figure: Any,
    returns: pd.Series,
    bins: Optional[int] = None,
    bin_method: Literal["auto", "fd", "sturges", "scott", "sqrt"] = "auto",
    show_normal: bool = True,
    show_mean: bool = True,
    show_median: bool = True,
    show_std: bool = True,
    show_stats: bool = True,
    backend: Literal["matplotlib", "bokeh"] = "matplotlib",
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Any:
    """Plot enhanced histogram of returns with statistical overlays.

    Args:
        ax_or_figure: Matplotlib axes or Bokeh figure
        returns: Returns series (as decimals, e.g., 0.01 for 1%)
        bins: Number of bins (if None, calculated automatically)
        bin_method: Method for automatic bin calculation
        show_normal: Overlay fitted normal distribution curve
        show_mean: Show mean line
        show_median: Show median line
        show_std: Show +/-1 SD and +/-2 SD markers
        show_stats: Show summary statistics annotation
        backend: Plotting backend ('matplotlib' or 'bokeh')
        color_mode: Color scheme ('color' or 'grayscale')
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes or figure
    """
    colors = _get_colors(color_mode)

    returns_pct = returns.dropna() * 100
    if len(returns_pct) == 0:
        raise ValueError("Returns series is empty after removing NaN values")

    if bins is None:
        bins = _calculate_optimal_bins(returns_pct, method=bin_method)

    logger.debug(
        "Plotting returns histogram",
        extra={
            "data_points": len(returns_pct),
            "bins": bins,
            "bin_method": bin_method,
            "backend": backend,
        },
    )

    if backend == "matplotlib":
        ax = ax_or_figure

        n, bin_edges, patches = ax.hist(
            returns_pct,
            bins=bins,
            density=True,
            alpha=0.7,
            edgecolor="black",
            linewidth=0.5,
        )

        for i, patch in enumerate(cast(Iterable[Any], patches)):
            if bin_edges[i] < 0:
                patch.set_facecolor(colors.get("loss", "#e74c3c"))
            else:
                patch.set_facecolor(colors.get("profit", "#2ecc71"))

        mu = returns_pct.mean()
        median = returns_pct.median()
        sigma = returns_pct.std()

        if show_normal and sigma > 0:
            x = np.linspace(returns_pct.min(), returns_pct.max(), 200)
            y = stats.norm.pdf(x, mu, sigma)

            ax.plot(
                x,
                y,
                color=colors.get("text", "#34495e"),
                linewidth=2,
                linestyle="--",
                label="Normal Distribution",
                alpha=0.8,
            )
        elif show_normal:
            logger.debug("Skipped normal overlay because std dev is zero")

        if show_mean:
            ax.axvline(
                mu,
                color=colors.get("text", "#34495e"),
                linestyle="-",
                linewidth=2,
                label=f"Mean: {mu:.2f}%",
                alpha=0.7,
            )

        if show_median:
            ax.axvline(
                median,
                color=colors.get("secondary", "#9b59b6"),
                linestyle="-",
                linewidth=2,
                label=f"Median: {median:.2f}%",
                alpha=0.7,
            )

        if show_std and sigma > 0:
            ax.axvline(
                mu + sigma,
                color=colors.get("text", "#7f8c8d"),
                linestyle=":",
                linewidth=1.5,
                label=f"+1 SD: {sigma:.2f}%",
                alpha=0.6,
            )
            ax.axvline(
                mu - sigma,
                color=colors.get("text", "#7f8c8d"),
                linestyle=":",
                linewidth=1.5,
                alpha=0.6,
            )

            ax.axvline(
                mu + 2 * sigma,
                color=colors.get("text", "#95a5a6"),
                linestyle=":",
                linewidth=1,
                label=f"+2 SD: {2 * sigma:.2f}%",
                alpha=0.5,
            )
            ax.axvline(
                mu - 2 * sigma,
                color=colors.get("text", "#95a5a6"),
                linestyle=":",
                linewidth=1,
                alpha=0.5,
            )
        elif show_std:
            logger.debug("Skipped std dev markers because std dev is zero")

        if show_stats:
            stats_text = (
                f"Mean: {mu:.2f}%\n"
                f"Median: {median:.2f}%\n"
                f"Std Dev: {sigma:.2f}%\n"
                f"Skew: {returns_pct.skew():.2f}\n"
                f"Kurtosis: {returns_pct.kurtosis():.2f}\n"
                f"Min: {returns_pct.min():.2f}%\n"
                f"Max: {returns_pct.max():.2f}%"
            )
            ax.text(
                0.98,
                0.98,
                stats_text,
                transform=ax.transAxes,
                fontsize=9,
                verticalalignment="top",
                horizontalalignment="right",
                bbox={
                    "boxstyle": "round",
                    "facecolor": "white",
                    "alpha": 0.9,
                    "edgecolor": colors.get("text", "#7f8c8d"),
                },
            )

        _format_axis(
            ax,
            title=kwargs.get("title", "Returns Distribution"),
            xlabel="Return (%)",
            ylabel="Density",
        )
        _format_grid(ax, alpha=0.3)

        if show_normal or show_mean or show_median or show_std:
            ax.legend(loc="upper left", fontsize=9)

        return ax

    raise NotImplementedError("Bokeh backend not yet implemented for _plot_histogram")


def _plot_qq(
    ax: Axes,
    returns: pd.Series,
    dist: str = "norm",
    show_fit_line: bool = True,
    show_r2: bool = True,
    highlight_outliers: bool = True,
    outlier_threshold: float = 2.5,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Axes:
    """Plot Q-Q (Quantile-Quantile) plot for normality assessment.

    Args:
        ax: Matplotlib axes
        returns: Returns series (as decimals)
        dist: Distribution to compare against ('norm' for normal)
        show_fit_line: Show reference line (y=x)
        show_r2: Display R^2 value for fit quality
        highlight_outliers: Highlight points deviating significantly
        outlier_threshold: Standard deviations for outlier detection
        color_mode: Color scheme ('color' or 'grayscale')
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes
    """
    colors = _get_colors(color_mode)

    returns_pct = returns.dropna() * 100
    if len(returns_pct) == 0:
        raise ValueError("Returns series is empty after removing NaN values")

    logger.debug(
        "Plotting Q-Q chart",
        extra={
            "data_points": len(returns_pct),
            "distribution": dist,
            "highlight_outliers": highlight_outliers,
            "outlier_threshold": outlier_threshold,
        },
    )

    (theoretical_quantiles, sample_quantiles), (slope, intercept, r) = stats.probplot(
        returns_pct, dist=dist
    )

    # Cast values to float for type safety
    slope_val = cast(float, slope)
    intercept_val = cast(float, intercept)
    r_value = cast(float, r) if r is not None else None
    r_squared = float(r_value**2) if r_value is not None else np.nan

    fitted_values = slope_val * theoretical_quantiles + intercept_val
    residuals = sample_quantiles - fitted_values
    std_residuals = np.std(residuals)
    outlier_mask = np.abs(residuals) > outlier_threshold * std_residuals

    ax.scatter(
        theoretical_quantiles[~outlier_mask],
        sample_quantiles[~outlier_mask],
        alpha=0.6,
        s=30,
        color=colors.get("primary", "#3498db"),
        label="Data Points",
        edgecolors="black",
        linewidth=0.5,
    )

    if highlight_outliers and outlier_mask.any():
        ax.scatter(
            theoretical_quantiles[outlier_mask],
            sample_quantiles[outlier_mask],
            alpha=0.8,
            s=50,
            color=colors.get("loss", "#e74c3c"),
            label="Outliers",
            edgecolors="black",
            linewidth=0.5,
            marker="^",
        )

    if show_fit_line:
        fit_line = slope_val * theoretical_quantiles + intercept_val
        fit_label = (
            f"Fit Line (R^2={r_squared:.3f})"
            if show_r2 and np.isfinite(r_squared)
            else "Fit Line"
        )
        ax.plot(
            theoretical_quantiles,
            fit_line,
            color=colors.get("text", "#34495e"),
            linestyle="--",
            linewidth=2,
            label=fit_label,
            alpha=0.8,
        )

    if show_r2 and np.isfinite(r_squared):
        interpretation = (
            "Excellent"
            if r_squared > 0.95
            else (
                "Good"
                if r_squared > 0.90
                else "Moderate" if r_squared > 0.80 else "Poor"
            )
        )
        r2_text = f"R^2 = {r_squared:.4f}\n({interpretation} fit)"

        ax.text(
            0.02,
            0.98,
            r2_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox={
                "boxstyle": "round",
                "facecolor": "white",
                "alpha": 0.9,
                "edgecolor": colors.get("text", "#7f8c8d"),
            },
        )

    _format_axis(
        ax,
        title=kwargs.get("title", "Q-Q Plot (Normal Distribution)"),
        xlabel="Theoretical Quantiles",
        ylabel="Sample Quantiles (%)",
    )
    _format_grid(ax, alpha=0.3)

    ax.legend(loc="lower right", fontsize=9)

    note_text = (
        "Points close to line -> Normal distribution\n" "Deviations -> Non-normality"
    )
    ax.text(
        0.98,
        0.02,
        note_text,
        transform=ax.transAxes,
        fontsize=8,
        verticalalignment="bottom",
        horizontalalignment="right",
        style="italic",
        alpha=0.7,
        color=colors.get("text", "#7f8c8d"),
    )

    return ax


def _plot_distribution(  # noqa: C901
    ax: Axes,
    returns: pd.Series,
    show_histogram: bool = True,
    show_kde: bool = True,
    show_normal: bool = True,
    show_percentiles: bool = True,
    percentiles: Optional[List[float]] = None,
    show_stats: bool = True,
    show_var: bool = True,
    var_confidence: float = 0.95,
    bins: Optional[int] = None,
    color_mode: Literal["color", "grayscale"] = "color",
    **kwargs: Any,
) -> Axes:
    """Plot comprehensive distribution with KDE, histogram, and percentiles.

    Args:
        ax: Matplotlib axes
        returns: Returns series (as decimals)
        show_histogram: Show histogram overlay
        show_kde: Show kernel density estimate
        show_normal: Show theoretical normal distribution
        show_percentiles: Show percentile markers
        percentiles: List of percentiles to mark (0-100)
        show_stats: Show summary statistics
        show_var: Show Value at Risk (VaR) marker
        var_confidence: Confidence level for VaR (e.g., 0.95 for 95%)
        bins: Number of histogram bins
        color_mode: Color scheme ('color' or 'grayscale')
        **kwargs: Additional plotting parameters

    Returns:
        Modified axes
    """
    colors = _get_colors(color_mode)

    returns_pct = returns.dropna() * 100
    # Filter out infinite values
    returns_pct = returns_pct[np.isfinite(returns_pct)]

    if len(returns_pct) == 0:
        raise ValueError(
            "Returns series is empty after removing NaN and infinite values"
        )

    logger.debug(
        "Plotting returns distribution",
        extra={
            "data_points": len(returns_pct),
            "show_histogram": show_histogram,
            "show_kde": show_kde,
            "show_normal": show_normal,
            "show_percentiles": show_percentiles,
            "show_var": show_var,
        },
    )

    percentiles = percentiles or [5, 25, 50, 75, 95]

    mu = returns_pct.mean()
    sigma = returns_pct.std()
    median = returns_pct.median()

    if bins is None:
        bins = _calculate_optimal_bins(returns_pct, method="fd")

    if show_histogram:
        _, bin_edges, patches = ax.hist(
            returns_pct,
            bins=bins,
            density=True,
            alpha=0.4,
            edgecolor="black",
            linewidth=0.5,
            label="Histogram",
        )

        for i, patch in enumerate(cast(Iterable[Any], patches)):
            if bin_edges[i] < 0:
                patch.set_facecolor(colors.get("loss", "#e74c3c"))
            else:
                patch.set_facecolor(colors.get("profit", "#2ecc71"))

    x_smooth = np.linspace(returns_pct.min(), returns_pct.max(), 500)

    if show_kde:
        kde = stats.gaussian_kde(returns_pct)
        kde_values = kde(x_smooth)

        ax.plot(
            x_smooth,
            kde_values,
            color=colors.get("primary", "#3498db"),
            linewidth=2.5,
            label="KDE",
            alpha=0.9,
        )

        ax.fill_between(
            x_smooth,
            kde_values,
            alpha=0.2,
            color=colors.get("primary", "#3498db"),
        )

    if show_normal and sigma > 0:
        normal_values = stats.norm.pdf(x_smooth, mu, sigma)

        ax.plot(
            x_smooth,
            normal_values,
            color=colors.get("text", "#34495e"),
            linewidth=2,
            linestyle="--",
            label="Normal Distribution",
            alpha=0.7,
        )
    elif show_normal:
        logger.debug("Skipped normal overlay because std dev is zero")

    if show_percentiles:
        percentile_array = np.asarray(
            np.percentile(returns_pct, percentiles), dtype=float
        )
        percentile_values: List[float] = [float(value) for value in percentile_array]

        for pct, val in zip(percentiles, percentile_values):
            if pct == 50:
                color = colors.get("secondary", "#9b59b6")
                linestyle = "-"
                linewidth: float = 2.0
            elif pct in [25, 75]:
                color = colors.get("text", "#7f8c8d")
                linestyle = "--"
                linewidth = 1.5
            else:
                color = colors.get("text", "#95a5a6")
                linestyle = ":"
                linewidth = 1.5

            ax.axvline(
                float(val),
                color=color,
                linestyle=linestyle,
                linewidth=linewidth,
                alpha=0.6,
            )

            ax.text(
                float(val),
                ax.get_ylim()[1] * 0.95,
                f"P{pct}\n{val:.2f}%",
                horizontalalignment="center",
                fontsize=7,
                bbox={
                    "boxstyle": "round,pad=0.3",
                    "facecolor": "white",
                    "alpha": 0.8,
                    "edgecolor": color,
                    "linewidth": 0.5,
                },
            )

    if show_var:
        var_percentile = (1 - var_confidence) * 100
        var_value = float(np.percentile(returns_pct, var_percentile))

        ax.axvline(
            var_value,
            color=colors.get("loss", "#e74c3c"),
            linestyle="-",
            linewidth=2.5,
            alpha=0.8,
            label=f"VaR ({var_confidence * 100:.0f}%): {var_value:.2f}%",
        )

        cvar_value = float(returns_pct[returns_pct <= var_value].mean())

        ax.axvline(
            cvar_value,
            color=colors.get("loss", "#c0392b"),
            linestyle="--",
            linewidth=2,
            alpha=0.8,
            label=f"CVaR: {cvar_value:.2f}%",
        )

    if show_stats:
        skew = returns_pct.skew()
        kurtosis = returns_pct.kurtosis()

        stats_text = (
            f"Mean: {mu:.2f}%\n"
            f"Median: {median:.2f}%\n"
            f"Std Dev: {sigma:.2f}%\n"
            f"Skew: {skew:.2f}\n"
            f"Kurtosis: {kurtosis:.2f}\n"
            f"Min: {returns_pct.min():.2f}%\n"
            f"Max: {returns_pct.max():.2f}%"
        )

        ax.text(
            0.98,
            0.98,
            stats_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="top",
            horizontalalignment="right",
            bbox={
                "boxstyle": "round",
                "facecolor": "white",
                "alpha": 0.9,
                "edgecolor": colors.get("text", "#7f8c8d"),
            },
        )

    _format_axis(
        ax,
        title=kwargs.get("title", "Returns Distribution Analysis"),
        xlabel="Return (%)",
        ylabel="Density",
    )
    _format_grid(ax, alpha=0.3)

    ax.legend(loc="upper left", fontsize=9)

    return ax


__all__ = [
    "_plot_histogram",
    "_plot_qq",
    "_plot_distribution",
]
