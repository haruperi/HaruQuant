"""Trade analysis plotting functions.

This module provides plotting functions for analyzing trade statistics including:
- Trade duration distribution
- Trade size distribution
- Trade P&L scatter plots
- Win/loss streak visualization
"""

from typing import Any, Dict, List, Literal, Optional, Tuple, cast

import matplotlib.pyplot as plt
import numpy as np

from apps.utils.logger import logger
from apps.plotting.core import _format_axis, _format_grid, _get_colors


def _extract_durations_and_outcomes(
    trades: List[Dict[str, Any]]
) -> Tuple[List[int], List[str]]:
    """Extract trade durations and outcomes."""
    durations = []
    outcomes = []
    for trade in trades:
        if trade.get("exit_bar") is not None and trade.get("entry_bar") is not None:
            duration = trade["exit_bar"] - trade["entry_bar"]
            durations.append(duration)
            outcomes.append("win" if trade.get("pl", 0) > 0 else "loss")
    return durations, outcomes


def _extract_scatter_data(
    trades: List[Dict[str, Any]]
) -> Tuple[List[int], List[float], List[float], List[str]]:
    """Extract data for scatter plot."""
    durations = []
    pl_pcts = []
    sizes = []
    directions = []

    for trade in trades:
        if (
            trade.get("exit_bar") is not None
            and trade.get("entry_bar") is not None
            and trade.get("pl_pct") is not None
        ):
            duration = trade["exit_bar"] - trade["entry_bar"]
            durations.append(duration)
            pl_pcts.append(trade["pl_pct"] * 100)  # Convert to percentage
            sizes.append(abs(trade.get("size", 1.0)))
            directions.append("long" if trade.get("size", 1) > 0 else "short")

    return durations, pl_pcts, sizes, directions


def _add_scatter_quadrants(
    ax: plt.Axes, median_duration: float, colors: Dict[str, Any]
) -> None:
    """Add quadrant lines and labels to scatter plot."""
    ax.axhline(
        0, color=colors["neutral"], linestyle="-", linewidth=1, alpha=0.5, zorder=1
    )
    ax.axvline(
        median_duration,
        color=colors["neutral"],
        linestyle="--",
        linewidth=1,
        alpha=0.5,
        zorder=1,
    )

    # Add quadrant labels
    y_max = ax.get_ylim()[1]
    y_min = ax.get_ylim()[0]
    x_max = ax.get_xlim()[1]

    labels = [
        (median_duration / 2, y_max * 0.9, "Quick Wins", "center", "top"),
        (
            median_duration + (x_max - median_duration) / 2,
            y_max * 0.9,
            "Slow Wins",
            "center",
            "top",
        ),
        (median_duration / 2, y_min * 0.9, "Quick Losses", "center", "bottom"),
        (
            median_duration + (x_max - median_duration) / 2,
            y_min * 0.9,
            "Slow Losses",
            "center",
            "bottom",
        ),
    ]

    for x, y, text, ha, va in labels:
        ax.text(x, y, text, ha=ha, va=va, fontsize=9, alpha=0.6, style="italic")


def _calculate_pl_streaks(trades: List[Dict[str, Any]]) -> List[int]:
    """Calculate win/loss streaks."""
    outcomes = []
    for trade in trades:
        pl = trade.get("pl", 0)
        if pl is not None:
            outcomes.append(1 if pl > 0 else -1)

    streaks: List[int] = []
    if not outcomes:
        return streaks

    current_streak = 0
    current_type = 0

    for outcome in outcomes:
        if outcome == current_type:
            current_streak += outcome  # Add 1 or -1
        else:
            if current_streak != 0:
                streaks.append(current_streak)
            current_streak = outcome
            current_type = outcome

    # Add final streak
    if current_streak != 0:
        streaks.append(current_streak)

    return streaks


def _plot_trade_durations(
    trades: List[Dict[str, Any]],
    separate_by_outcome: bool = True,
    show_stats: bool = True,
    bins: int = 30,
    ax: Optional[plt.Axes] = None,
    backend: str = "matplotlib",
    color_mode: str = "color",
) -> Optional[plt.Axes]:
    """Plot histogram of trade durations.

    Creates a histogram showing the distribution of how long trades were held.
    Optionally separates winning and losing trades into different histograms.

    Args:
        trades: List of trade dictionaries with 'entry_bar', 'exit_bar', 'pl' keys
        separate_by_outcome: If True, show separate histograms for wins/losses
        show_stats: If True, add mean and median lines
        bins: Number of histogram bins
        ax: Matplotlib axes to plot on (if None, creates new)
        backend: Plotting backend ('matplotlib' or 'bokeh')
        color_mode: Color mode ('color' or 'grayscale')

    Returns:
        Matplotlib axes object (for matplotlib backend)

    Raises:
        ValueError: If backend is not supported or trades data is invalid

    Examples:
        >>> trades = [
        ...     {"entry_bar": 0, "exit_bar": 10, "pl": 100},
        ...     {"entry_bar": 20, "exit_bar": 50, "pl": -50},
        ... ]
        >>> _plot_trade_durations(trades)
    """
    if backend != "matplotlib":
        raise ValueError(f"Only 'matplotlib' backend is supported, got '{backend}'")

    if not trades:
        logger.warning("No trades provided to plot trade durations")
        return ax

    logger.debug("Plotting trade duration distribution for %d trades", len(trades))

    # Extract durations
    durations_list, outcomes_list = _extract_durations_and_outcomes(trades)

    if not durations_list:
        logger.warning("No closed trades with duration data")
        return ax

    durations = np.array(durations_list)
    outcomes = np.array(outcomes_list)

    # Create axes if not provided
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 6))

    colors = _get_colors(cast(Literal["color", "grayscale"], color_mode))

    # Plot histogram
    if separate_by_outcome:
        # Cast to numpy array for comparison
        outcomes_arr = cast(Any, outcomes)
        wins = durations[outcomes_arr == "win"]
        losses = durations[outcomes_arr == "loss"]

        if len(wins) > 0:
            ax.hist(
                wins,
                bins=bins,
                alpha=0.6,
                color=colors["profit"],
                label=f"Wins ({len(wins)})",
                edgecolor="black",
                linewidth=0.5,
            )

        if len(losses) > 0:
            ax.hist(
                losses,
                bins=bins,
                alpha=0.6,
                color=colors["loss"],
                label=f"Losses ({len(losses)})",
                edgecolor="black",
                linewidth=0.5,
            )
        else:
            ax.hist(
                durations,
                bins=bins,
                alpha=0.7,
                color=colors["neutral"],
                edgecolor="black",
                linewidth=0.5,
            )  # Add statistics
    if show_stats:
        mean_duration = np.mean(durations)
        median_duration = np.median(durations)

        ax.axvline(
            mean_duration,
            color=colors["long_exit"],
            linestyle="--",
            linewidth=2,
            label=f"Mean: {mean_duration:.1f}",
        )
        ax.axvline(
            median_duration,
            color=colors["short_exit"],
            linestyle=":",
            linewidth=2,
            label=f"Median: {median_duration:.1f}",
        )

    # Format plot
    ax.set_xlabel("Trade Duration (bars)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Frequency", fontsize=11, fontweight="bold")
    ax.set_title("Trade Duration Distribution", fontsize=13, fontweight="bold", pad=15)
    ax.legend(loc="best", framealpha=0.9)

    _format_axis(ax)
    _format_grid(ax)

    logger.success("Trade duration plot created successfully")
    return ax


def _plot_trade_sizes(
    trades: List[Dict[str, Any]],
    separate_by_direction: bool = True,
    bins: int = 30,
    ax: Optional[plt.Axes] = None,
    backend: str = "matplotlib",
    color_mode: str = "color",
) -> Optional[plt.Axes]:
    """Plot histogram of trade sizes.

    Shows the distribution of position sizes across all trades.
    Optionally separates long and short positions.

    Args:
        trades: List of trade dictionaries with 'size' key
        separate_by_direction: If True, separate long/short trades
        bins: Number of histogram bins
        ax: Matplotlib axes to plot on (if None, creates new)
        backend: Plotting backend ('matplotlib' or 'bokeh')
        color_mode: Color mode ('color' or 'grayscale')

    Returns:
        Matplotlib axes object (for matplotlib backend)

    Raises:
        ValueError: If backend is not supported or trades data is invalid

    Examples:
        >>> trades = [
        ...     {"size": 1.5},
        ...     {"size": -2.0},
        ...     {"size": 1.0},
        ... ]
        >>> _plot_trade_sizes(trades)
    """
    if backend != "matplotlib":
        raise ValueError(f"Only 'matplotlib' backend is supported, got '{backend}'")

    if not trades:
        logger.warning("No trades provided to plot trade sizes")
        return ax

    logger.debug("Plotting trade size distribution for %d trades", len(trades))

    # Extract sizes
    sizes_list = [trade.get("size", 0) for trade in trades]

    if not sizes_list:
        logger.warning("No trades with size data")
        return ax

    sizes = np.array(sizes_list)

    # Create axes if not provided
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 6))

    colors = _get_colors(cast(Literal["color", "grayscale"], color_mode))

    # Plot histogram
    if separate_by_direction:
        longs = sizes[sizes > 0]
        shorts = np.abs(sizes[sizes < 0])

        if len(longs) > 0:
            ax.hist(
                longs,
                bins=bins,
                alpha=0.6,
                color=colors["profit"],
                label=f"Long ({len(longs)})",
                edgecolor="black",
                linewidth=0.5,
            )

        if len(shorts) > 0:
            ax.hist(
                shorts,
                bins=bins,
                alpha=0.6,
                color=colors["loss"],
                label=f"Short ({len(shorts)})",
                edgecolor="black",
                linewidth=0.5,
            )
    else:
        ax.hist(
            np.abs(sizes),
            bins=bins,
            alpha=0.7,
            color=colors["neutral"],
            edgecolor="black",
            linewidth=0.5,
        )

    # Format plot
    ax.set_xlabel("Position Size (abs)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Frequency", fontsize=11, fontweight="bold")
    ax.set_title("Trade Size Distribution", fontsize=13, fontweight="bold", pad=15)
    if separate_by_direction:
        ax.legend(loc="best", framealpha=0.9)

    _format_axis(ax)
    _format_grid(ax)

    logger.success("Trade size plot created successfully")
    return ax


def _plot_trade_scatter(
    trades: List[Dict[str, Any]],
    size_by_position: bool = True,
    show_quadrants: bool = True,
    ax: Optional[plt.Axes] = None,
    backend: str = "matplotlib",
    color_mode: str = "color",
) -> Optional[plt.Axes]:
    """Plot scatter of trade P&L vs duration.

    Creates a scatter plot showing the relationship between trade duration
    and profit/loss. Points are colored by direction (long/short) and optionally
    sized by position size.

    Args:
        trades: List of trade dictionaries with 'entry_bar', 'exit_bar', 'pl_pct', 'size'
        size_by_position: If True, marker size reflects position size
        show_quadrants: If True, show quadrant lines (quick wins, slow wins, etc.)
        ax: Matplotlib axes to plot on (if None, creates new)
        backend: Plotting backend ('matplotlib' or 'bokeh')
        color_mode: Color mode ('color' or 'grayscale')

    Returns:
        Matplotlib axes object (for matplotlib backend)

    Raises:
        ValueError: If backend is not supported or trades data is invalid

    Examples:
        >>> trades = [
        ...     {"entry_bar": 0, "exit_bar": 10, "pl_pct": 0.05, "size": 1.0},
        ...     {"entry_bar": 20, "exit_bar": 50, "pl_pct": -0.03, "size": -2.0},
        ... ]
        >>> _plot_trade_scatter(trades)
    """
    if backend != "matplotlib":
        raise ValueError(f"Only 'matplotlib' backend is supported, got '{backend}'")

    if not trades:
        logger.warning("No trades provided to plot trade scatter")
        return ax

    logger.debug("Plotting trade P&L scatter for %d trades", len(trades))

    # Extract data
    durations_list, pl_pcts_list, sizes_list, directions_list = _extract_scatter_data(
        trades
    )

    if not durations_list:
        logger.warning("No closed trades with required data for scatter plot")
        return ax

    durations = np.array(durations_list)
    pl_pcts = np.array(pl_pcts_list)
    sizes_array = np.array(sizes_list)
    directions = np.array(directions_list)

    # Create axes if not provided
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 7))

    colors = _get_colors(cast(Literal["color", "grayscale"], color_mode))

    # Calculate marker sizes
    if size_by_position:
        # Normalize sizes to reasonable range (20-300)
        min_size, max_size = 20, 300
        if sizes_array.max() > sizes_array.min():
            normalized_sizes = min_size + (sizes_array - sizes_array.min()) / (
                sizes_array.max() - sizes_array.min()
            ) * (max_size - min_size)
        else:
            normalized_sizes = np.full_like(sizes_array, (min_size + max_size) / 2)
    else:
        normalized_sizes = np.full_like(sizes_array, 50)

    # Plot long and short trades
    # Cast to numpy array for comparison
    directions_arr = cast(Any, directions)
    longs = directions_arr == "long"
    shorts = directions_arr == "short"

    if np.any(longs):
        ax.scatter(
            durations[longs],
            pl_pcts[longs],
            s=normalized_sizes[longs],
            c=colors["profit"],
            alpha=0.6,
            edgecolors="black",
            linewidth=0.5,
            label="Long",
        )

    if np.any(shorts):
        ax.scatter(
            durations[shorts],
            pl_pcts[shorts],
            s=normalized_sizes[shorts],
            c=colors["loss"],
            alpha=0.6,
            edgecolors="black",
            linewidth=0.5,
            label="Short",
            marker="s",
        )

    # Add quadrant lines
    if show_quadrants:
        median_duration = np.median(durations)
        _add_scatter_quadrants(ax, median_duration, colors)

    # Format plot
    ax.set_xlabel("Trade Duration (bars)", fontsize=11, fontweight="bold")
    ax.set_ylabel("P&L (%)", fontsize=11, fontweight="bold")
    ax.set_title("Trade P&L vs Duration", fontsize=13, fontweight="bold", pad=15)
    ax.legend(loc="best", framealpha=0.9)

    _format_axis(ax)
    _format_grid(ax)

    logger.success("Trade scatter plot created successfully")
    return ax


def _plot_win_loss_streaks(
    trades: List[Dict[str, Any]],
    highlight_longest: bool = True,
    ax: Optional[plt.Axes] = None,
    backend: str = "matplotlib",
    color_mode: str = "color",
) -> Optional[plt.Axes]:
    """Plot consecutive win/loss streaks over time.

    Creates a bar chart showing runs of consecutive wins and losses,
    helping identify periods of consistent performance or drawdown.

    Args:
        trades: List of trade dictionaries with 'pl', 'exit_time' keys
        highlight_longest: If True, highlight the longest streaks
        ax: Matplotlib axes to plot on (if None, creates new)
        backend: Plotting backend ('matplotlib' or 'bokeh')
        color_mode: Color mode ('color' or 'grayscale')

    Returns:
        Matplotlib axes object (for matplotlib backend)

    Raises:
        ValueError: If backend is not supported or trades data is invalid

    Examples:
        >>> trades = [
        ...     {"pl": 100, "exit_time": "2024-01-01"},
        ...     {"pl": 50, "exit_time": "2024-01-02"},
        ...     {"pl": -30, "exit_time": "2024-01-03"},
        ... ]
        >>> _plot_win_loss_streaks(trades)
    """
    if backend != "matplotlib":
        raise ValueError(f"Only 'matplotlib' backend is supported, got '{backend}'")

    if not trades:
        logger.warning("No trades provided to plot win/loss streaks")
        return ax

    logger.debug("Plotting win/loss streaks for %d trades", len(trades))

    # Extract outcomes and calculate streaks
    streaks = _calculate_pl_streaks(trades)

    if not streaks:
        logger.warning("No streaks to plot")
        return ax

    # Create axes if not provided
    if ax is None:
        _, ax = plt.subplots(figsize=(12, 6))

    colors = _get_colors(cast(Literal["color", "grayscale"], color_mode))

    # Plot bars
    x_positions = np.arange(len(streaks))
    bar_colors = [colors["profit"] if s > 0 else colors["loss"] for s in streaks]

    bars = ax.bar(
        x_positions,
        streaks,
        color=bar_colors,
        edgecolor="black",
        linewidth=0.5,
        alpha=0.7,
    )

    # Highlight longest streaks
    if highlight_longest and len(streaks) > 0:
        longest_win_idx = np.argmax([s if s > 0 else 0 for s in streaks])
        longest_loss_idx = np.argmax([abs(s) if s < 0 else 0 for s in streaks])

        if streaks[longest_win_idx] > 0:
            bars[longest_win_idx].set_edgecolor(colors["long_exit"])
            bars[longest_win_idx].set_linewidth(3)

        if streaks[longest_loss_idx] < 0:
            bars[longest_loss_idx].set_edgecolor(colors["short_exit"])
            bars[longest_loss_idx].set_linewidth(3)

    # Add zero line
    ax.axhline(0, color=colors["neutral"], linestyle="-", linewidth=1, zorder=1)

    # Format plot
    ax.set_xlabel("Streak Number", fontsize=11, fontweight="bold")
    ax.set_ylabel("Consecutive Wins (+) / Losses (-)", fontsize=11, fontweight="bold")
    ax.set_title("Win/Loss Streaks", fontsize=13, fontweight="bold", pad=15)

    # Add summary statistics as text
    max_win_streak = max([s for s in streaks if s > 0], default=0)
    max_loss_streak = abs(min([s for s in streaks if s < 0], default=0))

    stats_text = f"Max Win Streak: {max_win_streak}\nMax Loss Streak: {max_loss_streak}"
    ax.text(
        0.98,
        0.98,
        stats_text,
        transform=ax.transAxes,
        va="top",
        ha="right",
        bbox={
            "boxstyle": "round,pad=0.5",
            "facecolor": "white",
            "alpha": 0.8,
            "edgecolor": "gray",
        },
        fontsize=9,
    )

    _format_axis(ax)
    _format_grid(ax)

    logger.success("Win/loss streaks plot created successfully")
    return ax


__all__ = [
    "_plot_trade_durations",
    "_plot_trade_sizes",
    "_plot_trade_scatter",
    "_plot_win_loss_streaks",
]

