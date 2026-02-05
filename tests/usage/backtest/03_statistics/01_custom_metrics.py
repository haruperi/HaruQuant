"""Example 01: Custom Metrics

Calculate custom performance metrics beyond standard statistics.

Author: HaruQuant Development Team
Created: 2025-12-03
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

import pandas as pd  # noqa: E402
from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator
from apps.simulation.utils import calculate_metrics_from_simulator  # noqa: E402
from apps.indicator import sma  # noqa: E402
from apps.logger import logger  # noqa: E402
from apps.strategy import BaseStrategy  # noqa: E402
from apps.utils.data_getters import load_mt5  # noqa: E402


def calculate_custom_metrics(result):
    """Calculate custom metrics from backtest result."""
    # Custom metric 1: Risk-Adjusted Return
    total_return = result.total_return_pct
    max_dd = result.max_drawdown_pct
    risk_adj_return = total_return / abs(max_dd) if max_dd != 0 else 0

    # Custom metric 2: Profit Factor
    profit_factor = result.profit_factor

    # Custom metric 3: Win/Loss Ratio
    win_rate = result.win_rate / 100
    loss_rate = 1 - win_rate
    wl_ratio = win_rate / loss_rate if loss_rate > 0 else float('inf')
    
    return {
        'Risk-Adjusted Return': risk_adj_return,
        'Profit Factor': profit_factor,
        'Win/Loss Ratio': wl_ratio
    }


def example1_basic_custom_metrics():
    """Calculate basic custom metrics."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Custom Metrics")
    print("=" * 70)

    data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-20"
    )

    class MAStrategy(BaseStrategy):
        def __init__(self, params=None):
            super().__init__(params)
            self.fast_window = self.params.get("fast_window", 10)
            self.slow_window = self.params.get("slow_window", 30)

        def on_init(self) -> None:
            logger.info("MA strategy initialized")

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


            # Cleanup


            mt5_client.shutdown()


            


            return result

    strategy = MAStrategy(params={"symbol": "EURUSD"})
    # Initialize strategy
    strategy.on_init()

    # Calculate signals
    data = strategy.on_bar(data)

    # Get MT5 client for symbol info
    mt5_client = get_mt5_client()

    # Setup simulator components
    account_info = AccountInfoSimulator(
        balance=10000.0,
        equity=10000.0,
        margin_free=10000.0,
    )
    symbol_info = SymbolInfoSimulator.from_mt5_symbol('EURUSD')
    symbol_info.symbol = 'EURUSD'

    # Create simulator
    simulator = TradeSimulator(
        simulator_name="Backtest_EURUSD",
        mt5_client=mt5_client,
        account_info=account_info,
        symbols={'EURUSD': symbol_info},
    )

    # Run simulation
    simulator.run(
        data=data,
        strategy=strategy,
        symbol='EURUSD',
        volume=0.1,
        verbose=False,
        save_db=False,
        engine_type="event_driven",
        commission_per_contract=0.0002,
        slippage_points=0,
        start_date=backtest_start,
        end_date=backtest_end,
    )

    # Get results from simulator
    result = calculate_metrics_from_simulator(simulator)

    print("\nStandard Metrics:")
    print(f"  Total Return: {result.total_return_pct:.2f}%")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {result.max_drawdown_pct:.2f}%")

    custom = calculate_custom_metrics(result)
    print("\nCustom Metrics:")
    for name, value in custom.items():
        if value == float('inf'):
            print(f"  {name}: inf")
        else:
            print(f"  {name}: {value:.2f}")


def example2_metric_formulas():
    """Show formulas for common metrics."""
    print("\n" + "=" * 70)
    print("Example 2: Metric Formulas")
    print("=" * 70)

    print("\n1. Sharpe Ratio:")
    print("   Sharpe = (Return - RiskFreeRate) / Volatility")
    print("   Measures risk-adjusted return")

    print("\n2. Sortino Ratio:")
    print("   Sortino = (Return - RiskFreeRate) / DownsideDeviation")
    print("   Like Sharpe but only penalizes downside volatility")

    print("\n3. Calmar Ratio:")
    print("   Calmar = CAGR / MaxDrawdown")
    print("   Return per unit of maximum drawdown")

    print("\n4. Profit Factor:")
    print("   ProfitFactor = GrossProfit / GrossLoss")
    print("   >1 = profitable, >2 = good, >3 = excellent")

    print("\n5. Expectancy:")
    print("   Expectancy = (WinRate * AvgWin) - (LossRate * AvgLoss)")
    print("   Expected profit per trade")


def example3_best_practices():
    """Best practices for metrics."""
    print("\n" + "=" * 70)
    print("Example 3: Best Practices")
    print("=" * 70)

    print("\n1. Use Multiple Metrics:")
    print("   - Return alone is misleading")
    print("   - Consider risk (Sharpe, Sortino)")
    print("   - Check drawdown (Calmar)")
    print("   - Verify trade quality (Win rate, Profit factor)")

    print("\n2. Benchmark Comparison:")
    print("   - Compare to buy-and-hold")
    print("   - Compare to risk-free rate")
    print("   - Compare to similar strategies")

    print("\n3. Time Period Matters:")
    print("   - Longer periods more reliable")
    print("   - Check consistency across periods")
    print("   - Beware of curve-fitting")

    print("\n4. Common Pitfalls:")
    print("   - Focusing only on return")
    print("   - Ignoring drawdown")
    print("   - Not enough trades")
    print("   - Overfitting to metrics")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("CUSTOM METRICS EXAMPLES")
    print("=" * 70)

    try:
        example1_basic_custom_metrics()
        example2_metric_formulas()
        example3_best_practices()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED")
        print("=" * 70)

        print("\nKey Takeaways:")
        print("1. Use multiple metrics, not just return")
        print("2. Risk-adjusted metrics are crucial")
        print("3. Custom metrics provide deeper insights")
        print("4. Always benchmark against alternatives")

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
