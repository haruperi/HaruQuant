"""Example usage of trade markers and annotations.

This example demonstrates how to use trade marker functions:
1. Entry markers for long and short positions
2. Exit markers colored by profit/loss
3. Trade connection lines
4. Combining markers with price charts
5. Interactive Bokeh markers with hover tooltips

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

from apps.plotting.charts import _plot_ohlc_matplotlib
from apps.plotting.core import BOKEH_AVAILABLE
from apps.plotting.markers import (
    _plot_entry_markers,
    _plot_exit_markers,
    _plot_trade_lines,
)
from apps.utils.data_getters import load_mt5

if BOKEH_AVAILABLE:
    from bokeh.io import output_file, save
    from bokeh.layouts import column

    from apps.plotting.charts import _plot_ohlc_bokeh


def get_real_data_with_trades(symbol="EURUSD", start_date="2023-01-01", end_date="2023-04-01"):
    """Load real OHLC data and generate sample trades.

    Returns:
        Tuple of (OHLC DataFrame, list of trades)
    """
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        ohlc = data.rename(columns={
            "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
        })
        dates = ohlc.index
        close = ohlc["Close"]
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame(), []

    # Generate sample trades based on real data indices
    trades = []
    
    if len(dates) > 80:
        # Trade 1: Profitable long
        trades.append(
            {
                "entry_time": dates[10],
                "entry_price": close.iloc[10],
                "exit_time": dates[20],
                "exit_price": close.iloc[20],
                "size": 1000,
                "pl": (close.iloc[20] - close.iloc[10]) * 1000,
                "pl_pct": (close.iloc[20] - close.iloc[10]) / close.iloc[10],
                "is_long": True,
                "entry_tag": "MA Crossover",
                "exit_tag": "Target Hit",
            }
        )

        # Trade 2: Losing short
        trades.append(
            {
                "entry_time": dates[30],
                "entry_price": close.iloc[30],
                "exit_time": dates[40],
                "exit_price": close.iloc[40],
                "size": 1000,
                "pl": (close.iloc[30] - close.iloc[40]) * 1000, # Short PL: Entry - Exit
                "pl_pct": (close.iloc[30] - close.iloc[40]) / close.iloc[30],
                "is_long": False,
                "entry_tag": "Reversal Signal",
                "exit_tag": "Stop Loss",
            }
        )

        # Trade 3: Profitable long
        trades.append(
            {
                "entry_time": dates[50],
                "entry_price": close.iloc[50],
                "exit_time": dates[60],
                "exit_price": close.iloc[60],
                "size": 1500,
                "pl": (close.iloc[60] - close.iloc[50]) * 1500,
                "pl_pct": (close.iloc[60] - close.iloc[50]) / close.iloc[50],
                "is_long": True,
                "entry_tag": "Breakout",
                "exit_tag": "Trailing Stop",
            }
        )

        # Trade 4: Small loss long
        trades.append(
            {
                "entry_time": dates[70],
                "entry_price": close.iloc[70],
                "exit_time": dates[75],
                "exit_price": close.iloc[75],
                "size": 1000,
                "pl": (close.iloc[75] - close.iloc[70]) * 1000,
                "pl_pct": (close.iloc[75] - close.iloc[70]) / close.iloc[70],
                "is_long": True,
                "entry_tag": "Dip Buy",
                "exit_tag": "Quick Exit",
            }
        )

    return ohlc, trades


def example_1_entry_markers():
    """Example 1: Entry markers on price chart."""
    print("=" * 80)
    print("Example 1: Entry Markers")
    print("=" * 80)

    print("Loading EURUSD data...")
    ohlc, trades = get_real_data_with_trades("EURUSD")
    if ohlc.empty: return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot OHLC chart
    _plot_ohlc_matplotlib(ax, ohlc, title="EURUSD Price Chart with Entry Markers")

    # Add entry markers
    _plot_entry_markers(ax, trades, backend="matplotlib", marker_size=150)

    # Add legend
    ax.legend(loc="upper left")

    plt.tight_layout()
    plt.savefig("output/plotting/markers_entry.png", dpi=100)
    print("[OK] Entry markers example saved to: output/plotting/markers_entry.png")
    plt.close()


def example_2_exit_markers():
    """Example 2: Exit markers colored by P&L."""
    print("\n" + "=" * 80)
    print("Example 2: Exit Markers (Colored by P&L)")
    print("=" * 80)

    print("Loading GBPUSD data...")
    ohlc, trades = get_real_data_with_trades("GBPUSD")
    if ohlc.empty: return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot OHLC chart
    _plot_ohlc_matplotlib(ax, ohlc, title="GBPUSD Price Chart with Exit Markers")

    # Add exit markers
    _plot_exit_markers(ax, trades, backend="matplotlib", marker_size=150)

    # Add legend
    ax.legend(loc="upper left")

    plt.tight_layout()
    plt.savefig("output/plotting/markers_exit.png", dpi=100)
    print("[OK] Exit markers example saved to: output/plotting/markers_exit.png")
    plt.close()


def example_3_combined_markers():
    """Example 3: Entry and exit markers combined."""
    print("\n" + "=" * 80)
    print("Example 3: Combined Entry and Exit Markers")
    print("=" * 80)

    print("Loading USDJPY data...")
    ohlc, trades = get_real_data_with_trades("USDJPY")
    if ohlc.empty: return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot OHLC chart
    _plot_ohlc_matplotlib(ax, ohlc, title="USDJPY Price Chart with All Trade Markers")

    # Add both entry and exit markers
    _plot_entry_markers(ax, trades, backend="matplotlib", marker_size=150)
    _plot_exit_markers(ax, trades, backend="matplotlib", marker_size=150)

    # Add legend
    ax.legend(loc="upper left", fontsize=9, ncol=2)

    plt.tight_layout()
    plt.savefig("output/plotting/markers_combined.png", dpi=100)
    print(
        "[OK] Combined markers example saved to: output/plotting/markers_combined.png"
    )
    plt.close()


def example_4_trade_lines():
    """Example 4: Trade connection lines."""
    print("\n" + "=" * 80)
    print("Example 4: Trade Connection Lines")
    print("=" * 80)

    print("Loading AUDUSD data...")
    ohlc, trades = get_real_data_with_trades("AUDUSD")
    if ohlc.empty: return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot OHLC chart
    _plot_ohlc_matplotlib(ax, ohlc, title="AUDUSD Trades with Connection Lines")

    # Add trade lines first (lower z-order)
    _plot_trade_lines(ax, trades, backend="matplotlib", alpha=0.5, line_style="--")

    # Then add markers on top
    _plot_entry_markers(ax, trades, backend="matplotlib", marker_size=150)
    _plot_exit_markers(ax, trades, backend="matplotlib", marker_size=150)

    # Add legend
    ax.legend(loc="upper left", fontsize=9, ncol=2)

    plt.tight_layout()
    plt.savefig("output/plotting/markers_with_lines.png", dpi=100)
    print("[OK] Trade lines example saved to: output/plotting/markers_with_lines.png")
    plt.close()


def example_5_size_by_pl():
    """Example 5: Exit markers sized by P&L magnitude."""
    print("\n" + "=" * 80)
    print("Example 5: Exit Markers Sized by P&L")
    print("=" * 80)

    print("Loading EURUSD data...")
    ohlc, trades = get_real_data_with_trades("EURUSD")
    if ohlc.empty: return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot OHLC chart
    _plot_ohlc_matplotlib(ax, ohlc, title="Exit Markers Scaled by P&L Magnitude")

    # Add exit markers with size proportional to P&L
    _plot_exit_markers(
        ax, trades, backend="matplotlib", marker_size=100, size_by_pl=True
    )

    # Add legend
    ax.legend(loc="upper left")

    plt.tight_layout()
    plt.savefig("output/plotting/markers_sized.png", dpi=100)
    print("[OK] Sized markers example saved to: output/plotting/markers_sized.png")
    plt.close()


def example_6_grayscale():
    """Example 6: Markers in grayscale mode."""
    print("\n" + "=" * 80)
    print("Example 6: Grayscale Mode")
    print("=" * 80)

    print("Loading GBPUSD data...")
    ohlc, trades = get_real_data_with_trades("GBPUSD")
    if ohlc.empty: return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot OHLC chart in grayscale
    _plot_ohlc_matplotlib(
        ax, ohlc, color_mode="grayscale", title="Grayscale Trade Markers"
    )

    # Add markers in grayscale
    _plot_trade_lines(
        ax, trades, backend="matplotlib", color_mode="grayscale", alpha=0.4
    )
    _plot_entry_markers(
        ax, trades, backend="matplotlib", color_mode="grayscale", marker_size=150
    )
    _plot_exit_markers(
        ax, trades, backend="matplotlib", color_mode="grayscale", marker_size=150
    )

    # Add legend
    ax.legend(loc="upper left", fontsize=9, ncol=2)

    plt.tight_layout()
    plt.savefig("output/plotting/markers_grayscale.png", dpi=100)
    print("[OK] Grayscale example saved to: output/plotting/markers_grayscale.png")
    plt.close()


def example_7_bokeh_interactive():
    """Example 7: Interactive Bokeh markers with hover tooltips."""
    if not BOKEH_AVAILABLE:
        print("\n" + "=" * 80)
        print("Example 7: Bokeh Interactive Markers")
        print("=" * 80)
        print("[WARNING] Skipping - Bokeh not installed")
        print("  Install with: pip install bokeh")
        return

    print("\n" + "=" * 80)
    print("Example 7: Interactive Bokeh Markers")
    print("=" * 80)

    print("Loading USDJPY data...")
    ohlc, trades = get_real_data_with_trades("USDJPY")
    if ohlc.empty: return

    # Create Bokeh figure
    p = _plot_ohlc_bokeh(
        ohlc,
        width=1200,
        height=600,
        title="Interactive Trade Markers (Hover for Details)",
    )

    # Add trade lines
    _plot_trade_lines(p, trades, backend="bokeh", alpha=0.3)

    # Add entry and exit markers
    _plot_entry_markers(p, trades, backend="bokeh", marker_size=120)
    _plot_exit_markers(p, trades, backend="bokeh", marker_size=120)

    # Save to HTML
    output_file("output/plotting/markers_bokeh_interactive.html")
    save(p)

    print(
        "[OK] Interactive Bokeh markers saved to: output/plotting/markers_bokeh_interactive.html"
    )
    print("  Open in browser and hover over markers to see trade details")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("TRADE MARKERS & ANNOTATIONS - USAGE EXAMPLES")
    print("=" * 80)

    # Create output directory if it doesn't exist
    import os
    os.makedirs("output/plotting", exist_ok=True)

    try:
        # Matplotlib examples
        example_1_entry_markers()
        example_2_exit_markers()
        example_3_combined_markers()
        example_4_trade_lines()
        example_5_size_by_pl()
        example_6_grayscale()

        # Bokeh example
        example_7_bokeh_interactive()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)
        print("\nKey features demonstrated:")
        print("  * Entry markers (long/short positions)")
        print("  * Exit markers colored by profit/loss")
        print("  * Combined entry + exit markers")
        print("  * Trade connection lines")
        print("  * Exit markers sized by P&L magnitude")
        print("  * Grayscale mode for all markers")
        print("  * Interactive Bokeh markers with hover tooltips")
        print("\nOutput files in: output/plotting/")

    except Exception as e:
        print(f"\n[ERROR] Error in examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
