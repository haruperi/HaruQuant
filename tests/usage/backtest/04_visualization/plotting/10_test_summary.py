"""Test script for performance summary plotting functions.

This script tests the three main functions from the summary module:
1. plot_snapshot() - Comprehensive tearsheet summary
2. _plot_yearly_returns() - Annual returns bar chart
3. _plot_daily_returns() - Daily returns with volatility bands

Updated to include real market data tests.
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

from apps.plotting.summary import (
    _plot_daily_returns,
    _plot_yearly_returns,
    plot_snapshot,
)
from apps.utils.data_getters import load_mt5


def generate_sample_returns(
    start_date: str = "2020-01-01",
    end_date: str = "2023-12-31",
    annual_return: float = 0.12,
    annual_volatility: float = 0.15,
    seed: int = 42,
) -> pd.Series:
    """Generate sample daily returns for testing.

    Args:
        start_date: Start date for returns
        end_date: End date for returns
        annual_return: Expected annual return (e.g., 0.12 = 12%)
        annual_volatility: Annual volatility (e.g., 0.15 = 15%)
        seed: Random seed for reproducibility

    Returns:
        Series of daily returns
    """
    np.random.seed(seed)

    # Create date range (business days)
    dates = pd.bdate_range(start=start_date, end=end_date)

    # Convert annual parameters to daily
    daily_return = annual_return / 252
    daily_volatility = annual_volatility / np.sqrt(252)

    # Generate random returns
    returns = np.random.normal(daily_return, daily_volatility, len(dates))

    # Add some autocorrelation for realism
    for i in range(1, len(returns)):
        returns[i] += 0.1 * returns[i - 1]

    return pd.Series(returns, index=dates, name="returns")


def generate_sample_metrics() -> dict:
    """Generate sample performance metrics for testing.

    Returns:
        Dictionary of sample metrics
    """
    return {
        "Total Return": 0.485,
        "Annual Return": 0.121,
        "Sharpe Ratio": 1.52,
        "Sortino Ratio": 2.18,
        "Max Drawdown": -0.156,
        "Win Rate": 0.58,
        "Profit Factor": 1.85,
        "Total Trades": 247,
    }


def get_real_returns(symbol="EURUSD", start_date="2020-01-01", end_date="2023-12-31"):
    """Get real returns data."""
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        returns = data["close"].pct_change().dropna()
        return returns
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.Series()


def test_plot_snapshot():
    """Test the plot_snapshot() function."""
    print("Testing plot_snapshot()...")

    # Generate sample data
    returns = generate_sample_returns()
    benchmark_returns = generate_sample_returns(annual_return=0.08, seed=123)
    metrics = generate_sample_metrics()

    # Create output directory
    output_dir = Path("output/plotting")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Test 3x2 layout (default)
    print("  - Testing 3x2 layout...")
    fig1 = plot_snapshot(
        returns=returns,
        metrics=metrics,
        benchmark_returns=benchmark_returns,
        layout="3x2",
        color_mode="color",
        title="Strategy Performance Snapshot (3x2)",
        show=False,
    )

    fig1.savefig(output_dir / "test_snapshot_3x2.png", dpi=150, bbox_inches="tight")
    print(f"     Saved to {output_dir / 'test_snapshot_3x2.png'}")
    plt.close(fig1)

    # Test 2x2 layout
    print("  - Testing 2x2 layout...")
    fig2 = plot_snapshot(
        returns=returns,
        metrics=metrics,
        layout="2x2",
        color_mode="color",
        title="Strategy Performance Snapshot (2x2)",
        show=False,
    )
    fig2.savefig(output_dir / "test_snapshot_2x2.png", dpi=150, bbox_inches="tight")
    print(f"     Saved to {output_dir / 'test_snapshot_2x2.png'}")
    plt.close(fig2)

    # Test 2x3 layout
    print("  - Testing 2x3 layout...")
    fig3 = plot_snapshot(
        returns=returns,
        metrics=metrics,
        benchmark_returns=benchmark_returns,
        layout="2x3",
        color_mode="color",
        title="Strategy Performance Snapshot (2x3)",
        show=False,
    )
    fig3.savefig(output_dir / "test_snapshot_2x3.png", dpi=150, bbox_inches="tight")
    print(f"     Saved to {output_dir / 'test_snapshot_2x3.png'}")
    plt.close(fig3)

    # Test grayscale mode
    print("  - Testing grayscale mode...")
    fig4 = plot_snapshot(
        returns=returns,
        metrics=metrics,
        layout="3x2",
        color_mode="grayscale",
        title="Strategy Performance Snapshot (Grayscale)",
        show=False,
    )
    fig4.savefig(
        output_dir / "test_snapshot_grayscale.png", dpi=150, bbox_inches="tight"
    )
    print(f"     Saved to {output_dir / 'test_snapshot_grayscale.png'}")
    plt.close(fig4)

    print(" plot_snapshot() tests completed successfully!\n")


def test_plot_yearly_returns():
    """Test the _plot_yearly_returns() function."""
    print("Testing _plot_yearly_returns()...")

    # Generate sample data
    returns = generate_sample_returns()
    benchmark_returns = generate_sample_returns(annual_return=0.08, seed=123)

    output_dir = Path("output/plotting")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Test with benchmark
    print("  - Testing with benchmark comparison...")
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    _plot_yearly_returns(
        ax1,
        returns,
        benchmark_returns=benchmark_returns,
        color_mode="color",
        show_values=True,
        show_average=True,
    )
    ax1.set_title("Yearly Returns Comparison", fontsize=14, fontweight="bold")
    fig1.tight_layout()
    fig1.savefig(
        output_dir / "test_yearly_returns_benchmark.png", dpi=150, bbox_inches="tight"
    )
    print(f"     Saved to {output_dir / 'test_yearly_returns_benchmark.png'}")
    plt.close(fig1)

    # Test without benchmark
    print("  - Testing without benchmark...")
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    _plot_yearly_returns(
        ax2,
        returns,
        benchmark_returns=None,
        color_mode="color",
        show_values=True,
        show_average=True,
    )
    ax2.set_title("Yearly Returns (Strategy Only)", fontsize=14, fontweight="bold")
    fig2.tight_layout()
    fig2.savefig(
        output_dir / "test_yearly_returns_solo.png", dpi=150, bbox_inches="tight"
    )
    print(f"     Saved to {output_dir / 'test_yearly_returns_solo.png'}")
    plt.close(fig2)

    # Test grayscale mode
    print("  - Testing grayscale mode...")
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    _plot_yearly_returns(
        ax3,
        returns,
        benchmark_returns=benchmark_returns,
        color_mode="grayscale",
        show_values=True,
        show_average=True,
    )
    ax3.set_title(
        "Yearly Returns Comparison (Grayscale)", fontsize=14, fontweight="bold"
    )
    fig3.tight_layout()
    fig3.savefig(
        output_dir / "test_yearly_returns_grayscale.png", dpi=150, bbox_inches="tight"
    )
    print(f"     Saved to {output_dir / 'test_yearly_returns_grayscale.png'}")
    plt.close(fig3)

    print(" _plot_yearly_returns() tests completed successfully!\n")


def test_plot_daily_returns():
    """Test the _plot_daily_returns() function."""
    print("Testing _plot_daily_returns()...")

    # Generate sample data
    returns = generate_sample_returns()

    output_dir = Path("output/plotting")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Test bar plot with bands
    print("  - Testing bar plot with volatility bands...")
    fig1, ax1 = plt.subplots(figsize=(14, 6))
    _plot_daily_returns(
        ax1,
        returns,
        color_mode="color",
        plot_type="bar",
        smooth=False,
        show_bands=True,
        num_std=2.0,
    )
    ax1.set_title("Daily Returns with 2 Bands", fontsize=14, fontweight="bold")
    fig1.tight_layout()
    fig1.savefig(
        output_dir / "test_daily_returns_bar_bands.png", dpi=150, bbox_inches="tight"
    )
    print(f"     Saved to {output_dir / 'test_daily_returns_bar_bands.png'}")
    plt.close(fig1)

    # Test scatter plot with smoothing
    print("  - Testing scatter plot with smoothing...")
    fig2, ax2 = plt.subplots(figsize=(14, 6))
    _plot_daily_returns(
        ax2,
        returns,
        color_mode="color",
        plot_type="scatter",
        smooth=True,
        smooth_window=20,
        show_bands=True,
        num_std=2.0,
    )
    ax2.set_title(
        "Daily Returns (Scatter) with 20-day MA", fontsize=14, fontweight="bold"
    )
    fig2.tight_layout()
    fig2.savefig(
        output_dir / "test_daily_returns_scatter_smooth.png",
        dpi=150,
        bbox_inches="tight",
    )
    print(f"     Saved to {output_dir / 'test_daily_returns_scatter_smooth.png'}")
    plt.close(fig2)

    # Test bar plot without bands
    print("  - Testing bar plot without bands...")
    fig3, ax3 = plt.subplots(figsize=(14, 6))
    _plot_daily_returns(
        ax3,
        returns,
        color_mode="color",
        plot_type="bar",
        smooth=False,
        show_bands=False,
    )
    ax3.set_title("Daily Returns (Simple)", fontsize=14, fontweight="bold")
    fig3.tight_layout()
    fig3.savefig(
        output_dir / "test_daily_returns_simple.png", dpi=150, bbox_inches="tight"
    )
    print(f"     Saved to {output_dir / 'test_daily_returns_simple.png'}")
    plt.close(fig3)

    # Test grayscale mode
    print("  - Testing grayscale mode...")
    fig4, ax4 = plt.subplots(figsize=(14, 6))
    _plot_daily_returns(
        ax4,
        returns,
        color_mode="grayscale",
        plot_type="bar",
        smooth=True,
        smooth_window=20,
        show_bands=True,
        num_std=2.0,
    )
    ax4.set_title(
        "Daily Returns (Grayscale) with Bands", fontsize=14, fontweight="bold"
    )
    fig4.tight_layout()
    fig4.savefig(
        output_dir / "test_daily_returns_grayscale.png", dpi=150, bbox_inches="tight"
    )
    print(f"     Saved to {output_dir / 'test_daily_returns_grayscale.png'}")
    plt.close(fig4)

    print(" _plot_daily_returns() tests completed successfully!\n")


def test_real_data_summary():
    """Test using real market data."""
    print("Testing with Real Market Data (EURUSD)...")

    returns = get_real_returns("EURUSD")
    if returns.empty:
        print("  [SKIPPED] Could not load EURUSD data")
        return

    benchmark_returns = get_real_returns("GBPUSD")
    
    # Calculate some basic metrics for the real data
    total_return = (1 + returns).prod() - 1
    annual_return = returns.mean() * 252
    volatility = returns.std() * np.sqrt(252)
    sharpe = annual_return / volatility if volatility > 0 else 0
    
    metrics = {
        "Total Return": total_return,
        "Annual Return": annual_return,
        "Volatility": volatility,
        "Sharpe Ratio": sharpe,
        "Max Drawdown": ((1 + returns).cumprod() / (1 + returns).cumprod().cummax() - 1).min(),
    }

    output_dir = Path("output/plotting")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Plot Snapshot
    print("  - Plotting snapshot...")
    fig = plot_snapshot(
        returns=returns,
        metrics=metrics,
        benchmark_returns=benchmark_returns if not benchmark_returns.empty else None,
        layout="3x2",
        title="EURUSD Performance Snapshot",
        show=False,
    )
    fig.savefig(output_dir / "test_real_data_snapshot.png", dpi=150, bbox_inches="tight")
    print(f"     Saved to {output_dir / 'test_real_data_snapshot.png'}")
    plt.close(fig)
    
    print(" Real data tests completed successfully!\n")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Performance Summary Plotting Tests")
    print("=" * 70)
    print()

    try:
        # Test each function
        test_plot_snapshot()
        test_plot_yearly_returns()
        test_plot_daily_returns()
        test_real_data_summary()

        print("=" * 70)
        print("All tests completed successfully! ")
        print("=" * 70)
        print()
        print("Output files saved to:")
        output_dir = Path("output/plotting")
        print(f"  {output_dir.absolute()}")

    except Exception as e:
        print(f"\n Error during testing: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
