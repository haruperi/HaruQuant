"""RSI baseline strategy."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from services.indicator.momentum import rsi
from services.strategy.base import BaseStrategy, SignalDict
from services.strategy.baselines.common import (
    initialize_signal_columns,
    price_at,
)


class RsiBaselineStrategy(BaseStrategy):
    """Mean-reversion baseline using RSI overbought/oversold thresholds."""

    def __init__(self, params: Optional[dict[str, Any]] = None):
        super().__init__(params)
        self.period = int(self.params.get("period", 14))
        self.oversold = float(self.params.get("oversold", 30.0))
        self.overbought = float(self.params.get("overbought", 70.0))
        self.price_col = str(self.params.get("price_col", "close"))

    def on_init(self) -> None:
        if self.period <= 0:
            raise ValueError("period must be positive")
        if not 0 <= self.oversold < self.overbought <= 100:
            raise ValueError("RSI thresholds must satisfy 0 <= oversold < overbought <= 100")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        self.on_init()
        result = rsi(data, period=self.period, price_col=self.price_col)
        result = initialize_signal_columns(result)
        rsi_col = f"rsi_{self.period}"

        buy = result[rsi_col] <= self.oversold
        sell = result[rsi_col] >= self.overbought

        result.loc[buy, "entry_signal"] = 1
        result.loc[sell, "entry_signal"] = -1
        result.loc[buy | sell, "price"] = result.loc[buy | sell, self.price_col]
        result.loc[buy, "signal_reason"] = (
            f"RSI({self.period}) <= oversold threshold {self.oversold:g}"
        )
        result.loc[sell, "signal_reason"] = (
            f"RSI({self.period}) >= overbought threshold {self.overbought:g}"
        )
        result.loc[buy | sell, "signal_confidence"] = (
            (result.loc[buy | sell, rsi_col] - 50.0).abs() / 50.0
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
            "reason": str(row.get("signal_reason") or "RSI baseline signal"),
            "stop_loss": None,
            "take_profit": None,
        }
