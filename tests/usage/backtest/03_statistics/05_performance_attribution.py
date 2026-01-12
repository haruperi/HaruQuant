"""Example 05: Performance Attribution

Attribute performance to different factors.

Author: HaruQuant Development Team
Created: 2025-12-03
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

import pandas as pd  # noqa: E402
from apps.backtest import EventDrivenEngine  # noqa: E402
from apps.indicator import sma  # noqa: E402
from apps.strategy import BaseStrategy  # noqa: E402
from apps.utils.data_getters import load_mt5  # noqa: E402


def attribute_performance(result):
    """Attribute performance to different factors."""
    print("\nPerformance Attribution:")
    print(f"  Total Return: {result.total_return_pct:.2f}%")

    # Break down by trade direction
    trades = result.get_trades_df()
    if not trades.empty and "profit_loss" in trades.columns:
        total_pnl = trades["profit_loss"].sum()

        # Attribute to wins vs losses
        wins_pnl = trades[trades["profit_loss"] > 0]["profit_loss"].sum()
        losses_pnl = trades[trades["profit_loss"] < 0]["profit_loss"].sum()

        print(f"\nBy Trade Outcome:")
        if total_pnl != 0:
            print(
                f"  Wins contributed: ${wins_pnl:.2f} ({wins_pnl/total_pnl*100:.1f}%)"
            )
            print(
                f"  Losses contributed: ${losses_pnl:.2f} ({losses_pnl/total_pnl*100:.1f}%)"
            )
        else:
            print(f"  Wins contributed: ${wins_pnl:.2f}")
            print(f"  Losses contributed: ${losses_pnl:.2f}")


def main():
    print("\n" + "=" * 70)
    print("PERFORMANCE ATTRIBUTION EXAMPLE")
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

            return result

    strategy = MAStrategy(params={"symbol": "EURUSD"})
    engine = EventDrivenEngine(
        strategy=strategy,
        data=data,
        initial_balance=10000.0,
        commission=0.0002,
        timeframe="M1",
    )
    result = engine.run()

    attribute_performance(result)
    
    print("\n" + "=" * 70)
    print("Key Insights:")
    print("- Understand what drives returns")
    print("- Identify strengths and weaknesses")
    print("- Optimize based on attribution")
    print("=" * 70)


if __name__ == "__main__":
    main()
