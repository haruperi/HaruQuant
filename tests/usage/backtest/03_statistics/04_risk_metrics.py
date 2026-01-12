"""Example 04: Risk Metrics

Calculate risk-adjusted performance metrics.

Author: HaruQuant Development Team
Created: 2025-12-03
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

import pandas as pd  # noqa: E402
import numpy as np  # noqa: E402
from apps.backtest import EventDrivenEngine  # noqa: E402
from apps.indicator import sma  # noqa: E402
from apps.strategy import BaseStrategy  # noqa: E402
from apps.utils.data_getters import load_mt5  # noqa: E402


def calculate_risk_metrics(returns, equity=None):
    """Calculate various risk metrics."""
    print("\nRisk Metrics:")
    
    # Volatility
    volatility = returns.std() * np.sqrt(252) * 100  # Annualized
    print(f"  Volatility (annual): {volatility:.2f}%")
    
    # Sharpe Ratio (assuming 0% risk-free rate)
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
    print(f"  Sharpe Ratio: {sharpe:.2f}")
    
    # Sortino Ratio (downside deviation)
    downside_returns = returns[returns < 0]
    if len(downside_returns) > 0:
        downside_std = downside_returns.std()
        sortino = (returns.mean() / downside_std * np.sqrt(252)) if downside_std > 0 else 0
        print(f"  Sortino Ratio: {sortino:.2f}")
    
    # Value at Risk (95%)
    var_95 = np.percentile(returns, 5) * 100
    print(f"  VaR (95%): {var_95:.2f}%")


def main():
    print("\n" + "=" * 70)
    print("RISK METRICS EXAMPLE")
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

    equity_df = result.get_equity_df()
    if not equity_df.empty:
        equity = equity_df.set_index("timestamp")["equity"]
        returns = equity.pct_change().dropna()
        calculate_risk_metrics(returns, equity)
    
    print("\n" + "=" * 70)
    print("Key Insights:")
    print("- Higher Sharpe = better risk-adjusted return")
    print("- Sortino focuses on downside risk")
    print("- VaR estimates potential losses")
    print("=" * 70)


if __name__ == "__main__":
    main()
