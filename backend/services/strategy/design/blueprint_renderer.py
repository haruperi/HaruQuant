"""Render StrategyBlueprint contracts into Python strategy skeletons."""

from __future__ import annotations

import re

from backend.contracts.strategy_blueprint.model import StrategyBlueprint


class StrategyBlueprintRenderer:
    """Render a blueprint into a template_strategy.py-style code skeleton."""

    @staticmethod
    def _class_name(strategy_name: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", strategy_name)
        return "".join(word.capitalize() for word in words) + "Strategy"

    def render_python_strategy(self, blueprint: StrategyBlueprint) -> str:
        payload = blueprint.payload
        class_name = self._class_name(payload.strategy_name)
        asset_label = ", ".join(payload.asset_scope.assets)
        entry_comment = "\n        # ".join(payload.entry_logic)
        exit_comment = "\n        # ".join(payload.exit_logic)
        risk_comment = "\n        # ".join(payload.risk_management.additional_rules or ["No additional rules supplied."])

        return f'''"""
Generated from StrategyBlueprint: {payload.strategy_name}

Source idea:
{payload.source_idea}
"""

from typing import Any, Dict, Optional

import pandas as pd

from backend.common.logger import logger
from backend.services.strategy import BaseStrategy
from backend.services.strategy.base import SignalDict


class {class_name}(BaseStrategy):
    """
    {payload.strategy_name}.

    Strategy type: {payload.strategy_type}
    Assets: {asset_label}
    Timeframe: {payload.asset_scope.timeframe}

    Entry logic:
    - {payload.entry_logic[0]}

    Exit logic:
    - {payload.exit_logic[0]}
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.timeframe = self.params.get("timeframe", "{payload.asset_scope.timeframe}")

    def on_init(self) -> None:
        logger.info("{class_name} initialized for %s", self.params["symbol"])

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")

        # Entry logic from Strategy Creator:
        # {entry_comment}

        # Exit logic from Strategy Creator:
        # {exit_comment}

        # Risk management notes:
        # Stop-loss: {payload.risk_management.stop_loss}
        # Take-profit: {payload.risk_management.take_profit}
        # {risk_comment}

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

        return {{
            "entry_signal": entry,
            "exit_signal": exit_sig,
            "pending_signal": pending,
            "cancel_pending_signal": cancel,
            "price": float(price),
            "time": row.name,
            "reason": "{payload.strategy_name} generated a signal",
            "stop_loss": None,
            "take_profit": None,
        }}
'''

    def render_summary(self, blueprint: StrategyBlueprint) -> dict[str, object]:
        payload = blueprint.payload
        return {
            "strategy_name": payload.strategy_name,
            "strategy_type": payload.strategy_type,
            "assets": payload.asset_scope.assets,
            "timeframe": payload.asset_scope.timeframe,
            "backtest_readiness": payload.backtest_readiness,
        }
