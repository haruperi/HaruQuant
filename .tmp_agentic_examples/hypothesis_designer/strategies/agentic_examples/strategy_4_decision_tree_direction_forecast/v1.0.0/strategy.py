"""
Generated from StrategyBlueprint: Decision Tree Direction Forecast

Source idea:
Use a decision tree classifier to predict next-day direction.
"""

from typing import Any, Dict, Optional

import pandas as pd

from backend.common.logger import logger
from backend.services.strategy import BaseStrategy
from backend.services.strategy.base import SignalDict


class DecisionTreeDirectionForecastStrategy(BaseStrategy):
    """
    Decision Tree Direction Forecast.

    Strategy type: ml
    Assets: SPY
    Timeframe: 1D

    Entry logic:
    - Enter LONG when the model predicts the next-day return class is positive.

    Exit logic:
    - Exit LONG when the model prediction flips negative.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.timeframe = self.params.get("timeframe", "1D")

    def on_init(self) -> None:
        logger.info("DecisionTreeDirectionForecastStrategy initialized for %s", self.params["symbol"])

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")

        # Entry logic from Hypothesis Designer:
        # Enter LONG when the model predicts the next-day return class is positive.

        # Exit logic from Hypothesis Designer:
        # Exit LONG when the model prediction flips negative.

        # Risk management notes:
        # Stop-loss: 7% below entry price
        # Take-profit: 10% above entry price
        # Retrain model monthly on a rolling window.

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
            "reason": "Decision Tree Direction Forecast generated a signal",
            "stop_loss": None,
            "take_profit": None,
        }
