"""Example usage of rolling metrics charts.

This example demonstrates how to plot:
1. Rolling volatility
2. Rolling Sharpe ratio
3. Rolling Sortino ratio
4. Rolling beta (vs benchmark)
5. Rolling returns
6. Combined rolling metrics dashboard

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

from apps.plotting.rolling import (
    _plot_rolling_beta,
    _plot_rolling_returns,
    _plot_rolling_sharpe,
    _plot_rolling_sortino,
    _plot_rolling_volatility,
)
from apps.utils.data_getters import load_mt5


def get_real_returns_data(symbol="EURUSD", benchmark_symbol="GBPUSD", start_date="2022-01-01", end_date="2023-12-31"):
    """Get real returns data for symbol and benchmark.

    Returns:
        Tuple of (strategy_returns, benchmark_returns)
    """
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        benchmark_data = load_mt5(benchmark_symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        
        # Align dates
        common_index = data.index.intersection(benchmark_data.index)
        data = data.loc[common_index]
        benchmark_data = benchmark_data.loc[common_index]
        
        # Calculate returns
        strategy_returns = data["close"].pct_change().fillna(0)
        benchmark_returns = benchmark_data["close"].pct_change().fillna(0)
        
        return strategy_returns, benchmark_returns
        
    except Exception as e:
        print(f"Error loading data: {e}")
        # Fallback to empty series
        dates = pd.date_range(start_date, periods=10)
        return pd.Series(0, index=dates), pd.Series(0, index=dates)


def example_1_rolling_volatility():
    """Example 1: Rolling volatility chart."""
    print("=" * 80)
    print("Example 1: Rolling Volatility")
    print("=" * 80)

    print("Loading EURUSD returns...")
    strategy_returns, _ = get_real_returns_data("EURUSD")
    if strategy_returns.empty: return

    fig, ax = plt.subplots(figsize=(14, 6))
    _plot_rolling_volatility(ax, strategy_returns, window=30, title="EURUSD Rolling Volatility (30-day)")

    plt.tight_layout()
    plt.savefig("output/plotting/rolling_volatility.png", dpi=100)
    print("[OK] Rolling volatility saved to: output/plotting/rolling_volatility.png")
    plt.close()


def example_2_rolling_volatility_with_benchmark():
    """Example 2: Rolling volatility with benchmark comparison."""
    print("\n" + "=" * 80)
    print("Example 2: Rolling Volatility with Benchmark")
    print("=" * 80)

    print("Loading EURUSD vs GBPUSD...")
    strategy_returns, benchmark_returns = get_real_returns_data("EURUSD", "GBPUSD")

    fig, ax = plt.subplots(figsize=(14, 6))
    _plot_rolling_volatility(
        ax,
        strategy_returns,
        benchmark_returns=benchmark_returns,
        window=60,
        title="Rolling Volatility: EURUSD vs GBPUSD",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/rolling_volatility_benchmark.png", dpi=100)
    print(
        "[OK] Rolling volatility with benchmark saved to: output/plotting/rolling_volatility_benchmark.png"
    )
    plt.close()


def example_3_rolling_sharpe():
    """Example 3: Rolling Sharpe ratio."""
    print("\n" + "=" * 80)
    print("Example 3: Rolling Sharpe Ratio")
    print("=" * 80)

    print("Loading USDJPY returns...")
    strategy_returns, _ = get_real_returns_data("USDJPY")

    fig, ax = plt.subplots(figsize=(14, 6))
    _plot_rolling_sharpe(ax, strategy_returns, window=60, title="USDJPY Rolling Sharpe (60-day)")

    plt.tight_layout()
    plt.savefig("output/plotting/rolling_sharpe.png", dpi=100)
    print("[OK] Rolling Sharpe saved to: output/plotting/rolling_sharpe.png")
    plt.close()


def example_4_rolling_sharpe_with_benchmark():
    """Example 4: Rolling Sharpe with benchmark."""
    print("\n" + "=" * 80)
    print("Example 4: Rolling Sharpe with Benchmark")
    print("=" * 80)

    print("Loading AUDUSD vs NZDUSD...")
    strategy_returns, benchmark_returns = get_real_returns_data("AUDUSD", "NZDUSD")

    fig, ax = plt.subplots(figsize=(14, 6))
    _plot_rolling_sharpe(
        ax,
        strategy_returns,
        benchmark_returns=benchmark_returns,
        window=126,
        title="Rolling Sharpe Ratio: AUDUSD vs NZDUSD",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/rolling_sharpe_benchmark.png", dpi=100)
    print(
        "[OK] Rolling Sharpe with benchmark saved to: output/plotting/rolling_sharpe_benchmark.png"
    )
    plt.close()


def example_5_rolling_sortino():
    """Example 5: Rolling Sortino ratio."""
    print("\n" + "=" * 80)
    print("Example 5: Rolling Sortino Ratio")
    print("=" * 80)

    print("Loading GBPUSD returns...")
    strategy_returns, _ = get_real_returns_data("GBPUSD")

    fig, ax = plt.subplots(figsize=(14, 6))
    _plot_rolling_sortino(ax, strategy_returns, window=60, title="GBPUSD Rolling Sortino (60-day)")

    plt.tight_layout()
    plt.savefig("output/plotting/rolling_sortino.png", dpi=100)
    print("[OK] Rolling Sortino saved to: output/plotting/rolling_sortino.png")
    plt.close()


def example_6_rolling_beta():
    """Example 6: Rolling beta vs benchmark."""
    print("\n" + "=" * 80)
    print("Example 6: Rolling Beta")
    print("=" * 80)

    print("Loading EURUSD vs USDCHF...")
    strategy_returns, benchmark_returns = get_real_returns_data("EURUSD", "USDCHF")

    fig, ax = plt.subplots(figsize=(14, 6))
    _plot_rolling_beta(ax, strategy_returns, benchmark_returns, window=60, title="Rolling Beta: EURUSD vs USDCHF")

    plt.tight_layout()
    plt.savefig("output/plotting/rolling_beta.png", dpi=100)
    print("[OK] Rolling beta saved to: output/plotting/rolling_beta.png")
    plt.close()


def example_7_rolling_returns():
    """Example 7: Rolling period returns."""
    print("\n" + "=" * 80)
    print("Example 7: Rolling Returns (Monthly)")
    print("=" * 80)

    print("Loading USDJPY returns...")
    strategy_returns, _ = get_real_returns_data("USDJPY")

    fig, ax = plt.subplots(figsize=(14, 6))
    _plot_rolling_returns(ax, strategy_returns, window=21, period_label="Monthly", title="USDJPY Rolling Monthly Returns")

    plt.tight_layout()
    plt.savefig("output/plotting/rolling_returns.png", dpi=100)
    print("[OK] Rolling returns saved to: output/plotting/rolling_returns.png")
    plt.close()


def example_8_rolling_returns_annualized():
    """Example 8: Annualized rolling returns."""
    print("\n" + "=" * 80)
    print("Example 8: Annualized Rolling Returns")
    print("=" * 80)

    print("Loading AUDUSD returns...")
    strategy_returns, _ = get_real_returns_data("AUDUSD")

    fig, ax = plt.subplots(figsize=(14, 6))
    _plot_rolling_returns(
        ax,
        strategy_returns,
        window=63,
        period_label="Quarterly",
        annualize=True,
        periods_per_year=252,
        title="AUDUSD Annualized Quarterly Rolling Returns",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/rolling_returns_annualized.png", dpi=100)
    print(
        "[OK] Annualized rolling returns saved to: output/plotting/rolling_returns_annualized.png"
    )
    plt.close()


def example_9_rolling_metrics_dashboard():
    """Example 9: Complete rolling metrics dashboard."""
    print("\n" + "=" * 80)
    print("Example 9: Rolling Metrics Dashboard")
    print("=" * 80)

    print("Loading EURUSD vs GBPUSD data...")
    strategy_returns, benchmark_returns = get_real_returns_data("EURUSD", "GBPUSD")

    # Create figure with 6 subplots
    fig = plt.figure(figsize=(16, 14))

    # Rolling volatility (top left)
    ax1 = plt.subplot(3, 2, 1)
    _plot_rolling_volatility(
        ax1,
        strategy_returns,
        benchmark_returns=benchmark_returns,
        window=30,
        title="Rolling Volatility (30-day)",
    )

    # Rolling Sharpe (top right)
    ax2 = plt.subplot(3, 2, 2)
    _plot_rolling_sharpe(
        ax2,
        strategy_returns,
        benchmark_returns=benchmark_returns,
        window=60,
        title="Rolling Sharpe Ratio (60-day)",
    )

    # Rolling Sortino (middle left)
    ax3 = plt.subplot(3, 2, 3)
    _plot_rolling_sortino(
        ax3,
        strategy_returns,
        benchmark_returns=benchmark_returns,
        window=60,
        title="Rolling Sortino Ratio (60-day)",
    )

    # Rolling beta (middle right)
    ax4 = plt.subplot(3, 2, 4)
    _plot_rolling_beta(
        ax4,
        strategy_returns,
        benchmark_returns,
        window=60,
        title="Rolling Beta (60-day)",
    )

    # Rolling returns (bottom left)
    ax5 = plt.subplot(3, 2, 5)
    _plot_rolling_returns(
        ax5,
        strategy_returns,
        benchmark_returns=benchmark_returns,
        window=21,
        period_label="Monthly",
        title="Rolling Monthly Returns",
    )

    # Rolling volatility comparison (bottom right) - different window
    ax6 = plt.subplot(3, 2, 6)
    _plot_rolling_volatility(
        ax6,
        strategy_returns,
        benchmark_returns=benchmark_returns,
        window=126,
        title="Rolling Volatility (126-day)",
    )

    plt.suptitle("EURUSD Rolling Metrics Dashboard", fontsize=16, y=0.995)
    plt.tight_layout()
    plt.savefig("output/plotting/rolling_dashboard.png", dpi=100)
    print(
        "[OK] Rolling metrics dashboard saved to: output/plotting/rolling_dashboard.png"
    )
    plt.close()


def example_10_grayscale_mode():
    """Example 10: Rolling metrics in grayscale."""
    print("\n" + "=" * 80)
    print("Example 10: Grayscale Rolling Metrics")
    print("=" * 80)

    print("Loading USDJPY vs EURUSD...")
    strategy_returns, benchmark_returns = get_real_returns_data("USDJPY", "EURUSD")

    # Create figure with 3 subplots
    fig = plt.figure(figsize=(14, 10))

    # Rolling volatility
    ax1 = plt.subplot(3, 1, 1)
    _plot_rolling_volatility(
        ax1,
        strategy_returns,
        benchmark_returns=benchmark_returns,
        window=30,
        color_mode="grayscale",
        title="Rolling Volatility (Grayscale)",
    )

    # Rolling Sharpe
    ax2 = plt.subplot(3, 1, 2)
    _plot_rolling_sharpe(
        ax2,
        strategy_returns,
        benchmark_returns=benchmark_returns,
        window=60,
        color_mode="grayscale",
        title="Rolling Sharpe Ratio (Grayscale)",
    )

    # Rolling beta
    ax3 = plt.subplot(3, 1, 3)
    _plot_rolling_beta(
        ax3,
        strategy_returns,
        benchmark_returns,
        window=60,
        color_mode="grayscale",
        title="Rolling Beta (Grayscale)",
    )

    plt.tight_layout()
    plt.savefig("output/plotting/rolling_grayscale.png", dpi=100)
    print(
        "[OK] Grayscale rolling metrics saved to: output/plotting/rolling_grayscale.png"
    )
    plt.close()


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("ROLLING METRICS CHARTS - USAGE EXAMPLES")
    print("=" * 80)

    # Create output directory
    import os
    os.makedirs("output/plotting", exist_ok=True)

    try:
        example_1_rolling_volatility()
        example_2_rolling_volatility_with_benchmark()
        example_3_rolling_sharpe()
        example_4_rolling_sharpe_with_benchmark()
        example_5_rolling_sortino()
        example_6_rolling_beta()
        example_7_rolling_returns()
        example_8_rolling_returns_annualized()
        example_9_rolling_metrics_dashboard()
        example_10_grayscale_mode()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)
        print("\nKey features demonstrated:")
        print("  * Rolling volatility with annualization")
        print("  * Rolling Sharpe ratio with reference lines")
        print("  * Rolling Sortino ratio (downside-focused)")
        print("  * Rolling beta vs benchmark")
        print("  * Rolling period returns (monthly, quarterly)")
        print("  * Annualized rolling returns")
        print("  * Complete rolling metrics dashboard")
        print("  * Benchmark comparison throughout")
        print("  * Grayscale mode")
        print("\nOutput files in: output/plotting/")

    except Exception as e:
        print(f"\n[ERROR] Error in examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
