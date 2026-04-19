"""
Generated from StrategyBlueprint: RSI Mean Reversion

Source idea:
Buy when RSI is low and exit when it recovers.
"""

from typing import Any, Dict, Optional

import pandas as pd

from backend.common.logger import logger
from backend.services.strategy import BaseStrategy
from backend.services.strategy.base import SignalDict


class RsiMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean Reversion.

    Strategy type: technical
    Assets: SPY
    Timeframe: 1D

    Entry logic:
    - Enter LONG when RSI is low enough to indicate an oversold condition.

    Exit logic:
    - Exit LONG when RSI normalizes back into the mid-range.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.timeframe = self.params.get("timeframe", "1D")

    def on_init(self) -> None:
        logger.info("RsiMeanReversionStrategy initialized for %s", self.params["symbol"])

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")

        # Entry logic from Hypothesis Designer:
        # Enter LONG when RSI is low enough to indicate an oversold condition.

        # Exit logic from Hypothesis Designer:
        # Exit LONG when RSI normalizes back into the mid-range.

        # Risk management notes:
        # Stop-loss: 7% below entry price
        # Take-profit: 10% above entry price
        # Do not open a second position while one is active.

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
            "reason": "RSI Mean Reversion generated a signal",
            "stop_loss": None,
            "take_profit": None,
        }
