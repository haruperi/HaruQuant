"""RSI cost-averaging plus pyramiding stateful strategy."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from services.strategy.base import BaseStrategy
from services.strategy.stateful import (
    PositionSnapshot,
    StatefulStrategyMixin,
    StrategyContext,
    TradeAction,
)

from data.strategies.stateful_common import (
    ensure_no_signal_columns,
    historical_mid_prices,
    is_bar_close,
    positions_for_side,
)


class RsiAveragingPyramidStrategy(StatefulStrategyMixin, BaseStrategy):
    """Faithful port of an RSI basket EA that averages losers and pyramids winners."""

    strategy_name = "RsiAveragingPyramidStrategy"
    strategy_type = "stateful"
    signal_schema_version = "1.0"
    action_schema_version = "1.0"

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.rsi_period = int(self.params.get("rsi_period", 14))
        self.os_level = float(self.params.get("os_level", 30.0))
        self.ob_level = float(self.params.get("ob_level", 70.0))
        self.balance_increase = float(self.params.get("balance_increase", 2000.0))
        self.volume_increase = float(self.params.get("volume_increase", 0.01))
        self.initial_lot = float(self.params.get("initial_lot", 0.01))
        self.min_lot = float(self.params.get("min_lot", 0.01))
        self.max_lot = float(self.params.get("max_lot", 100.0))
        self.cost_averaging_distance_pips = float(
            self.params.get("cost_averaging_distance_pips", 10.0)
        )
        self.pyramiding_distance_pips = float(
            self.params.get("pyramiding_distance_pips", 10.0)
        )
        self.lot_divisor = float(self.params.get("lot_divisor", 2.0))
        self.sl_displacement_pips = float(self.params.get("sl_displacement_pips", 5.0))
        self.pip_value = float(self.params.get("pip_value", 0.0001))
        self.strategy_risk_controls = self.params.get("risk_controls", {})
        self._validate_params()

    def _validate_params(self) -> None:
        if self.rsi_period <= 0:
            raise ValueError("rsi_period must be positive.")
        if not 0 < self.os_level < self.ob_level < 100:
            raise ValueError("RSI levels must satisfy 0 < os_level < ob_level < 100.")
        if self.balance_increase <= 0:
            raise ValueError("balance_increase must be positive.")
        if self.volume_increase <= 0:
            raise ValueError("volume_increase must be positive.")
        if self.initial_lot <= 0:
            raise ValueError("initial_lot must be positive.")
        if self.min_lot <= 0:
            raise ValueError("min_lot must be positive.")
        if self.max_lot < self.min_lot:
            raise ValueError("max_lot must be greater than or equal to min_lot.")
        if self.cost_averaging_distance_pips <= 0:
            raise ValueError("cost_averaging_distance_pips must be positive.")
        if self.pyramiding_distance_pips <= 0:
            raise ValueError("pyramiding_distance_pips must be positive.")
        if self.lot_divisor <= 1:
            raise ValueError("lot_divisor must be greater than 1.")
        if self.sl_displacement_pips <= 0:
            raise ValueError("sl_displacement_pips must be positive.")
        if self.pip_value <= 0:
            raise ValueError("pip_value must be positive.")

    def on_init(self) -> None:
        self.state.setdefault("buy", self._empty_side_state())
        self.state.setdefault("sell", self._empty_side_state())

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        return ensure_no_signal_columns(data)

    def on_event(self, context: StrategyContext) -> list[TradeAction]:
        if not is_bar_close(context):
            return []

        rsi_values = self._rsi_values(historical_mid_prices(context))
        if len(rsi_values) < 2:
            return []

        previous_rsi = float(rsi_values.iloc[-1])
        prior_rsi = float(rsi_values.iloc[-2])
        buy_signal = previous_rsi >= self.os_level and prior_rsi < self.os_level
        sell_signal = previous_rsi <= self.ob_level and prior_rsi > self.ob_level

        actions: list[TradeAction] = []
        actions.extend(self._initial_entry("BUY", buy_signal, context))
        actions.extend(self._initial_entry("SELL", sell_signal, context))
        actions.extend(self._cost_average("BUY", buy_signal, context))
        actions.extend(self._cost_average("SELL", sell_signal, context))
        actions.extend(self._pyramid("BUY", context))
        actions.extend(self._pyramid("SELL", context))
        return actions

    def _initial_entry(
        self, side: str, signal: bool, context: StrategyContext
    ) -> list[TradeAction]:
        positions = positions_for_side(context, side)
        side_state = self._side_state(side)
        if positions:
            self._hydrate_side_state(side, context, positions)
            return []

        side_state.update(self._empty_side_state())
        if not signal:
            return []

        price = self._entry_price(side, context)
        lot = self._lot_size(context)
        side_state.update(
            {
                "cost_averaging_lot": lot,
                "pyramiding_lot": self._normalize_lot(lot / self.lot_divisor),
                "next_cost_averaging_price": self._round_price(
                    price - self._cost_distance()
                    if side == "BUY"
                    else price + self._cost_distance()
                ),
                "next_pyramiding_price": self._round_price(
                    price + self._pyramid_distance()
                    if side == "BUY"
                    else price - self._pyramid_distance()
                ),
                "last_price": price,
            }
        )

        return [
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                volume=lot,
                setup_id=self._setup_id(context.symbol, side),
                group_id=self._setup_id(context.symbol, side),
                reason=f"First{side.title()}",
                metadata={"role": "initial", "basket_type": "rsi_averaging_pyramid"},
            )
        ]

    def _cost_average(
        self, side: str, signal: bool, context: StrategyContext
    ) -> list[TradeAction]:
        positions = positions_for_side(context, side)
        if not positions or not signal:
            return []

        self._hydrate_side_state(side, context, positions)
        side_state = self._side_state(side)
        price = self._entry_price(side, context)
        next_price = float(side_state.get("next_cost_averaging_price") or 0.0)
        if side == "BUY" and price > next_price:
            return []
        if side == "SELL" and price < next_price:
            return []

        lot = self._normalize_lot(
            float(side_state.get("cost_averaging_lot") or self._lot_size(context))
        )
        side_state["next_cost_averaging_price"] = self._round_price(
            price - self._cost_distance()
            if side == "BUY"
            else price + self._cost_distance()
        )
        average_price = self._simple_average_price([*positions], price)
        setup_id = self._setup_id(context.symbol, side)

        return [
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                volume=lot,
                setup_id=setup_id,
                group_id=setup_id,
                reason=f"C.Averaging {side.title()}",
                metadata={
                    "role": "cost_average",
                    "basket_type": "rsi_averaging_pyramid",
                },
            ),
            TradeAction(
                action_type="MODIFY_SL",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                stop_loss=0.0,
                reason=f"Clear {side} SL after cost averaging",
            ),
            TradeAction(
                action_type="MODIFY_TP",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                take_profit=average_price,
                reason=f"Move {side} TP to simple basket average",
            ),
        ]

    def _pyramid(self, side: str, context: StrategyContext) -> list[TradeAction]:
        positions = positions_for_side(context, side)
        if not positions:
            return []

        self._hydrate_side_state(side, context, positions)
        side_state = self._side_state(side)
        price = self._entry_price(side, context)
        next_price = float(side_state.get("next_pyramiding_price") or 0.0)
        if side == "BUY" and price < next_price:
            return []
        if side == "SELL" and price > next_price:
            return []

        lot = self._normalize_lot(
            float(side_state.get("pyramiding_lot") or self._lot_size(context))
        )
        last_price = self._round_price(
            price - self._pyramid_distance()
            if side == "BUY"
            else price + self._pyramid_distance()
        )
        stop_loss = self._round_price(
            last_price + self._sl_displacement()
            if side == "BUY"
            else last_price - self._sl_displacement()
        )
        side_state.update(
            {
                "last_price": last_price,
                "next_pyramiding_price": self._round_price(
                    price + self._pyramid_distance()
                    if side == "BUY"
                    else price - self._pyramid_distance()
                ),
                "pyramiding_lot": self._normalize_lot(lot / self.lot_divisor),
            }
        )
        setup_id = self._setup_id(context.symbol, side)

        return [
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                volume=lot,
                setup_id=setup_id,
                group_id=setup_id,
                reason=f"Pyramid {side.title()}",
                metadata={"role": "pyramid", "basket_type": "rsi_averaging_pyramid"},
            ),
            TradeAction(
                action_type="MODIFY_SL",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                stop_loss=stop_loss,
                reason=f"Move {side} SL after pyramid add",
            ),
            TradeAction(
                action_type="MODIFY_TP",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                take_profit=0.0,
                reason=f"Clear {side} TP after pyramid add",
            ),
        ]

    def _hydrate_side_state(
        self, side: str, context: StrategyContext, positions: list[PositionSnapshot]
    ) -> None:
        side_state = self._side_state(side)
        if side_state.get("next_cost_averaging_price") and side_state.get(
            "next_pyramiding_price"
        ):
            return

        last_price = float(positions[-1].open_price)
        lot = self._lot_size(context)
        side_state.setdefault("cost_averaging_lot", lot)
        side_state.setdefault(
            "pyramiding_lot", self._normalize_lot(lot / self.lot_divisor)
        )
        side_state["next_cost_averaging_price"] = self._round_price(
            last_price - self._cost_distance()
            if side == "BUY"
            else last_price + self._cost_distance()
        )
        side_state["next_pyramiding_price"] = self._round_price(
            last_price + self._pyramid_distance()
            if side == "BUY"
            else last_price - self._pyramid_distance()
        )
        side_state["last_price"] = last_price

    def _side_state(self, side: str) -> dict[str, float]:
        return self.state.setdefault(side.lower(), self._empty_side_state())

    @staticmethod
    def _empty_side_state() -> dict[str, float]:
        return {
            "cost_averaging_lot": 0.0,
            "pyramiding_lot": 0.0,
            "next_cost_averaging_price": 0.0,
            "next_pyramiding_price": 0.0,
            "last_price": 0.0,
        }

    def _lot_size(self, context: StrategyContext) -> float:
        balance = float(
            context.account.get("balance", context.account.get("equity", 0.0)) or 0.0
        )
        if balance > 0.0 and self.balance_increase > 0.0:
            return self._normalize_lot(
                self.volume_increase * balance / self.balance_increase
            )
        return self._normalize_lot(self.initial_lot)

    def _normalize_lot(self, lot: float) -> float:
        bounded = min(max(float(lot), self.min_lot), self.max_lot)
        return round(bounded + 1e-12, 2)

    def _entry_price(self, side: str, context: StrategyContext) -> float:
        tick = context.current_tick or {}
        bid = float(tick.get("bid", 0.0) or 0.0)
        ask = float(tick.get("ask", bid) or bid)
        return ask if side == "BUY" else bid

    def _cost_distance(self) -> float:
        return self.cost_averaging_distance_pips * self.pip_value

    def _pyramid_distance(self) -> float:
        return self.pyramiding_distance_pips * self.pip_value

    def _sl_displacement(self) -> float:
        return self.sl_displacement_pips * self.pip_value

    def _round_price(self, price: float) -> float:
        return round(float(price), int(self.params.get("digits", 5)))

    @staticmethod
    def _setup_id(symbol: str, side: str) -> str:
        return f"{symbol}:{side.lower()}:rsi_averaging_pyramid"

    def _simple_average_price(
        self, positions: list[PositionSnapshot], new_price: float
    ) -> float:
        total = sum(float(position.open_price) for position in positions) + float(
            new_price
        )
        return self._round_price(total / (len(positions) + 1))

    def _rsi_values(self, prices: pd.Series) -> pd.Series:
        if len(prices) < self.rsi_period + 2:
            return pd.Series(dtype="float64")
        delta = prices.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(
            alpha=1 / self.rsi_period, adjust=False, min_periods=self.rsi_period
        ).mean()
        avg_loss = loss.ewm(
            alpha=1 / self.rsi_period, adjust=False, min_periods=self.rsi_period
        ).mean()
        rs = avg_gain / avg_loss.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.mask(avg_loss == 0, 100.0)
        return rsi.dropna()
