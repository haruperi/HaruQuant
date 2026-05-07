"""Bi-directional trade decomposition example strategy."""

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
    oldest_position,
    positions_for_side,
    rolling_rsi,
    weighted_average_price,
)


class TradeDecompositionStrategy(StatefulStrategyMixin, BaseStrategy):
    """Partially closes older trades and re-enters at better basket prices."""

    strategy_name = "TradeDecompositionStrategy"
    strategy_type = "stateful"
    signal_schema_version = "1.0"
    action_schema_version = "1.0"

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.rsi_period = int(self.params.get("rsi_period", 14))
        self.os_level = float(self.params.get("os_level", 30.0))
        self.ob_level = float(self.params.get("ob_level", 70.0))
        self.initial_lot = float(self.params.get("initial_lot", 0.06))
        self.vol_increase = float(self.params.get("vol_increase", 0.06))
        self.vol_decrease = float(self.params.get("vol_decrease", 0.02))
        self.trade_distance = float(self.params.get("trade_distance", 20.0))
        self.trail_points = float(self.params.get("trail_points", 10.0))
        self.child_take_profit_pips = float(
            self.params.get("child_take_profit_pips", self.trail_points)
        )
        self.pip_value = float(self.params.get("pip_value", 0.0001))
        self.strategy_risk_controls = self.params.get("risk_controls", {})
        self._validate_params()

    def _validate_params(self) -> None:
        if self.rsi_period <= 0:
            raise ValueError("rsi_period must be positive.")
        if not 0 < self.os_level < self.ob_level < 100:
            raise ValueError("RSI levels must satisfy 0 < os_level < ob_level < 100.")
        if self.initial_lot <= 0:
            raise ValueError("initial_lot must be positive.")
        if self.vol_increase <= 0:
            raise ValueError("vol_increase must be positive.")
        if self.vol_decrease <= 0:
            raise ValueError("vol_decrease must be positive.")
        if self.vol_decrease > self.vol_increase:
            raise ValueError("vol_decrease must not exceed vol_increase.")
        if self.trade_distance <= 0:
            raise ValueError("trade_distance must be positive.")
        if self.trail_points <= 0:
            raise ValueError("trail_points must be positive.")
        if self.child_take_profit_pips <= 0:
            raise ValueError("child_take_profit_pips must be positive.")
        if self.pip_value <= 0:
            raise ValueError("pip_value must be positive.")

    def on_init(self) -> None:
        self.state.setdefault("previous_rsi", None)

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        return ensure_no_signal_columns(data)

    def on_event(self, context: StrategyContext) -> list[TradeAction]:
        if not is_bar_close(context):
            return []
        prices = historical_mid_prices(context)
        rsi = rolling_rsi(prices, self.rsi_period)
        if rsi is None:
            return []

        previous_rsi = self.state.get("previous_rsi")
        self.state["previous_rsi"] = rsi
        actions: list[TradeAction] = []
        actions.extend(self._process_side("BUY", rsi, previous_rsi, context))
        actions.extend(self._process_side("SELL", rsi, previous_rsi, context))
        return actions

    def _process_side(
        self,
        side: str,
        rsi: float,
        previous_rsi: float | None,
        context: StrategyContext,
    ) -> list[TradeAction]:
        positions = positions_for_side(context, side)
        current_price = current_mid_price(context)
        child_actions = self._child_take_profit_actions(side, current_price, positions)
        if child_actions:
            return child_actions

        if not positions:
            if self._initial_trigger(side, rsi, previous_rsi):
                group_id = self._group_id(context, side)
                return [
                    TradeAction(
                        action_type="OPEN",
                        symbol=context.symbol,
                        side=side,  # type: ignore[arg-type]
                        volume=self.initial_lot,
                        setup_id=group_id,
                        group_id=group_id,
                        metadata={"role": "parent"},
                        reason=f"Initial {side} decomposition entry",
                    )
                ]
            return []

        if not self._drawdown_trigger(side, current_price, positions):
            return []
        if not self._rsi_confirmed(side, rsi):
            return []

        oldest = oldest_position(positions)
        if oldest is None:
            return []
        subtract_amount = min(self.vol_decrease, float(oldest.volume or 0.0))
        if subtract_amount <= 0.0:
            return []

        group_id = self._group_id(context, side, positions)
        new_lot = self.initial_lot + (len(positions) * subtract_amount)
        average_price = weighted_average_price(positions) or current_price
        target_tp = (
            average_price + (self.trail_points * self.pip_value)
            if side == "BUY"
            else average_price - (self.trail_points * self.pip_value)
        )
        return [
            TradeAction(
                action_type="REDUCE",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                ticket=oldest.ticket,
                volume=subtract_amount,
                setup_id=group_id,
                group_id=group_id,
                reason=f"Decompose oldest {side} position",
            ),
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                volume=new_lot,
                setup_id=group_id,
                group_id=group_id,
                metadata={"role": "child", "parent_ticket": oldest.ticket},
                reason=f"{side} decomposition cycle add",
            ),
            TradeAction(
                action_type="MODIFY_TP",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                take_profit=target_tp,
                setup_id=group_id,
                group_id=group_id,
                reason=f"Consolidate {side} basket TP",
            ),
        ]

    def _child_take_profit_actions(
        self,
        side: str,
        current_price: float,
        positions,
    ) -> list[TradeAction]:
        child = self._first_child_at_target(side, current_price, positions)
        if child is None:
            return []

        group_id = self._position_group_id(child)
        actions = [
            TradeAction(
                action_type="CLOSE",
                symbol=child.symbol,
                side=side,  # type: ignore[arg-type]
                ticket=child.ticket,
                volume=child.volume,
                setup_id=child.setup_id or group_id,
                group_id=group_id,
                reason=f"Close first {side} decomposition child at TP",
            )
        ]
        for position in positions:
            if position.ticket == child.ticket:
                continue
            actions.append(
                TradeAction(
                    action_type="MOVE_TO_BREAKEVEN",
                    symbol=position.symbol,
                    side=side,  # type: ignore[arg-type]
                    ticket=position.ticket,
                    setup_id=position.setup_id or group_id,
                    group_id=self._position_group_id(position) or group_id,
                    reason=f"Move remaining {side} decomposition trade to breakeven",
                )
            )
        return actions

    def _first_child_at_target(self, side: str, current_price: float, positions):
        target_distance = self.child_take_profit_pips * self.pip_value
        children = [position for position in positions if self._is_child(position)]
        for position in sorted(children, key=lambda item: str(item.opened_at or "")):
            if side == "BUY" and current_price >= position.open_price + target_distance:
                return position
            if (
                side == "SELL"
                and current_price <= position.open_price - target_distance
            ):
                return position
        return None

    @staticmethod
    def _is_child(position) -> bool:
        metadata = getattr(position, "metadata", {}) or {}
        return metadata.get("role") == "child" or metadata.get("decomposition_child")

    def _group_id(self, context: StrategyContext, side: str, positions=None) -> str:
        for position in positions or []:
            group_id = self._position_group_id(position)
            if group_id:
                return group_id
        return f"{context.strategy_id}:{context.symbol}:{side}:decomposition"

    @staticmethod
    def _position_group_id(position) -> str | None:
        metadata = getattr(position, "metadata", {}) or {}
        return (
            metadata.get("group_id")
            or metadata.get("setup_id")
            or getattr(position, "setup_id", None)
        )

    def _initial_trigger(
        self,
        side: str,
        rsi: float,
        previous_rsi: float | None,
    ) -> bool:
        if previous_rsi is None:
            return False
        if side == "BUY":
            return previous_rsi < self.os_level <= rsi
        return previous_rsi > self.ob_level >= rsi

    def _rsi_confirmed(self, side: str, rsi: float) -> bool:
        return rsi <= self.os_level if side == "BUY" else rsi >= self.ob_level

    def _drawdown_trigger(self, side: str, current_price: float, positions) -> bool:
        distance = self.trade_distance * self.pip_value
        prices = [float(position.open_price or 0.0) for position in positions]
        if side == "BUY":
            lowest = min(prices)
            return current_price <= lowest - distance
        highest = max(prices)
        return current_price >= highest + distance
