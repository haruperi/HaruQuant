"""EMA crossover baseline strategy with trend bias filter."""

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
    """Trend-following baseline using EMA(20)/EMA(50) crossovers with EMA(200) bias filter.

    Rules:
    - Long: EMA(20) crosses above EMA(50) AND both above EMA(200)
    - Exit Long: EMA(20) crosses below EMA(50)
    - Short: EMA(20) crosses below EMA(50) AND both below EMA(200)
    - Exit Short: EMA(20) crosses above EMA(50)
    """

    def __init__(self, params: Optional[dict[str, Any]] = None):
        super().__init__(params)
        self.fast_period = int(self.params.get("fast_period", 20))
        self.slow_period = int(self.params.get("slow_period", 50))
        self.bias_period = int(self.params.get("bias_period", 200))
        self.price_col = str(self.params.get("price_col", "close"))

    def on_init(self) -> None:
        if self.fast_period <= 0 or self.slow_period <= 0 or self.bias_period <= 0:
            raise ValueError("EMA periods must be positive")
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")
        if self.slow_period >= self.bias_period:
            raise ValueError("slow_period must be less than bias_period")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        self.on_init()
        result = ema(data, self.fast_period, price_col=self.price_col)
        result = ema(result, self.slow_period, price_col=self.price_col)
        result = ema(result, self.bias_period, price_col=self.price_col)
        result = initialize_signal_columns(result)

        fast_col = f"ema_{self.fast_period}"
        slow_col = f"ema_{self.slow_period}"
        bias_col = f"ema_{self.bias_period}"

        prev_fast = result[fast_col].shift(1)
        prev_slow = result[slow_col].shift(1)
        prev_bias = result[bias_col].shift(1)

        # Crossover signals
        bullish_cross = (prev_fast <= prev_slow) & (result[fast_col] > result[slow_col])
        bearish_cross = (prev_fast >= prev_slow) & (result[fast_col] < result[slow_col])

        # Bias filter: both fast and slow must be above/below bias EMA
        above_bias = (result[fast_col] > result[bias_col]) & (result[slow_col] > result[bias_col])
        below_bias = (result[fast_col] < result[bias_col]) & (result[slow_col] < result[bias_col])

        # Entry signals with bias filter
        result.loc[bullish_cross & above_bias, "entry_signal"] = 1
        result.loc[bearish_cross & below_bias, "entry_signal"] = -1

        # Exit signals (crossover against position, no bias filter needed)
        result.loc[bearish_cross, "exit_signal"] = 1  # Exit long
        result.loc[bullish_cross, "exit_signal"] = -1  # Exit short

        # Set entry price for signals
        has_signal = bullish_cross | bearish_cross
        result.loc[has_signal, "price"] = result.loc[has_signal, self.price_col]

        # Signal reasons
        result.loc[bullish_cross & above_bias, "signal_reason"] = (
            f"EMA({self.fast_period}) crossed above EMA({self.slow_period}), "
            f"both above EMA({self.bias_period})"
        )
        result.loc[bearish_cross & below_bias, "signal_reason"] = (
            f"EMA({self.fast_period}) crossed below EMA({self.slow_period}), "
            f"both below EMA({self.bias_period})"
        )
        result.loc[bearish_cross, "exit_reason"] = (
            f"EMA({self.fast_period}) crossed below EMA({self.slow_period}) - exit long"
        )
        result.loc[bullish_cross, "exit_reason"] = (
            f"EMA({self.fast_period}) crossed above EMA({self.slow_period}) - exit short"
        )

        # Confidence based on separation between fast and slow EMA
        spread = (result[fast_col] - result[slow_col]).abs()
        denom = result[self.price_col].abs().replace(0, pd.NA)
        result.loc[has_signal, "signal_confidence"] = (
            spread.loc[has_signal] / denom.loc[has_signal]
        ).clip(0.0, 1.0)
        return result

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        row = data.iloc[index]
        entry = int(row.get("entry_signal", 0) or 0)
        exit_sig = int(row.get("exit_signal", 0) or 0)

        if entry == 0 and exit_sig == 0:
            return None

        return {
            "entry_signal": entry,
            "exit_signal": exit_sig,
            "pending_signal": 0,
            "cancel_pending_signal": 0,
            "pending_signal_2": 0,
            "cancel_pending_signal_2": 0,
            "price": price_at(row, "price"),
            "price_2": None,
            "time": data.index[index],
            "reason": str(row.get("signal_reason") or row.get("exit_reason") or "EMA crossover signal"),
            "stop_loss": None,
            "take_profit": None,
        }
