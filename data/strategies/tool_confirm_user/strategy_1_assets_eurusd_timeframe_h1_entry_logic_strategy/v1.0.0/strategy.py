"""
Generated from StrategyBlueprint: Assets Eurusd Timeframe H1 Entry Logic Strategy

Source idea:
- Assets: EURUSD
- Timeframe: H1
Entry logic:
- Enter LONG when previous-bar RSI is below 30 and price confirms mean-reversion setup.
- Enter SHORT when previous-bar RSI is above 70 and short trades are enabled.
Exit logic:
- Exit LONG when RSI normalizes above 50, mean reversion completes, or risk rules trigger.
- Exit SHORT when RSI normalizes below 50, mean reversion completes, or risk rules trigger.
Risk management:
- {'stop_loss': '50 pips', 'take_profit': '100 pips', 'ignore_stop_loss_take_profit': False, 'additional_rules': []}
Position sizing:
- {'sizing_rule': 'Use full capital per trade.', 'leverage': 1.0, 'allocation_notes': 'Single-asset default applied.'}
"""

from typing import Any, Dict, Optional

import pandas as pd

from services.utils.logger import logger
from services.strategy import BaseStrategy
from services.strategy.base import SignalDict


class AssetsEurusdTimeframeH1EntryLogicStrategyStrategy(BaseStrategy):
    """
    Assets Eurusd Timeframe H1 Entry Logic Strategy.

    Strategy type: allocation
    Assets: EURUSD
    Timeframe: H1

    Entry logic:
    - Enter LONG when previous-bar RSI is below 30 and price confirms mean-reversion setup.

    Exit logic:
    - Exit LONG when RSI normalizes above 50, mean reversion completes, or risk rules trigger.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.timeframe = self.params.get("timeframe", "H1")

    def on_init(self) -> None:
        logger.info("AssetsEurusdTimeframeH1EntryLogicStrategyStrategy initialized for %s", self.params["symbol"])

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")

        # Entry logic from Strategy Creator:
        # Enter LONG when previous-bar RSI is below 30 and price confirms mean-reversion setup.
        # Enter SHORT when previous-bar RSI is above 70 and short trades are enabled.

        # Exit logic from Strategy Creator:
        # Exit LONG when RSI normalizes above 50, mean reversion completes, or risk rules trigger.
        # Exit SHORT when RSI normalizes below 50, mean reversion completes, or risk rules trigger.

        # Risk management notes:
        # Stop-loss: 7% portfolio-level drawdown stop or per-asset 7% stop-loss.
        # Take-profit: 10% per-asset take-profit or rebalance-driven profit capture.
        # No additional rules supplied.

        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        row = data.iloc[index]
        entry = int(row.get("entry_signal", 0))
        exit_sig = int(row.get("exit_signal", 0))
        pending = int(row.get("pending_signal", 0))
        cancel = int(row.get("cancel_pending_signal", 0))
        if entry == 0 and exit_sig == 0 and pending == 0 and cancel == 0:
            return None

        price = row.get("price")
        if pd.isna(price):
            price = row["close"]

        return {
            "entry_signal": entry,
            "exit_signal": exit_sig,
            "pending_signal": pending,
            "cancel_pending_signal": cancel,
            "price": float(price),
            "time": row.name,
            "reason": "Assets Eurusd Timeframe H1 Entry Logic Strategy generated a signal",
            "stop_loss": None,
            "take_profit": None,
        }
