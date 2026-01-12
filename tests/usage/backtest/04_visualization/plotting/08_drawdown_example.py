"""Example usage of drawdown charts.

This example demonstrates how to plot:
1. Underwater/drawdown plot
2. Drawdown periods bar chart
3. Combined drawdown analysis

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

from apps.plotting.drawdown import (
    _calculate_drawdown,
    _plot_drawdown,
    _plot_drawdown_periods,
)
from apps.utils.data_getters import load_mt5


def get_real_equity_curve(symbol="EURUSD", start_date="2022-01-01", end_date="2023-12-31"):
    """Get real equity curve (Buy & Hold) for testing."""
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        # Normalize close price to start at 10000
        equity = data["close"] / data["close"].iloc[0] * 10000
        return equity
    except Exception as e:
        print(f"Error loading data: {e}")
        # Fallback to random data if load fails
        dates = pd.date_range(start_date, periods=252, freq="D")
        return pd.Series(10000 * (1 + np.random.randn(252) * 0.01).cumprod(), index=dates)


def example_1_basic_drawdown():
    """Example 1: Basic underwater plot."""
    print("=" * 80)
    print("Example 1: Underwater Plot")
    print("=" * 80)

    print("Loading EURUSD data...")
    equity = get_real_equity_curve("EURUSD")

    fig, ax = plt.subplots(figsize=(14, 6))
    _plot_drawdown(ax, equity=equity, backend="matplotlib", title="EURUSD Drawdown (Buy & Hold)")

    plt.tight_layout()
    plt.savefig("output/plotting/drawdown_underwater.png", dpi=100)
    print("[OK] Underwater plot saved to: output/plotting/drawdown_underwater.png")
    plt.close()


def example_2_drawdown_no_recovery():
    """Example 2: Drawdown without recovery highlighting."""
    print("\n" + "=" * 80)
    print("Example 2: Drawdown Without Recovery Highlighting")
    print("=" * 80)

    print("Loading GBPUSD data...")
    equity = get_real_equity_curve("GBPUSD")

    fig, ax = plt.subplots(figsize=(14, 6))
    _plot_drawdown(
        ax,
        equity=equity,
        backend="matplotlib",
        show_recovery=False,
        title="GBPUSD Drawdown (No Recovery Highlighting)",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/drawdown_no_recovery.png", dpi=100)
    print(
        "[OK] Drawdown without recovery saved to: output/plotting/drawdown_no_recovery.png"
    )
    plt.close()


def example_3_drawdown_periods_by_duration():
    """Example 3: Top drawdown periods by duration."""
    print("\n" + "=" * 80)
    print("Example 3: Drawdown Periods by Duration")
    print("=" * 80)

    print("Loading USDJPY data...")
    equity = get_real_equity_curve("USDJPY")

    fig, ax = plt.subplots(figsize=(12, 8))
    _plot_drawdown_periods(ax, equity=equity, top_n=5, sort_by="duration", title="USDJPY Top Drawdowns (Duration)")

    plt.tight_layout()
    plt.savefig("output/plotting/drawdown_periods_duration.png", dpi=100)
    print(
        "[OK] Drawdown periods (duration) saved to: output/plotting/drawdown_periods_duration.png"
    )
    plt.close()


def example_4_drawdown_periods_by_magnitude():
    """Example 4: Top drawdown periods by magnitude."""
    print("\n" + "=" * 80)
    print("Example 4: Drawdown Periods by Magnitude")
    print("=" * 80)

    print("Loading AUDUSD data...")
    equity = get_real_equity_curve("AUDUSD")

    fig, ax = plt.subplots(figsize=(12, 8))
    _plot_drawdown_periods(ax, equity=equity, top_n=5, sort_by="magnitude", title="AUDUSD Top Drawdowns (Magnitude)")

    plt.tight_layout()
    plt.savefig("output/plotting/drawdown_periods_magnitude.png", dpi=100)
    print(
        "[OK] Drawdown periods (magnitude) saved to: output/plotting/drawdown_periods_magnitude.png"
    )
    plt.close()


def example_5_combined_analysis():
    """Example 5: Combined drawdown analysis."""
    print("\n" + "=" * 80)
    print("Example 5: Combined Drawdown Analysis")
    print("=" * 80)

    print("Loading EURUSD data (2020-2023)...")
    equity = get_real_equity_curve("EURUSD", start_date="2020-01-01", end_date="2023-12-31")

    # Create figure with 3 subplots
    fig = plt.figure(figsize=(14, 12))

    # Underwater plot
    ax1 = plt.subplot(3, 1, 1)
    _plot_drawdown(ax1, equity=equity, backend="matplotlib", title="EURUSD Underwater Equity")

    # Top periods by duration
    ax2 = plt.subplot(3, 1, 2)
    _plot_drawdown_periods(
        ax2, equity=equity, top_n=5, sort_by="duration", title="Top 5 by Duration"
    )

    # Top periods by magnitude
    ax3 = plt.subplot(3, 1, 3)
    _plot_drawdown_periods(
        ax3, equity=equity, top_n=5, sort_by="magnitude", title="Top 5 by Magnitude"
    )

    plt.suptitle("EURUSD Drawdown Analysis Dashboard", fontsize=16, y=0.995)
    plt.tight_layout()
    plt.savefig("output/plotting/drawdown_combined.png", dpi=100)
    print("[OK] Combined analysis saved to: output/plotting/drawdown_combined.png")
    plt.close()


def example_6_grayscale():
    """Example 6: Drawdown charts in grayscale."""
    print("\n" + "=" * 80)
    print("Example 6: Grayscale Drawdown Charts")
    print("=" * 80)

    print("Loading EURUSD data...")
    equity = get_real_equity_curve("EURUSD")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # Underwater plot
    _plot_drawdown(
        ax1,
        equity=equity,
        backend="matplotlib",
        color_mode="grayscale",
        title="Underwater Equity (Grayscale)",
    )

    # Drawdown periods
    _plot_drawdown_periods(
        ax2,
        equity=equity,
        top_n=5,
        sort_by="duration",
        color_mode="grayscale",
        title="Top Drawdown Periods (Grayscale)",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/drawdown_grayscale.png", dpi=100)
    print("[OK] Grayscale drawdown saved to: output/plotting/drawdown_grayscale.png")
    plt.close()


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("DRAWDOWN CHARTS - USAGE EXAMPLES")
    print("=" * 80)

    # Create output directory
    import os
    os.makedirs("output/plotting", exist_ok=True)

    try:
        example_1_basic_drawdown()
        example_2_drawdown_no_recovery()
        example_3_drawdown_periods_by_duration()
        example_4_drawdown_periods_by_magnitude()
        example_5_combined_analysis()
        example_6_grayscale()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)
        print("\nKey features demonstrated:")
        print("  * Underwater/drawdown plot with filled area")
        print("  * Recovery period highlighting")
        print("  * Top N drawdown periods by duration")
        print("  * Top N drawdown periods by magnitude")
        print("  * Combined drawdown analysis dashboard")
        print("  * Grayscale mode")
        print("\nOutput files in: output/plotting/")

    except Exception as e:
        print(f"\n[ERROR] Error in examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
