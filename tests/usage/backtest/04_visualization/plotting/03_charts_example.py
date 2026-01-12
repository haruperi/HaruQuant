"""Example usage of price chart components.

This example demonstrates how to use the individual chart components:
1. OHLC/Candlestick charts (Matplotlib and Bokeh)
2. Line charts for equity curves
3. Volume charts
4. Combining multiple chart components

Updated to use real market data from MT5.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from apps.plotting.charts import (
    _plot_line,
    _plot_ohlc_matplotlib,
    _plot_volume_matplotlib,
)
from apps.plotting.core import BOKEH_AVAILABLE
from apps.utils.data_getters import load_mt5

if BOKEH_AVAILABLE:
    from bokeh.io import output_file, save
    from bokeh.layouts import column

    from apps.plotting.charts import _plot_ohlc_bokeh, _plot_volume_bokeh


def example_1_matplotlib_ohlc():
    """Example 1: Basic OHLC chart with Matplotlib."""
    print("=" * 80)
    print("Example 1: Matplotlib OHLC Chart")
    print("=" * 80)

    # Load real data
    print("Loading EURUSD data...")
    try:
        data = load_mt5("EURUSD", start_date="2023-01-01", end_date="2023-03-01", timeframe="D1")
        # Rename columns to Title Case for plotting functions if they expect it
        # The plotting functions likely expect 'Open', 'High', 'Low', 'Close', 'Volume'
        # Check if they handle lowercase. If not, rename.
        # Based on previous files, plotting usually expects Title Case.
        data = data.rename(columns={
            "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
        })
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Create figure and plot OHLC
    fig, ax = plt.subplots(figsize=(12, 6))
    _plot_ohlc_matplotlib(ax, data, title="EURUSD Price Chart - Matplotlib")

    plt.tight_layout()
    plt.savefig("output/plotting/charts_matplotlib_ohlc.png", dpi=100)
    print(
        "[OK] Matplotlib OHLC chart saved to: output/plotting/charts_matplotlib_ohlc.png"
    )
    plt.close()


def example_2_matplotlib_with_volume():
    """Example 2: OHLC chart with volume subplot (Matplotlib)."""
    print("\n" + "=" * 80)
    print("Example 2: OHLC with Volume - Matplotlib")
    print("=" * 80)

    # Load real data
    print("Loading GBPUSD data...")
    try:
        data = load_mt5("GBPUSD", start_date="2023-01-01", end_date="2023-03-01", timeframe="D1")
        data = data.rename(columns={
            "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
        })
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(12, 8),
        gridspec_kw={"height_ratios": [3, 1]},
        sharex=True,
    )

    # Plot OHLC on top panel
    _plot_ohlc_matplotlib(ax1, data, title="GBPUSD Price with Volume")

    # Plot volume on bottom panel
    _plot_volume_matplotlib(ax2, data)

    plt.tight_layout()
    plt.savefig("output/plotting/charts_matplotlib_ohlc_volume.png", dpi=100)
    print(
        "[OK] OHLC + Volume chart saved to: output/plotting/charts_matplotlib_ohlc_volume.png"
    )
    plt.close()


def example_3_line_chart():
    """Example 3: Line chart for price curve."""
    print("\n" + "=" * 80)
    print("Example 3: Line Chart - Price Curve")
    print("=" * 80)

    # Load real data
    print("Loading USDJPY data...")
    try:
        data = load_mt5("USDJPY", start_date="2023-01-01", end_date="2023-12-31", timeframe="D1")
        # Use Close price as series
        price_series = data["close"]
        price_series.name = "USDJPY Close"
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Create figure and plot line
    fig, ax = plt.subplots(figsize=(12, 5))
    _plot_line(
        ax,
        price_series,
        label="USDJPY Close Price",
        color="#2ecc71",
        style="-",
        backend="matplotlib",
    )

    ax.set_title("USDJPY Price Curve")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("output/plotting/charts_line_price.png", dpi=100)
    print("[OK] Price line chart saved to: output/plotting/charts_line_price.png")
    plt.close()


def example_4_multiple_lines():
    """Example 4: Multiple line charts - comparison."""
    print("\n" + "=" * 80)
    print("Example 4: Multiple Lines - Asset Comparison")
    print("=" * 80)

    # Load real data
    print("Loading EURUSD, GBPUSD, USDJPY data...")
    try:
        eur = load_mt5("EURUSD", start_date="2023-01-01", end_date="2023-12-31", timeframe="D1")["close"]
        gbp = load_mt5("GBPUSD", start_date="2023-01-01", end_date="2023-12-31", timeframe="D1")["close"]
        jpy = load_mt5("USDJPY", start_date="2023-01-01", end_date="2023-12-31", timeframe="D1")["close"]
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Normalize to 100
    eur = eur / eur.iloc[0] * 100
    gbp = gbp / gbp.iloc[0] * 100
    jpy = jpy / jpy.iloc[0] * 100

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot each line
    _plot_line(
        ax, eur, label="EURUSD", color="#2ecc71", backend="matplotlib"
    )
    _plot_line(
        ax, gbp, label="GBPUSD", color="#3498db", backend="matplotlib"
    )
    _plot_line(
        ax,
        jpy,
        label="USDJPY",
        color="#e74c3c",
        style="--",
        backend="matplotlib",
    )

    ax.set_title("Asset Performance Comparison (Normalized)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Normalized Price")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("output/plotting/charts_multi_line.png", dpi=100)
    print("[OK] Multi-line comparison saved to: output/plotting/charts_multi_line.png")
    plt.close()


def example_5_grayscale_mode():
    """Example 5: OHLC chart in grayscale mode."""
    print("\n" + "=" * 80)
    print("Example 5: Grayscale Mode")
    print("=" * 80)

    # Load real data
    print("Loading EURUSD data...")
    try:
        data = load_mt5("EURUSD", start_date="2023-01-01", end_date="2023-03-01", timeframe="D1")
        data = data.rename(columns={
            "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
        })
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Create figure with grayscale
    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(12, 8),
        gridspec_kw={"height_ratios": [3, 1]},
        sharex=True,
    )

    # Plot in grayscale mode
    _plot_ohlc_matplotlib(ax1, data, color_mode="grayscale", title="Grayscale Mode (EURUSD)")
    _plot_volume_matplotlib(ax2, data, color_mode="grayscale")

    plt.tight_layout()
    plt.savefig("output/plotting/charts_grayscale.png", dpi=100)
    print("[OK] Grayscale chart saved to: output/plotting/charts_grayscale.png")
    plt.close()


def example_6_bokeh_interactive():
    """Example 6: Interactive Bokeh charts."""
    if not BOKEH_AVAILABLE:
        print("\n" + "=" * 80)
        print("Example 6: Bokeh Interactive Charts")
        print("=" * 80)
        print(" Skipping - Bokeh not installed")
        print("  Install with: pip install bokeh")
        return

    print("\n" + "=" * 80)
    print("Example 6: Bokeh Interactive Charts")
    print("=" * 80)

    # Load real data
    print("Loading EURUSD data...")
    try:
        data = load_mt5("EURUSD", start_date="2023-01-01", end_date="2023-06-01", timeframe="D1")
        data = data.rename(columns={
            "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
        })
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Create OHLC chart
    ohlc_fig = _plot_ohlc_bokeh(
        data,
        width=1000,
        height=400,
        title="Interactive EURUSD Chart (Hover for details)",
    )

    # Create volume chart linked to OHLC
    volume_fig = _plot_volume_bokeh(
        data,
        width=1000,
        height=150,
        link_to=ohlc_fig,  # Link x-axis for synchronized zooming
    )

    # Combine charts
    layout = column(ohlc_fig, volume_fig)

    # Save to HTML
    output_file("output/plotting/charts_bokeh_interactive.html")
    save(layout)

    print(
        "[OK] Interactive Bokeh chart saved to: output/plotting/charts_bokeh_interactive.html"
    )
    print("  Open in browser to interact with the chart")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("CHART COMPONENTS - USAGE EXAMPLES")
    print("=" * 80)

    # Create output directory if it doesn't exist
    import os

    os.makedirs("output/plotting", exist_ok=True)

    try:
        # Matplotlib examples
        example_1_matplotlib_ohlc()
        example_2_matplotlib_with_volume()
        example_3_line_chart()
        example_4_multiple_lines()
        example_5_grayscale_mode()

        # # Bokeh example
        example_6_bokeh_interactive()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)
        print("\nKey features demonstrated:")
        print("  * OHLC/Candlestick charts (Matplotlib)")
        print("  * Volume charts with price-direction coloring")
        print("  * Line charts for equity curves and comparisons")
        print("  * Multiple charts on same figure")
        print("  * Color and grayscale modes")
        print("  * Interactive Bokeh charts with hover tooltips")
        print("\nOutput files in: output/plotting/")

    except Exception as e:
        print(f"\n[ERROR] Error in examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
