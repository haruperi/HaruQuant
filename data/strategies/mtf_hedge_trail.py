"""Multi-timeframe structure hedge and trailing-management strategy."""

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

from data.strategies.stateful_common import ensure_no_signal_columns, is_bar_close


class StructureHedgeTrailStrategy(StatefulStrategyMixin, BaseStrategy):
    """Port of a two-timeframe higher-low/lower-high EA with basket TP trailing."""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.higher_timeframe = str(self.params.get("higher_timeframe", "H1")).upper()
        self.lower_timeframe = str(self.params.get("lower_timeframe", "M5")).upper()
        self.ht_min_distance_pips = float(self.params.get("ht_min_distance_pips", 5.0))
        self.lt_min_distance_pips = float(self.params.get("lt_min_distance_pips", 2.0))
        self.take_profit_pips = float(self.params.get("take_profit_pips", 30.0))
        self.stop_loss_pips = float(self.params.get("stop_loss_pips", 5.0))
        self.when_to_trail_pips = float(self.params.get("when_to_trail_pips", 10.0))
        self.balance_increase = float(self.params.get("balance_increase", 3000.0))
        self.volume_increase = float(self.params.get("volume_increase", 0.01))
        self.initial_lot = float(self.params.get("initial_lot", 0.01))
        self.min_lot = float(self.params.get("min_lot", 0.01))
        self.max_lot = float(self.params.get("max_lot", 100.0))
        self.pip_value = float(self.params.get("pip_value", 0.0001))

    def on_init(self) -> None:
        self.state.setdefault("bought", False)
        self.state.setdefault("sold", False)

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        return ensure_no_signal_columns(data)

    def on_event(self, context: StrategyContext) -> list[TradeAction]:
        if not is_bar_close(context):
            return []

        lower_bars = self._lower_bars(context)
        higher_bars = self._higher_bars(lower_bars)
        if len(lower_bars) < 2 or len(higher_bars) < 2:
            return []

        buy_positions = self._positions(context, "BUY")
        sell_positions = self._positions(context, "SELL")

        buy_signal = self._higher_low(
            higher_bars, self.ht_min_distance_pips * self.pip_value
        ) and self._higher_low(lower_bars, self.lt_min_distance_pips * self.pip_value)
        sell_signal = self._lower_high(
            higher_bars, self.ht_min_distance_pips * self.pip_value
        ) and self._lower_high(lower_bars, self.lt_min_distance_pips * self.pip_value)

        actions: list[TradeAction] = []
        buy_entries = self._entry_actions("BUY", buy_signal, context)
        sell_entries = self._entry_actions("SELL", sell_signal, context)
        actions.extend(buy_entries)
        actions.extend(sell_entries)

        if not buy_positions and not buy_entries:
            self.state["bought"] = False
        if not sell_positions and not sell_entries:
            self.state["sold"] = False

        actions.extend(self._trailing_tp_actions("BUY", buy_positions, context))
        actions.extend(self._trailing_tp_actions("SELL", sell_positions, context))
        actions.extend(
            self._trailing_sl_actions("BUY", buy_positions, lower_bars, context)
        )
        actions.extend(
            self._trailing_sl_actions("SELL", sell_positions, lower_bars, context)
        )
        return actions

    def _entry_actions(
        self, side: str, signal: bool, context: StrategyContext
    ) -> list[TradeAction]:
        flag = "bought" if side == "BUY" else "sold"
        if not signal or bool(self.state.get(flag)):
            return []

        price = self._entry_price(side, context)
        tp = self._round_price(
            price + self.take_profit_pips * self.pip_value
            if side == "BUY"
            else price - self.take_profit_pips * self.pip_value
        )
        self.state["bought"] = side == "BUY"
        self.state["sold"] = side == "SELL"
        setup_id = self._setup_id(context.symbol, side)

        return [
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                volume=self._lot_size(context),
                stop_loss=0.0,
                take_profit=tp,
                setup_id=setup_id,
                group_id=setup_id,
                reason=side.title(),
                metadata={"basket_type": "structure_hedge_trail"},
            )
        ]

    def _trailing_tp_actions(
        self,
        side: str,
        positions: list[PositionSnapshot],
        context: StrategyContext,
    ) -> list[TradeAction]:
        if len(positions) < 2:
            return []

        average_tp = self._simple_average_price(positions)
        actions: list[TradeAction] = []
        for position in positions:
            current_tp = float(position.take_profit or 0.0)
            current_price = float(
                position.current_price or self._entry_price(side, context)
            )
            if current_tp != 0.0:
                if average_tp == current_tp:
                    continue
                if side == "BUY" and average_tp <= current_price:
                    continue
                if side == "SELL" and average_tp >= current_price:
                    continue
            actions.extend(
                [
                    TradeAction(
                        action_type="MODIFY_SL",
                        symbol=context.symbol,
                        side=side,  # type: ignore[arg-type]
                        ticket=position.ticket,
                        stop_loss=0.0,
                        reason=f"Clear {side} SL before average TP trail",
                    ),
                    TradeAction(
                        action_type="MODIFY_TP",
                        symbol=context.symbol,
                        side=side,  # type: ignore[arg-type]
                        ticket=position.ticket,
                        take_profit=average_tp,
                        reason=f"Trail {side} TP to simple basket average",
                    ),
                ]
            )
        return actions

    def _trailing_sl_actions(
        self,
        side: str,
        positions: list[PositionSnapshot],
        lower_bars: pd.DataFrame,
        context: StrategyContext,
    ) -> list[TradeAction]:
        if len(positions) != 1 or lower_bars.empty:
            return []

        position = positions[0]
        current_price = float(
            position.current_price or self._entry_price(side, context)
        )
        open_price = float(position.open_price or 0.0)
        trigger_distance = self.when_to_trail_pips * self.pip_value
        if side == "BUY" and current_price < open_price + trigger_distance:
            return []
        if side == "SELL" and current_price > open_price - trigger_distance:
            return []

        previous_bar = lower_bars.iloc[-1]
        new_sl = self._round_price(
            float(previous_bar["low"] if side == "BUY" else previous_bar["high"])
        )
        current_sl = float(position.stop_loss or 0.0)
        if current_sl != 0.0:
            if side == "BUY" and (new_sl <= current_sl or new_sl >= current_price):
                return []
            if side == "SELL" and (new_sl >= current_sl or new_sl <= current_price):
                return []

        return [
            TradeAction(
                action_type="MODIFY_SL",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                ticket=position.ticket,
                stop_loss=new_sl,
                reason=f"Trail {side} SL to previous lower-timeframe bar",
            )
        ]

    def _lower_bars(self, context: StrategyContext) -> pd.DataFrame:
        data = context.market_data
        tick_index = int(
            context.metadata.get("tick_index", 0) if context.metadata else 0
        )
        if data is None or data.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close"])

        window = data.iloc[: tick_index + 1].copy()
        if "source_bar_time" in window.columns:
            source_times = pd.to_datetime(window["source_bar_time"], errors="coerce")
        elif isinstance(window.index, pd.DatetimeIndex):
            source_times = window.index.floor(self._pandas_freq(self.lower_timeframe))
        else:
            return pd.DataFrame(columns=["open", "high", "low", "close"])

        bid = pd.to_numeric(window["bid"], errors="coerce")
        bars = (
            pd.DataFrame({"source_bar_time": source_times, "bid": bid})
            .dropna()
            .groupby("source_bar_time")["bid"]
            .agg(open="first", high="max", low="min", close="last")
            .dropna()
        )
        return bars

    def _higher_bars(self, lower_bars: pd.DataFrame) -> pd.DataFrame:
        if lower_bars.empty:
            return lower_bars
        freq = self._pandas_freq(self.higher_timeframe)
        return (
            lower_bars.resample(freq)
            .agg(
                open=("open", "first"),
                high=("high", "max"),
                low=("low", "min"),
                close=("close", "last"),
            )
            .dropna()
        )

    @staticmethod
    def _higher_low(bars: pd.DataFrame, min_distance: float) -> bool:
        current = bars.iloc[-1]
        previous = bars.iloc[-2]
        return bool(
            float(current["low"]) > float(previous["low"])
            and float(current["open"]) < float(current["close"])
            and float(current["low"]) - float(previous["low"]) > float(min_distance)
        )

    @staticmethod
    def _lower_high(bars: pd.DataFrame, min_distance: float) -> bool:
        current = bars.iloc[-1]
        previous = bars.iloc[-2]
        return bool(
            float(current["high"]) < float(previous["high"])
            and float(current["open"]) > float(current["close"])
            and float(previous["high"]) - float(current["high"]) > float(min_distance)
        )

    @staticmethod
    def _positions(context: StrategyContext, side: str) -> list[PositionSnapshot]:
        target = side.upper()
        return [
            position
            for position in context.positions_for_symbol()
            if str(position.side).upper() == target
        ]

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

    def _simple_average_price(self, positions: list[PositionSnapshot]) -> float:
        total = sum(float(position.open_price) for position in positions)
        return self._round_price(total / len(positions))

    def _round_price(self, price: float) -> float:
        return round(float(price), int(self.params.get("digits", 5)))

    @staticmethod
    def _setup_id(symbol: str, side: str) -> str:
        return f"{symbol}:{side.lower()}:structure_hedge_trail"

    @staticmethod
    def _pandas_freq(timeframe: str) -> str:
        value = str(timeframe).strip().upper()
        if value.startswith("M") and value[1:].isdigit():
            return f"{int(value[1:])}min"
        if value.startswith("H") and value[1:].isdigit():
            return f"{int(value[1:])}h"
        if value.startswith("D") and value[1:].isdigit():
            return f"{int(value[1:])}D"
        return value
