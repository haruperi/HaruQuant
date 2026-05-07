"""EMA crossover trend-following strategy."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from haruquant.indicator import ema
from services.strategy.base import BaseStrategy, SignalDict
from services.utils.logger import logger

from data.strategies.stateful_common import ensure_signal_columns


class TrendFollowingStrategy(BaseStrategy):
    """Classic EMA crossover strategy with a slow trend filter."""

    strategy_name = "TrendFollowingStrategy"
    strategy_type = "simple"
    signal_schema_version = "1.0"

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.symbol = str(self.params.get("symbol", "UNKNOWN"))
        self.fast_period = int(self.params.get("fast_period", 20))
        self.slow_period = int(self.params.get("slow_period", 50))
        self.filter_period = int(self.params.get("filter_period", 200))
        self._validate_params()

    def _validate_params(self) -> None:
        if self.fast_period <= 0:
            raise ValueError("fast_period must be positive.")
        if self.slow_period <= 0:
            raise ValueError("slow_period must be positive.")
        if self.filter_period <= 0:
            raise ValueError("filter_period must be positive.")
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be less than slow_period.")

    def on_init(self) -> None:
        logger.info(
            "%s initialized for %s fast=%s slow=%s filter=%s",
            self.strategy_name,
            self.symbol,
            self.fast_period,
            self.slow_period,
            self.filter_period,
        )

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()
        data = self._calculate_indicators(data)
        data = self._shift_features(data)
        data = ensure_signal_columns(data)
        data = self._generate_simple_signals(data)
        return data

    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        data = ema(data, self.fast_period)
        data = ema(data, self.slow_period)
        data = ema(data, self.filter_period)
        return data

    def _shift_features(self, data: pd.DataFrame) -> pd.DataFrame:
        fast = f"ema_{self.fast_period}"
        slow = f"ema_{self.slow_period}"
        trend_filter = f"ema_{self.filter_period}"

        data[f"{fast}_signal"] = data[fast].shift(1)
        data[f"{slow}_signal"] = data[slow].shift(1)
        data[f"{trend_filter}_signal"] = data[trend_filter].shift(1)
        data[f"prev_{fast}_signal"] = data[f"{fast}_signal"].shift(1)
        data[f"prev_{slow}_signal"] = data[f"{slow}_signal"].shift(1)
        return data

    def _generate_simple_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        fast = f"ema_{self.fast_period}_signal"
        slow = f"ema_{self.slow_period}_signal"
        trend_filter = f"ema_{self.filter_period}_signal"
        prev_fast = f"prev_ema_{self.fast_period}_signal"
        prev_slow = f"prev_ema_{self.slow_period}_signal"

        bullish_cross = (data[fast] > data[slow]) & (data[prev_fast] <= data[prev_slow])
        bearish_cross = (data[fast] < data[slow]) & (data[prev_fast] >= data[prev_slow])
        buy = bullish_cross & (data[slow] > data[trend_filter])
        sell = bearish_cross & (data[slow] < data[trend_filter])

        data.loc[bullish_cross, "exit_signal"] = -1
        data.loc[bullish_cross, "price"] = data.loc[bullish_cross, "open"]
        data.loc[bullish_cross, "signal_reason"] = "Bullish EMA crossover exit"

        data.loc[bearish_cross, "exit_signal"] = 1
        data.loc[bearish_cross, "price"] = data.loc[bearish_cross, "open"]
        data.loc[bearish_cross, "signal_reason"] = "Bearish EMA crossover exit"

        data.loc[buy, "entry_signal"] = 1
        data.loc[buy, "price"] = data.loc[buy, "open"]
        data.loc[buy, "signal_reason"] = (
            f"EMA {self.fast_period} crossed above EMA {self.slow_period} "
            f"with EMA {self.slow_period} above EMA {self.filter_period}"
        )
        data.loc[buy, "setup_id"] = "ema_trend_buy"
        data.loc[buy, "group_id"] = "ema_trend_buy"

        data.loc[sell, "entry_signal"] = -1
        data.loc[sell, "price"] = data.loc[sell, "open"]
        data.loc[sell, "signal_reason"] = (
            f"EMA {self.fast_period} crossed below EMA {self.slow_period} "
            f"with EMA {self.slow_period} below EMA {self.filter_period}"
        )
        data.loc[sell, "setup_id"] = "ema_trend_sell"
        data.loc[sell, "group_id"] = "ema_trend_sell"
        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        return super().get_signal(data, index)
