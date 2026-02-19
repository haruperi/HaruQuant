"""Example usage of performance and equity charts.

This example demonstrates how to plot:
1. Equity curve with optional benchmark
2. Cumulative returns chart
3. Per-trade P&L chart with cumulative line
4. Returns distribution histogram
5. Combined performance dashboard

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

from apps.plotting.performance import (
    _plot_cumulative_returns,
    _plot_equity_curve,
    _plot_pl,
    _plot_returns_distribution,
)
from apps.utils.data_getters import load_mt5


def get_real_performance_data(symbol="EURUSD", benchmark_symbol="GBPUSD", start_date="2023-01-01", end_date="2023-12-31"):
    """Get real performance data (Equity, Returns, Trades) from simulation.

    Returns:
        Tuple of (equity, returns, trades, benchmark_equity, benchmark_returns)
    """
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        benchmark_data = load_mt5(benchmark_symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        
        # Align dates
        common_index = data.index.intersection(benchmark_data.index)
        data = data.loc[common_index]
        benchmark_data = benchmark_data.loc[common_index]
        
        dates = data.index
        
        # Simulate Strategy: Simple Moving Average Crossover (Fast=10, Slow=30)
        close = data["close"]
        fast_ma = close.rolling(10).mean()
        slow_ma = close.rolling(30).mean()
        
        # Signal: 1 (Long) when Fast > Slow, 0 otherwise
        signal = (fast_ma > slow_ma).astype(int)
        
        # Calculate Strategy Returns
        # Shift signal by 1 because we trade on next open/close based on signal
        strategy_returns = close.pct_change() * signal.shift(1)
        strategy_returns = strategy_returns.fillna(0)
        
        # Calculate Equity
        initial_capital = 10000
        equity = initial_capital * (1 + strategy_returns).cumprod()
        
        # Calculate Benchmark (Buy & Hold)
        benchmark_returns = benchmark_data["close"].pct_change().fillna(0)
        benchmark_equity = initial_capital * (1 + benchmark_returns).cumprod()
        
        # Generate Trades from Signal
        trades = []
        position = 0
        entry_price = 0
        entry_date = None
        
        for i in range(1, len(data)):
            current_signal = signal.iloc[i-1] # Signal from previous bar
            current_date = dates[i]
            current_price = close.iloc[i]
            
            if position == 0 and current_signal == 1:
                # Open Long
                position = 1
                entry_price = current_price
                entry_date = current_date
            elif position == 1 and current_signal == 0:
                # Close Long
                position = 0
                exit_price = current_price
                pl_pct = (exit_price - entry_price) / entry_price
                pl = initial_capital * pl_pct # Simplified PL
                
                trades.append({
                    "entry_time": entry_date,
                    "exit_time": current_date,
                    "pl": pl,
                    "pl_pct": pl_pct,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "size": initial_capital / entry_price
                })
        
        return (
            equity,
            strategy_returns,
            trades,
            benchmark_equity,
            benchmark_returns,
        )

    except Exception as e:
        print(f"Error loading data: {e}")
        # Fallback to empty/random
        dates = pd.date_range(start_date, periods=100)
        return (
            pd.Series(10000, index=dates),
            pd.Series(0, index=dates),
            [],
            pd.Series(10000, index=dates),
            pd.Series(0, index=dates)
        )


def example_1_equity_curve():
    """Example 1: Basic equity curve."""
    print("=" * 80)
    print("Example 1: Equity Curve")
    print("=" * 80)

    print("Loading EURUSD data...")
    equity, _, _, _, _ = get_real_performance_data("EURUSD")

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot equity curve
    _plot_equity_curve(ax, equity, backend="matplotlib", title="EURUSD Strategy Equity")

    plt.tight_layout()
    plt.savefig("output/plotting/performance_equity.png", dpi=100)
    print("[OK] Equity curve saved to: output/plotting/performance_equity.png")
    plt.close()


def example_2_equity_with_benchmark():
    """Example 2: Equity curve with benchmark comparison."""
    print("\n" + "=" * 80)
    print("Example 2: Equity Curve with Benchmark")
    print("=" * 80)

    print("Loading EURUSD vs GBPUSD...")
    equity, _, _, benchmark_equity, _ = get_real_performance_data("EURUSD", "GBPUSD")

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot equity curve with benchmark
    _plot_equity_curve(
        ax,
        equity,
        benchmark=benchmark_equity,
        backend="matplotlib",
        title="Strategy (EURUSD) vs Benchmark (GBPUSD)",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/performance_equity_benchmark.png", dpi=100)
    print(
        "[OK] Equity with benchmark saved to: output/plotting/performance_equity_benchmark.png"
    )
    plt.close()


def example_3_equity_smoothed():
    """Example 3: Smoothed equity curve."""
    print("\n" + "=" * 80)
    print("Example 3: Smoothed Equity Curve")
    print("=" * 80)

    print("Loading USDJPY data...")
    equity, _, _, _, _ = get_real_performance_data("USDJPY")

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot with smoothing
    _plot_equity_curve(
        ax,
        equity,
        backend="matplotlib",
        smooth=True,
        smooth_window=10,
        title="USDJPY Strategy Equity (10-day Moving Average)",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/performance_equity_smoothed.png", dpi=100)
    print(
        "[OK] Smoothed equity saved to: output/plotting/performance_equity_smoothed.png"
    )
    plt.close()


def example_4_cumulative_returns():
    """Example 4: Cumulative returns chart."""
    print("\n" + "=" * 80)
    print("Example 4: Cumulative Returns")
    print("=" * 80)

    print("Loading AUDUSD data...")
    _, returns, _, _, _ = get_real_performance_data("AUDUSD")

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot cumulative returns
    _plot_cumulative_returns(ax, returns, backend="matplotlib", title="AUDUSD Cumulative Returns")

    plt.tight_layout()
    plt.savefig("output/plotting/performance_cumulative_returns.png", dpi=100)
    print(
        "[OK] Cumulative returns saved to: output/plotting/performance_cumulative_returns.png"
    )
    plt.close()


def example_5_cumulative_returns_with_benchmark():
    """Example 5: Cumulative returns with benchmark."""
    print("\n" + "=" * 80)
    print("Example 5: Cumulative Returns with Benchmark")
    print("=" * 80)

    print("Loading EURUSD vs USDJPY...")
    _, returns, _, _, benchmark_returns = get_real_performance_data("EURUSD", "USDJPY")

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot cumulative returns with benchmark
    _plot_cumulative_returns(
        ax,
        returns,
        benchmark_returns=benchmark_returns,
        backend="matplotlib",
        title="Cumulative Returns: EURUSD vs USDJPY",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/performance_cumulative_benchmark.png", dpi=100)
    print(
        "[OK] Cumulative with benchmark saved to: output/plotting/performance_cumulative_benchmark.png"
    )
    plt.close()


def example_6_pl_chart():
    """Example 6: Per-trade P&L chart."""
    print("\n" + "=" * 80)
    print("Example 6: Per-Trade P&L Chart")
    print("=" * 80)

    print("Loading GBPUSD trades...")
    _, _, trades, _, _ = get_real_performance_data("GBPUSD")

    if not trades:
        print("No trades generated for GBPUSD example.")
        return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot P&L
    _plot_pl(ax, trades, backend="matplotlib", title="GBPUSD Trade P&L")

    plt.tight_layout()
    plt.savefig("output/plotting/performance_pl.png", dpi=100)
    print("[OK] P&L chart saved to: output/plotting/performance_pl.png")
    plt.close()


def example_7_pl_by_trade_number():
    """Example 7: P&L by trade number."""
    print("\n" + "=" * 80)
    print("Example 7: P&L by Trade Number")
    print("=" * 80)

    print("Loading EURUSD trades...")
    _, _, trades, _, _ = get_real_performance_data("EURUSD")

    if not trades:
        print("No trades generated.")
        return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot P&L by trade number
    _plot_pl(
        ax,
        trades,
        backend="matplotlib",
        by_date=False,
        title="EURUSD P&L by Trade Sequence",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/performance_pl_by_number.png", dpi=100)
    print(
        "[OK] P&L by trade number saved to: output/plotting/performance_pl_by_number.png"
    )
    plt.close()


def example_8_pl_no_cumulative():
    """Example 8: P&L without cumulative line."""
    print("\n" + "=" * 80)
    print("Example 8: P&L Without Cumulative Line")
    print("=" * 80)

    print("Loading USDJPY trades...")
    _, _, trades, _, _ = get_real_performance_data("USDJPY")

    if not trades:
        print("No trades generated.")
        return

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot P&L without cumulative
    _plot_pl(
        ax,
        trades,
        backend="matplotlib",
        show_cumulative=False,
        title="USDJPY Trade P&L (No Cumulative)",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/performance_pl_no_cumulative.png", dpi=100)
    print(
        "[OK] P&L without cumulative saved to: output/plotting/performance_pl_no_cumulative.png"
    )
    plt.close()


def example_9_returns_distribution():
    """Example 9: Returns distribution."""
    print("\n" + "=" * 80)
    print("Example 9: Returns Distribution")
    print("=" * 80)

    print("Loading AUDUSD returns...")
    _, returns, _, _, _ = get_real_performance_data("AUDUSD")

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot distribution
    _plot_returns_distribution(ax, returns, title="AUDUSD Returns Distribution")

    plt.tight_layout()
    plt.savefig("output/plotting/performance_distribution.png", dpi=100)
    print(
        "[OK] Returns distribution saved to: output/plotting/performance_distribution.png"
    )
    plt.close()


def example_10_returns_distribution_custom():
    """Example 10: Returns distribution with custom settings."""
    print("\n" + "=" * 80)
    print("Example 10: Custom Returns Distribution")
    print("=" * 80)

    print("Loading EURUSD returns...")
    _, returns, _, _, _ = get_real_performance_data("EURUSD")

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot distribution with custom settings
    _plot_returns_distribution(
        ax,
        returns,
        bins=30,
        show_normal=True,
        show_stats=True,
        title="EURUSD Daily Returns Distribution (Custom)",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/performance_distribution_custom.png", dpi=100)
    print(
        "[OK] Custom distribution saved to: output/plotting/performance_distribution_custom.png"
    )
    plt.close()


def example_11_performance_dashboard():
    """Example 11: Complete performance dashboard."""
    print("\n" + "=" * 80)
    print("Example 11: Performance Dashboard")
    print("=" * 80)

    print("Loading EURUSD vs GBPUSD data...")
    equity, returns, trades, benchmark_equity, benchmark_returns = (
        get_real_performance_data("EURUSD", "GBPUSD")
    )

    # Create figure with 4 subplots
    fig = plt.figure(figsize=(16, 12))

    # Equity curve (top left)
    ax1 = plt.subplot(2, 2, 1)
    _plot_equity_curve(
        ax1,
        equity,
        benchmark=benchmark_equity,
        backend="matplotlib",
        title="Equity Curve",
    )

    # Cumulative returns (top right)
    ax2 = plt.subplot(2, 2, 2)
    _plot_cumulative_returns(
        ax2,
        returns,
        benchmark_returns=benchmark_returns,
        backend="matplotlib",
        title="Cumulative Returns",
    )

    # P&L chart (bottom left)
    ax3 = plt.subplot(2, 2, 3)
    if trades:
        _plot_pl(ax3, trades, backend="matplotlib", title="Trade P&L")
    else:
        ax3.text(0.5, 0.5, "No Trades", ha="center", va="center")

    # Returns distribution (bottom right)
    ax4 = plt.subplot(2, 2, 4)
    _plot_returns_distribution(ax4, returns, title="Returns Distribution")

    plt.suptitle("EURUSD Performance Dashboard", fontsize=16, y=0.995)
    plt.tight_layout()
    plt.savefig("output/plotting/performance_dashboard.png", dpi=100)
    print(
        "[OK] Performance dashboard saved to: output/plotting/performance_dashboard.png"
    )
    plt.close()


def example_12_grayscale_mode():
    """Example 12: Performance charts in grayscale."""
    print("\n" + "=" * 80)
    print("Example 12: Grayscale Performance Charts")
    print("=" * 80)

    print("Loading USDJPY data...")
    equity, returns, trades, _, _ = get_real_performance_data("USDJPY")

    # Create figure with 3 subplots
    fig = plt.figure(figsize=(14, 10))

    # Equity curve
    ax1 = plt.subplot(3, 1, 1)
    _plot_equity_curve(
        ax1,
        equity,
        backend="matplotlib",
        color_mode="grayscale",
        title="Equity Curve (Grayscale)",
    )

    # P&L chart
    ax2 = plt.subplot(3, 1, 2)
    if trades:
        _plot_pl(
            ax2,
            trades,
            backend="matplotlib",
            color_mode="grayscale",
            title="Trade P&L (Grayscale)",
        )
    else:
        ax2.text(0.5, 0.5, "No Trades", ha="center", va="center")

    # Returns distribution
    ax3 = plt.subplot(3, 1, 3)
    _plot_returns_distribution(
        ax3, returns, color_mode="grayscale", title="Returns Distribution (Grayscale)"
    )

    plt.tight_layout()
    plt.savefig("output/plotting/performance_grayscale.png", dpi=100)
    print(
        "[OK] Grayscale performance saved to: output/plotting/performance_grayscale.png"
    )
    plt.close()


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("PERFORMANCE & EQUITY CHARTS - USAGE EXAMPLES")
    print("=" * 80)

    # Create output directory if it doesn't exist
    import os
    os.makedirs("output/plotting", exist_ok=True)

    try:
        example_1_equity_curve()
        example_2_equity_with_benchmark()
        example_3_equity_smoothed()
        example_4_cumulative_returns()
        example_5_cumulative_returns_with_benchmark()
        example_6_pl_chart()
        example_7_pl_by_trade_number()
        example_8_pl_no_cumulative()
        example_9_returns_distribution()
        example_10_returns_distribution_custom()
        example_11_performance_dashboard()
        example_12_grayscale_mode()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)
        print("\nKey features demonstrated:")
        print("  * Equity curve with optional benchmark")
        print("  * Smoothed equity curves")
        print("  * Cumulative returns (percentage-based)")
        print("  * Per-trade P&L bars with cumulative line")
        print("  * P&L by trade number or date")
        print("  * Returns distribution with normal overlay")
        print("  * Complete performance dashboard")
        print("  * Grayscale mode for all charts")
        print("\nOutput files in: output/plotting/")

    except Exception as e:
        print(f"\n[ERROR] Error in examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
