"""Example usage of trade analysis plotting functions.

This example demonstrates how to use the trade analysis plotting functions to
visualize trading patterns, position sizing, and win/loss streaks.

Updated to include real market data examples.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from apps.plotting.trades import (
    _plot_trade_durations,
    _plot_trade_scatter,
    _plot_trade_sizes,
    _plot_win_loss_streaks,
)
from apps.logger import logger
from apps.utils.data_getters import load_mt5

# Configure output directory
OUTPUT_DIR = os.path.join("output", "plotting", "trades")
os.makedirs(OUTPUT_DIR, exist_ok=True)

logger.info("Starting trade analysis plotting examples")


def generate_sample_trades(n_trades: int = 50, seed: int = 42) -> list:
    """Generate realistic sample trades for demonstration.

    Args:
        n_trades: Number of trades to generate
        seed: Random seed for reproducibility

    Returns:
        List of trade dictionaries
    """
    np.random.seed(seed)

    trades = []
    current_bar = 0
    start_date = datetime(2024, 1, 1)

    for i in range(n_trades):
        # Random entry
        entry_bar = current_bar
        entry_time = start_date + timedelta(hours=current_bar)

        # Random duration (1 to 50 bars)
        duration = np.random.randint(1, 51)
        exit_bar = entry_bar + duration
        exit_time = entry_time + timedelta(hours=duration)

        # Random size (0.5 to 5.0, can be negative for short)
        size = np.random.uniform(0.5, 5.0) * np.random.choice([1, -1], p=[0.6, 0.4])

        # Random P&L with some correlation to duration
        # Longer trades tend to have higher variance
        base_return = np.random.normal(0.01, 0.03)
        duration_factor = 1 + (duration / 100)
        pl_pct = base_return * duration_factor

        # Calculate absolute P&L (assume entry price around 100)
        entry_price = 100
        pl = entry_price * abs(size) * pl_pct

        trade = {
            "entry_bar": entry_bar,
            "exit_bar": exit_bar,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "size": size,
            "pl": pl,
            "pl_pct": pl_pct,
        }

        trades.append(trade)

        # Advance to next potential entry
        current_bar = exit_bar + np.random.randint(1, 10)

    logger.success(f"Generated {n_trades} sample trades")
    return trades


def get_real_trades(symbol="EURUSD", start_date="2023-01-01", end_date="2023-12-31"):
    """Generate trades based on real price data (Simple MA Crossover)."""
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        
        # Simple Strategy: MA Crossover
        close = data["close"]
        fast_ma = close.rolling(10).mean()
        slow_ma = close.rolling(30).mean()
        
        signal = (fast_ma > slow_ma).astype(int)
        dates = data.index
        
        trades = []
        position = 0
        entry_price = 0
        entry_date = None
        entry_idx = 0
        
        for i in range(1, len(data)):
            current_signal = signal.iloc[i-1]
            current_date = dates[i]
            current_price = close.iloc[i]
            
            if position == 0 and current_signal == 1:
                # Open Long
                position = 1
                entry_price = current_price
                entry_date = current_date
                entry_idx = i
            elif position == 1 and current_signal == 0:
                # Close Long
                position = 0
                exit_price = current_price
                pl_pct = (exit_price - entry_price) / entry_price
                size = 10000 # Fixed size
                pl = size * pl_pct
                
                trades.append({
                    "entry_time": entry_date,
                    "exit_time": current_date,
                    "entry_bar": entry_idx,
                    "exit_bar": i,
                    "size": size,
                    "pl": pl,
                    "pl_pct": pl_pct,
                    "entry_price": entry_price,
                    "exit_price": exit_price
                })
                
        return trades
        
    except Exception as e:
        logger.error(f"Error generating real trades: {e}")
        return []


def example_trade_durations():
    """Example of trade duration distribution plot."""
    logger.info("Creating trade duration distribution example")

    trades = generate_sample_trades(100)

    # Create figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Trade Duration Analysis Examples", fontsize=16, fontweight="bold", y=0.995
    )

    # 1. Basic duration histogram
    _plot_trade_durations(
        trades, separate_by_outcome=False, show_stats=False, ax=axes[0, 0]
    )
    axes[0, 0].set_title("All Trades Combined", fontsize=12, fontweight="bold")

    # 2. Separated by outcome
    _plot_trade_durations(
        trades, separate_by_outcome=True, show_stats=False, ax=axes[0, 1]
    )
    axes[0, 1].set_title("Wins vs Losses", fontsize=12, fontweight="bold")

    # 3. With statistics
    _plot_trade_durations(
        trades, separate_by_outcome=True, show_stats=True, ax=axes[1, 0]
    )
    axes[1, 0].set_title("With Mean & Median", fontsize=12, fontweight="bold")

    # 4. Grayscale mode
    _plot_trade_durations(
        trades,
        separate_by_outcome=True,
        show_stats=True,
        ax=axes[1, 1],
        color_mode="grayscale",
    )
    axes[1, 1].set_title("Grayscale Mode", fontsize=12, fontweight="bold")

    plt.tight_layout()

    # Save figure
    output_path = os.path.join(OUTPUT_DIR, "trade_durations.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.success(f"Saved trade duration plot to {output_path}")
    plt.close()


def example_trade_sizes():
    """Example of trade size distribution plot."""
    logger.info("Creating trade size distribution example")

    trades = generate_sample_trades(100)

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Position Size Analysis Examples", fontsize=16, fontweight="bold", y=0.995
    )

    # 1. All trades combined
    _plot_trade_sizes(trades, separate_by_direction=False, ax=axes[0, 0])
    axes[0, 0].set_title("All Positions", fontsize=12, fontweight="bold")

    # 2. Separated by direction
    _plot_trade_sizes(trades, separate_by_direction=True, ax=axes[0, 1])
    axes[0, 1].set_title("Long vs Short", fontsize=12, fontweight="bold")

    # 3. More bins
    _plot_trade_sizes(trades, separate_by_direction=True, bins=40, ax=axes[1, 0])
    axes[1, 0].set_title("Finer Resolution (40 bins)", fontsize=12, fontweight="bold")

    # 4. Grayscale
    _plot_trade_sizes(
        trades, separate_by_direction=True, ax=axes[1, 1], color_mode="grayscale"
    )
    axes[1, 1].set_title("Grayscale Mode", fontsize=12, fontweight="bold")

    plt.tight_layout()

    # Save figure
    output_path = os.path.join(OUTPUT_DIR, "trade_sizes.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.success(f"Saved trade size plot to {output_path}")
    plt.close()


def example_trade_scatter():
    """Example of trade P&L vs duration scatter plot."""
    logger.info("Creating trade scatter plot example")

    trades = generate_sample_trades(150)

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle(
        "Trade P&L vs Duration Analysis", fontsize=16, fontweight="bold", y=0.995
    )

    # 1. Basic scatter
    _plot_trade_scatter(
        trades, size_by_position=False, show_quadrants=False, ax=axes[0, 0]
    )
    axes[0, 0].set_title("Basic Scatter", fontsize=12, fontweight="bold")

    # 2. With quadrants
    _plot_trade_scatter(
        trades, size_by_position=False, show_quadrants=True, ax=axes[0, 1]
    )
    axes[0, 1].set_title("With Quadrant Analysis", fontsize=12, fontweight="bold")

    # 3. Sized by position
    _plot_trade_scatter(
        trades, size_by_position=True, show_quadrants=True, ax=axes[1, 0]
    )
    axes[1, 0].set_title("Marker Size = Position Size", fontsize=12, fontweight="bold")

    # 4. Grayscale
    _plot_trade_scatter(
        trades,
        size_by_position=True,
        show_quadrants=True,
        ax=axes[1, 1],
        color_mode="grayscale",
    )
    axes[1, 1].set_title("Grayscale Mode", fontsize=12, fontweight="bold")

    plt.tight_layout()

    # Save figure
    output_path = os.path.join(OUTPUT_DIR, "trade_scatter.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.success(f"Saved trade scatter plot to {output_path}")
    plt.close()


def example_win_loss_streaks():
    """Example of win/loss streak visualization."""
    logger.info("Creating win/loss streaks example")

    # Create trades with interesting streak patterns
    np.random.seed(42)
    n_trades = 50

    trades = []
    current_time = datetime(2024, 1, 1)

    for i in range(n_trades):
        # Create streaks by biasing random outcomes
        if i < 10:  # Initial winning streak
            pl = abs(np.random.normal(100, 30))
        elif i < 15:  # Short losing streak
            pl = -abs(np.random.normal(50, 20))
        elif i < 25:  # Mixed period
            pl = np.random.normal(20, 60)
        elif i < 30:  # Another losing streak
            pl = -abs(np.random.normal(40, 15))
        else:  # Final winning streak
            pl = abs(np.random.normal(80, 25))

        trade = {"pl": pl, "exit_time": current_time.strftime("%Y-%m-%d %H:%M")}

        trades.append(trade)
        current_time += timedelta(hours=6)

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Win/Loss Streak Analysis Examples", fontsize=16, fontweight="bold", y=0.995
    )

    # 1. Basic streaks
    _plot_win_loss_streaks(trades, highlight_longest=False, ax=axes[0, 0])
    axes[0, 0].set_title("All Streaks", fontsize=12, fontweight="bold")

    # 2. With highlighting
    _plot_win_loss_streaks(trades, highlight_longest=True, ax=axes[0, 1])
    axes[0, 1].set_title("Longest Streaks Highlighted", fontsize=12, fontweight="bold")

    # Generate different pattern for bottom plots
    trades2 = []
    current_time = datetime(2024, 1, 1)
    for i in range(40):
        # Alternating with some randomness
        if i % 3 == 0:
            pl = abs(np.random.normal(100, 20))
        else:
            pl = -abs(np.random.normal(60, 15))

        trade = {"pl": pl, "exit_time": current_time.strftime("%Y-%m-%d %H:%M")}
        trades2.append(trade)
        current_time += timedelta(hours=4)

    # 3. Alternating pattern
    _plot_win_loss_streaks(trades2, highlight_longest=True, ax=axes[1, 0])
    axes[1, 0].set_title("More Volatile Pattern", fontsize=12, fontweight="bold")

    # 4. Grayscale
    _plot_win_loss_streaks(
        trades, highlight_longest=True, ax=axes[1, 1], color_mode="grayscale"
    )
    axes[1, 1].set_title("Grayscale Mode", fontsize=12, fontweight="bold")

    plt.tight_layout()

    # Save figure
    output_path = os.path.join(OUTPUT_DIR, "win_loss_streaks.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.success(f"Saved win/loss streaks plot to {output_path}")
    plt.close()


def example_combined_analysis():
    """Example showing all trade analysis plots together."""
    logger.info("Creating combined trade analysis dashboard")

    trades = generate_sample_trades(200)

    # Create comprehensive figure
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    fig.suptitle(
        "Comprehensive Trade Analysis Dashboard",
        fontsize=18,
        fontweight="bold",
        y=0.995,
    )

    # 1. Trade durations (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    _plot_trade_durations(trades, separate_by_outcome=True, show_stats=True, ax=ax1)
    ax1.set_title("Duration Distribution", fontsize=13, fontweight="bold")

    # 2. Trade sizes (top right)
    ax2 = fig.add_subplot(gs[0, 1])
    _plot_trade_sizes(trades, separate_by_direction=True, ax=ax2)
    ax2.set_title("Position Size Distribution", fontsize=13, fontweight="bold")

    # 3. Trade scatter (middle, spanning both columns)
    ax3 = fig.add_subplot(gs[1, :])
    _plot_trade_scatter(trades, size_by_position=True, show_quadrants=True, ax=ax3)
    ax3.set_title("P&L vs Duration Analysis", fontsize=13, fontweight="bold")

    # 4. Win/loss streaks (bottom, spanning both columns)
    ax4 = fig.add_subplot(gs[2, :])
    _plot_win_loss_streaks(trades, highlight_longest=True, ax=ax4)
    ax4.set_title("Win/Loss Streak Patterns", fontsize=13, fontweight="bold")

    # Save figure
    output_path = os.path.join(OUTPUT_DIR, "combined_analysis.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.success(f"Saved combined analysis to {output_path}")
    plt.close()


def example_real_trades_analysis():
    """Example using real trades from EURUSD strategy."""
    logger.info("Creating real trades analysis dashboard (EURUSD)")
    
    trades = get_real_trades("EURUSD")
    if not trades:
        logger.warning("No real trades generated, skipping real trades analysis")
        return

    # Create comprehensive figure
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    fig.suptitle(
        "EURUSD Strategy Trade Analysis",
        fontsize=18,
        fontweight="bold",
        y=0.995,
    )

    # 1. Trade durations
    ax1 = fig.add_subplot(gs[0, 0])
    _plot_trade_durations(trades, separate_by_outcome=True, show_stats=True, ax=ax1)
    ax1.set_title("Duration Distribution", fontsize=13, fontweight="bold")

    # 2. Trade sizes
    ax2 = fig.add_subplot(gs[0, 1])
    _plot_trade_sizes(trades, separate_by_direction=True, ax=ax2)
    ax2.set_title("Position Size Distribution", fontsize=13, fontweight="bold")

    # 3. Trade scatter
    ax3 = fig.add_subplot(gs[1, :])
    _plot_trade_scatter(trades, size_by_position=True, show_quadrants=True, ax=ax3)
    ax3.set_title("P&L vs Duration Analysis", fontsize=13, fontweight="bold")

    # 4. Win/loss streaks
    ax4 = fig.add_subplot(gs[2, :])
    _plot_win_loss_streaks(trades, highlight_longest=True, ax=ax4)
    ax4.set_title("Win/Loss Streak Patterns", fontsize=13, fontweight="bold")

    # Save figure
    output_path = os.path.join(OUTPUT_DIR, "real_trades_analysis.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    logger.success(f"Saved real trades analysis to {output_path}")
    plt.close()


def main():
    """Run all examples."""
    logger.info("=" * 60)
    logger.info("Trade Analysis Plotting Examples")
    logger.info("=" * 60)

    # Run individual examples
    example_trade_durations()
    example_trade_sizes()
    example_trade_scatter()
    example_win_loss_streaks()

    # Run combined example
    example_combined_analysis()
    
    # Run real data example
    example_real_trades_analysis()

    logger.success("All trade analysis plotting examples completed!")
    logger.info(f"Output saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
