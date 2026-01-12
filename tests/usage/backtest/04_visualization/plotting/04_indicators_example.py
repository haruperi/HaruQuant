"""Example usage of indicator overlays.

This example demonstrates how to plot technical indicators:
1. Overlay indicators (moving averages, Bollinger Bands)
2. Panel indicators (RSI, MACD)
3. Multi-line indicators
4. Indicator classification
5. Custom indicator styling

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
from apps.plotting.indicators import (
    _classify_indicator,
    _create_indicator_subplot,
    _plot_overlay_indicators,
    _plot_panel_indicators,
)
from apps.utils.data_getters import load_mt5


def get_real_data_with_indicators(symbol="EURUSD", start_date="2023-01-01", end_date="2023-04-01"):
    """Load real OHLC data and calculate indicators.

    Returns:
        Tuple of (OHLC DataFrame, overlay indicators dict, panel indicators dict)
    """
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        # Rename columns to Title Case for plotting functions
        ohlc = data.rename(columns={
            "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
        })
        close_series = ohlc["Close"]
        dates = ohlc.index
    except Exception as e:
        print(f"Error loading data: {e}")
        # Fallback to empty
        return pd.DataFrame(), {}, {}

    # Calculate overlay indicators
    overlay_indicators = {
        "SMA_20": close_series.rolling(window=20).mean(),
        "SMA_50": close_series.rolling(window=50).mean(),
        "Bollinger_Bands": pd.DataFrame(
            {
                "Lower": close_series.rolling(20).mean()
                - 2 * close_series.rolling(20).std(),
                "Middle": close_series.rolling(20).mean(),
                "Upper": close_series.rolling(20).mean()
                + 2 * close_series.rolling(20).std(),
            },
            index=dates,
        ),
    }

    # Calculate panel indicators
    # Simple RSI calculation
    delta = close_series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # Simple MACD calculation
    ema12 = close_series.ewm(span=12).mean()
    ema26 = close_series.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    histogram = macd_line - signal_line

    panel_indicators = {
        "RSI": rsi,
        "MACD": pd.DataFrame(
            {
                "MACD": macd_line,
                "Signal": signal_line,
                "Histogram": histogram,
            },
            index=dates,
        ),
    }

    return ohlc, overlay_indicators, panel_indicators


def example_1_overlay_indicators():
    """Example 1: Overlay indicators on price chart."""
    print("=" * 80)
    print("Example 1: Overlay Indicators")
    print("=" * 80)

    print("Loading EURUSD data...")
    ohlc, overlay_indicators, _ = get_real_data_with_indicators("EURUSD")
    if ohlc.empty: return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot OHLC chart
    _plot_ohlc_matplotlib(ax, ohlc, title="EURUSD Price Chart with Overlay Indicators")

    # Add overlay indicators
    _plot_overlay_indicators(ax, overlay_indicators)

    # Add legend
    ax.legend(loc="upper left", fontsize=9)

    plt.tight_layout()
    plt.savefig("output/plotting/indicators_overlay.png", dpi=100)
    print(
        "[OK] Overlay indicators example saved to: output/plotting/indicators_overlay.png"
    )
    plt.close()


def example_2_panel_indicators():
    """Example 2: Panel indicators in separate subplots."""
    print("\n" + "=" * 80)
    print("Example 2: Panel Indicators")
    print("=" * 80)

    print("Loading GBPUSD data...")
    _, _, panel_indicators = get_real_data_with_indicators("GBPUSD")
    if not panel_indicators: return

    # Get dates from one of the indicators
    dates = panel_indicators["RSI"].index

    # Create panel indicators plot
    fig, axes = _plot_panel_indicators(panel_indicators, dates, figsize=(14, 8))

    plt.savefig("output/plotting/indicators_panel.png", dpi=100)
    print(
        "[OK] Panel indicators example saved to: output/plotting/indicators_panel.png"
    )
    plt.close()


def example_3_combined_chart():
    """Example 3: Price chart with both overlay and panel indicators."""
    print("\n" + "=" * 80)
    print("Example 3: Combined Chart with Overlay and Panel Indicators")
    print("=" * 80)

    print("Loading USDJPY data...")
    ohlc, overlay_indicators, panel_indicators = get_real_data_with_indicators("USDJPY")
    if ohlc.empty: return

    # Create figure with subplots
    fig = plt.figure(figsize=(14, 12))

    # Price chart with overlay indicators (top, 60% height)
    ax1 = plt.subplot(3, 1, 1)
    _plot_ohlc_matplotlib(ax1, ohlc, title="USDJPY Price Chart with Indicators")
    _plot_overlay_indicators(ax1, overlay_indicators)
    ax1.legend(loc="upper left", fontsize=8)

    # RSI panel (middle, 20% height)
    ax2 = plt.subplot(3, 1, 2, sharex=ax1)
    ax2.plot(ohlc.index, panel_indicators["RSI"], label="RSI", color="#3498db")
    ax2.axhline(y=30, color="gray", linestyle="--", alpha=0.5)
    ax2.axhline(y=70, color="gray", linestyle="--", alpha=0.5)
    ax2.set_ylabel("RSI")
    ax2.set_ylim(0, 100)
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(True, alpha=0.3)

    # MACD panel (bottom, 20% height)
    ax3 = plt.subplot(3, 1, 3, sharex=ax1)
    macd_data = panel_indicators["MACD"]
    ax3.plot(ohlc.index, macd_data["MACD"], label="MACD", color="#2ecc71")
    ax3.plot(ohlc.index, macd_data["Signal"], label="Signal", color="#e74c3c")
    ax3.bar(
        ohlc.index,
        macd_data["Histogram"],
        label="Histogram",
        color="#95a5a6",
        alpha=0.3,
    )
    ax3.axhline(y=0, color="black", linestyle="-", alpha=0.3)
    ax3.set_ylabel("MACD")
    ax3.set_xlabel("Date")
    ax3.legend(loc="upper left", fontsize=8)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("output/plotting/indicators_combined.png", dpi=100)
    print("[OK] Combined chart saved to: output/plotting/indicators_combined.png")
    plt.close()


def example_4_bollinger_bands():
    """Example 4: Bollinger Bands with filled area."""
    print("\n" + "=" * 80)
    print("Example 4: Bollinger Bands with Filled Area")
    print("=" * 80)

    print("Loading AUDUSD data...")
    ohlc, overlay_indicators, _ = get_real_data_with_indicators("AUDUSD")
    if ohlc.empty: return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot OHLC chart
    _plot_ohlc_matplotlib(ax, ohlc, title="AUDUSD Price Chart with Bollinger Bands")

    # Add only Bollinger Bands
    bb_indicators = {"Bollinger_Bands": overlay_indicators["Bollinger_Bands"]}
    _plot_overlay_indicators(ax, bb_indicators, fill_alpha=0.15)

    # Add legend
    ax.legend(loc="upper left", fontsize=9)

    plt.tight_layout()
    plt.savefig("output/plotting/indicators_bollinger.png", dpi=100)
    print(
        "[OK] Bollinger Bands example saved to: output/plotting/indicators_bollinger.png"
    )
    plt.close()


def example_5_indicator_classification():
    """Example 5: Demonstrate indicator classification."""
    print("\n" + "=" * 80)
    print("Example 5: Indicator Classification")
    print("=" * 80)

    # Test various indicator names
    indicators = [
        "SMA_20",
        "EMA_50",
        "RSI",
        "MACD",
        "Bollinger_Bands",
        "Stochastic",
        "ATR",
        "VWAP",
    ]

    print("\nIndicator Classifications:")
    print("-" * 50)

    for ind_name in indicators:
        plot_type, style_hints = _classify_indicator(ind_name)
        levels = style_hints.get("levels", "None")
        print(f"{ind_name:20} -> {plot_type:10} (levels: {levels})")

    print("\n[OK] Indicator classification demonstrated")


def example_6_create_subplot():
    """Example 6: Creating indicator subplot using helper function."""
    print("\n" + "=" * 80)
    print("Example 6: Creating Indicator Subplot")
    print("=" * 80)

    print("Loading EURUSD data...")
    ohlc, overlay_indicators, panel_indicators = get_real_data_with_indicators("EURUSD")
    if ohlc.empty: return

    # Create main chart
    fig, main_ax = plt.subplots(figsize=(14, 8))
    _plot_ohlc_matplotlib(main_ax, ohlc, title="EURUSD Price Chart")
    _plot_overlay_indicators(main_ax, {"SMA_20": overlay_indicators["SMA_20"]})

    # Add RSI subplot below
    _create_indicator_subplot(
        main_ax,
        "RSI",
        panel_indicators["RSI"],
        height_ratio=0.3,
    )

    plt.savefig("output/plotting/indicators_subplot.png", dpi=100)
    print("[OK] Subplot example saved to: output/plotting/indicators_subplot.png")
    plt.close()


def example_7_custom_colors():
    """Example 7: Custom color sequence for indicators."""
    print("\n" + "=" * 80)
    print("Example 7: Custom Color Sequence")
    print("=" * 80)

    print("Loading GBPUSD data...")
    ohlc, overlay_indicators, _ = get_real_data_with_indicators("GBPUSD")
    if ohlc.empty: return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Plot OHLC chart
    _plot_ohlc_matplotlib(ax, ohlc, title="GBPUSD Price Chart with Custom Colors")

    # Use custom colors for indicators
    custom_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8"]

    # Add only moving averages
    ma_indicators = {
        "SMA_20": overlay_indicators["SMA_20"],
        "SMA_50": overlay_indicators["SMA_50"],
    }
    _plot_overlay_indicators(ax, ma_indicators, color_sequence=custom_colors)

    # Add legend
    ax.legend(loc="upper left", fontsize=9)

    plt.tight_layout()
    plt.savefig("output/plotting/indicators_custom_colors.png", dpi=100)
    print(
        "[OK] Custom colors example saved to: output/plotting/indicators_custom_colors.png"
    )
    plt.close()


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("INDICATOR OVERLAYS - USAGE EXAMPLES")
    print("=" * 80)

    # Create output directory if it doesn't exist
    import os
    os.makedirs("output/plotting", exist_ok=True)

    try:
        example_1_overlay_indicators()
        example_2_panel_indicators()
        example_3_combined_chart()
        example_4_bollinger_bands()
        example_5_indicator_classification()
        example_6_create_subplot()
        example_7_custom_colors()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)
        print("\nKey features demonstrated:")
        print("  * Overlay indicators (SMA, EMA, Bollinger Bands)")
        print("  * Panel indicators (RSI, MACD)")
        print("  * Multi-line indicators (Bollinger Bands, MACD)")
        print("  * Automatic indicator classification")
        print("  * Filled areas for bands")
        print("  * Reference levels for oscillators")
        print("  * Custom color sequences")
        print("  * Helper function for creating subplots")
        print("\nOutput files in: output/plotting/")

    except Exception as e:
        print(f"\n[ERROR] Error in examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
