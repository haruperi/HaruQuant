"""Bollinger Bands and RSI mean-reversion strategy."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from haruquant.indicator import bbands, rsi
from services.strategy.base import BaseStrategy, SignalDict
from services.utils.logger import logger

from data.strategies.stateful_common import ensure_signal_columns


class MeanReversionStrategy(BaseStrategy):
    """Counter-trend strategy using Bollinger extremes confirmed by RSI."""

    strategy_name = "MeanReversionStrategy"
    strategy_type = "simple"
    signal_schema_version = "1.0"

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.symbol = str(self.params.get("symbol", "UNKNOWN"))
        self.bb_period = int(self.params.get("bb_period", 20))
        self.bb_std = float(self.params.get("bb_std", 2.0))
        self.rsi_period = int(self.params.get("rsi_period", 14))
        self.rsi_oversold = float(self.params.get("rsi_oversold", 30.0))
        self.rsi_overbought = float(self.params.get("rsi_overbought", 70.0))
        self._validate_params()

    def _validate_params(self) -> None:
        if self.bb_period <= 0:
            raise ValueError("bb_period must be positive.")
        if self.bb_std <= 0:
            raise ValueError("bb_std must be positive.")
        if self.rsi_period <= 0:
            raise ValueError("rsi_period must be positive.")
        if not 0 < self.rsi_oversold < self.rsi_overbought < 100:
            raise ValueError(
                "RSI thresholds must satisfy 0 < oversold < overbought < 100."
            )

    def on_init(self) -> None:
        logger.info(
            "%s initialized for %s bb=%s/%s rsi=%s",
            self.strategy_name,
            self.symbol,
            self.bb_period,
            self.bb_std,
            self.rsi_period,
        )

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()
        data = self._calculate_indicators(data)
        data = self._shift_features(data)
        data = ensure_signal_columns(data)
        data = self._generate_simple_signals(data)
        return data

    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        data = bbands(
            data,
            period=self.bb_period,
            std_dev=self.bb_std,
            price_col="close",
        )
        data = rsi(data, self.rsi_period)
        return data

    def _shift_features(self, data: pd.DataFrame) -> pd.DataFrame:
        upper, middle, lower = self._band_columns()
        rsi_col = f"rsi_{self.rsi_period}"
        for column in (upper, middle, lower, rsi_col):
            data[f"{column}_signal"] = data[column].shift(1)
        data["prev_close_signal"] = data["close"].shift(1)
        return data

    def _generate_simple_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        upper, middle, lower = self._band_columns(signal=True)
        rsi_col = f"rsi_{self.rsi_period}_signal"

        buy = (data["prev_close_signal"] <= data[lower]) & (
            data[rsi_col] < self.rsi_oversold
        )
        sell = (data["prev_close_signal"] >= data[upper]) & (
            data[rsi_col] > self.rsi_overbought
        )
        band_width = data[upper] - data[lower]

        data.loc[buy, "entry_signal"] = 1
        data.loc[buy, "price"] = data.loc[buy, "open"]
        data.loc[buy, "stop_loss"] = data.loc[buy, "open"] - (band_width.loc[buy] * 0.5)
        data.loc[buy, "take_profit"] = data.loc[buy, middle]
        data.loc[buy, "signal_reason"] = "Oversold Bollinger/RSI mean reversion"
        data.loc[buy, "setup_id"] = "bb_rsi_buy"
        data.loc[buy, "group_id"] = "bb_rsi_buy"

        data.loc[sell, "entry_signal"] = -1
        data.loc[sell, "price"] = data.loc[sell, "open"]
        data.loc[sell, "stop_loss"] = data.loc[sell, "open"] + (
            band_width.loc[sell] * 0.5
        )
        data.loc[sell, "take_profit"] = data.loc[sell, middle]
        data.loc[sell, "signal_reason"] = "Overbought Bollinger/RSI mean reversion"
        data.loc[sell, "setup_id"] = "bb_rsi_sell"
        data.loc[sell, "group_id"] = "bb_rsi_sell"
        return data

    def _band_columns(self, *, signal: bool = False) -> tuple[str, str, str]:
        std_label = int(self.bb_std)
        suffix = "_signal" if signal else ""
        return (
            f"bb_upper_{self.bb_period}_{std_label}{suffix}",
            f"bb_middle_{self.bb_period}_{std_label}{suffix}",
            f"bb_lower_{self.bb_period}_{std_label}{suffix}",
        )

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        return super().get_signal(data, index)
