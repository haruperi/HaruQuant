"""Example usage of backtest plotting helpers.

This example demonstrates how to:
1. Run a backtest with a simple strategy
2. Plot the results with various options
3. Save plots to files
4. Customize plot appearance

Updated to use real market data from MT5.
"""

import os
import sys
from pathlib import Path

import pandas as pd

# Add project root to path
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

from apps.backtest import EventDrivenEngine
from apps.indicator import sma
from apps.plotting import plot_drawdown, plot_returns, plot_snapshot
from apps.strategy import BaseStrategy
from apps.utils.data_getters import load_mt5


class SMAStrategy(BaseStrategy):
    """Simple Moving Average Crossover Strategy."""

    def __init__(self, params=None):
        super().__init__(params)
        self.fast_window = self.params.get("fast_window", 10)
        self.slow_window = self.params.get("slow_window", 30)

    def on_init(self) -> None:
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        result = sma(data, window=self.fast_window)
        result = sma(result, window=self.slow_window)

        fast_col = f"sma_{self.fast_window}"
        slow_col = f"sma_{self.slow_window}"

        result["entry_signal"] = 0
        result["exit_signal"] = 0
        result["pending_signal"] = 0
        result["cancel_pending_signal"] = 0
        result["price"] = float("nan")

        buy = result[fast_col] > result[slow_col]
        sell = result[fast_col] < result[slow_col]

        result.loc[buy, "entry_signal"] = 1
        result.loc[buy, "price"] = result.loc[buy, "open"]
        result.loc[sell, "exit_signal"] = 1

        return result


def get_real_data(symbol="EURUSD", start_date="2023-01-01", end_date="2023-12-31"):
    """Load real data for testing."""
    try:
        data = load_mt5(
            symbol, start_date=start_date, end_date=end_date, timeframe="D1"
        )
        return data if data is not None else pd.DataFrame()
    except Exception as exc:
        print(f"Error loading data: {exc}")
        return pd.DataFrame()


def run_backtest(symbol: str, params: dict | None = None):
    """Run a simple MA backtest and return result and equity series."""
    data = get_real_data(symbol)
    if data.empty:
        return None, pd.Series(dtype=float)

    strategy = SMAStrategy(params={"symbol": symbol, **(params or {})})
    engine = EventDrivenEngine(
        strategy=strategy,
        data=data,
        initial_balance=10000.0,
        commission=0.0001,
        timeframe="D1",
    )
    result = engine.run()

    equity_df = result.get_equity_df()
    equity = pd.Series(
        equity_df["equity"].values, index=pd.to_datetime(equity_df["timestamp"])
    )
    return result, equity


def example_basic_plot():
    """Example: Basic plot with default settings."""
    print("=" * 80)
    print("Example 1: Basic Plot")
    print("=" * 80)

    print("Loading EURUSD data...")
    result, equity = run_backtest("EURUSD")
    if result is None:
        return

    print("\nRunning backtest...")
    print("Creating plot...")
    fig = plot_returns(
        equity,
        title="EURUSD Cumulative Returns",
        savefig="output/plotting/plot_basic_returns.png",
        show=False,
    )

    print(f"Basic plot created with {len(fig.axes)} panels")
    print(f"  Total trades: {result.total_trades}")
    print(f"  Final equity: ${equity.iloc[-1]:.2f}")


def example_plot_with_all_panels():
    """Example: Plot with all available panels."""
    print("\n" + "=" * 80)
    print("Example 2: Plot with All Panels")
    print("=" * 80)

    print("Loading GBPUSD data...")
    result, equity = run_backtest("GBPUSD")
    if result is None:
        return

    print("\nRunning backtest...")
    print("Creating comprehensive plot...")
    returns = equity.pct_change().dropna()
    fig = plot_snapshot(
        returns=returns,
        metrics=result.summary(),
        layout="3x2",
        title="GBPUSD Performance Snapshot",
        show=False,
    )
    fig.savefig("output/plotting/plot_snapshot.png", dpi=150, bbox_inches="tight")

    print(f"Comprehensive plot created with {len(fig.axes)} panels")
    print("  Panels include returns, distribution, and metrics")


def example_plot_and_save():
    """Example: Create and save plot to file."""
    print("\n" + "=" * 80)
    print("Example 3: Save Plot to File")
    print("=" * 80)

    print("Loading USDJPY data...")
    result, equity = run_backtest("USDJPY")
    if result is None:
        return

    print("\nRunning backtest...")
    print("Creating and saving plot...")

    output_path = "output/plotting/plot_drawdown.png"
    plot_drawdown(
        equity,
        title="USDJPY Drawdown",
        savefig=output_path,
        show=False,
    )

    print(f"Plot saved to: {output_path}")


def example_custom_figsize():
    """Example: Custom figure size."""
    print("\n" + "=" * 80)
    print("Example 4: Custom Figure Size")
    print("=" * 80)

    print("Loading AUDUSD data...")
    result, equity = run_backtest("AUDUSD")
    if result is None:
        return

    print("\nRunning backtest...")
    print("Creating plot with custom size...")
    fig = plot_returns(
        equity,
        title="AUDUSD Cumulative Returns",
        figsize=(16, 10),
        savefig="output/plotting/plot_custom_size.png",
        show=False,
    )

    print(f"Custom sized plot created: {fig.get_figwidth()} x {fig.get_figheight()}")


def example_minimal_plot():
    """Example: Minimal plot (equity only)."""
    print("\n" + "=" * 80)
    print("Example 5: Minimal Plot (Equity Only)")
    print("=" * 80)

    print("Loading EURUSD data...")
    result, equity = run_backtest("EURUSD")
    if result is None:
        return

    print("\nRunning backtest...")
    print("Creating minimal plot...")
    fig = plot_returns(
        equity,
        title="EURUSD Cumulative Returns",
        savefig="output/plotting/plot_minimal.png",
        show=False,
    )

    print(f"Minimal plot created with {len(fig.axes)} panels")
    print("  Showing only cumulative returns")


def example_compare_strategies():
    """Example: Run multiple strategies and compare plots."""
    print("\n" + "=" * 80)
    print("Example 6: Compare Multiple Strategy Parameters")
    print("=" * 80)

    param_sets = [
        {"fast_period": 5, "slow_period": 20},
        {"fast_period": 10, "slow_period": 30},
        {"fast_period": 20, "slow_period": 50},
    ]

    results_list = []

    for params in param_sets:
        print(
            f"\nRunning backtest with fast={params['fast_period']}, slow={params['slow_period']}..."
        )
        result, equity = run_backtest("GBPUSD", params=params)
        if result is None:
            continue
        results_list.append((params, result, equity))

        final_equity = equity.iloc[-1]
        total_trades = result.total_trades
        print(f"  Final equity: ${final_equity:.2f}")
        print(f"  Total trades: {total_trades}")

    if not results_list:
        print("No successful runs to compare.")
        return

    best_idx = max(
        range(len(results_list)), key=lambda i: results_list[i][2].iloc[-1]
    )
    best_params, _best_result, best_equity = results_list[best_idx]

    print(
        f"\nBest performing: fast={best_params['fast_period']}, slow={best_params['slow_period']}"
    )
    print("Creating plot for best strategy...")

    plot_drawdown(
        best_equity,
        title="Best Strategy Drawdown",
        savefig="output/plotting/best_strategy_drawdown.png",
        show=False,
    )

    print("Best strategy plot saved")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("BACKTEST PLOTTING - USAGE EXAMPLES")
    print("=" * 80)

    os.makedirs("output/plotting", exist_ok=True)

    try:
        example_basic_plot()
        example_plot_with_all_panels()
        example_plot_and_save()
        example_custom_figsize()
        example_minimal_plot()
        example_compare_strategies()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)
        print("\nKey features demonstrated:")
        print("  Basic plotting with default settings")
        print("  Multi-panel snapshot")
        print("  Saving plots to files")
        print("  Custom figure sizes")
        print("  Minimal plots for quick analysis")
        print("  Strategy parameter comparison")
        print("\nOutput files saved to: output/plotting/")

    except Exception as exc:
        print(f"\nError in examples: {exc}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
