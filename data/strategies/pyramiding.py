"""Bi-directional pyramiding example strategy."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from services.strategy.base import BaseStrategy
from services.strategy.stateful import (
    StatefulStrategyMixin,
    StrategyContext,
    TradeAction,
)

from data.strategies.stateful_common import (
    current_mid_price,
    ensure_no_signal_columns,
    historical_mid_prices,
    is_bar_close,
    positions_for_side,
    rolling_sma,
    weighted_average_price,
)


class PyramidingStrategy(StatefulStrategyMixin, BaseStrategy):
    """Adds to winning trend positions and moves basket stops to lock profit."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.fast_ma_period = int(self.params.get("fast_ma_period", 10))
        self.slow_ma_period = int(self.params.get("slow_ma_period", 20))
        self.initial_lot = float(self.params.get("initial_lot", 1.0))
        self.lot_divisor = float(self.params.get("lot_divisor", 2.0))
        self.min_step_pips = float(self.params.get("min_step_pips", 30.0))
        self.trailing_sl_pips = float(self.params.get("trailing_sl_pips", 10.0))
        self.pip_value = float(self.params.get("pip_value", 0.0001))
        self.max_positions_per_side = int(self.params.get("max_positions_per_side", 6))

    def on_init(self) -> None:
        self.state.setdefault("buy", {"last_price": 0.0, "total_positions": 0})
        self.state.setdefault("sell", {"last_price": 0.0, "total_positions": 0})

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        return ensure_no_signal_columns(data)

    def on_event(self, context: StrategyContext) -> list[TradeAction]:
        if not is_bar_close(context):
            return []
        prices = historical_mid_prices(context)
        fast_ma = rolling_sma(prices, self.fast_ma_period)
        slow_ma = rolling_sma(prices, self.slow_ma_period)
        if fast_ma is None or slow_ma is None:
            return []

        current_price = current_mid_price(context)
        actions: list[TradeAction] = []
        actions.extend(
            self._side_actions(
                "BUY",
                trend_confirmed=fast_ma > slow_ma,
                current_price=current_price,
                context=context,
            )
        )
        actions.extend(
            self._side_actions(
                "SELL",
                trend_confirmed=fast_ma < slow_ma,
                current_price=current_price,
                context=context,
            )
        )
        return actions

    def _side_actions(
        self,
        side: str,
        *,
        trend_confirmed: bool,
        current_price: float,
        context: StrategyContext,
    ) -> list[TradeAction]:
        positions = positions_for_side(context, side)
        side_key = side.lower()
        side_state = self.state.setdefault(
            side_key,
            {"last_price": 0.0, "total_positions": 0},
        )

        if not positions:
            side_state.update({"last_price": 0.0, "total_positions": 0})
            if not trend_confirmed:
                return []
            side_state.update({"last_price": current_price, "total_positions": 1})
            return [
                TradeAction(
                    action_type="OPEN",
                    symbol=context.symbol,
                    side=side,  # type: ignore[arg-type]
                    volume=self.initial_lot,
                    reason=f"Initial {side} pyramiding trend entry",
                )
            ]

        if not trend_confirmed or len(positions) >= self.max_positions_per_side:
            return []
        if not self._basket_is_profitable(side, current_price, positions):
            return []

        last_price = float(side_state.get("last_price") or positions[-1].open_price)
        step = self.min_step_pips * self.pip_value
        profit_dist = (
            current_price - last_price if side == "BUY" else last_price - current_price
        )
        if profit_dist < step:
            return []

        total_positions = int(side_state.get("total_positions") or len(positions))
        new_lot = self.initial_lot / (self.lot_divisor**total_positions)
        trailing_distance = self.trailing_sl_pips * self.pip_value
        new_sl = (
            current_price - trailing_distance
            if side == "BUY"
            else current_price + trailing_distance
        )
        side_state.update(
            {"last_price": current_price, "total_positions": total_positions + 1}
        )
        return [
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                volume=new_lot,
                reason=f"{side} pyramiding add",
            ),
            TradeAction(
                action_type="MODIFY_SL",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                stop_loss=new_sl,
                reason=f"Trail all {side} stops after pyramid add",
            ),
        ]

    @staticmethod
    def _basket_is_profitable(side: str, current_price: float, positions) -> bool:
        average_price = weighted_average_price(positions)
        if average_price is None:
            return False
        if side == "BUY":
            return current_price > average_price
        return current_price < average_price
