"""Naive momentum baseline strategy."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from backend.services.strategy.base import BaseStrategy, SignalDict
from backend.services.strategy.baselines.common import (
    initialize_signal_columns,
    price_at,
)


class NaiveMomentumStrategy(BaseStrategy):
    """Baseline that buys positive N-period momentum and sells negative momentum."""

    def __init__(self, params: Optional[dict[str, Any]] = None):
        super().__init__(params)
        self.lookback = int(self.params.get("lookback", 20))
        self.threshold = float(self.params.get("threshold", 0.0))
        self.price_col = str(self.params.get("price_col", "close"))

    def on_init(self) -> None:
        if self.lookback <= 0:
            raise ValueError("lookback must be positive")
        if self.threshold < 0:
            raise ValueError("threshold cannot be negative")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        self.on_init()
        result = initialize_signal_columns(data)
        momentum_col = f"momentum_{self.lookback}"
        result[momentum_col] = result[self.price_col].pct_change(self.lookback)

        buy = result[momentum_col] > self.threshold
        sell = result[momentum_col] < -self.threshold
        result.loc[buy, "entry_signal"] = 1
        result.loc[sell, "entry_signal"] = -1
        result.loc[buy | sell, "price"] = result.loc[buy | sell, self.price_col]
        result.loc[buy, "signal_reason"] = (
            f"{self.lookback}-bar momentum > {self.threshold:g}"
        )
        result.loc[sell, "signal_reason"] = (
            f"{self.lookback}-bar momentum < -{self.threshold:g}"
        )
        result.loc[buy | sell, "signal_confidence"] = (
            result.loc[buy | sell, momentum_col].abs()
        ).clip(0.0, 1.0)
        return result

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        row = data.iloc[index]
        entry = int(row.get("entry_signal", 0) or 0)
        if entry == 0:
            return None
        return {
            "entry_signal": entry,
            "exit_signal": 0,
            "pending_signal": 0,
            "cancel_pending_signal": 0,
            "pending_signal_2": 0,
            "cancel_pending_signal_2": 0,
            "price": price_at(row, "price"),
            "price_2": None,
            "time": data.index[index],
            "reason": str(row.get("signal_reason") or "Naive momentum baseline signal"),
            "stop_loss": None,
            "take_profit": None,
        }
