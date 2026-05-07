"""RSI decomposing re-entry strategy with hedge entries."""

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
    positions_for_side,
)


class RsiDecomposingReentryStrategy(StatefulStrategyMixin, BaseStrategy):
    """Faithful port of an RSI EA that decomposes old entries and re-enters."""

    strategy_name = "RsiDecomposingReentryStrategy"
    strategy_type = "stateful"
    signal_schema_version = "1.0"
    action_schema_version = "1.0"

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.rsi_period = int(self.params.get("rsi_period", 14))
        self.os_level = float(self.params.get("os_level", 30.0))
        self.ob_level = float(self.params.get("ob_level", 70.0))
        self.balance_increase = float(self.params.get("balance_increase", 3000.0))
        self.volume_increase = float(self.params.get("volume_increase", 0.06))
        self.volume_decrease = float(self.params.get("volume_decrease", 0.02))
        self.when_to_trail_pips = float(self.params.get("when_to_trail_pips", 20.0))
        self.trail_by_pips = float(self.params.get("trail_by_pips", 10.0))
        self.trade_distance_pips = float(self.params.get("trade_distance_pips", 20.0))
        self.initial_lot = float(self.params.get("initial_lot", 0.06))
        self.min_lot = float(self.params.get("min_lot", 0.01))
        self.max_lot = float(self.params.get("max_lot", 100.0))
        self.lot_step = float(self.params.get("lot_step", 0.01))
        self.pip_value = float(self.params.get("pip_value", 0.0001))
        self._rsi_cache_key: tuple[int, int] | None = None
        self._rsi_cache: pd.Series | None = None
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
        if self.volume_decrease <= 0:
            raise ValueError("volume_decrease must be positive.")
        if self.when_to_trail_pips <= 0:
            raise ValueError("when_to_trail_pips must be positive.")
        if self.trail_by_pips <= 0:
            raise ValueError("trail_by_pips must be positive.")
        if self.trade_distance_pips <= 0:
            raise ValueError("trade_distance_pips must be positive.")
        if self.initial_lot <= 0:
            raise ValueError("initial_lot must be positive.")
        if self.min_lot <= 0:
            raise ValueError("min_lot must be positive.")
        if self.max_lot < self.min_lot:
            raise ValueError("max_lot must be greater than or equal to min_lot.")
        if self.lot_step <= 0:
            raise ValueError("lot_step must be positive.")
        if self.pip_value <= 0:
            raise ValueError("pip_value must be positive.")

    def on_init(self) -> None:
        self.state.setdefault("previous_rsi", None)
        self.state.setdefault("buy_lot", 0.0)
        self.state.setdefault("sell_lot", 0.0)
        self.state.setdefault("buy_lot_subtract", 0.0)
        self.state.setdefault("sell_lot_subtract", 0.0)
        self.state.setdefault("buy_price", 0.0)
        self.state.setdefault("sell_price", 0.0)

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        return ensure_no_signal_columns(data)

    def on_event(self, context: StrategyContext) -> list[TradeAction]:
        if not self._is_new_bar_event(context):
            return []

        rsi_values = self._rsi_values_for_context(context)
        if len(rsi_values) < 2:
            return []

        rsi = float(rsi_values.iloc[-1])
        previous_rsi = float(rsi_values.iloc[-2])
        self.state["previous_rsi"] = rsi

        buy_positions = positions_for_side(context, "BUY")
        sell_positions = positions_for_side(context, "SELL")
        buy_signal = previous_rsi < self.os_level <= rsi
        sell_signal = previous_rsi > self.ob_level >= rsi
        oppose_buy_signal = previous_rsi > self.os_level >= rsi
        oppose_sell_signal = previous_rsi < self.ob_level <= rsi

        actions: list[TradeAction] = []
        actions.extend(
            self._first_entry(
                "BUY",
                buy_signal or (oppose_sell_signal and bool(sell_positions)),
                context,
                buy_positions,
            )
        )
        actions.extend(
            self._first_entry(
                "SELL",
                sell_signal or (oppose_buy_signal and bool(buy_positions)),
                context,
                sell_positions,
            )
        )
        actions.extend(self._trailing_sl("BUY", buy_positions, context))
        actions.extend(self._trailing_sl("SELL", sell_positions, context))
        actions.extend(self._manage_side("BUY", buy_signal, buy_positions, context))
        actions.extend(self._manage_side("SELL", sell_signal, sell_positions, context))
        return actions

    def _first_entry(
        self,
        side: str,
        signal: bool,
        context: StrategyContext,
        positions: list[PositionSnapshot],
    ) -> list[TradeAction]:
        if not signal or positions:
            return []

        lot = self._lot_size(context)
        price = self._entry_price(side, context)
        subtract = self._normalize_lot(lot / self._volume_ratio())
        side_key = side.lower()
        self.state[f"{side_key}_lot"] = lot
        self.state[f"{side_key}_lot_subtract"] = subtract
        self.state[f"{side_key}_price"] = price
        reason = "FBuy" if side == "BUY" else "FSell"
        setup_id = self._setup_id(context.symbol, side)
        return [
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                volume=lot,
                setup_id=setup_id,
                group_id=setup_id,
                reason=reason,
                metadata={
                    "role": "first",
                    "comment": reason,
                    "basket_type": "rsi_decomposing_reentry",
                },
            )
        ]

    def _trailing_sl(
        self,
        side: str,
        positions: list[PositionSnapshot],
        context: StrategyContext,
    ) -> list[TradeAction]:
        if not positions or self._has_child(positions, side):
            return []

        actions: list[TradeAction] = []
        trail_trigger = self.when_to_trail_pips * self.pip_value
        trail_by = self.trail_by_pips * self.pip_value
        for position in positions:
            current_price = float(
                position.current_price or self._entry_price(side, context)
            )
            open_price = float(position.open_price or 0.0)
            if side == "BUY":
                if current_price < open_price + trail_trigger:
                    continue
                new_sl = self._round_price(current_price - trail_by)
                if position.stop_loss and new_sl <= float(position.stop_loss):
                    continue
            else:
                if current_price > open_price - trail_trigger:
                    continue
                new_sl = self._round_price(current_price + trail_by)
                if position.stop_loss and new_sl >= float(position.stop_loss):
                    continue
            actions.append(
                TradeAction(
                    action_type="MODIFY_SL",
                    symbol=context.symbol,
                    side=side,  # type: ignore[arg-type]
                    ticket=position.ticket,
                    stop_loss=new_sl,
                    reason=f"Trail {side} SL",
                )
            )
        return actions

    def _manage_side(
        self,
        side: str,
        signal: bool,
        positions: list[PositionSnapshot],
        context: StrategyContext,
    ) -> list[TradeAction]:
        if not positions or not signal:
            return []

        bid = float((context.current_tick or {}).get("bid", 0.0) or 0.0)
        ask = float((context.current_tick or {}).get("ask", bid) or bid)
        next_price = self._next_price(side, positions)
        if side == "BUY" and bid >= next_price:
            return []
        if side == "SELL" and ask <= next_price:
            return []

        target = self._decomposition_target(side, positions)
        if target is None:
            return []

        side_key = side.lower()
        base_lot = float(self.state.get(f"{side_key}_lot") or self._lot_size(context))
        subtract = float(
            self.state.get(f"{side_key}_lot_subtract")
            or self._normalize_lot(base_lot / self._volume_ratio())
        )
        subtract = min(subtract, float(target.volume or 0.0))
        if subtract <= 0.0:
            return []

        new_lot = self._normalize_lot(base_lot + (len(positions) * subtract))
        entry_price = self._entry_price(side, context)
        target_tp = self._projected_basket_tp(
            side,
            positions,
            reduce_ticket=target.ticket,
            reduce_volume=subtract,
            add_price=entry_price,
            add_volume=new_lot,
        )
        reason = "CBuy" if side == "BUY" else "CSell"
        setup_id = self._setup_id(context.symbol, side)

        return [
            TradeAction(
                action_type="REDUCE",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                ticket=target.ticket,
                volume=subtract,
                setup_id=setup_id,
                group_id=setup_id,
                reason=f"Partial close {side} decomposition target",
            ),
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                volume=new_lot,
                setup_id=setup_id,
                group_id=setup_id,
                reason=reason,
                metadata={
                    "role": "child",
                    "comment": reason,
                    "basket_type": "rsi_decomposing_reentry",
                    "parent_ticket": target.ticket,
                },
            ),
            TradeAction(
                action_type="MODIFY_SL",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                stop_loss=0.0,
                setup_id=setup_id,
                group_id=setup_id,
                reason=f"Clear {side} SL before weighted basket TP",
            ),
            TradeAction(
                action_type="MODIFY_TP",
                symbol=context.symbol,
                side=side,  # type: ignore[arg-type]
                take_profit=target_tp,
                setup_id=setup_id,
                group_id=setup_id,
                reason=f"Move {side} TP to decomposed weighted target",
            ),
        ]

    def _next_price(self, side: str, positions: list[PositionSnapshot]) -> float:
        distance = self.trade_distance_pips * self.pip_value
        prices = [float(position.open_price or 0.0) for position in positions]
        if side == "BUY":
            return self._round_price(min(prices) - distance)
        return self._round_price(max(prices) + distance)

    @staticmethod
    def _decomposition_target(
        side: str, positions: list[PositionSnapshot]
    ) -> PositionSnapshot | None:
        if not positions:
            return None
        if side == "BUY":
            return max(
                positions, key=lambda position: float(position.open_price or 0.0)
            )
        return min(positions, key=lambda position: float(position.open_price or 0.0))

    def _projected_basket_tp(
        self,
        side: str,
        positions: list[PositionSnapshot],
        *,
        reduce_ticket,
        reduce_volume: float,
        add_price: float,
        add_volume: float,
    ) -> float:
        rows: list[tuple[float, float]] = []
        for position in positions:
            volume = float(position.volume or 0.0)
            if position.ticket == reduce_ticket:
                volume = max(0.0, volume - reduce_volume)
            if volume > 0.0:
                rows.append((float(position.open_price or 0.0), volume))
        rows.append((float(add_price), float(add_volume)))
        total_volume = sum(volume for _, volume in rows)
        average = (
            sum(price * volume for price, volume in rows) / total_volume
            if total_volume > 0.0
            else float(add_price)
        )
        trail = self.trail_by_pips * self.pip_value
        return self._round_price(average + trail if side == "BUY" else average - trail)

    def _has_child(self, positions: list[PositionSnapshot], side: str) -> bool:
        target_comment = "CBuy" if side == "BUY" else "CSell"
        for position in positions:
            metadata = position.metadata or {}
            comment = str(metadata.get("comment", "") or "")
            if metadata.get("role") == "child" or comment == target_comment:
                return True
        return False

    def _lot_size(self, context: StrategyContext) -> float:
        balance = float(
            context.account.get("balance", context.account.get("equity", 0.0)) or 0.0
        )
        if balance > 0.0 and self.balance_increase > 0.0:
            return self._normalize_lot(
                self.volume_increase * (balance / self.balance_increase)
            )
        return self._normalize_lot(self.initial_lot)

    def _normalize_lot(self, lot: float) -> float:
        step = self.lot_step if self.lot_step > 0.0 else 0.01
        rounded = round(float(lot) / step) * step
        bounded = min(max(rounded, self.min_lot), self.max_lot)
        return round(bounded + 1e-12, 2)

    def _volume_ratio(self) -> float:
        if self.volume_decrease <= 0.0:
            return 1.0
        return self.volume_increase / self.volume_decrease

    def _entry_price(self, side: str, context: StrategyContext) -> float:
        tick = context.current_tick or {}
        bid = float(tick.get("bid", 0.0) or 0.0)
        ask = float(tick.get("ask", bid) or bid)
        return ask if side == "BUY" else bid

    def _round_price(self, price: float) -> float:
        return round(float(price), int(self.params.get("digits", 5)))

    @staticmethod
    def _setup_id(symbol: str, side: str) -> str:
        return f"{symbol}:{side.lower()}:rsi_decomposing_reentry"

    @staticmethod
    def _is_new_bar_event(context: StrategyContext) -> bool:
        tick = context.current_tick or {}
        phase = str(tick.get("is_bar_close", "") or "").lower()
        phases = {part.strip() for part in phase.split("|") if part.strip()}
        if "open" in phases:
            return True

        # Unit tests and hand-built contexts usually provide only closed bars.
        # Real timeframe tick data has source_bar_time, so it will use open only.
        return "source_bar_time" not in tick and "close" in phases

    @staticmethod
    def _bar_close_prices(context: StrategyContext) -> pd.Series:
        data = context.market_data
        if data is None or data.empty:
            return pd.Series(dtype="float64")

        tick_index = int(
            getattr(context, "tick_index", context.metadata.get("tick_index", 0))
        )
        window = data.iloc[: tick_index + 1]
        if "is_bar_close" in window.columns:
            phases = window["is_bar_close"].astype(str).str.lower()
            close_mask = phases.apply(
                lambda value: "close"
                in {part.strip() for part in value.split("|") if part.strip()}
            )
            window = window.loc[close_mask]
        if window.empty:
            return pd.Series(dtype="float64")

        price_col = "close" if "close" in window.columns else "bid"
        prices = pd.to_numeric(window[price_col], errors="coerce")
        if "source_bar_time" in window.columns:
            close_frame = pd.DataFrame(
                {
                    "time": pd.to_datetime(window["source_bar_time"], errors="coerce"),
                    "price": prices,
                }
            ).dropna()
            if close_frame.empty:
                return pd.Series(dtype="float64")
            return close_frame.groupby("time")["price"].last().dropna()

        prices.index = window.index
        return prices.dropna()

    def _rsi_values_for_context(self, context: StrategyContext) -> pd.Series:
        tick = context.current_tick or {}
        if "source_bar_time" not in tick:
            return self._rsi_values(self._bar_close_prices(context))

        data = context.market_data
        if data is None or data.empty:
            return pd.Series(dtype="float64")

        cache_key = (id(data), len(data))
        if self._rsi_cache_key != cache_key or self._rsi_cache is None:
            self._rsi_cache_key = cache_key
            self._rsi_cache = self._rsi_values(self._all_bar_close_prices(data))

        current_bar_time = pd.to_datetime(tick.get("source_bar_time"), errors="coerce")
        if pd.isna(current_bar_time):
            return self._rsi_cache
        return self._rsi_cache.loc[self._rsi_cache.index < current_bar_time]

    @staticmethod
    def _all_bar_close_prices(data: pd.DataFrame) -> pd.Series:
        if data is None or data.empty:
            return pd.Series(dtype="float64")
        window = data
        if "is_bar_close" in window.columns:
            phases = window["is_bar_close"].astype(str).str.lower()
            close_mask = phases.apply(
                lambda value: "close"
                in {part.strip() for part in value.split("|") if part.strip()}
            )
            window = window.loc[close_mask]
        if window.empty:
            return pd.Series(dtype="float64")

        price_col = "close" if "close" in window.columns else "bid"
        prices = pd.to_numeric(window[price_col], errors="coerce")
        if "source_bar_time" in window.columns:
            close_frame = pd.DataFrame(
                {
                    "time": pd.to_datetime(window["source_bar_time"], errors="coerce"),
                    "price": prices,
                }
            ).dropna()
            if close_frame.empty:
                return pd.Series(dtype="float64")
            return close_frame.groupby("time")["price"].last().dropna()

        prices.index = window.index
        return prices.dropna()

    def _rsi_values(self, prices: pd.Series) -> pd.Series:
        if len(prices) < self.rsi_period + 2:
            return pd.Series(dtype="float64")
        prices = pd.to_numeric(prices, errors="coerce").dropna()
        delta = prices.diff()
        gains = delta.clip(lower=0.0)
        losses = -delta.clip(upper=0.0)

        rsi = pd.Series(index=prices.index, dtype="float64")
        avg_gain = float(gains.iloc[1 : self.rsi_period + 1].mean())
        avg_loss = float(losses.iloc[1 : self.rsi_period + 1].mean())

        def calc_rsi(gain_value: float, loss_value: float) -> float:
            if loss_value == 0.0:
                return 100.0 if gain_value > 0.0 else 50.0
            rs = gain_value / loss_value
            return 100.0 - (100.0 / (1.0 + rs))

        rsi.iloc[self.rsi_period] = calc_rsi(avg_gain, avg_loss)
        for index in range(self.rsi_period + 1, len(prices)):
            avg_gain = (
                (avg_gain * (self.rsi_period - 1)) + float(gains.iloc[index])
            ) / self.rsi_period
            avg_loss = (
                (avg_loss * (self.rsi_period - 1)) + float(losses.iloc[index])
            ) / self.rsi_period
            rsi.iloc[index] = calc_rsi(avg_gain, avg_loss)

        return rsi.dropna()
