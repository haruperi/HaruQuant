"""Single-leg previous-bar breakout strategy."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from services.strategy.base import BaseStrategy, SignalDict
from services.utils.logger import logger

from data.strategies.stateful_common import ensure_signal_columns


class PositionType:
    BUY = 0
    SELL = 1


class BreakoutStrategy(BaseStrategy):
    """Places one pending breakout order and refreshes it each bar."""

    strategy_name = "BreakoutStrategy"
    strategy_type = "simple"
    signal_schema_version = "1.0"

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.symbol = str(self.params.get("symbol", "UNKNOWN"))
        self._validate_params()

    def _validate_params(self) -> None:
        if not self.symbol:
            raise ValueError("symbol must be provided.")

    def on_init(self) -> None:
        logger.info("%s initialized for %s", self.strategy_name, self.symbol)

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()
        data["prev_high"] = data["high"].shift(1)
        data["prev_low"] = data["low"].shift(1)
        data["prev_close"] = data["close"].shift(1)
        data["prev_open"] = data["open"].shift(1)
        data = ensure_signal_columns(data)

        valid_setup = data["prev_high"].notna() & data["prev_low"].notna()
        bullish_bias = data["prev_close"] > data["prev_open"]
        buy = valid_setup & bullish_bias
        sell = valid_setup & ~bullish_bias

        data.loc[valid_setup, "cancel_pending_signal"] = 1
        data.loc[buy, "pending_signal"] = 1
        data.loc[buy, "price"] = data.loc[buy, "prev_high"]
        data.loc[buy, "signal_reason"] = "Previous bar bullish breakout pending"
        data.loc[buy, "setup_id"] = "breakout_buy"
        data.loc[buy, "group_id"] = "breakout_buy"

        data.loc[sell, "pending_signal"] = -1
        data.loc[sell, "price"] = data.loc[sell, "prev_low"]
        data.loc[sell, "signal_reason"] = "Previous bar bearish breakout pending"
        data.loc[sell, "setup_id"] = "breakout_sell"
        data.loc[sell, "group_id"] = "breakout_sell"
        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        if index < 1:
            return None

        row = data.iloc[index]
        if pd.isna(row.get("prev_high")) or pd.isna(row.get("prev_low")):
            return None

        signal = super().get_signal(data, index)
        if signal is None:
            return None

        if self.position and hasattr(self.position, "positions"):
            is_long = False
            is_short = False
            for position in self.position.positions.values():
                if position.symbol != self.symbol:
                    continue
                is_long = position.type == PositionType.BUY
                is_short = position.type == PositionType.SELL
                break

            if is_long:
                signal["pending_signal"] = -1
                signal["price"] = float(row["prev_low"])
                signal["reason"] = "Reverse long with previous bar sell stop"
                signal["setup_id"] = "breakout_reverse_sell"
                signal["group_id"] = "breakout_reverse_sell"
            elif is_short:
                signal["pending_signal"] = 1
                signal["price"] = float(row["prev_high"])
                signal["reason"] = "Reverse short with previous bar buy stop"
                signal["setup_id"] = "breakout_reverse_buy"
                signal["group_id"] = "breakout_reverse_buy"

        return signal
