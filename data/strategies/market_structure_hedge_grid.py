"""Market-structure breakout strategy with hedge stops and grid recovery."""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from services.strategy.base import BaseStrategy
from services.strategy.stateful import (
    OrderSnapshot,
    PositionSnapshot,
    StatefulStrategyMixin,
    StrategyContext,
    TradeAction,
)

from data.strategies.stateful_common import ensure_no_signal_columns


class MarketStructureHedgeGridStrategy(StatefulStrategyMixin, BaseStrategy):
    """Port of a ZigZag market-structure EA with hedge and grid management."""

    event_phases = {"open"}

    F_BUY = "FirstBuy"
    F_SELL = "FirstSell"
    H_BUY = "HedgeBuy"
    H_SELL = "HedgeSell"
    C_BUY = "CABuy"
    C_SELL = "CASell"
    G_BUY = "GridBuy"
    G_SELL = "GridSell"

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.depth = int(self.params.get("zigzag_depth", self.params.get("depth", 12)))
        self.deviation = float(
            self.params.get("zigzag_deviation", self.params.get("deviation", 5.0))
        )
        self.backstep = int(
            self.params.get("zigzag_backstep", self.params.get("backstep", 3))
        )
        self.balance_increase = float(self.params.get("balance_increase", 3000.0))
        self.volume_increase = float(self.params.get("volume_increase", 0.04))
        self.hedge_displacement_pips = float(
            self.params.get("hedge_displacement_pips", 2.0)
        )
        self.profit_factor = float(self.params.get("profit_factor", 2.0))
        self.initial_lot = float(self.params.get("initial_lot", 0.04))
        self.min_lot = float(self.params.get("min_lot", 0.01))
        self.max_lot = float(self.params.get("max_lot", 100.0))
        self.lot_step = float(self.params.get("lot_step", 0.01))
        self.pip_value = float(self.params.get("pip_value", 0.0001))
        self.zigzag_lookback = int(self.params.get("zigzag_lookback", 500))
        self._bars_cache_key: tuple[int, int] | None = None
        self._bars_cache: pd.DataFrame | None = None

    def on_init(self) -> None:
        self.state.setdefault("buy_lot_used", self.initial_lot)
        self.state.setdefault("sell_lot_used", self.initial_lot)
        self.state.setdefault("buy_hedge_distance", 0.0)
        self.state.setdefault("sell_hedge_distance", 0.0)
        self.state.setdefault("next_buy_price", 0.0)
        self.state.setdefault("next_sell_price", 0.0)

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        return ensure_no_signal_columns(data)

    def on_event(self, context: StrategyContext) -> list[TradeAction]:
        if not self._is_new_bar_event(context):
            return []

        bars = self._bars(context)
        if len(bars) < max(8, self.depth + 3):
            return []
        zz = self._zz_values(bars)

        buy_positions = self._positions(context, "BUY")
        sell_positions = self._positions(context, "SELL")
        all_positions = buy_positions + sell_positions
        orders = context.orders_for_symbol()

        actions: list[TradeAction] = []
        if not all_positions and zz is not None:
            if self._bullish_break(bars, zz):
                actions.extend(self._initial_buy_actions(context, zz))
            elif self._bearish_break(bars, zz):
                actions.extend(self._initial_sell_actions(context, zz))

        if len(buy_positions) == 1 and len(sell_positions) == 1:
            actions.extend(self._cost_average_actions(context, orders))

        if len(buy_positions) > 1:
            actions.extend(self._trailing_tp_actions("BUY", buy_positions, context))
            actions.extend(self._cancel_orders_by_comment(context, orders, self.C_SELL))
            actions.extend(self._grid_buy_actions(context, buy_positions))

        if len(sell_positions) > 1:
            actions.extend(self._trailing_tp_actions("SELL", sell_positions, context))
            actions.extend(self._cancel_orders_by_comment(context, orders, self.C_BUY))
            actions.extend(self._grid_sell_actions(context, sell_positions))

        actions.extend(self._cleanup_pending_actions(context, orders, all_positions))
        return actions

    def _initial_buy_actions(
        self, context: StrategyContext, zz: dict[str, float]
    ) -> list[TradeAction]:
        ask = self._entry_price("BUY", context)
        low0 = float(zz["low0"])
        hedge_sell_price = self._round_price(
            low0 - self.hedge_displacement_pips * self.pip_value
        )
        distance = self._round_price(ask - hedge_sell_price)
        buy_tp = self._round_price(ask + distance * self.profit_factor)
        hedge_tp = self._round_price(hedge_sell_price - distance * self.profit_factor)
        lot = self._lot_size(context)
        setup_id = self._setup_id(context.symbol)
        self.state["buy_lot_used"] = lot
        self.state["sell_lot_used"] = lot
        self.state["buy_hedge_distance"] = self._round_price(
            (ask - hedge_sell_price) * self.profit_factor
        )
        self.state["next_buy_price"] = hedge_tp
        self.state["next_sell_price"] = buy_tp

        return [
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side="BUY",
                volume=lot,
                take_profit=buy_tp,
                setup_id=setup_id,
                group_id=setup_id,
                reason=self.F_BUY,
                metadata={"role": self.F_BUY},
            ),
            TradeAction(
                action_type="PLACE_PENDING",
                symbol=context.symbol,
                side="SELL",
                order_type="STOP",
                volume=lot,
                price=hedge_sell_price,
                take_profit=hedge_tp,
                setup_id=setup_id,
                group_id=setup_id,
                reason=self.H_SELL,
                metadata={"role": self.H_SELL},
            ),
        ]

    def _initial_sell_actions(
        self, context: StrategyContext, zz: dict[str, float]
    ) -> list[TradeAction]:
        bid = self._entry_price("SELL", context)
        high0 = float(zz["high0"])
        hedge_buy_price = self._round_price(
            high0 + self.hedge_displacement_pips * self.pip_value
        )
        distance = self._round_price(hedge_buy_price - bid)
        sell_tp = self._round_price(bid - distance * self.profit_factor)
        hedge_tp = self._round_price(hedge_buy_price + distance * self.profit_factor)
        lot = self._lot_size(context)
        setup_id = self._setup_id(context.symbol)
        self.state["sell_lot_used"] = lot
        self.state["buy_lot_used"] = lot
        self.state["sell_hedge_distance"] = self._round_price(
            (hedge_buy_price - bid) * self.profit_factor
        )
        self.state["next_sell_price"] = hedge_tp
        self.state["next_buy_price"] = sell_tp

        return [
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side="SELL",
                volume=lot,
                take_profit=sell_tp,
                setup_id=setup_id,
                group_id=setup_id,
                reason=self.F_SELL,
                metadata={"role": self.F_SELL},
            ),
            TradeAction(
                action_type="PLACE_PENDING",
                symbol=context.symbol,
                side="BUY",
                order_type="STOP",
                volume=lot,
                price=hedge_buy_price,
                take_profit=hedge_tp,
                setup_id=setup_id,
                group_id=setup_id,
                reason=self.H_BUY,
                metadata={"role": self.H_BUY},
            ),
        ]

    def _cost_average_actions(
        self, context: StrategyContext, orders: list[OrderSnapshot]
    ) -> list[TradeAction]:
        if self._num_pending(orders, self.C_BUY) or self._num_pending(
            orders, self.C_SELL
        ):
            return []
        return [
            self._buy_limit_action(context, float(self.state["buy_lot_used"])),
            self._sell_limit_action(context, float(self.state["sell_lot_used"])),
        ]

    def _buy_limit_action(self, context: StrategyContext, volume: float) -> TradeAction:
        setup_id = self._setup_id(context.symbol)
        price = self._round_price(float(self.state["next_buy_price"]))
        self._advance_next_buy_price(context)
        return TradeAction(
            action_type="PLACE_PENDING",
            symbol=context.symbol,
            side="BUY",
            order_type="LIMIT",
            volume=volume,
            price=price,
            setup_id=setup_id,
            group_id=setup_id,
            reason=self.C_BUY,
            metadata={"role": self.C_BUY},
        )

    def _sell_limit_action(
        self, context: StrategyContext, volume: float
    ) -> TradeAction:
        setup_id = self._setup_id(context.symbol)
        price = self._round_price(float(self.state["next_sell_price"]))
        self._advance_next_sell_price(context)
        return TradeAction(
            action_type="PLACE_PENDING",
            symbol=context.symbol,
            side="SELL",
            order_type="LIMIT",
            volume=volume,
            price=price,
            setup_id=setup_id,
            group_id=setup_id,
            reason=self.C_SELL,
            metadata={"role": self.C_SELL},
        )

    def _grid_buy_actions(
        self, context: StrategyContext, positions: list[PositionSnapshot]
    ) -> list[TradeAction]:
        ask = self._entry_price("BUY", context)
        if ask > float(self.state["next_buy_price"]):
            return []
        setup_id = self._setup_id(context.symbol)
        self._advance_next_buy_price(context)
        return [
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side="BUY",
                volume=float(self.state["buy_lot_used"]),
                setup_id=setup_id,
                group_id=setup_id,
                reason=self.G_BUY,
                metadata={"role": self.G_BUY},
            )
        ]

    def _grid_sell_actions(
        self, context: StrategyContext, positions: list[PositionSnapshot]
    ) -> list[TradeAction]:
        bid = self._entry_price("SELL", context)
        if bid < float(self.state["next_sell_price"]):
            return []
        setup_id = self._setup_id(context.symbol)
        self._advance_next_sell_price(context)
        return [
            TradeAction(
                action_type="OPEN",
                symbol=context.symbol,
                side="SELL",
                volume=float(self.state["sell_lot_used"]),
                setup_id=setup_id,
                group_id=setup_id,
                reason=self.G_SELL,
                metadata={"role": self.G_SELL},
            )
        ]

    def _trailing_tp_actions(
        self,
        side: str,
        positions: list[PositionSnapshot],
        context: StrategyContext,
    ) -> list[TradeAction]:
        target_tp = self._simple_average_price(positions)
        if target_tp is None:
            return []
        actions: list[TradeAction] = []
        for position in positions:
            if float(position.take_profit or 0.0) == target_tp:
                continue
            actions.append(
                TradeAction(
                    action_type="MODIFY_TP",
                    symbol=context.symbol,
                    side=side,  # type: ignore[arg-type]
                    ticket=position.ticket,
                    take_profit=target_tp,
                    reason=f"Trail {side} TP to average structure price",
                )
            )
        return actions

    def _cleanup_pending_actions(
        self,
        context: StrategyContext,
        orders: list[OrderSnapshot],
        positions: list[PositionSnapshot],
    ) -> list[TradeAction]:
        actions: list[TradeAction] = []
        first_buy_exists = self._num_positions_with_comment(positions, self.F_BUY) > 0
        first_sell_exists = self._num_positions_with_comment(positions, self.F_SELL) > 0
        if not first_sell_exists:
            actions.extend(self._cancel_orders_by_comment(context, orders, self.H_BUY))
        if not first_buy_exists:
            actions.extend(self._cancel_orders_by_comment(context, orders, self.H_SELL))
        if not positions:
            actions.extend(self._cancel_orders_by_comment(context, orders, self.C_BUY))
            actions.extend(self._cancel_orders_by_comment(context, orders, self.C_SELL))
        return actions

    def _cancel_orders_by_comment(
        self, context: StrategyContext, orders: list[OrderSnapshot], comment: str
    ) -> list[TradeAction]:
        return [
            TradeAction(
                action_type="CANCEL_ORDER",
                symbol=context.symbol,
                side=order.side,
                ticket=order.ticket,
                reason=f"Delete pending {comment}",
            )
            for order in orders
            if self._comment(order) == comment
        ]

    def _advance_next_buy_price(self, context: StrategyContext) -> None:
        if self._num_positions_with_comment(context.positions, self.F_BUY):
            distance = float(self.state.get("buy_hedge_distance") or 0.0)
        else:
            distance = float(self.state.get("sell_hedge_distance") or 0.0)
        self.state["next_buy_price"] = self._round_price(
            float(self.state["next_buy_price"]) - distance
        )

    def _advance_next_sell_price(self, context: StrategyContext) -> None:
        if self._num_positions_with_comment(context.positions, self.F_SELL):
            distance = float(self.state.get("sell_hedge_distance") or 0.0)
        else:
            distance = float(self.state.get("buy_hedge_distance") or 0.0)
        self.state["next_sell_price"] = self._round_price(
            float(self.state["next_sell_price"]) + distance
        )

    def _bullish_break(self, bars: pd.DataFrame, zz: dict[str, float]) -> bool:
        close1 = float(bars["close"].iloc[-1])
        close2 = float(bars["close"].iloc[-2])
        return bool(
            close1 > zz["high1"]
            and close2 < zz["high1"]
            and zz["high1"] > zz["high2"]
            and zz["high2"] < zz["high3"]
            and zz["low0"] > zz["low1"]
            and zz["low1"] < zz["low2"]
        )

    def _bearish_break(self, bars: pd.DataFrame, zz: dict[str, float]) -> bool:
        close1 = float(bars["close"].iloc[-1])
        close2 = float(bars["close"].iloc[-2])
        return bool(
            close1 < zz["low1"]
            and close2 > zz["low1"]
            and zz["low1"] < zz["low2"]
            and zz["low2"] > zz["low3"]
            and zz["high0"] < zz["high1"]
            and zz["high1"] > zz["high2"]
        )

    def _zz_values(self, bars: pd.DataFrame) -> dict[str, float] | None:
        extremes = self._zigzag_extremes(bars, 8)
        if len(extremes) < 8:
            return None
        values = [price for _, price in extremes[:8]]
        if values[0] > values[1]:
            keys = ["high0", "low0", "high1", "low1", "high2", "low2", "high3", "low3"]
        else:
            keys = ["low0", "high0", "low1", "high1", "low2", "high2", "low3", "high3"]
        return dict(zip(keys, values))

    def _zigzag_extremes(
        self, bars: pd.DataFrame, count: int
    ) -> list[tuple[pd.Timestamp, float]]:
        deviation = self.deviation * self.pip_value
        raw: list[tuple[int, str, float]] = []
        depth = max(1, min(self.depth, max(1, len(bars) // 3)))
        highs = pd.to_numeric(bars["high"], errors="coerce").to_numpy()
        lows = pd.to_numeric(bars["low"], errors="coerce").to_numpy()
        for idx in range(depth, len(bars) - depth):
            start = idx - depth
            stop = idx + depth + 1
            high = float(highs[idx])
            low = float(lows[idx])
            if high >= float(highs[start:stop].max()):
                raw.append((idx, "high", high))
            if low <= float(lows[start:stop].min()):
                raw.append((idx, "low", low))

        filtered: list[tuple[int, str, float]] = []
        for item in raw:
            if not filtered:
                filtered.append(item)
                continue
            last = filtered[-1]
            if item[1] == last[1]:
                if item[1] == "high" and item[2] >= last[2]:
                    filtered[-1] = item
                elif item[1] == "low" and item[2] <= last[2]:
                    filtered[-1] = item
                continue
            if abs(item[2] - last[2]) < deviation:
                continue
            filtered.append(item)

        return [
            (pd.Timestamp(bars.index[idx]), price)
            for idx, _, price in reversed(filtered[-count:])
        ]

    def _bars(self, context: StrategyContext) -> pd.DataFrame:
        data = context.market_data
        if data is None or data.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close"])

        bars = self._all_bars(data)
        tick = context.current_tick or {}
        current_bar_time = pd.to_datetime(tick.get("source_bar_time"), errors="coerce")
        if not pd.isna(current_bar_time) and isinstance(bars.index, pd.DatetimeIndex):
            bars = bars.loc[bars.index < current_bar_time]
        elif context.metadata and isinstance(bars.index, pd.DatetimeIndex):
            tick_index = int(context.metadata.get("tick_index", 0))
            tick_time = data.index[min(max(tick_index, 0), len(data) - 1)]
            bars = bars.loc[bars.index <= tick_time]
        return bars.tail(self.zigzag_lookback)

    def _all_bars(self, data: pd.DataFrame) -> pd.DataFrame:
        cache_key = (id(data), len(data))
        if self._bars_cache_key == cache_key and self._bars_cache is not None:
            return self._bars_cache

        window = data.copy()
        if {"open", "high", "low", "close"}.issubset(window.columns):
            bars = window[["open", "high", "low", "close"]].dropna()
            self._bars_cache_key = cache_key
            self._bars_cache = bars
            return bars

        if "source_bar_time" in window.columns:
            source_times = pd.to_datetime(window["source_bar_time"], errors="coerce")
        elif isinstance(window.index, pd.DatetimeIndex):
            source_times = window.index
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
        self._bars_cache_key = cache_key
        self._bars_cache = bars
        return bars

    @staticmethod
    def _is_new_bar_event(context: StrategyContext) -> bool:
        tick = context.current_tick or {}
        phase = str(tick.get("is_bar_close", "") or "").lower()
        phases = {part.strip() for part in phase.split("|") if part.strip()}
        if "open" in phases:
            return True
        return "source_bar_time" not in tick and "close" in phases

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

    @staticmethod
    def _positions(context: StrategyContext, side: str) -> list[PositionSnapshot]:
        return [
            position
            for position in context.positions_for_symbol()
            if str(position.side).upper() == side
        ]

    @staticmethod
    def _simple_average_price(positions: list[PositionSnapshot]) -> float | None:
        if not positions:
            return None
        return round(
            sum(float(position.open_price or 0.0) for position in positions)
            / len(positions),
            5,
        )

    def _entry_price(self, side: str, context: StrategyContext) -> float:
        tick = context.current_tick or {}
        bid = float(tick.get("bid", 0.0) or 0.0)
        ask = float(tick.get("ask", bid) or bid)
        return ask if side == "BUY" else bid

    def _round_price(self, price: float) -> float:
        return round(float(price), int(self.params.get("digits", 5)))

    @staticmethod
    def _setup_id(symbol: str) -> str:
        return f"{symbol}:market_structure_hedge_grid"

    @staticmethod
    def _comment(row: PositionSnapshot | OrderSnapshot) -> str:
        metadata = row.metadata or {}
        return str(metadata.get("comment", "") or "")

    def _num_pending(self, orders: list[OrderSnapshot], comment: str) -> int:
        return sum(1 for order in orders if self._comment(order) == comment)

    def _num_positions_with_comment(
        self, positions: list[PositionSnapshot], comment: str
    ) -> int:
        return sum(1 for position in positions if self._comment(position) == comment)
