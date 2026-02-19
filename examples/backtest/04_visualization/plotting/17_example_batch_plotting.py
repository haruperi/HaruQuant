"""Example demonstrating batch plot generation and HTML report creation.

This example shows how to use the plot_all() function and create_html_report()
to generate comprehensive visualizations and reports from backtest results.

Updated to use real market data.
"""

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path (robust)
# Resolve the file path and use parents[5] so this works regardless of cwd
try:
    project_root = Path(__file__).resolve().parents[5]
except Exception:
    # Fallback: use current working directory
    project_root = Path.cwd()

# Insert project root to the front of sys.path if not already present
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

# Extra fallback: if the 'apps' package is still not importable, try the parent
try:
    import pkgutil

    if pkgutil.find_loader("apps") is None:
        alt_root = project_root.parent
        alt_root_str = str(alt_root)
        if alt_root_str not in sys.path:
            sys.path.insert(0, alt_root_str)
except Exception:
    # Keep silent on failures here; the import error will be raised below with context
    pass

from apps.backtest.engine import VectorizedEngine
from apps.strategy import BaseStrategy
from apps.plotting.batch import create_html_report, plot_all
from apps.plotting.wrappers import (
    plot_daily_returns,
    plot_distribution,
    plot_drawdown,
    plot_monthly_heatmap,
    plot_returns,
    plot_rolling_sharpe,
    plot_yearly_returns,
)
from apps.utils.data_getters import load_mt5

# Set UTF-8 encoding for console output (Windows compatibility)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


# Simple Strategy for generating results
class SMAStrategy(BaseStrategy):
    """Simple Moving Average Crossover Strategy."""
    
    def on_init(self):
        # Parameters from self.params
        self.fast_period = self.params.get("fast_period", 10)
        self.slow_period = self.params.get("slow_period", 30)

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        # Calculate indicators
        data["sma_fast"] = data["close"].rolling(self.fast_period).mean()
        data["sma_slow"] = data["close"].rolling(self.slow_period).mean()
        
        # Initialize signal columns
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        
        # Ensure we have enough data
        if len(data) < self.slow_period:
            return data
            
        # Detect Crossovers
        # Fast > Slow = Buy
        # Fast < Slow = Sell/Exit
        
        # Vectorized logic
        # 1. Create conditions
        fast_gt_slow = data["sma_fast"] > data["sma_slow"]
        fast_lt_slow = data["sma_fast"] < data["sma_slow"]
        
        # 2. Shift to identify crossovers (change from previous state)
        # Use simple numeric diff on boolean series (True=1, False=0)
        # 1 - 0 = 1 (True now, False before) -> Crossover Up
        # 0 - 1 = -1 (False now, True before) -> Crossover Down
        crossover = fast_gt_slow.astype(int).diff()
        
        # 3. Assign signals
        # Buy on crossover up
        data.loc[crossover == 1, "entry_signal"] = 1
        
        # Exit on crossover down
        data.loc[crossover == -1, "exit_signal"] = 1  # Exit buy
        
        return data


def get_real_results(symbol="EURUSD", start_date="2023-01-01", end_date="2023-12-31"):
    """Run backtest on real data and return results."""
    try:
        data = load_mt5(symbol, start_date=start_date, end_date=end_date, timeframe="D1")
        
        strategy = SMAStrategy(params={"symbol": symbol, "fast_period": 10, "slow_period": 30})
        
        bt = VectorizedEngine(
            strategy=strategy,
            data=data,
            initial_balance=10000,
            commission=0.0001
        )
        
        results = bt.run()
        return results
        
    except Exception as e:
        print(f"Error running backtest: {e}")
        return None


def example_wrapper_functions():
    """Demonstrate using wrapper functions for individual plots."""
    print("\n" + "=" * 70)
    print("Example 1: Using Wrapper Functions")
    print("=" * 70)

    # Get real results
    print("Running backtest on EURUSD...")
    results = get_real_results("EURUSD")
    if results is None: return

    # Extract equity curve
    # Use internal helper if available, or extract from equity_curve list
    if hasattr(results, "_get_equity_series"):
        equity = results._get_equity_series()
    else:
        # Fallback manual extraction
        equity_data = [(p.timestamp, p.equity) for p in results.equity_curve]
        times, values = zip(*equity_data) if equity_data else ([], [])
        equity = pd.Series(values, index=pd.DatetimeIndex(times))

    # Use wrapper functions with consistent interface
    print("\n1. Plotting returns...")
    plot_returns(
        equity,
        title="EURUSD Strategy Returns",
        savefig="output/plotting/example_returns.png",
        show=False,
    )
    print("    Returns plot saved")

    print("\n2. Plotting drawdown...")
    plot_drawdown(
        equity,
        title="EURUSD Strategy Drawdown",
        savefig="output/plotting/example_drawdown.png",
        show=False,
    )
    print("    Drawdown plot saved")

    print("\n3. Plotting monthly heatmap...")
    plot_monthly_heatmap(
        equity,
        title="EURUSD Monthly Performance",
        savefig="output/plotting/example_monthly.png",
        show=False,
    )
    print("    Monthly heatmap saved")

    print("\n4. Plotting rolling Sharpe ratio...")
    plot_rolling_sharpe(
        equity,
        window=30,
        title="EURUSD 30-Day Rolling Sharpe",
        savefig="output/plotting/example_sharpe.png",
        show=False,
    )
    print("    Rolling Sharpe plot saved")

    print("\n5. Plotting yearly returns...")
    plot_yearly_returns(
        equity,
        title="EURUSD Yearly Performance",
        savefig="output/plotting/example_yearly.png",
        show=False,
    )
    print("    Yearly returns plot saved")

    print("\n6. Plotting daily returns distribution...")
    plot_daily_returns(
        equity,
        title="EURUSD Daily Returns Distribution",
        savefig="output/plotting/example_daily.png",
        show=False,
    )
    print("    Daily returns plot saved")

    print("\n7. Plotting returns distribution...")
    plot_distribution(
        equity,
        title="EURUSD Return Distribution Analysis",
        savefig="output/plotting/example_distribution.png",
        show=False,
    )
    print("    Distribution plot saved")

    print("\n All individual plots created successfully!")


def example_batch_plotting():
    """Generate all plots at once with plot_all()."""
    print("\n" + "=" * 70)
    print("Example 2: Batch Plot Generation")
    print("=" * 70)

    # Get real results
    print("Running backtest on GBPUSD...")
    results = get_real_results("GBPUSD")
    if results is None: return

    # Generate all plots at once
    print("\nGenerating all plots...")
    saved_plots = plot_all(
        results,
        output_dir="output/plotting/batch_example",
        prefix="GBPUSD_Strategy",
        formats=["png", "pdf"],
        dpi=150,
        create_manifest=True,
    )

    print(f"\n Generated {len(saved_plots)} plot types:")
    for plot_name, file_paths in saved_plots.items():
        print(f"    {plot_name}: {len(file_paths)} files")

    print(f"\nTotal files created: {sum(len(paths) for paths in saved_plots.values())}")
    print("\n Batch plot generation complete!")


def example_html_report():
    """Create HTML report with embedded plots."""
    print("\n" + "=" * 70)
    print("Example 3: HTML Report Generation")
    print("=" * 70)

    # Get real results
    print("Running backtest on USDJPY...")
    results = get_real_results("USDJPY")
    if results is None: return

    # Generate comprehensive HTML report
    print("\nGenerating HTML report...")
    report_path = create_html_report(
        results,
        output_path="output/plotting/example_report.html",
        title="USDJPY Strategy - Backtest Report",
        include_plots=None,  # Include all plots
    )

    print(f"\n HTML report created: {report_path}")
    print("   You can open this file in a web browser to view the report")


def example_custom_formats():
    """Example: Save plots in multiple formats."""
    print("\n" + "=" * 70)
    print("Example 4: Multiple Output Formats")
    print("=" * 70)

    # Get real results
    print("Running backtest on AUDUSD...")
    results = get_real_results("AUDUSD")
    if results is None: return

    print("\nGenerating plots in PNG, PDF, and SVG formats...")
    saved_plots = plot_all(
        results,
        output_dir="output/plotting/multi_format",
        prefix="AUDUSD_MultiFormat",
        formats=["png", "pdf", "svg"],
        dpi=300,  # High DPI for publication quality
        create_manifest=True,
    )

    print("\n Generated plots in 3 formats:")
    # Check if we have any plots
    if saved_plots:
        example_plot = list(saved_plots.keys())[0]
        print(f"\nExample ({example_plot}):")
        for path in saved_plots[example_plot]:
            print(f"    {path.name}")
    else:
        print("   No plots generated.")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("BATCH PLOTTING AND REPORT GENERATION EXAMPLES")
    print("=" * 70)

    # Create output directory
    import os
    os.makedirs("output/plotting", exist_ok=True)

    try:
        # Example 1: Wrapper functions
        example_wrapper_functions()

        # Example 2: Batch plotting
        example_batch_plotting()

        # Example 3: HTML report
        example_html_report()

        # Example 4: Multiple formats
        example_custom_formats()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\nCheck the 'output/plotting/' directory for generated files:")
        print("   Individual plots from wrapper functions")
        print("   Batch plots with manifest")
        print("   HTML report (open in browser)")
        print("   Multi-format plots (PNG, PDF, SVG)")

    except Exception as e:
        print(f"\n Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
