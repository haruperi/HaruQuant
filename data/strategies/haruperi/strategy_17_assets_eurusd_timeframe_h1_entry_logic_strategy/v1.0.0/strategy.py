"""
Generated from StrategyBlueprint: Assets Eurusd Timeframe H1 Entry Logic Strategy

Source idea:
- Assets: EURUSD
- Timeframe: H1
Entry logic:
- Enter LONG when RSI(12) crosses up through 50 on the completed bar.
- Enter SHORT when RSI(12) crosses down through 50 on the completed bar.
Exit logic:
- Exit LONG when RSI(12) crosses down through 50 on the completed bar.
- Exit SHORT when RSI(12) crosses up through 50 on the completed bar.
Risk management:
- {'stop_loss': None, 'take_profit': None, 'ignore_stop_loss_take_profit': True, 'additional_rules': ['No stop-loss or take-profit. Exits are governed by the explicit exit logic.']}
Position sizing:
- {'sizing_rule': 'Use fixed 0.1 lots per trade.', 'leverage': 1.0, 'allocation_notes': 'Fixed-lot position sizing supplied by the user.'}
"""

from typing import Any, Dict, Optional

import pandas as pd

from haruquant.utils import logger
from haruquant.strategy import BaseStrategy
from haruquant.strategy import SignalDict


class AssetsEurusdTimeframeH1EntryLogicStrategyStrategy(BaseStrategy):
    """
    Assets Eurusd Timeframe H1 Entry Logic Strategy.

    Strategy type: allocation
    Assets: EURUSD
    Timeframe: H1

    Entry logic:
    - Enter LONG when RSI(12) crosses up through 50 on the completed bar.

    Exit logic:
    - Exit LONG when RSI(12) crosses down through 50 on the completed bar.
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
        # Enter LONG when RSI(12) crosses up through 50 on the completed bar.
        # Enter SHORT when RSI(12) crosses down through 50 on the completed bar.

        # Exit logic from Strategy Creator:
        # Exit LONG when RSI(12) crosses down through 50 on the completed bar.
        # Exit SHORT when RSI(12) crosses up through 50 on the completed bar.

        # Risk management notes:
        # Stop-loss: None
        # Take-profit: None
        # No stop-loss or take-profit. Exits are governed by the explicit exit logic.

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
