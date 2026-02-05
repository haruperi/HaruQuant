"""Example 03: Drawdown Analysis

Deep dive into drawdown periods and recovery.

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
from apps.strategy import BaseStrategy  # noqa: E402
from apps.utils.data_getters import load_mt5  # noqa: E402


def analyze_drawdowns(equity_series):
    """Analyze drawdown periods."""
    # Calculate running maximum
    running_max = equity_series.expanding().max()
    
    # Calculate drawdown
    drawdown = (equity_series - running_max) / running_max * 100
    
    # Find drawdown periods
    in_drawdown = drawdown < 0
    
    print(f"\nDrawdown Analysis:")
    print(f"  Max Drawdown: {drawdown.min():.2f}%")
    print(f"  Avg Drawdown: {drawdown[in_drawdown].mean():.2f}%")
    print(f"  Time in Drawdown: {in_drawdown.sum() / len(drawdown) * 100:.1f}%")
    
    # Recovery time
    if drawdown.min() < 0:
        max_dd_idx = drawdown.idxmin()
        recovery_idx = equity_series[max_dd_idx:][equity_series[max_dd_idx:] >= running_max[max_dd_idx]].index
        if len(recovery_idx) > 0:
            recovery_time = (recovery_idx[0] - max_dd_idx).days
            print(f"  Max DD Recovery: {recovery_time} days")


def main():
    print("\n" + "=" * 70)
    print("DRAWDOWN ANALYSIS EXAMPLE")
    print("=" * 70)

    data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-25"
    )

    class MAStrategy(BaseStrategy):
        def __init__(self, params=None):
            super().__init__(params)
            self.window = self.params.get("window", 20)

        def on_init(self) -> None:
            pass

        def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
            result = sma(data, window=self.window)
            sma_col = f"sma_{self.window}"

            result["entry_signal"] = 0
            result["exit_signal"] = 0
            result["pending_signal"] = 0
            result["cancel_pending_signal"] = 0
            result["price"] = float("nan")

            above = result["close"] > result[sma_col]
            below = result["close"] < result[sma_col]

            result.loc[above, "entry_signal"] = 1
            result.loc[above, "price"] = result.loc[above, "open"]
            result.loc[below, "exit_signal"] = 1


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

    equity_df = result.get_equity_df()
    if not equity_df.empty:
        equity_series = equity_df.set_index("timestamp")["equity"]
        analyze_drawdowns(equity_series)
    
    print("\n" + "=" * 70)
    print("Key Insights:")
    print("- Monitor max drawdown")
    print("- Check recovery time")
    print("- Assess risk tolerance")
    print("=" * 70)


if __name__ == "__main__":
    main()
