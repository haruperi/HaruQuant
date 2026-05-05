"""
Close Breakout Strategy.

Places stop orders at the previous bar high/low and refreshes them every bar.
"""

from typing import Any, Dict, Optional
import pandas as pd
from haruquant.utils import logger
from haruquant.strategy import BaseStrategy, SignalDict


class CloseBreakoutStrategy(BaseStrategy):
    """Two-sided pending breakout strategy using previous bar levels."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)

    def on_init(self) -> None:
        logger.info(f"CloseBreakoutStrategy initialized for {self.params['symbol']}")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()
        data["prev_high"] = data["high"].shift(1)
        data["prev_low"] = data["low"].shift(1)

        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["pending_signal_2"] = 0
        data["cancel_pending_signal_2"] = 0
        data["price"] = 0.0
        data["price_2"] = 0.0
        data["sl"] = 0.0
        data["tp"] = 0.0

        valid_setup = data["prev_high"].notna() & data["prev_low"].notna()

        data.loc[valid_setup, "cancel_pending_signal"] = 1
        data.loc[valid_setup, "cancel_pending_signal_2"] = -1
        data.loc[valid_setup, "pending_signal"] = 1
        data.loc[valid_setup, "pending_signal_2"] = -1
        data.loc[valid_setup, "price"] = data.loc[valid_setup, "prev_high"]
        data.loc[valid_setup, "price_2"] = data.loc[valid_setup, "prev_low"]

        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        row = data.iloc[index]
        pending_1 = int(row.get("pending_signal", 0) or 0)
        pending_2 = int(row.get("pending_signal_2", 0) or 0)
        cancel_1 = int(row.get("cancel_pending_signal", 0) or 0)
        cancel_2 = int(row.get("cancel_pending_signal_2", 0) or 0)

        if pending_1 == 0 and pending_2 == 0 and cancel_1 == 0 and cancel_2 == 0:
            return None

        return {
            "entry_signal": 0,
            "exit_signal": 0,
            "pending_signal": pending_1,
            "cancel_pending_signal": cancel_1,
            "pending_signal_2": pending_2,
            "cancel_pending_signal_2": cancel_2,
            "price": float(row.get("price", 0.0) or 0.0),
            "price_2": float(row.get("price_2", 0.0) or 0.0),
            "time": row.name,
            "reason": "Refresh breakout stop orders at previous bar high/low",
            "stop_loss": None,
            "take_profit": None,
        }
