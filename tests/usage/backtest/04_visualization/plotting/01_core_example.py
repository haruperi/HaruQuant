"""Example usage of plotting core configuration and utilities.

This example demonstrates:
1. Matplotlib and Seaborn configuration
2. Color schemes and themes
3. Custom formatters
4. Axis and legend formatting
5. Figure creation and saving
6. Backend management

Updated to use real market data from MT5.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

from apps.plotting import (
    FLATUI_COLORS,
    TRADING_COLORS,
    CompactNumberFormatter,
    CurrencyFormatter,
    PercentageFormatter,
    _add_watermark,
    _create_figure,
    _format_axis,
    _format_date_axis,
    _format_grid,
    _format_legend,
    _get_colors,
    initialize_plotting,
    save_figure,
)
from apps.utils.data_getters import load_mt5


def example_basic_configuration():
    """Example: Basic plotting configuration."""
    print("=" * 80)
    print("Example 1: Basic Configuration")
    print("=" * 80)

    # Initialize with custom settings
    initialize_plotting(
        matplotlib_dpi=100,
        matplotlib_figsize=(10, 6),
        seaborn_context="notebook",
    )

    print("OK Plotting libraries configured with custom settings")
    print(f"  Figure DPI: {plt.rcParams['figure.dpi']}")
    print(f"  Figure size: {plt.rcParams['figure.figsize']}")


def example_color_schemes():
    """Example: Using color schemes."""
    print("\n" + "=" * 80)
    print("Example 2: Color Schemes")
    print("=" * 80)

    # Get color mode colors
    colors_standard = _get_colors(mode="color")
    colors_grayscale = _get_colors(mode="grayscale")

    print("\nStandard Trading Colors:")
    print(f"  Profit: {colors_standard['profit']}")
    print(f"  Loss: {colors_standard['loss']}")
    print(f"  Candle Up: {colors_standard['candle_up']}")
    print(f"  Candle Down: {colors_standard['candle_down']}")

    print("\nGrayscale Mode:")
    print(f"  Profit: {colors_grayscale['profit']}")
    print(f"  Loss: {colors_grayscale['loss']}")

    # Create a plot with FlatUI colors
    fig, ax = _create_figure(figsize=(10, 6))

    x = np.linspace(0, 10, 100)
    for i, (name, color) in enumerate(list(FLATUI_COLORS.items())[:6]):
        y = np.sin(x + i * 0.5)
        ax.plot(x, y, color=color, label=name.replace("_", " ").title(), linewidth=2)

    _format_axis(ax, title="FlatUI Color Palette Demo", xlabel="X", ylabel="Y")
    _format_grid(ax)
    _format_legend(ax)

    output_path = save_figure(
        fig, "output/plotting/color_schemes_demo", formats=["png"]
    )
    print(f"\nOK Color scheme demo saved to: {output_path[0]}")

    plt.close(fig)


def example_formatters():
    """Example: Using custom formatters."""
    print("\n" + "=" * 80)
    print("Example 3: Custom Axis Formatters")
    print("=" * 80)

    fig, axes = _create_figure(nrows=1, ncols=3, figsize=(15, 5))

    # Percentage formatter
    ax1 = axes[0]
    x = np.arange(10)
    y = np.random.uniform(-0.1, 0.2, 10)
    ax1.bar(
        x,
        y,
        color=[
            TRADING_COLORS["profit"] if v > 0 else TRADING_COLORS["loss"] for v in y
        ],
    )
    ax1.yaxis.set_major_formatter(PercentageFormatter(decimals=1))
    _format_axis(ax1, title="Percentage Formatter", xlabel="Period", ylabel="Return")
    _format_grid(ax1)

    # Currency formatter
    ax2 = axes[1]
    y = np.cumsum(np.random.randn(10)) * 10000 + 100000
    ax2.plot(x, y, color=FLATUI_COLORS["emerald"], linewidth=2, marker="o")
    ax2.yaxis.set_major_formatter(CurrencyFormatter(symbol="$", decimals=0))
    _format_axis(
        ax2, title="Currency Formatter", xlabel="Period", ylabel="Portfolio Value"
    )
    _format_grid(ax2)

    # Compact number formatter
    ax3 = axes[2]
    y = np.random.exponential(1_000_000, 10)
    ax3.bar(x, y, color=FLATUI_COLORS["peter_river"])
    ax3.yaxis.set_major_formatter(CompactNumberFormatter())
    _format_axis(
        ax3, title="Compact Number Formatter", xlabel="Period", ylabel="Volume"
    )
    _format_grid(ax3)

    fig.tight_layout()
    output_path = save_figure(fig, "output/plotting/formatters_demo", formats=["png"])
    print(f"\nOK Formatters demo saved to: {output_path[0]}")

    plt.close(fig)


def example_equity_curve():
    """Example: Equity curve with professional styling."""
    print("\n" + "=" * 80)
    print("Example 4: Equity Curve with Professional Styling")
    print("=" * 80)

    # Load real data
    print("Loading EURUSD data...")
    try:
        data = load_mt5("EURUSD", start_date="2023-01-01", end_date="2023-12-31", timeframe="D1")
        # Simulate a simple Buy & Hold equity curve
        initial_capital = 100000
        returns = data["close"].pct_change().fillna(0)
        equity = initial_capital * (1 + returns).cumprod()
        dates = data.index
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Create figure
    fig, axes = _create_figure(nrows=2, ncols=1, figsize=(12, 8), sharex=True)

    # Equity curve
    ax1 = axes[0]
    ax1.plot(
        dates, equity, color=FLATUI_COLORS["emerald"], linewidth=2, label="Strategy (Buy & Hold)"
    )
    ax1.fill_between(dates, equity, initial_capital, alpha=0.1, color=FLATUI_COLORS["emerald"])

    _format_axis(ax1, title="Portfolio Equity Curve (EURUSD Buy & Hold)", ylabel="Portfolio Value ($)")
    _format_grid(ax1)
    _format_legend(ax1)
    ax1.yaxis.set_major_formatter(CurrencyFormatter(symbol="$"))

    # Add watermark
    _add_watermark(ax1, text="HaruQuant", alpha=0.05)

    # Returns distribution
    ax2 = axes[1]
    ax2.bar(
        dates,
        returns,
        color=[
            TRADING_COLORS["profit"] if r > 0 else TRADING_COLORS["loss"]
            for r in returns
        ],
    )

    _format_axis(ax2, title="Daily Returns", xlabel="Date", ylabel="Return (%)")
    _format_grid(ax2)
    _format_date_axis(ax2, dates)
    ax2.yaxis.set_major_formatter(PercentageFormatter())
    ax2.axhline(0, color="black", linewidth=0.5)

    fig.tight_layout()
    output_path = save_figure(
        fig, "output/plotting/equity_curve_demo", formats=["png", "pdf"]
    )
    print("\nOK Equity curve demo saved to:")
    for path in output_path:
        print(f"    {path}")

    plt.close(fig)


def example_candlestick_style():
    """Example: Candlestick-style chart with trading colors."""
    print("\n" + "=" * 80)
    print("Example 5: Candlestick Style Chart")
    print("=" * 80)

    # Load real data
    print("Loading GBPUSD data...")
    try:
        data = load_mt5("GBPUSD", start_date="2023-01-01", end_date="2023-03-01", timeframe="D1")
        dates = data.index
        close = data["close"]
        open_ = data["open"]
        high = data["high"]
        low = data["low"]
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    fig, ax = _create_figure(figsize=(12, 6))

    # Plot candlesticks as bars
    colors = [
        TRADING_COLORS["candle_up"] if c >= o else TRADING_COLORS["candle_down"]
        for c, o in zip(close, open_)
    ]

    ax.bar(dates, height=high - low, bottom=low, width=0.6, color=colors, alpha=0.3)
    ax.bar(
        dates,
        height=np.abs(close - open_),
        bottom=np.minimum(close, open_),
        width=0.8,
        color=colors,
    )

    _format_axis(ax, title="GBPUSD Price Chart", ylabel="Price ($)")
    _format_grid(ax)
    _format_date_axis(ax, dates)
    ax.yaxis.set_major_formatter(CurrencyFormatter(symbol="$", decimals=4))

    fig.tight_layout()
    output_path = save_figure(fig, "output/plotting/candlestick_demo", formats=["png"])
    print(f"\nOK Candlestick demo saved to: {output_path[0]}")

    plt.close(fig)


def example_performance_summary():
    """Example: Performance summary with multiple subplots."""
    print("\n" + "=" * 80)
    print("Example 6: Performance Summary Dashboard")
    print("=" * 80)

    # Load real data
    print("Loading USDJPY data...")
    try:
        data = load_mt5("USDJPY", start_date="2023-01-01", end_date="2023-12-31", timeframe="D1")
        initial_capital = 100000
        returns = data["close"].pct_change().fillna(0)
        equity = initial_capital * (1 + returns).cumprod()
        drawdown = (equity - np.maximum.accumulate(equity)) / np.maximum.accumulate(equity)
        dates = data.index
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Create 2x2 grid
    fig, axes = _create_figure(nrows=2, ncols=2, figsize=(14, 10))

    # Top-left: Equity curve
    ax1 = axes[0, 0]
    ax1.plot(dates, equity, color=FLATUI_COLORS["emerald"], linewidth=2)
    ax1.fill_between(
        dates, equity, equity.min(), alpha=0.1, color=FLATUI_COLORS["emerald"]
    )
    _format_axis(ax1, title="Equity Curve (USDJPY Buy & Hold)", ylabel="Portfolio Value ($)")
    _format_grid(ax1)
    ax1.yaxis.set_major_formatter(CurrencyFormatter())

    # Top-right: Returns histogram
    ax2 = axes[0, 1]
    n, bins, patches = ax2.hist(returns, bins=30, edgecolor="black", alpha=0.7)
    # Color bars by value
    for i, patch in enumerate(patches):
        if bins[i] < 0:
            patch.set_facecolor(TRADING_COLORS["loss"])
        else:
            patch.set_facecolor(TRADING_COLORS["profit"])
    ax2.axvline(0, color="black", linewidth=1)
    _format_axis(
        ax2, title="Returns Distribution", xlabel="Daily Return", ylabel="Frequency"
    )
    _format_grid(ax2)
    ax2.xaxis.set_major_formatter(PercentageFormatter())

    # Bottom-left: Drawdown
    ax3 = axes[1, 0]
    ax3.fill_between(dates, drawdown, 0, color=TRADING_COLORS["loss"], alpha=0.3)
    ax3.plot(dates, drawdown, color=TRADING_COLORS["loss"], linewidth=1.5)
    _format_axis(ax3, title="Underwater Plot", xlabel="Date", ylabel="Drawdown (%)")
    _format_grid(ax3)
    _format_date_axis(ax3, dates)
    ax3.yaxis.set_major_formatter(PercentageFormatter())

    # Bottom-right: Monthly returns
    ax4 = axes[1, 1]
    monthly = (
        pd.Series(returns, index=dates)
        .resample("ME")
        .apply(lambda x: (1 + x).prod() - 1)
    )
    colors_monthly = [
        TRADING_COLORS["profit"] if r > 0 else TRADING_COLORS["loss"] for r in monthly
    ]
    ax4.bar(monthly.index, monthly.values, color=colors_monthly, width=20)
    ax4.axhline(0, color="black", linewidth=0.5)
    _format_axis(ax4, title="Monthly Returns", xlabel="Date", ylabel="Return (%)")
    _format_grid(ax4)
    _format_date_axis(ax4, monthly.index)
    ax4.yaxis.set_major_formatter(PercentageFormatter())

    fig.tight_layout()
    output_path = save_figure(
        fig, "output/plotting/performance_summary", formats=["png", "pdf"]
    )
    print("\nOK Performance summary saved to:")
    for path in output_path:
        print(f"    {path}")

    plt.close(fig)


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("PLOTTING CORE MODULE - USAGE EXAMPLES")
    print("=" * 80)

    # Create output directory if it doesn't exist
    import os
    os.makedirs("output/plotting", exist_ok=True)

    # example_basic_configuration()
    # example_color_schemes()
    # example_formatters()
    # example_equity_curve()
    # example_candlestick_style()
    example_performance_summary()

    print("\n" + "=" * 80)
    print("All examples completed successfully!")
    print("=" * 80)
    print("\nOutput files saved to: output/plotting/")
    print("\nKey features demonstrated:")
    print("  OK Custom matplotlib and seaborn configuration")
    print("  OK Color schemes (FlatUI, Trading, Grayscale)")
    print("  OK Custom formatters (Percentage, Currency, Compact)")
    print("  OK Professional axis and legend formatting")
    print("  OK Date axis handling")
    print("  OK Figure creation and saving (multiple formats)")
    print("  OK Trading-specific visualizations")


if __name__ == "__main__":
    main()
