"""Two-sided previous-bar breakout strategy."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from services.strategy.base import BaseStrategy, SignalDict
from services.utils.logger import logger

from data.strategies.stateful_common import ensure_signal_columns


class CloseBreakoutStrategy(BaseStrategy):
    """Refreshes buy-stop and sell-stop orders at previous bar high/low."""

    strategy_name = "CloseBreakoutStrategy"
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
        data = ensure_signal_columns(data)

        valid_setup = data["prev_high"].notna() & data["prev_low"].notna()
        data.loc[valid_setup, "cancel_pending_signal"] = 1
        data.loc[valid_setup, "cancel_pending_signal_2"] = -1
        data.loc[valid_setup, "pending_signal"] = 1
        data.loc[valid_setup, "pending_signal_2"] = -1
        data.loc[valid_setup, "price"] = data.loc[valid_setup, "prev_high"]
        data.loc[valid_setup, "price_2"] = data.loc[valid_setup, "prev_low"]
        data.loc[valid_setup, "signal_reason"] = (
            "Refresh breakout stop orders at previous bar high/low"
        )
        data.loc[valid_setup, "setup_id"] = "close_breakout_refresh"
        data.loc[valid_setup, "group_id"] = "close_breakout_refresh"
        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        return super().get_signal(data, index)
