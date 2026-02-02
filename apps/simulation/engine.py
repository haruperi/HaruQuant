"""
Simulation engine for bar-by-bar execution.

Classes:
    SimulationEngine: Engine that drives per-bar simulation flow.

Functions:
    monitor_positions: Update running P/L for all positions and close on SL/TP hits.
    monitor_account: Update account metrics based on current positions.
    run: Main loop that run the simulation in an event-driven manner.

"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional, Tuple

from apps.logger import logger
from apps.mt5 import get_mt5_api
from apps.simulation.data import SymbolTickSimulator
from apps.simulation.records import TradeRecordMixin
from apps.trade import PositionInfo
from apps.utils.validate import TradeValidator

mt5 = get_mt5_api()


def _support_point_split(total_points: int) -> Tuple[int, int, int]:
    mapping = {
        11: (3, 5, 3),
        10: (2, 6, 2),
        9: (2, 5, 2),
        8: (2, 4, 2),
        7: (2, 3, 2),
        6: (1, 4, 1),
        5: (1, 3, 1),
        4: (1, 2, 1),
        3: (1, 1, 1),
    }
    if total_points <= 2:
        return (0, total_points, 0)
    return mapping.get(total_points, (1, total_points - 2, 1))


def _linspace(a: float, b: float, count: int) -> list[float]:
    if count <= 0:
        return []
    if count == 1:
        return [a + (b - a) / 2.0]
    step = (b - a) / (count + 1)
    return [a + (step * (i + 1)) for i in range(count)]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _expand_ticks(  # noqa: C901
    points: list[float], total: int, point_size: float
) -> list[float]:
    if len(points) >= total:
        if total <= 2:
            return [points[0], points[-1]][:total]
        mid_count = total - 2
        mid = points[1:-1]
        if not mid:
            return [points[0], points[-1]]
        step = max(int(len(mid) / mid_count), 1)
        picked = mid[::step][:mid_count]
        return [points[0]] + picked + [points[-1]]

    extra = total - len(points)
    if extra <= 0:
        return points

    distances = [abs(points[i + 1] - points[i]) for i in range(len(points) - 1)]
    total_dist = sum(distances) or 1.0
    allocations = [int(round(extra * (d / total_dist))) for d in distances]
    while sum(allocations) < extra:
        allocations[distances.index(max(distances))] += 1
    while sum(allocations) > extra:
        idx = allocations.index(max(allocations))
        allocations[idx] = max(0, allocations[idx] - 1)

    expanded = [points[0]]
    for i in range(len(points) - 1):
        # Create wave-like interpolation between support points (MT5-style).
        a = points[i]
        b = points[i + 1]
        mid = _linspace(a, b, allocations[i])
        if mid:
            low = min(a, b)
            high = max(a, b)
            amp = min(abs(b - a) * 0.1, point_size * 2)
            if amp > 0:
                waved = []
                for j, v in enumerate(mid):
                    offset = amp if j % 2 == 0 else -amp
                    waved.append(_clamp(v + offset, low, high))
                mid = waved
        expanded.extend(mid)
        expanded.append(points[i + 1])
    return expanded


class SimulationEngine(TradeRecordMixin):
    """Engine that drives per-bar simulation flow."""

    _ticks_data: dict[str, SymbolTickSimulator]
    _positions_data: dict[int, Any]
    _symbols_data: dict[str, Any]
    _simulator: Any
    _account_data: Any
    trade: Any
    mt5_client: Any
    simulator_name: str
    open_position: Callable[..., bool]
    close_position: Callable[..., bool]
    close_all_positions: Callable[..., Any]
    _save_backtest_to_db: Callable[..., Any]
    _normalize_pending_type: Callable[[object], str]
    _normalize_expiry_date: Callable[..., Any]
    _pending_action: Callable[[object], str]
    _update_position_entry: Callable[..., Any]
    _ensure_trade_record: Callable[..., Any]
    _update_trade_tracker: Callable[..., Any]

    def _ensure_tick(self, symbol: str) -> SymbolTickSimulator:
        """Ensure a tick container exists for the symbol."""
        tick = self._ticks_data.get(symbol)
        if tick is None:
            self._ticks_data[symbol] = SymbolTickSimulator()
            tick = self._ticks_data[symbol]
        return tick

    def _on_tick(
        self,
        symbol: str,
        tick_time,
        bid: float,
        ask: float,
        last: float,
        log_every: int = 0,
        idx: Optional[int] = None,
        total: Optional[int] = None,
    ) -> None:
        """
        Handle a single tick update.

        This method updates the tick snapshot, runs pending/order/position monitoring,
        and refreshes account metrics. It is the common step handler for all modeling modes.
        """
        self._current_time = self._to_datetime(tick_time)
        tick = self._ensure_tick(symbol)
        tick.bid = float(bid)
        tick.ask = float(ask)
        tick.last = float(last)

        if log_every and idx is not None and total and idx % log_every == 0:
            logger.info(f"Processed step {idx}/{total} bid={bid:.5f} ask={ask:.5f}")

        # Pending orders can be triggered by this tick
        self.monitor_pending_orders()
        # Update P/L and apply SL/TP exits
        totals = self.monitor_positions()
        # Update account metrics based on positions
        self.monitor_account(totals)

    def _process_bar_signal(
        self,
        data: Any,
        idx: int,
        strategy: Any,
        symbol: str,
        volume: float,
        tick: SymbolTickSimulator,
        validator: TradeValidator,
        verbose: bool,
    ) -> None:
        """
        Process a single trading-timeframe bar for signals.

        Signals are always generated from the trading timeframe, regardless of modeling mode.
        """
        row = data.iloc[idx]
        self._current_time = self._to_datetime(row.name)

        if verbose:
            self._print_bar_status(row)

        signal = strategy.get_signal(data, idx)
        if signal is None:
            return

        exit_signal = signal.get("exit_signal", 0)
        entry_signal = signal.get("entry_signal", 0)

        # Exit only when explicitly asked by exit_signal (hedging-safe)
        positions = self._simulator.positions_get(symbol=symbol) or []
        for position in positions:
            pos_data = (
                position._asdict() if hasattr(position, "_asdict") else dict(position)
            )
            pos_type = pos_data.get("type")
            is_buy = pos_type == mt5.POSITION_TYPE_BUY or str(pos_type).lower() == "buy"
            if (exit_signal == 1 and is_buy) or (exit_signal == -1 and not is_buy):
                self.close_position(pos_data, reason=signal.get("reason"))

        # Entry signals can open new positions without checking existing ones
        if entry_signal == 1:
            self.open_position(
                "buy",
                symbol,
                volume,
                tick.ask,
                comment=f"BUY {self.trade.RequestMagic()}",
                validator=validator,
                open_time=row.name,
            )
        elif entry_signal == -1:
            self.open_position(
                "sell",
                symbol,
                volume,
                tick.bid,
                comment=f"SELL {self.trade.RequestMagic()}",
                validator=validator,
                open_time=row.name,
            )

    def _print_bar_status(self, row) -> None:
        """Print verbose status for the current bar."""
        print(
            f"{row.name} | Balance {self._account_data.balance} | Equity {self._account_data.equity} | "
            f"Free Margin {self._account_data.margin_free} | Margin {self._account_data.margin} | "
            f"Profit {self._account_data.profit}"
        )

        if self._positions_data:
            position_info = PositionInfo(api=self._simulator)
            for pos_idx in range(len(self._positions_data)):
                if position_info.SelectByIndex(pos_idx):
                    print(
                        f"Symbol={position_info.Symbol()} | Ticket={position_info.Identifier()} | "
                        f"Time={position_info.Time()} | Type={position_info.TypeDescription()} | "
                        f"Volume={position_info.Volume():.2f} | OpenPrice={position_info.PriceOpen():.5f} | "
                        f"SL={position_info.StopLoss():.5f} | TP={position_info.TakeProfit():.5f} | "
                        f"Price={position_info.PriceCurrent():.5f} | Swap={position_info.Swap():.2f} | "
                        f"Profit={position_info.Profit():.2f} | MarginReq={position_info.MarginRequired():.2f} | "
                        f"Comment={position_info.Comment()}"
                    )
        else:
            print("No open positions")

    def _m1_run(
        self,
        m1_data: Any,
        symbol: str,
        point: float,
        spread_default: float,
    ) -> Iterable[Tuple[object, float, float, float]]:
        """
        Generate a 4-tick OHLC sequence for each M1 bar.

        Pattern:
        - bullish: open -> low -> high -> close
        - bearish: open -> high -> low -> close
        """
        for _idx in range(len(m1_data)):
            row = m1_data.iloc[_idx]
            ts = row.name
            open_price = float(row["open"])
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            spread_points = float(row.get("spread", spread_default))

            is_bull = close >= open_price
            if is_bull:
                prices = [open_price, low, high, close]
            else:
                prices = [open_price, high, low, close]

            for price in prices:
                bid = float(price)
                ask = float(price + (spread_points * point))
                yield ts, bid, ask, bid

    def _generate_ticks(
        self,
        m1_data: Any,
        symbol: str,
        point: float,
        spread_default: float,
    ) -> Iterable[Tuple[object, float, float, float]]:
        """Generate synthetic ticks from M1 bars (MT5 "Every tick" model)."""
        prev_open = None
        prev_close = None
        for _idx in range(len(m1_data)):
            row = m1_data.iloc[_idx]
            ts = row.name
            open_price = float(row["open"])
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            spread_points = float(row.get("spread", spread_default))

            tick_volume = int(row.get("tick_volume", row.get("volume", 1)) or 1)
            if tick_volume <= 0:
                tick_volume = 1

            is_bull = close > open_price
            if close == open_price and prev_open is not None and prev_close is not None:
                is_bull = prev_close >= prev_open

            if tick_volume == 1:
                prices = [close]
            elif tick_volume == 2:
                prices = [open_price, close]
            elif tick_volume == 3:
                prices = (
                    [open_price, high, close] if is_bull else [open_price, low, close]
                )
            else:
                support_count = min(tick_volume - 2, 11)
                open_shadow_pts, body_pts, close_shadow_pts = _support_point_split(
                    support_count
                )

                if is_bull:
                    open_shadow = _linspace(open_price, low, open_shadow_pts)
                    body = _linspace(low, high, body_pts)
                    close_shadow = _linspace(high, close, close_shadow_pts)
                    support = open_shadow + body + close_shadow
                else:
                    open_shadow = _linspace(open_price, high, open_shadow_pts)
                    body = _linspace(high, low, body_pts)
                    close_shadow = _linspace(low, close, close_shadow_pts)
                    support = open_shadow + body + close_shadow

                base = [open_price] + support + [close]
                prices = _expand_ticks(base, tick_volume, point)

            prev_open = open_price
            prev_close = close

            for price in prices:
                bid = float(price)
                ask = float(price + (spread_points * point))
                yield ts, bid, ask, bid

    def monitor_positions(self) -> dict[str, float]:
        """
        Update running P/L for all positions and close on SL/TP hits.

        Uses current ticks (bid/ask) and the MT5 profit calculation for accuracy.
        """
        total_profit = 0.0
        total_margin = 0.0
        total_commission = 0.0
        total_fee = 0.0
        total_swap = 0.0
        for position_id, position in list(self._positions_data.items()):
            symbol = position.symbol
            tick = self._ticks_data.get(symbol)
            if tick is None:
                continue

            pos_type = position.type
            is_buy = pos_type == mt5.POSITION_TYPE_BUY or pos_type == mt5.ORDER_TYPE_BUY
            if isinstance(pos_type, str):
                is_buy = pos_type.lower() == "buy"

            current_price = tick.bid if is_buy else tick.ask
            if current_price is None:
                continue

            # Update per-position metrics using the latest tick
            position.price_current = current_price
            action = "buy" if is_buy else "sell"
            position.profit = self.mt5_client.order_calc_profit(
                0 if action == "buy" else 1,
                symbol,
                position.volume,
                position.price_open,
                current_price,
            )
            self._ensure_trade_record(
                pos_id=int(position_id),
                action=action,
                symbol=symbol,
                volume=position.volume,
                price=position.price_open,
                sl=position.sl,
                tp=position.tp,
                comment=position.comment,
                requested_entry_price=position.price_open,
                open_time=position.time,
            )
            self._update_trade_tracker(
                pos_id=int(position_id),
                action=action,
                symbol=symbol,
                entry_price=position.price_open,
                current_price=current_price,
                profit_usd=position.profit,
            )
            position.margin_required = self.mt5_client.order_calc_margin(
                0 if action == "buy" else 1,
                symbol,
                position.volume,
                position.price_open,
            )
            total_profit += float(position.profit or 0.0)
            total_margin += float(position.margin_required or 0.0)
            total_commission += float(getattr(position, "commission", 0.0) or 0.0)
            total_fee += float(getattr(position, "fee", 0.0) or 0.0)
            total_swap += float(getattr(position, "swap", 0.0) or 0.0)

            # Auto-close when SL/TP is hit by current price
            sl_hit = position.sl and (
                current_price <= position.sl if is_buy else current_price >= position.sl
            )
            tp_hit = position.tp and (
                current_price >= position.tp if is_buy else current_price <= position.tp
            )

            if sl_hit or tp_hit:
                reason = "Take profit" if tp_hit else "Stop loss"
                self.close_position(position._asdict(), reason=reason)
        return {
            "profit": float(total_profit),
            "margin": float(total_margin),
            "commission": float(total_commission),
            "fee": float(total_fee),
            "swap": float(total_swap),
        }

    def monitor_account(self, totals: Optional[dict[str, float]] = None) -> None:
        """Update account metrics based on current positions."""
        if totals is None:
            totals = {
                "profit": 0.0,
                "margin": 0.0,
                "commission": 0.0,
                "fee": 0.0,
                "swap": 0.0,
            }
            for position in self._positions_data.values():
                totals["profit"] += float(position.profit or 0.0)
                totals["margin"] += float(position.margin_required or 0.0)
                totals["commission"] += float(
                    getattr(position, "commission", 0.0) or 0.0
                )
                totals["fee"] += float(getattr(position, "fee", 0.0) or 0.0)
                totals["swap"] += float(getattr(position, "swap", 0.0) or 0.0)

        total_profit = float(totals.get("profit", 0.0))
        total_margin = float(totals.get("margin", 0.0))
        total_commission = float(totals.get("commission", 0.0))
        total_fee = float(totals.get("fee", 0.0))
        total_swap = float(totals.get("swap", 0.0))

        self._account_data.profit = total_profit
        self._account_data.margin = total_margin
        self._account_data.commission_blocked = float(total_commission + total_fee)
        self._account_data.liabilities = total_swap
        self._account_data.equity = float(
            self._account_data.balance
            + total_profit
            + self._account_data.credit
            + total_commission
            + total_fee
            + total_swap
        )
        self._account_data.margin_free = float(self._account_data.equity - total_margin)
        if self._account_data.margin > 0:
            self._account_data.margin_level = float(
                (self._account_data.equity / self._account_data.margin) * 100.0
            )
        else:
            self._account_data.margin_level = 0.0

    def monitor_pending_orders(self) -> None:
        """Process pending orders: expire them or trigger into positions."""
        if not self._simulator._orders_data:
            return

        now = self._current_sim_time()
        expired_orders: list[tuple[int, object]] = []
        triggered_orders: list[tuple[int, object]] = []

        for ticket, order in list(self._simulator._orders_data.items()):
            status, result = self._check_and_process_order(ticket, order, now)
            if status == "expired" and result:
                expired_orders.append(result)
            elif status == "triggered" and result:
                triggered_orders.append(result)

        done_time = int(now.timestamp())
        for _ticket, order in expired_orders:
            self._simulator._archive_order(
                order,
                getattr(mt5, "ORDER_STATE_EXPIRED", 5),
                done_time,
            )
        for _ticket, order in triggered_orders:
            self._simulator._archive_order(
                order,
                getattr(mt5, "ORDER_STATE_FILLED", 2),
                done_time,
            )
        for ticket, _order in expired_orders + triggered_orders:
            if ticket in self._simulator._orders_data:
                del self._simulator._orders_data[ticket]

    def _check_and_process_order(
        self, ticket: int, order, now
    ) -> tuple[Optional[str], Optional[tuple[int, object]]]:
        """Check validitity and triggers for a single order."""
        data = order._asdict() if hasattr(order, "_asdict") else dict(order)
        expiration_mode = str(data.get("expiration_mode", "gtc")).lower()
        expiry_date = data.get("expiry_date")
        if (
            expiration_mode in ("daily", "daily_excluding_stops")
            and expiry_date
            and now >= self._normalize_expiry_date(expiry_date)
        ):
            return "expired", (ticket, order)

        symbol = data.get("symbol", "")
        tick = self._ticks_data.get(symbol)
        if tick is None:
            return None, None

        ask = float(tick.ask or 0.0)
        bid = float(tick.bid or 0.0)
        open_price = float(data.get("open_price", data.get("price_open", 0.0)))
        order_type = self._normalize_pending_type(data.get("type", ""))

        if order_type in ("buy limit", "buy stop"):
            data["price"] = ask
        if order_type in ("sell limit", "sell stop"):
            data["price"] = bid

        triggered = False
        if (order_type == "buy limit" and ask <= open_price) or (
            order_type == "buy stop" and ask >= open_price
        ):
            triggered = self.open_position(
                action="buy",
                symbol=symbol,
                volume=data.get("volume_current", data.get("volume", 0.0)),
                price=ask,
                sl_price=data.get("sl", 0.0),
                tp_price=data.get("tp", 0.0),
                comment=data.get("comment", ""),
                open_time=now,
            )
        elif (order_type == "sell limit" and bid >= open_price) or (
            order_type == "sell stop" and bid <= open_price
        ):
            triggered = self.open_position(
                action="sell",
                symbol=symbol,
                volume=data.get("volume_current", data.get("volume", 0.0)),
                price=bid,
                sl_price=data.get("sl", 0.0),
                tp_price=data.get("tp", 0.0),
                comment=data.get("comment", ""),
                open_time=now,
            )

        if triggered:
            self._handle_triggered_order(data, ask, bid, now)
            return "triggered", (ticket, order)

        return None, None

    def _handle_triggered_order(self, data, ask, bid, now) -> None:
        """Handle the post-trigger logic for an order."""
        pos_id = self._simulator._next_position_id - 1
        pending_action = self._pending_action(data.get("type", ""))
        self._update_position_entry(
            action=pending_action,
            symbol=data.get("symbol", ""),
            volume=float(data.get("volume_current", data.get("volume", 0.0))),
            price=float(ask if pending_action == "buy" else bid),
            sl=float(data.get("sl", 0.0)),
            tp=float(data.get("tp", 0.0)),
            comment=str(data.get("comment", "")),
            margin_required=self.mt5_client.order_calc_margin(
                0 if pending_action == "buy" else 1,
                data.get("symbol", ""),
                float(data.get("volume_current", data.get("volume", 0.0))),
                float(data.get("open_price", data.get("price_open", 0.0))),
            ),
            open_time=now,
            pos_id=pos_id,
        )
        self._ensure_trade_record(
            pos_id=pos_id,
            action=pending_action,
            symbol=data.get("symbol", ""),
            volume=float(data.get("volume_current", data.get("volume", 0.0))),
            price=float(ask if pending_action == "buy" else bid),
            sl=float(data.get("sl", 0.0)),
            tp=float(data.get("tp", 0.0)),
            comment=str(data.get("comment", "")),
            requested_entry_price=float(
                data.get("open_price", data.get("price_open", 0.0))
            ),
            open_time=now,
        )

    def run(  # noqa: C901
        self,
        data: Any,
        strategy: Any,
        symbol: str,
        volume: float,
        validator: Optional[TradeValidator] = None,
        log_every: int = 500,
        verbose: bool = False,
        save_db: bool = False,
        metadata: Optional[dict] = None,
        step_data: Optional[Any] = None,
        data_modelling: str = "trading_timeframe",
    ) -> None:  # noqa: C901
        """
        Run the main simulation engine.

        Runs a backtest using the selected data modeling mode.

        data_modelling options:
        - "trading_timeframe": step through trading bars (default)
        - "m1_ohlc": step through M1 bars using 4-tick OHLC pattern
        - "synthetic_ticks": generate synthetic ticks from M1 data
        - "real_ticks": step through real tick data
        """
        logger.info(f"Starting simulation: {self.simulator_name}")
        logger.info("=" * 70)

        symbol_info = self._symbols_data.get(symbol)
        if symbol_info is None:
            logger.error(f"Symbol not found in simulator: {symbol}")
            return

        tick = self._ensure_tick(symbol)
        point = symbol_info.point
        spread_default = symbol_info.spread

        if validator is None:
            validator = TradeValidator()

        mode = str(data_modelling or "trading_timeframe").strip().lower()
        if mode not in (
            "trading_timeframe",
            "m1_ohlc",
            "synthetic_ticks",
            "real_ticks",
        ):
            logger.error(f"Unknown data_modelling: {data_modelling}")
            return

        def _advance_bars(current_time, next_idx: int) -> int:
            """Advance trading-timeframe bars up to current_time and process signals."""
            while next_idx < len(data) and current_time >= self._to_datetime(
                data.index[next_idx]
            ):
                self._process_bar_signal(
                    data,
                    next_idx,
                    strategy,
                    symbol,
                    volume,
                    tick,
                    validator,
                    verbose,
                )
                next_idx += 1
            return next_idx

        if mode == "trading_timeframe":
            for idx in range(len(data)):
                row = data.iloc[idx]
                self._current_time = self._to_datetime(row.name)
                close = float(row["close"])
                spread_points = float(row.get("spread", spread_default))
                spread = spread_points * point

                # Use bar close as bid and add spread for ask.
                bid = close
                ask = close + spread

                self._on_tick(
                    symbol=symbol,
                    tick_time=row.name,
                    bid=bid,
                    ask=ask,
                    last=close,
                    log_every=log_every,
                    idx=idx,
                    total=len(data),
                )

                self._process_bar_signal(
                    data,
                    idx,
                    strategy,
                    symbol,
                    volume,
                    tick,
                    validator,
                    verbose,
                )
        else:
            if step_data is None or len(step_data) == 0:
                logger.error("step_data is required for the selected data_modelling")
                return

            next_bar_idx = 0

            if mode == "real_ticks":
                next_bar_idx = self._run_real_ticks(
                    step_data,
                    symbol,
                    point,
                    spread_default,
                    _advance_bars,
                    next_bar_idx,
                )

            elif mode == "m1_ohlc":
                next_bar_idx = self._run_m1_ohlc(
                    step_data,
                    symbol,
                    point,
                    spread_default,
                    _advance_bars,
                    next_bar_idx,
                )

            elif mode == "synthetic_ticks":
                next_bar_idx = self._run_synthetic_ticks(
                    step_data,
                    symbol,
                    point,
                    spread_default,
                    _advance_bars,
                    next_bar_idx,
                )

        # Close any remaining positions at the end of the run (MT5-style)
        self.close_all_positions(reason="Time exit")

        if save_db:
            self._save_backtest_to_db(metadata)

        logger.info("\n" + "=" * 70)
        logger.info("Simulation completed")

    def _run_real_ticks(
        self,
        step_data: Any,
        symbol: str,
        point: float,
        spread_default: float,
        advance_func: Any,
        start_idx: int,
    ) -> int:
        """Run simulation with real ticks."""
        next_bar_idx = start_idx
        for idx, row in enumerate(step_data.itertuples()):
            row_dict = row._asdict() if hasattr(row, "_asdict") else None
            if row_dict is not None:
                ts = row_dict.get("timestamp")
                bid = row_dict.get("bid")
                ask = row_dict.get("ask")
                last = row_dict.get("last")
                spread_points = row_dict.get("spread", spread_default)
            else:
                ts = getattr(row, "timestamp", None)
                bid = getattr(row, "bid", None)
                ask = getattr(row, "ask", None)
                last = getattr(row, "last", None)
                spread_points = getattr(row, "spread", spread_default)

            if ts is None:
                ts = step_data.index[idx]
            if bid is None:
                bid = float(getattr(row, "price", 0.0) or 0.0)
            if ask is None:
                ask = float(bid + (float(spread_points) * point))
            if last is None:
                last = float(bid)

            self._on_tick(
                symbol=symbol,
                tick_time=ts,
                bid=float(bid),
                ask=float(ask),
                last=float(last),
                log_every=0,
            )
            next_bar_idx = advance_func(self._current_time, next_bar_idx)
        return next_bar_idx

    def _run_m1_ohlc(
        self,
        step_data: Any,
        symbol: str,
        point: float,
        spread_default: float,
        advance_func: Any,
        start_idx: int,
    ) -> int:
        """Run simulation with M1 OHLC pattern."""
        next_bar_idx = start_idx
        for idx in range(len(step_data)):
            row = step_data.iloc[idx]
            self._current_time = self._to_datetime(row.name)
            close = float(row["close"])
            spread_points = float(row.get("spread", spread_default))
            spread = spread_points * point

            bid = close
            ask = close + spread

            self._on_tick(
                symbol=symbol,
                tick_time=row.name,
                bid=bid,
                ask=ask,
                last=close,
                log_every=0,
                idx=idx,
                total=len(step_data),
            )
            next_bar_idx = advance_func(self._current_time, next_bar_idx)
        return next_bar_idx

    def _run_synthetic_ticks(
        self,
        step_data: Any,
        symbol: str,
        point: float,
        spread_default: float,
        advance_func: Any,
        start_idx: int,
    ) -> int:
        """Run simulation with synthetic ticks."""
        next_bar_idx = start_idx
        for _idx, (ts, bid, ask, last) in enumerate(
            self._generate_ticks(step_data, symbol, point, spread_default)
        ):
            self._on_tick(
                symbol=symbol,
                tick_time=ts,
                bid=bid,
                ask=ask,
                last=last,
                log_every=0,
            )
            next_bar_idx = advance_func(self._current_time, next_bar_idx)
        return next_bar_idx
