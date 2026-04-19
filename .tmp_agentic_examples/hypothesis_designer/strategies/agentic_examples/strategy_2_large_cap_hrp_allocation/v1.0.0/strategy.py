"""
Generated from StrategyBlueprint: Large Cap HRP Allocation

Source idea:
Build an HRP portfolio over large-cap tech and rebalance weekly.
"""

from typing import Any, Dict, Optional

import pandas as pd

from backend.common.logger import logger
from backend.services.strategy import BaseStrategy
from backend.services.strategy.base import SignalDict


class LargeCapHrpAllocationStrategy(BaseStrategy):
    """
    Large Cap HRP Allocation.

    Strategy type: portfolio
    Assets: NVDA, MSFT, AAPL, AMZN, GOOG, AVGO, META, TSLA, JPM, LLY, WMT, ORCL, V, MA, XOM, NFLX, JNJ, PLTR, COST
    Timeframe: 1D

    Entry logic:
    - Rebalance into the current HRP weight vector at the scheduled rebalance date.

    Exit logic:
    - Exit and recompute weights on the next rebalance date.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.timeframe = self.params.get("timeframe", "1D")

    def on_init(self) -> None:
        logger.info("LargeCapHrpAllocationStrategy initialized for %s", self.params["symbol"])

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")

        # Entry logic from Hypothesis Designer:
        # Rebalance into the current HRP weight vector at the scheduled rebalance date.

        # Exit logic from Hypothesis Designer:
        # Exit and recompute weights on the next rebalance date.
        # Exit positions if the portfolio-level drawdown rule triggers.

        # Risk management notes:
        # Stop-loss: 7% portfolio-level drawdown stop or per-asset 7% stop-loss.
        # Take-profit: 10% per-asset take-profit or rebalance-driven profit capture.
        # Cap portfolio drawdown at 12 percent.

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
            "reason": "Large Cap HRP Allocation generated a signal",
            "stop_loss": None,
            "take_profit": None,
        }
