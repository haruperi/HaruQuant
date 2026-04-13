"""EMA crossover baseline strategy."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from backend.services.indicators.trend import ema
from backend.services.strategy.base import BaseStrategy, SignalDict
from backend.services.strategy.baselines.common import (
    initialize_signal_columns,
    price_at,
)


class EmaCrossBaselineStrategy(BaseStrategy):
    """Trend-following baseline using fast/slow EMA crossovers."""

    def __init__(self, params: Optional[dict[str, Any]] = None):
        super().__init__(params)
        self.fast_period = int(self.params.get("fast_period", 12))
        self.slow_period = int(self.params.get("slow_period", 26))
        self.price_col = str(self.params.get("price_col", "close"))

    def on_init(self) -> None:
        if self.fast_period <= 0 or self.slow_period <= 0:
            raise ValueError("EMA periods must be positive")
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        self.on_init()
        result = ema(data, self.fast_period, price_col=self.price_col)
        result = ema(result, self.slow_period, price_col=self.price_col)
        result = initialize_signal_columns(result)

        fast_col = f"ema_{self.fast_period}"
        slow_col = f"ema_{self.slow_period}"
        prev_fast = result[fast_col].shift(1)
        prev_slow = result[slow_col].shift(1)
        bullish_cross = (prev_fast <= prev_slow) & (result[fast_col] > result[slow_col])
        bearish_cross = (prev_fast >= prev_slow) & (result[fast_col] < result[slow_col])

        result.loc[bullish_cross, "entry_signal"] = 1
        result.loc[bearish_cross, "entry_signal"] = -1
        result.loc[bullish_cross | bearish_cross, "price"] = result.loc[
            bullish_cross | bearish_cross, self.price_col
        ]
        result.loc[bullish_cross, "signal_reason"] = (
            f"EMA({self.fast_period}) crossed above EMA({self.slow_period})"
        )
        result.loc[bearish_cross, "signal_reason"] = (
            f"EMA({self.fast_period}) crossed below EMA({self.slow_period})"
        )

        spread = (result[fast_col] - result[slow_col]).abs()
        denom = result[self.price_col].abs().replace(0, pd.NA)
        result.loc[bullish_cross | bearish_cross, "signal_confidence"] = (
            spread.loc[bullish_cross | bearish_cross] / denom.loc[bullish_cross | bearish_cross]
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
            "reason": str(row.get("signal_reason") or "EMA crossover baseline signal"),
            "stop_loss": None,
            "take_profit": None,
        }
