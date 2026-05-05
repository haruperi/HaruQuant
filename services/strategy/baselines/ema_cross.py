"""EMA crossover baseline strategy with trend bias filter."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from services.indicator.trend import ema
from services.strategy.base import BaseStrategy, SignalDict
from services.strategy.baselines.common import (
    initialize_signal_columns,
    price_at,
)


class EmaCrossBaselineStrategy(BaseStrategy):
    """Trend-following baseline using fast/slow EMA crossovers.

    Rules:
    - Long: fast EMA crosses above slow EMA
    - Exit Long: EMA(20) crosses below EMA(50)
    - Short: fast EMA crosses below slow EMA
    - Exit Short: EMA(20) crosses above EMA(50)
    - Optional bias filter: require both EMAs to be above/below a bias EMA
    """

    def __init__(self, params: Optional[dict[str, Any]] = None):
        super().__init__(params)
        self.fast_period = int(self.params.get("fast_period", 20))
        self.slow_period = int(self.params.get("slow_period", 50))
        self.use_bias_filter = bool(
            self.params.get("use_bias_filter", "bias_period" in self.params)
        )
        self.bias_period = int(self.params.get("bias_period", 200))
        self.price_col = str(self.params.get("price_col", "close"))

    def on_init(self) -> None:
        if self.fast_period <= 0 or self.slow_period <= 0 or self.bias_period <= 0:
            raise ValueError("EMA periods must be positive")
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period")
        if self.use_bias_filter and self.slow_period >= self.bias_period:
            raise ValueError("slow_period must be less than bias_period")

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        self.on_init()
        result = ema(data, self.fast_period, price_col=self.price_col)
        result = ema(result, self.slow_period, price_col=self.price_col)
        if self.use_bias_filter:
            result = ema(result, self.bias_period, price_col=self.price_col)
        result = initialize_signal_columns(result)

        fast_col = f"ema_{self.fast_period}"
        slow_col = f"ema_{self.slow_period}"

        prev_fast = result[fast_col].shift(1)
        prev_slow = result[slow_col].shift(1)

        # Crossover signals
        bullish_cross = (prev_fast <= prev_slow) & (result[fast_col] > result[slow_col])
        bearish_cross = (prev_fast >= prev_slow) & (result[fast_col] < result[slow_col])

        if self.use_bias_filter:
            bias_col = f"ema_{self.bias_period}"
            above_bias = (result[fast_col] > result[bias_col]) & (result[slow_col] > result[bias_col])
            below_bias = (result[fast_col] < result[bias_col]) & (result[slow_col] < result[bias_col])
        else:
            above_bias = pd.Series(True, index=result.index)
            below_bias = pd.Series(True, index=result.index)

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
        long_reason = f"EMA({self.fast_period}) crossed above EMA({self.slow_period})"
        short_reason = f"EMA({self.fast_period}) crossed below EMA({self.slow_period})"
        if self.use_bias_filter:
            long_reason = f"{long_reason}, both above EMA({self.bias_period})"
            short_reason = f"{short_reason}, both below EMA({self.bias_period})"
        result.loc[bullish_cross & above_bias, "signal_reason"] = long_reason
        result.loc[bearish_cross & below_bias, "signal_reason"] = short_reason
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
