"""Bi-directional RSI martingale example strategy."""

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
    basket_pnl,
    current_mid_price,
    ensure_no_signal_columns,
    historical_mid_prices,
    is_bar_close,
    positions_for_side,
    rolling_rsi,
)


class RsiMartingaleStrategy(StatefulStrategyMixin, BaseStrategy):
    """Both BUY and SELL martingale baskets run concurrently and independently."""

    strategy_name = "RsiMartingaleStrategy"
    strategy_type = "stateful"
    signal_schema_version = "1.0"
    action_schema_version = "1.0"

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.rsi_period = int(self.params.get("rsi_period", 14))
        self.rsi_oversold = float(self.params.get("rsi_oversold", 30.0))
        self.rsi_overbought = float(self.params.get("rsi_overbought", 70.0))
        self.initial_lot = float(self.params.get("initial_lot", 0.1))
        self.multiplier = float(self.params.get("multiplier", 2.0))
        self.min_step_pips = float(self.params.get("min_step_pips", 30.0))
        self.target_profit_usd = float(self.params.get("target_profit_usd", 10.0))
        self.pip_value = float(self.params.get("pip_value", 0.0001))
        self.max_lot = float(self.params.get("max_lot", 50.0))
        self.max_steps = int(self.params.get("max_steps", 999999))
        self.strategy_risk_controls = self.params.get("risk_controls", {})
        self._validate_params()

    def _validate_params(self) -> None:
        if self.rsi_period <= 0:
            raise ValueError("rsi_period must be positive.")
        if not 0 < self.rsi_oversold < self.rsi_overbought < 100:
            raise ValueError(
                "RSI thresholds must satisfy 0 < oversold < overbought < 100."
            )
        if self.initial_lot <= 0:
            raise ValueError("initial_lot must be positive.")
        if self.multiplier <= 1:
            raise ValueError("multiplier must be greater than 1.")
        if self.min_step_pips <= 0:
            raise ValueError("min_step_pips must be positive.")
        if self.pip_value <= 0:
            raise ValueError("pip_value must be positive.")
        if self.max_lot <= 0:
            raise ValueError("max_lot must be positive.")
        if self.max_steps <= 0:
            raise ValueError("max_steps must be positive.")

    def on_init(self) -> None:
        self.state.setdefault("buy", {"last_price": 0.0, "total_vol": 0.0, "steps": 0})
        self.state.setdefault("sell", {"last_price": 0.0, "total_vol": 0.0, "steps": 0})

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        return ensure_no_signal_columns(data)

    def on_event(self, context: StrategyContext) -> list[TradeAction]:
        if not is_bar_close(context):
            return []
        prices = historical_mid_prices(context)
        rsi = rolling_rsi(prices, self.rsi_period)
        if rsi is None:
            return []

        current_price = current_mid_price(context)
        step = self.min_step_pips * self.pip_value
        actions: list[TradeAction] = []
        actions.extend(self._side_actions("BUY", rsi, current_price, step, context))
        actions.extend(self._side_actions("SELL", rsi, current_price, step, context))
        return actions

    def _side_actions(
        self,
        side: str,
        rsi: float,
        current_price: float,
        step: float,
        context: StrategyContext,
    ) -> list[TradeAction]:
        positions = positions_for_side(context, side)
        side_key = side.lower()
        side_state = self.state.setdefault(
            side_key,
            {"last_price": 0.0, "total_vol": 0.0, "steps": 0},
        )
        is_buy = side == "BUY"
        trigger = rsi <= self.rsi_oversold if is_buy else rsi >= self.rsi_overbought

        if positions and basket_pnl(positions) >= self.target_profit_usd:
            side_state.update({"last_price": 0.0, "total_vol": 0.0, "steps": 0})
            return [
                TradeAction(
                    action_type="CLOSE_GROUP",
                    symbol=context.symbol,
                    side=side,  # type: ignore[arg-type]
                    reason=f"{side} basket target profit reached",
                )
            ]

        if not positions:
            side_state.update({"last_price": 0.0, "total_vol": 0.0, "steps": 0})
            if not trigger:
                return []
            side_state.update(
                {
                    "last_price": current_price,
                    "total_vol": self.initial_lot,
                    "steps": 1,
                }
            )
            return [
                TradeAction(
                    action_type="OPEN",
                    symbol=context.symbol,
                    side=side,  # type: ignore[arg-type]
                    volume=self.initial_lot,
                    metadata={
                        "martingale_step": 1,
                        "setup_id": f"{side.lower()}_martingale",
                    },
                    reason=f"Initial {side} RSI martingale entry",
                )
            ]

        last_price = float(side_state.get("last_price") or positions[-1].open_price)
        drawdown = last_price - current_price if is_buy else current_price - last_price
        if drawdown < step or not trigger:
            return []

        steps = int(side_state.get("steps") or len(positions))
        if steps >= self.max_steps:
            return []

        total_vol = float(
            side_state.get("total_vol") or sum(p.volume for p in positions)
        )
        new_lot = min(total_vol * self.multiplier, self.max_lot)
        side_state.update(
            {
                "last_price": current_price,
                "total_vol": total_vol + new_lot,
                "steps": steps + 1,
            }
        )
        return [
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                volume=new_lot,
                metadata={
                    "martingale_step": steps + 1,
                    "setup_id": f"{side.lower()}_martingale",
                },
                reason=f"{side} martingale drawdown add",
            )
        ]
