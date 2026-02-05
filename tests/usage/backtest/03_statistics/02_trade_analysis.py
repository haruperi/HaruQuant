"""Example 02: Trade Analysis

Analyze individual trades and trading patterns.

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


def analyze_trades(result):
    """Analyze trade statistics."""
    trades = result.get_trades_df()
    if trades.empty:
        print("No trades to analyze")
        return

    print(f"\nTotal Trades: {len(trades)}")

    if "profit_loss" in trades.columns:
        wins = trades[trades["profit_loss"] > 0]
        losses = trades[trades["profit_loss"] < 0]

        print(f"Winning Trades: {len(wins)} ({len(wins)/len(trades)*100:.1f}%)")
        print(f"Losing Trades: {len(losses)} ({len(losses)/len(trades)*100:.1f}%)")

        if len(wins) > 0:
            print(f"Avg Win: ${wins['profit_loss'].mean():.2f}")
            print(f"Max Win: ${wins['profit_loss'].max():.2f}")

        if len(losses) > 0:
            print(f"Avg Loss: ${losses['profit_loss'].mean():.2f}")
            print(f"Max Loss: ${losses['profit_loss'].min():.2f}")


def main():
    print("\n" + "=" * 70)
    print("TRADE ANALYSIS EXAMPLE")
    print("=" * 70)

    data = load_mt5(
        "EURUSD", timeframe="M1", start_date="2025-11-03", end_date="2025-11-20"
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

    analyze_trades(result)
    
    print("\n" + "=" * 70)
    print("Key Insights:")
    print("- Analyze win/loss distribution")
    print("- Check for outlier trades")
    print("- Verify trade logic")
    print("=" * 70)


if __name__ == "__main__":
    main()
