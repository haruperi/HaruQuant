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

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, cast

import numpy as np

from apps.logger import logger
from apps.mt5 import get_mt5_api
from apps.simulation.data import SymbolTickSimulator
from apps.simulation.records import TradeRecordMixin
from apps.simulation.utils import (
    NUMBA_AVAILABLE,
    PositionArrayState,
    numba_position_update,
)
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
    _completed_trades: list[Any]
    _vectorized_trade_buffer: Optional[list[Any]]
    _vectorized_trade_count: int
    _use_position_arrays: bool
    _use_fast_calc: bool
    _symbol_calc_cache: dict[str, dict[str, float]]
    _pos_buf_size: int
    _pos_buf_current_prices: np.ndarray
    _pos_buf_price_open: np.ndarray
    _pos_buf_volume: np.ndarray
    _pos_buf_direction: np.ndarray
    _pos_buf_sl: np.ndarray
    _pos_buf_tp: np.ndarray
    _pos_buf_is_buy: np.ndarray
    _pos_buf_valid: np.ndarray
    _pos_buf_profit: np.ndarray
    _pos_buf_margin: np.ndarray
    _pos_buf_commission: np.ndarray
    _pos_buf_fee: np.ndarray
    _pos_buf_swap: np.ndarray
    _pos_buf_contract_size: np.ndarray
    _pos_buf_tick_size: np.ndarray
    _pos_buf_tick_value: np.ndarray
    _pos_buf_margin_mode: np.ndarray
    _pos_buf_leverage: np.ndarray
    _pos_buf_sl_hit: np.ndarray
    _pos_buf_tp_hit: np.ndarray
    _use_numba: bool
    _position_array_state: Optional[PositionArrayState]

    def _ensure_tick(self, symbol: str) -> SymbolTickSimulator:
        """Ensure a tick container exists for the symbol."""
        tick = self._ticks_data.get(symbol)
        if tick is None:
            self._ticks_data[symbol] = SymbolTickSimulator()
            tick = self._ticks_data[symbol]
        return tick

    def _fast_calc_profit_margin_arrays(
        self,
        current_prices: np.ndarray,
        price_open: np.ndarray,
        volume: np.ndarray,
        direction: np.ndarray,
        contract_size: np.ndarray,
        tick_size: np.ndarray,
        tick_value: np.ndarray,
        margin_mode: np.ndarray,
        leverage: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute profit/margin arrays with fast calc params (vectorized)."""
        price_delta = (current_prices - price_open) * direction
        profit = np.zeros_like(price_delta, dtype=np.float64)
        margin = np.zeros_like(price_open, dtype=np.float64)

        tick_mask = (tick_size > 0.0) & (tick_value > 0.0)
        if np.any(tick_mask):
            profit[tick_mask] = (
                (price_delta[tick_mask] / tick_size[tick_mask])
                * tick_value[tick_mask]
                * volume[tick_mask]
            )

        contract_mask = (~tick_mask) & (contract_size > 0.0)
        if np.any(contract_mask):
            profit[contract_mask] = (
                price_delta[contract_mask]
                * contract_size[contract_mask]
                * volume[contract_mask]
            )

        lev = np.where(leverage > 0.0, leverage, 1.0)
        mm = margin_mode
        mask0 = mm == 0.0
        if np.any(mask0):
            margin[mask0] = (volume[mask0] * contract_size[mask0]) / lev[mask0]
        mask1 = mm == 1.0
        if np.any(mask1):
            margin[mask1] = volume[mask1] * contract_size[mask1]
        mask2 = mm == 2.0
        if np.any(mask2):
            margin[mask2] = volume[mask2] * contract_size[mask2] * price_open[mask2]
        mask3 = mm == 3.0
        if np.any(mask3):
            margin[mask3] = (
                volume[mask3] * contract_size[mask3] * price_open[mask3] / lev[mask3]
            )
        mask4 = (mm == 4.0) & (tick_size > 0.0)
        if np.any(mask4):
            margin[mask4] = (
                volume[mask4]
                * contract_size[mask4]
                * price_open[mask4]
                * tick_value[mask4]
                / tick_size[mask4]
            )
        mask56 = (mm == 5.0) | (mm == 6.0)
        if np.any(mask56):
            margin[mask56] = volume[mask56] * contract_size[mask56] * price_open[mask56]

        return profit, margin

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

        if (
            log_every
            and __debug__
            and not getattr(self, "_suppress_backtest_logs", False)
            and idx is not None
            and total
            and idx % log_every == 0
        ):
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
        row_name = data.index[idx]
        self._current_time = self._to_datetime(row_name)

        if verbose:
            row = data.iloc[idx]
            self._print_bar_status(row)

        cache = getattr(self, "_signal_cache", None)
        if cache is not None:
            # Account for warmup offset when accessing signal cache
            cache_offset = getattr(self, "_signal_cache_offset", 0)
            cache_idx = idx + cache_offset
            signal = cache[cache_idx]
        else:
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
                open_time=row_name,
            )
        elif entry_signal == -1:
            self.open_position(
                "sell",
                symbol,
                volume,
                tick.bid,
                comment=f"SELL {self.trade.RequestMagic()}",
                validator=validator,
                open_time=row_name,
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
        if not self._positions_data:
            return {
                "profit": 0.0,
                "margin": 0.0,
                "commission": 0.0,
                "fee": 0.0,
                "swap": 0.0,
            }

        if getattr(self, "_use_position_arrays", False):
            return self._monitor_positions_arrays()

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
            position.profit = self._calc_profit(
                action=action,
                symbol=symbol,
                volume=position.volume,
                price_open=position.price_open,
                price_close=current_price,
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
            position.margin_required = self._calc_margin(
                action=action,
                symbol=symbol,
                volume=position.volume,
                price=position.price_open,
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

    def _monitor_positions_arrays(self) -> dict[str, float]:  # noqa: C901
        """Vectorized-style monitor that still updates all fields per bar."""
        position_state = getattr(self, "_position_array_state", None)
        if position_state is not None:
            if position_state.count != len(self._positions_data):
                position_state.rebuild_from_positions(
                    self._positions_data,
                    get_symbol_params=self._get_symbol_calc_params,
                    leverage=getattr(self._account_data, "leverage", None),
                )
            count = position_state.count
            if count == 0:
                return {
                    "profit": 0.0,
                    "margin": 0.0,
                    "commission": 0.0,
                    "fee": 0.0,
                    "swap": 0.0,
                }
            positions = []
        else:
            positions = list(self._positions_data.items())
            if not positions:
                return {
                    "profit": 0.0,
                    "margin": 0.0,
                    "commission": 0.0,
                    "fee": 0.0,
                    "swap": 0.0,
                }
            count = len(positions)

        self._ensure_position_buffers(count)
        current_prices = self._pos_buf_current_prices[:count]
        price_open_arr = self._pos_buf_price_open[:count]
        volume_arr = self._pos_buf_volume[:count]
        direction_arr = self._pos_buf_direction[:count]
        sl_arr = self._pos_buf_sl[:count]
        tp_arr = self._pos_buf_tp[:count]
        is_buy_arr = self._pos_buf_is_buy[:count]
        valid_arr = self._pos_buf_valid[:count]
        profit_arr = self._pos_buf_profit[:count]
        margin_arr = self._pos_buf_margin[:count]
        commission_arr = self._pos_buf_commission[:count]
        fee_arr = self._pos_buf_fee[:count]
        swap_arr = self._pos_buf_swap[:count]
        contract_size_arr = self._pos_buf_contract_size[:count]
        tick_size_arr = self._pos_buf_tick_size[:count]
        tick_value_arr = self._pos_buf_tick_value[:count]
        margin_mode_arr = self._pos_buf_margin_mode[:count]
        leverage_arr = self._pos_buf_leverage[:count]
        sl_hit_arr = self._pos_buf_sl_hit[:count]
        tp_hit_arr = self._pos_buf_tp_hit[:count]

        current_prices.fill(0.0)
        price_open_arr.fill(0.0)
        volume_arr.fill(0.0)
        direction_arr.fill(0)
        sl_arr.fill(0.0)
        tp_arr.fill(0.0)
        is_buy_arr.fill(False)
        valid_arr.fill(False)
        profit_arr.fill(0.0)
        margin_arr.fill(0.0)
        commission_arr.fill(0.0)
        fee_arr.fill(0.0)
        swap_arr.fill(0.0)
        contract_size_arr.fill(0.0)
        tick_size_arr.fill(0.0)
        tick_value_arr.fill(0.0)
        margin_mode_arr.fill(0.0)
        leverage_arr.fill(0.0)
        sl_hit_arr.fill(False)
        tp_hit_arr.fill(False)

        ticks = self._ticks_data
        mt5_pos_buy = mt5.POSITION_TYPE_BUY
        mt5_order_buy = mt5.ORDER_TYPE_BUY
        calc_profit = self._calc_profit
        calc_margin = self._calc_margin
        ensure_trade_record = self._ensure_trade_record
        update_trade_tracker = self._update_trade_tracker
        close_position = self.close_position
        use_state = position_state is not None and position_state.count == count
        fast_ready = bool(use_state and getattr(self, "_use_fast_calc", False))
        numba_ready = (
            bool(getattr(self, "_use_numba", False))
            and bool(getattr(self, "_use_fast_calc", False))
            and NUMBA_AVAILABLE
        )
        numba_ok = True
        fast_ok = True
        params_cache = self._symbol_calc_cache

        if use_state:
            symbols = position_state.symbols
            pos_objects = position_state.pos_objects
            for idx in range(count):
                symbol = symbols[idx]
                tick = ticks.get(symbol)
                if tick is None:
                    continue

                is_buy = position_state.direction[idx] == 1
                current_price = tick.bid if is_buy else tick.ask
                if current_price is None:
                    continue

                valid_arr[idx] = True
                is_buy_arr[idx] = bool(is_buy)
                current_prices[idx] = float(current_price)

                price_open_arr[idx] = position_state.price_open[idx]
                volume_arr[idx] = position_state.volume[idx]
                sl_arr[idx] = position_state.sl[idx]
                tp_arr[idx] = position_state.tp[idx]
                direction_arr[idx] = position_state.direction[idx]
                commission_arr[idx] = position_state.commission[idx]
                fee_arr[idx] = position_state.fee[idx]
                swap_arr[idx] = position_state.swap[idx]

                if numba_ready or fast_ready:
                    contract_size_arr[idx] = position_state.contract_size[idx]
                    margin_mode_arr[idx] = position_state.margin_mode[idx]
                    leverage_arr[idx] = position_state.leverage[idx]
                    tick_size_arr[idx] = position_state.tick_size[idx]
                    tick_value_arr[idx] = position_state.tick_value[idx]
                    if (
                        contract_size_arr[idx] == 0.0
                        and tick_size_arr[idx] == 0.0
                        and tick_value_arr[idx] == 0.0
                    ):
                        params = params_cache.get(symbol)
                        if params is None:
                            params = self._get_symbol_calc_params(symbol)
                        if params is None:
                            numba_ok = False
                            fast_ok = False
                        else:
                            contract_size_arr[idx] = params["contract_size"]
                            margin_mode_arr[idx] = params["margin_mode"]
                            leverage_arr[idx] = params["leverage"]
                            tick_size_arr[idx] = params["tick_size"]
                            tick_value_arr[idx] = params["tick_value"]
                            position_state.contract_size[idx] = contract_size_arr[idx]
                            position_state.margin_mode[idx] = margin_mode_arr[idx]
                            position_state.leverage[idx] = leverage_arr[idx]
                            position_state.tick_size[idx] = tick_size_arr[idx]
                            position_state.tick_value[idx] = tick_value_arr[idx]
            if fast_ready and fast_ok and not numba_ready:
                profit_arr[:], margin_arr[:] = self._fast_calc_profit_margin_arrays(
                    current_prices=current_prices,
                    price_open=price_open_arr,
                    volume=volume_arr,
                    direction=direction_arr,
                    contract_size=contract_size_arr,
                    tick_size=tick_size_arr,
                    tick_value=tick_value_arr,
                    margin_mode=margin_mode_arr,
                    leverage=leverage_arr,
                )
            if not numba_ready:
                for idx in range(count):
                    if not valid_arr[idx]:
                        continue
                    pos_obj = pos_objects[idx]
                    if pos_obj is None:
                        continue
                    symbol = symbols[idx]
                    current_price = float(current_prices[idx])
                    is_buy = bool(is_buy_arr[idx])
                    action = "buy" if is_buy else "sell"

                    pos_obj.price_current = current_price
                    if fast_ready and fast_ok:
                        pos_obj.profit = float(profit_arr[idx])
                    else:
                        pos_obj.profit = calc_profit(
                            action=action,
                            symbol=symbol,
                            volume=volume_arr[idx],
                            price_open=price_open_arr[idx],
                            price_close=current_price,
                        )
                    ensure_trade_record(
                        pos_id=int(position_state.pos_id[idx]),
                        action=action,
                        symbol=symbol,
                        volume=volume_arr[idx],
                        price=price_open_arr[idx],
                        sl=sl_arr[idx],
                        tp=tp_arr[idx],
                        comment=position_state.comments[idx],
                        requested_entry_price=price_open_arr[idx],
                        open_time=position_state.open_time[idx],
                    )
                    update_trade_tracker(
                        pos_id=int(position_state.pos_id[idx]),
                        action=action,
                        symbol=symbol,
                        entry_price=price_open_arr[idx],
                        current_price=current_price,
                        profit_usd=pos_obj.profit,
                    )
                    if fast_ready and fast_ok:
                        pos_obj.margin_required = float(margin_arr[idx])
                    else:
                        pos_obj.margin_required = calc_margin(
                            action=action,
                            symbol=symbol,
                            volume=volume_arr[idx],
                            price=price_open_arr[idx],
                        )

                    if not (fast_ready and fast_ok):
                        profit_arr[idx] = float(pos_obj.profit or 0.0)
                        margin_arr[idx] = float(pos_obj.margin_required or 0.0)
                    position_state.profit[idx] = profit_arr[idx]
                    position_state.margin_required[idx] = margin_arr[idx]
                    position_state.price_current[idx] = current_price
        else:
            for idx, (position_id, position) in enumerate(positions):
                symbol = position.symbol
                tick = ticks.get(symbol)
                if tick is None:
                    continue

                pos_type = position.type
                is_buy = pos_type in (mt5_pos_buy, mt5_order_buy)
                if isinstance(pos_type, str):
                    is_buy = pos_type.lower() == "buy"

                current_price = tick.bid if is_buy else tick.ask
                if current_price is None:
                    continue

                valid_arr[idx] = True
                is_buy_arr[idx] = bool(is_buy)
                current_prices[idx] = float(current_price)
                price_open_arr[idx] = float(position.price_open)
                volume_arr[idx] = float(position.volume)
                sl_arr[idx] = float(position.sl or 0.0)
                tp_arr[idx] = float(position.tp or 0.0)
                direction_arr[idx] = 1 if is_buy else -1

                if numba_ready:
                    params = params_cache.get(symbol)
                    if params is None:
                        params = self._get_symbol_calc_params(symbol)
                    if params is None:
                        numba_ok = False
                    else:
                        contract_size_arr[idx] = params["contract_size"]
                        margin_mode_arr[idx] = params["margin_mode"]
                        leverage_arr[idx] = params["leverage"]
                        tick_size_arr[idx] = params["tick_size"]
                        tick_value_arr[idx] = params["tick_value"]
                else:
                    # Update per-position metrics using the latest tick
                    position.price_current = float(current_price)
                    action = "buy" if is_buy else "sell"
                    position.profit = calc_profit(
                        action=action,
                        symbol=symbol,
                        volume=position.volume,
                        price_open=position.price_open,
                        price_close=current_price,
                    )
                    ensure_trade_record(
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
                    update_trade_tracker(
                        pos_id=int(position_id),
                        action=action,
                        symbol=symbol,
                        entry_price=position.price_open,
                        current_price=current_price,
                        profit_usd=position.profit,
                    )
                    position.margin_required = calc_margin(
                        action=action,
                        symbol=symbol,
                        volume=position.volume,
                        price=position.price_open,
                    )

                    profit_arr[idx] = float(position.profit or 0.0)
                    margin_arr[idx] = float(position.margin_required or 0.0)
                    commission_arr[idx] = float(
                        getattr(position, "commission", 0.0) or 0.0
                    )
                    fee_arr[idx] = float(getattr(position, "fee", 0.0) or 0.0)
                    swap_arr[idx] = float(getattr(position, "swap", 0.0) or 0.0)

        if numba_ready and not numba_ok:
            if use_state:
                for idx in range(count):
                    if not valid_arr[idx]:
                        continue
                    pos_obj = position_state.pos_objects[idx]
                    if pos_obj is None:
                        continue
                    current_price = float(current_prices[idx])
                    is_buy = bool(is_buy_arr[idx])
                    action = "buy" if is_buy else "sell"

                    pos_obj.price_current = current_price
                    pos_obj.profit = calc_profit(
                        action=action,
                        symbol=position_state.symbols[idx],
                        volume=volume_arr[idx],
                        price_open=price_open_arr[idx],
                        price_close=current_price,
                    )
                    ensure_trade_record(
                        pos_id=int(position_state.pos_id[idx]),
                        action=action,
                        symbol=position_state.symbols[idx],
                        volume=volume_arr[idx],
                        price=price_open_arr[idx],
                        sl=sl_arr[idx],
                        tp=tp_arr[idx],
                        comment=position_state.comments[idx],
                        requested_entry_price=price_open_arr[idx],
                        open_time=position_state.open_time[idx],
                    )
                    update_trade_tracker(
                        pos_id=int(position_state.pos_id[idx]),
                        action=action,
                        symbol=position_state.symbols[idx],
                        entry_price=price_open_arr[idx],
                        current_price=current_price,
                        profit_usd=pos_obj.profit,
                    )
                    pos_obj.margin_required = calc_margin(
                        action=action,
                        symbol=position_state.symbols[idx],
                        volume=volume_arr[idx],
                        price=price_open_arr[idx],
                    )

                    profit_arr[idx] = float(pos_obj.profit or 0.0)
                    margin_arr[idx] = float(pos_obj.margin_required or 0.0)
                    commission_arr[idx] = float(
                        getattr(pos_obj, "commission", 0.0) or 0.0
                    )
                    fee_arr[idx] = float(getattr(pos_obj, "fee", 0.0) or 0.0)
                    swap_arr[idx] = float(getattr(pos_obj, "swap", 0.0) or 0.0)
            else:
                for idx, (position_id, position) in enumerate(positions):
                    if not valid_arr[idx]:
                        continue
                    current_price = float(current_prices[idx])
                    is_buy = bool(is_buy_arr[idx])
                    action = "buy" if is_buy else "sell"

                    position.price_current = current_price
                    position.profit = calc_profit(
                        action=action,
                        symbol=position.symbol,
                        volume=position.volume,
                        price_open=position.price_open,
                        price_close=current_price,
                    )
                    ensure_trade_record(
                        pos_id=int(position_id),
                        action=action,
                        symbol=position.symbol,
                        volume=position.volume,
                        price=position.price_open,
                        sl=position.sl,
                        tp=position.tp,
                        comment=position.comment,
                        requested_entry_price=position.price_open,
                        open_time=position.time,
                    )
                    update_trade_tracker(
                        pos_id=int(position_id),
                        action=action,
                        symbol=position.symbol,
                        entry_price=position.price_open,
                        current_price=current_price,
                        profit_usd=position.profit,
                    )
                    position.margin_required = calc_margin(
                        action=action,
                        symbol=position.symbol,
                        volume=position.volume,
                        price=position.price_open,
                    )

                    profit_arr[idx] = float(position.profit or 0.0)
                    margin_arr[idx] = float(position.margin_required or 0.0)
                    commission_arr[idx] = float(
                        getattr(position, "commission", 0.0) or 0.0
                    )
                    fee_arr[idx] = float(getattr(position, "fee", 0.0) or 0.0)
                    swap_arr[idx] = float(getattr(position, "swap", 0.0) or 0.0)

        if numba_ready and numba_ok:
            profit_arr[:], margin_arr[:], sl_hit_arr[:], tp_hit_arr[:] = (
                numba_position_update(
                    current_prices,
                    price_open_arr,
                    volume_arr,
                    direction_arr,
                    sl_arr,
                    tp_arr,
                    valid_arr,
                    contract_size_arr,
                    tick_size_arr,
                    tick_value_arr,
                    margin_mode_arr,
                    leverage_arr,
                )
            )

            if use_state:
                for idx in range(count):
                    if not valid_arr[idx]:
                        continue
                    pos_obj = position_state.pos_objects[idx]
                    if pos_obj is None:
                        continue
                    current_price = float(current_prices[idx])
                    pos_obj.price_current = current_price
                    action = "buy" if direction_arr[idx] == 1 else "sell"
                    pos_obj.profit = float(profit_arr[idx])
                    pos_obj.margin_required = float(margin_arr[idx])

                    ensure_trade_record(
                        pos_id=int(position_state.pos_id[idx]),
                        action=action,
                        symbol=position_state.symbols[idx],
                        volume=volume_arr[idx],
                        price=price_open_arr[idx],
                        sl=sl_arr[idx],
                        tp=tp_arr[idx],
                        comment=position_state.comments[idx],
                        requested_entry_price=price_open_arr[idx],
                        open_time=position_state.open_time[idx],
                    )
                    update_trade_tracker(
                        pos_id=int(position_state.pos_id[idx]),
                        action=action,
                        symbol=position_state.symbols[idx],
                        entry_price=price_open_arr[idx],
                        current_price=current_price,
                        profit_usd=pos_obj.profit,
                    )

                    commission_arr[idx] = float(
                        getattr(pos_obj, "commission", 0.0) or 0.0
                    )
                    fee_arr[idx] = float(getattr(pos_obj, "fee", 0.0) or 0.0)
                    swap_arr[idx] = float(getattr(pos_obj, "swap", 0.0) or 0.0)

                    position_state.profit[idx] = profit_arr[idx]
                    position_state.margin_required[idx] = margin_arr[idx]
                    position_state.price_current[idx] = current_price
            else:
                for idx, (position_id, position) in enumerate(positions):
                    if not valid_arr[idx]:
                        continue
                    current_price = float(current_prices[idx])
                    position.price_current = current_price
                    action = "buy" if direction_arr[idx] == 1 else "sell"
                    position.profit = float(profit_arr[idx])
                    position.margin_required = float(margin_arr[idx])

                    ensure_trade_record(
                        pos_id=int(position_id),
                        action=action,
                        symbol=position.symbol,
                        volume=position.volume,
                        price=position.price_open,
                        sl=position.sl,
                        tp=position.tp,
                        comment=position.comment,
                        requested_entry_price=position.price_open,
                        open_time=position.time,
                    )
                    update_trade_tracker(
                        pos_id=int(position_id),
                        action=action,
                        symbol=position.symbol,
                        entry_price=position.price_open,
                        current_price=current_price,
                        profit_usd=position.profit,
                    )

                    commission_arr[idx] = float(
                        getattr(position, "commission", 0.0) or 0.0
                    )
                    fee_arr[idx] = float(getattr(position, "fee", 0.0) or 0.0)
                    swap_arr[idx] = float(getattr(position, "swap", 0.0) or 0.0)

        total_profit = float(profit_arr.sum())
        total_margin = float(margin_arr.sum())
        total_commission = float(commission_arr.sum())
        total_fee = float(fee_arr.sum())
        total_swap = float(swap_arr.sum())

        if numba_ready and numba_ok:
            sl_hit = sl_hit_arr
            tp_hit = tp_hit_arr
        else:
            valid_mask = valid_arr
            sl_hit = (
                valid_mask
                & (sl_arr != 0.0)
                & (
                    (is_buy_arr & (current_prices <= sl_arr))
                    | (~is_buy_arr & (current_prices >= sl_arr))
                )
            )
            tp_hit = (
                valid_mask
                & (tp_arr != 0.0)
                & (
                    (is_buy_arr & (current_prices >= tp_arr))
                    | (~is_buy_arr & (current_prices <= tp_arr))
                )
            )

        to_close = np.where(sl_hit | tp_hit)[0]
        for idx in to_close:
            reason = "Take profit" if bool(tp_hit[int(idx)]) else "Stop loss"
            if use_state:
                pos_obj = position_state.pos_objects[int(idx)]
                if pos_obj is None:
                    continue
                close_position(pos_obj._asdict(), reason=reason)
            else:
                position = positions[int(idx)][1]
                close_position(position._asdict(), reason=reason)

        return {
            "profit": total_profit,
            "margin": total_margin,
            "commission": total_commission,
            "fee": total_fee,
            "swap": total_swap,
        }

    def _ensure_position_buffers(self, count: int) -> None:
        """Ensure reusable position arrays are large enough for the current bar."""
        size = int(getattr(self, "_pos_buf_size", 0) or 0)
        if size >= count:
            return

        new_size = max(count, size * 2 if size else count)
        self._pos_buf_size = new_size
        self._pos_buf_current_prices = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_price_open = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_volume = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_direction = np.zeros(new_size, dtype=np.int8)
        self._pos_buf_sl = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_tp = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_is_buy = np.zeros(new_size, dtype=bool)
        self._pos_buf_valid = np.zeros(new_size, dtype=bool)
        self._pos_buf_profit = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_margin = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_commission = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_fee = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_swap = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_contract_size = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_tick_size = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_tick_value = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_margin_mode = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_leverage = np.zeros(new_size, dtype=np.float64)
        self._pos_buf_sl_hit = np.zeros(new_size, dtype=bool)
        self._pos_buf_tp_hit = np.zeros(new_size, dtype=bool)

    def _calc_profit(
        self,
        action: str,
        symbol: str,
        volume: float,
        price_open: float,
        price_close: float,
    ) -> float:
        if not getattr(self, "_use_fast_calc", False):
            return float(
                self.mt5_client.order_calc_profit(
                    0 if action == "buy" else 1,
                    symbol,
                    volume,
                    price_open,
                    price_close,
                )
                or 0.0
            )

        params = self._get_symbol_calc_params(symbol)
        if params is None:
            return float(
                self.mt5_client.order_calc_profit(
                    0 if action == "buy" else 1,
                    symbol,
                    volume,
                    price_open,
                    price_close,
                )
                or 0.0
            )

        direction = 1.0 if action == "buy" else -1.0
        price_delta = (price_close - price_open) * direction
        tick_size = params["tick_size"]
        tick_value = params["tick_value"]
        if tick_size > 0 and tick_value > 0:
            return float((price_delta / tick_size) * tick_value * volume)

        contract_size = params["contract_size"]
        if contract_size > 0:
            return float(price_delta * contract_size * volume)

        return 0.0

    def _calc_margin(
        self,
        action: str,
        symbol: str,
        volume: float,
        price: float,
    ) -> float:
        if not getattr(self, "_use_fast_calc", False):
            return float(
                self.mt5_client.order_calc_margin(
                    0 if action == "buy" else 1,
                    symbol,
                    volume,
                    price,
                )
                or 0.0
            )

        params = self._get_symbol_calc_params(symbol)
        if params is None:
            return float(
                self.mt5_client.order_calc_margin(
                    0 if action == "buy" else 1,
                    symbol,
                    volume,
                    price,
                )
                or 0.0
            )

        contract_size = params["contract_size"]
        margin_mode = params["margin_mode"]
        leverage = params["leverage"]
        tick_size = params["tick_size"]
        tick_value = params["tick_value"]

        if margin_mode == 0:
            return (volume * contract_size) / leverage
        if margin_mode == 1:
            return volume * contract_size
        if margin_mode == 2:
            return volume * contract_size * price
        if margin_mode == 3:
            return (volume * contract_size * price) / leverage
        if margin_mode == 4 and tick_size > 0:
            return volume * contract_size * price * tick_value / tick_size
        if margin_mode in (5, 6):
            return volume * contract_size * price

        return 0.0

    def _get_symbol_calc_params(self, symbol: str) -> Optional[dict[str, float]]:
        cache = cast(
            Optional[dict[str, dict[str, float]]],
            getattr(self, "_symbol_calc_cache", None),
        )
        if cache is None:
            cache = {}
            self._symbol_calc_cache = cache

        if symbol in cache:
            return cache[symbol]

        symbol_info = self._symbols_data.get(symbol)
        if symbol_info is None:
            return None

        contract_size = float(getattr(symbol_info, "trade_contract_size", 0.0) or 0.0)
        margin_mode = float(getattr(symbol_info, "trade_calc_mode", 0) or 0)
        leverage = float(getattr(self._account_data, "leverage", 100) or 100)
        tick_size = float(
            getattr(symbol_info, "trade_tick_size", 0.0)
            or getattr(symbol_info, "point", 0.0001)
        )
        tick_value = float(getattr(symbol_info, "trade_tick_value", 0.0) or 0.0)

        cache[symbol] = {
            "contract_size": contract_size,
            "margin_mode": margin_mode,
            "leverage": leverage,
            "tick_size": tick_size,
            "tick_value": tick_value,
        }
        return cache[symbol]

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

    def _run_portfolio(  # noqa: C901
        self,
        data: Dict[str, Any],
        strategy: Dict[str, Any],
        symbols: List[str],
        volume: float,
        validator: Optional[TradeValidator] = None,
        log_every: int = 500,
        verbose: bool = False,
        save_db: bool = False,
        metadata: Optional[dict] = None,
        engine_type: str = "event_driven",
        use_position_arrays: bool = True,
        use_fast_calc: bool = True,
        use_numba: bool = True,
        commission_per_contract: float = 0.0,
        slippage_points: float = 0.0,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        allocations: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Run portfolio backtest with multiple symbols.

        Args:
            data: Dictionary mapping symbol to DataFrame
            strategy: Dictionary mapping symbol to Strategy
            symbols: List of symbols to trade
            volume: Base volume for each symbol
            allocations: Dictionary mapping symbol to allocation weight (0.0-1.0)
        """
        suppress_logs = bool(not verbose)

        if not suppress_logs:
            logger.info(f"Portfolio backtest: {len(symbols)} symbols")
            logger.info(f"Symbols: {', '.join(symbols)}")

        # Validate inputs
        if not symbols:
            logger.error("No symbols provided for portfolio backtest")
            return

        # Check that all symbols have data and strategy
        for symbol in symbols:
            if symbol not in data:
                logger.error(f"Missing data for symbol: {symbol}")
                return
            if symbol not in strategy:
                logger.error(f"Missing strategy for symbol: {symbol}")
                return
            if symbol not in self._symbols_data:
                logger.error(f"Symbol not found in simulator: {symbol}")
                return

        # Use equal allocations if not provided
        if allocations is None:
            allocation_weight = 1.0 / len(symbols)
            allocations = {symbol: allocation_weight for symbol in symbols}
        else:
            # Validate allocations
            for symbol in symbols:
                if symbol not in allocations:
                    logger.warning(
                        f"Missing allocation for {symbol}, defaulting to 0.0"
                    )
                    allocations[symbol] = 0.0

        if not suppress_logs:
            logger.info(f"Allocations: {allocations}")

        # Vectorized mode not supported for portfolio
        if engine_type == "vectorised":
            logger.error("Vectorized engine not supported for portfolio mode yet")
            return

        # Get common timeline (assuming data is already synchronized)
        first_symbol = symbols[0]
        common_index = data[first_symbol].index

        # Verify all symbols have same index
        for symbol in symbols[1:]:
            if not data[symbol].index.equals(common_index):
                logger.warning(
                    f"Data for {symbol} has different index than {first_symbol}. "
                    "Data should be synchronized before running portfolio backtest."
                )

        if not suppress_logs:
            logger.info(f"Common timeline: {len(common_index)} bars")
            logger.info(f"Period: {common_index[0]} to {common_index[-1]}")

        # Handle warmup period - slice data to trading period
        trading_start = None
        trading_end = None
        warmup_bars = 0

        if start_date is not None:
            trading_start = self._to_datetime(start_date)
            if not suppress_logs:
                logger.info(f"Trading period starts: {trading_start}")

            # Filter data for all symbols to trading period
            mask = common_index >= trading_start
            if mask.any():
                warmup_bars = (~mask).sum()
                common_index = common_index[mask]
                data = {sym: df[mask].copy() for sym, df in data.items()}

                if not suppress_logs:
                    logger.info(
                        f"Warmup period: {warmup_bars} bars (signals calculated but trades excluded)"
                    )
                    logger.info(f"Trading period: {len(common_index)} bars")

        if end_date is not None:
            trading_end = self._to_datetime(end_date)
            if not suppress_logs:
                logger.info(f"Trading period ends: {trading_end}")

            # Filter data to end date
            mask = common_index <= trading_end
            if mask.any():
                common_index = common_index[mask]
                data = {sym: df[mask].copy() for sym, df in data.items()}

        # Initialize
        if validator is None:
            validator = TradeValidator()

        self._use_position_arrays = bool(use_position_arrays)
        self._use_fast_calc = bool(use_fast_calc)
        self._use_numba = bool(use_numba and NUMBA_AVAILABLE)

        # Store backtest settings in simulator (where commission is calculated)
        self._backtest_commission_per_contract = float(commission_per_contract)
        self._backtest_slippage_points = float(slippage_points)

        # IMPORTANT: Set commission and slippage on the simulator client
        if hasattr(self, "_simulator"):
            self._simulator._backtest_commission_per_contract = float(
                commission_per_contract
            )
            self._simulator._backtest_slippage_points = float(slippage_points)
            if not suppress_logs:
                logger.info(
                    f"Commission set to: ${commission_per_contract} per contract"
                )
                logger.info(f"Slippage set to: {slippage_points} points")

        # Initialize equity curve
        equity_curve = []
        initial_balance = self._account_data.balance

        # Main simulation loop - iterate over common timeline
        for i, timestamp in enumerate(common_index):

            # Update ticks for ALL symbols
            for symbol in symbols:
                bar = data[symbol].loc[timestamp]
                symbol_info = self._symbols_data[symbol]

                # Update tick data
                tick = self._ensure_tick(symbol)
                tick.bid = float(bar.get("close", bar.get("Close", 0.0)))
                tick.ask = tick.bid + (symbol_info.spread * symbol_info.point)
                tick.last = tick.bid
                tick.time = (
                    int(timestamp.timestamp()) if hasattr(timestamp, "timestamp") else 0
                )
                tick.time_msc = tick.time * 1000

            # Process signals for EACH symbol
            # Note: _process_bar_signal() handles pending orders and position monitoring
            for symbol in symbols:
                # Get strategy for this symbol
                strat = strategy[symbol]
                symbol_data = data[symbol]

                # Apply allocation to volume
                adjusted_volume = volume * allocations.get(symbol, 0.0)

                # Round volume to symbol's volume step to ensure valid volume
                symbol_info = self._symbols_data.get(symbol)
                if symbol_info and adjusted_volume > 0:
                    vol_step = float(getattr(symbol_info, "volume_step", 0.01))
                    vol_min = float(getattr(symbol_info, "volume_min", 0.01))
                    if vol_step > 0:
                        # Round to nearest valid step
                        steps = round((adjusted_volume - vol_min) / vol_step)
                        adjusted_volume = vol_min + (steps * vol_step)
                        # Ensure volume is at least vol_min
                        adjusted_volume = max(adjusted_volume, vol_min)

                if adjusted_volume > 0:
                    # Get tick for this symbol (guaranteed to exist from _ensure_tick above)
                    sym_tick = self._ticks_data.get(symbol)
                    if sym_tick is None:
                        continue

                    # Process bar signal using existing infrastructure
                    self._process_bar_signal(
                        symbol_data,
                        i,
                        strat,
                        symbol,
                        adjusted_volume,
                        sym_tick,
                        validator,
                        verbose,
                    )

            # Monitor positions to update P&L, MAE/MFE, and check SL/TP
            # This also updates trade trackers for MAE/MFE calculation
            totals = self.monitor_positions()

            # Update account metrics based on positions
            self.monitor_account(totals)

            # Get current equity for equity curve
            current_equity = self._account_data.equity

            # Append to equity curve
            equity_curve.append((timestamp, current_equity))

            # Logging
            if not suppress_logs and log_every > 0 and (i + 1) % log_every == 0:
                logger.info(
                    f"Bar {i + 1}/{len(common_index)} | "
                    f"Equity: ${current_equity:,.2f} | "
                    f"Open Positions: {len(self._positions_data)}"
                )

        # Close all positions at end
        self.close_all_positions(reason="Portfolio backtest end")

        # Final summary
        final_balance = self._account_data.balance
        total_return = final_balance - initial_balance
        total_return_pct = (
            (total_return / initial_balance * 100) if initial_balance > 0 else 0.0
        )

        if not suppress_logs:
            logger.info("=" * 70)
            logger.info("Portfolio Backtest Complete")
            logger.info(f"Initial Balance: ${initial_balance:,.2f}")
            logger.info(f"Final Balance: ${final_balance:,.2f}")
            logger.info(f"Total Return: ${total_return:,.2f} ({total_return_pct:.2f}%)")
            logger.info(f"Total Trades: {len(self._completed_trades)}")

            # Per-symbol breakdown
            symbol_trade_counts: dict[str, int] = {}
            for trade in self._completed_trades:
                symbol = trade.symbol
                symbol_trade_counts[symbol] = symbol_trade_counts.get(symbol, 0) + 1

            logger.info("\nPer-Symbol Breakdown:")
            for symbol in symbols:
                count = symbol_trade_counts.get(symbol, 0)
                alloc = allocations.get(symbol, 0.0)
                logger.info(f"  {symbol}: {count} trades (allocation: {alloc:.1%})")

            logger.info("=" * 70)

        if save_db:
            self._save_backtest_to_db(metadata)

    def run(  # noqa: C901
        self,
        data: Any,  # Union[DataFrame, Dict[str, DataFrame]] for portfolio mode
        strategy: Any,  # Union[Strategy, Dict[str, Strategy]] for portfolio mode
        symbol: Any,  # Union[str, List[str]] for portfolio mode
        volume: float,
        validator: Optional[TradeValidator] = None,
        log_every: int = 500,
        verbose: bool = False,
        save_db: bool = False,
        metadata: Optional[dict] = None,
        step_data: Optional[Any] = None,
        data_modelling: str = "trading_timeframe",
        engine_type: str = "event_driven",
        use_position_arrays: bool = True,
        use_fast_calc: bool = True,
        use_numba: bool = True,
        commission_per_contract: float = 0.0,
        slippage_points: float = 0.0,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        allocations: Optional[Dict[str, float]] = None,  # For portfolio mode
    ) -> None:  # noqa: C901
        """
        Run the main simulation engine.

        Runs a backtest using the selected data modeling mode.

        data_modelling options:
        - "trading_timeframe": step through trading bars (default)
        - "m1_ohlc": step through M1 bars using 4-tick OHLC pattern
        - "synthetic_ticks": generate synthetic ticks from M1 data
        - "real_ticks": step through real tick data

        engine_type options:
        - "event_driven": current tick/bar-based simulator (default)
        - "vectorised": close-based vectorized backtest (fast, simplified)

        Portfolio mode:
        - Pass data as Dict[str, DataFrame] for multiple symbols
        - Pass strategy as Dict[str, Strategy] for multiple symbols
        - Pass symbol as List[str] for multiple symbols
        - Pass allocations as Dict[str, float] for position sizing

        Args:
            start_date: Optional start date for active trading period (warmup before this)
            end_date: Optional end date for active trading period (no trading after this)
            allocations: Optional dict of symbol -> allocation weight (0.0-1.0) for portfolio mode
        """
        suppress_logs = bool(not verbose)
        prev_suppress_logs = bool(getattr(self, "_suppress_backtest_logs", False))
        self._suppress_backtest_logs = suppress_logs

        # Detect portfolio mode
        is_portfolio = isinstance(data, dict)

        if is_portfolio:
            if not suppress_logs:
                logger.info(f"Starting PORTFOLIO simulation: {self.simulator_name}")
                logger.info("=" * 70)

            # Route to portfolio execution
            return self._run_portfolio(
                data=data,
                strategy=strategy,
                symbols=symbol if isinstance(symbol, list) else list(data.keys()),
                volume=volume,
                validator=validator,
                log_every=log_every,
                verbose=verbose,
                save_db=save_db,
                metadata=metadata,
                engine_type=engine_type,
                use_position_arrays=use_position_arrays,
                use_fast_calc=use_fast_calc,
                use_numba=use_numba,
                commission_per_contract=commission_per_contract,
                slippage_points=slippage_points,
                start_date=start_date,
                end_date=end_date,
                allocations=allocations,
            )

        # Single-symbol mode (existing code)
        if not suppress_logs:
            logger.info(f"Starting simulation: {self.simulator_name}")
            logger.info("=" * 70)

        symbol_info = self._symbols_data.get(symbol)
        if symbol_info is None:
            logger.error(f"Symbol not found in simulator: {symbol}")
            return

        tick = self._ensure_tick(symbol)
        point = symbol_info.point
        spread_default = symbol_info.spread

        # Convert start_date and end_date to datetime for warmup period handling
        trading_start = None
        trading_end = None
        warmup_bars = 0

        if start_date is not None:
            trading_start = self._to_datetime(start_date)
            if not suppress_logs:
                logger.info(f"Trading period starts: {trading_start}")
        if end_date is not None:
            trading_end = self._to_datetime(end_date)
            if not suppress_logs:
                logger.info(f"Trading period ends: {trading_end}")

        # Slice data to trading period for efficiency (skip warmup bars in simulation)
        # Note: Indicators are already calculated on the full dataset by the strategy
        original_data = data
        original_len = len(data)

        if trading_start is not None:
            # Find the first bar >= trading_start
            mask = data.index >= trading_start
            if mask.any():
                warmup_bars = (~mask).sum()
                data = data[mask].copy()
                if not suppress_logs:
                    logger.info(
                        f"Skipping {warmup_bars} warmup bars (data loaded from earlier for indicators)"
                    )

        if trading_end is not None:
            # Find the last bar <= trading_end
            mask = data.index <= trading_end
            if mask.any():
                data = data[mask].copy()
                if not suppress_logs:
                    bars_after = original_len - warmup_bars - len(data)
                    if bars_after > 0:
                        logger.info(f"Skipping {bars_after} bars after end_date")

        engine = str(engine_type or "event_driven").strip().lower().replace("-", "_")
        if engine not in ("event_driven", "vectorised"):
            logger.error(f"Unknown engine_type: {engine_type}")
            return

        if validator is None:
            validator = TradeValidator()

        if engine == "vectorised":
            if str(data_modelling or "trading_timeframe").strip().lower() != (
                "trading_timeframe"
            ):
                logger.error("Vectorized engine only supports trading_timeframe bars")
                return
            if metadata is not None:
                metadata["engine"] = "vectorised"

            self._use_position_arrays = bool(use_position_arrays)
            self._use_fast_calc = bool(use_fast_calc)
            self._symbol_calc_cache = {}

            # Slice data for vectorized mode (data is already sliced above)
            self._run_vectorized(
                data=data,
                strategy=strategy,
                symbol=symbol,
                volume=volume,
                point=point,
                spread_default=spread_default,
                verbose=verbose,
            )

            if save_db:
                self._save_backtest_to_db(metadata)

            if not suppress_logs:
                logger.info("\n" + "=" * 70)
                logger.info("Simulation completed")
            self._suppress_backtest_logs = prev_suppress_logs
            return

        self._use_position_arrays = bool(use_position_arrays)
        self._use_fast_calc = bool(use_fast_calc)
        self._use_numba = bool(use_numba and NUMBA_AVAILABLE)
        if suppress_logs:
            log_every = 0
        self._log_trades = bool((verbose or log_every) and not suppress_logs)
        self._symbol_calc_cache = {}
        prev_fast_backtest = None
        prev_commission = None
        prev_slippage = None
        if hasattr(self._simulator, "_fast_backtest"):
            prev_fast_backtest = self._simulator._fast_backtest
            self._simulator._fast_backtest = bool(suppress_logs)
        if hasattr(self._simulator, "_backtest_commission_per_contract"):
            prev_commission = self._simulator._backtest_commission_per_contract
            self._simulator._backtest_commission_per_contract = float(
                commission_per_contract or 0.0
            )
        if hasattr(self._simulator, "_backtest_slippage_points"):
            prev_slippage = self._simulator._backtest_slippage_points
            self._simulator._backtest_slippage_points = float(slippage_points or 0.0)
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
                # Data is already sliced to trading period, so process all bars
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
            # Build signal cache from the original full dataset
            self._signal_cache = self._build_signal_cache(original_data, strategy)
            # Account for warmup offset when accessing signal cache
            self._signal_cache_offset = warmup_bars

            close_arr = None
            spread_arr = None
            try:
                close_arr = data["close"].to_numpy()
                if "spread" in data:
                    spread_arr = data["spread"].to_numpy()
            except Exception:
                close_arr = None
                spread_arr = None

            for idx in range(len(data)):
                tick_time = data.index[idx]
                self._current_time = self._to_datetime(tick_time)

                if close_arr is not None:
                    close = float(close_arr[idx])
                    spread_points = (
                        float(spread_arr[idx])
                        if spread_arr is not None
                        else spread_default
                    )
                else:
                    row = data.iloc[idx]
                    close = float(row["close"])
                    spread_points = float(row.get("spread", spread_default))
                spread = spread_points * point

                # Use bar close as bid and add spread for ask.
                bid = close
                ask = close + spread

                self._on_tick(
                    symbol=symbol,
                    tick_time=tick_time,
                    bid=bid,
                    ask=ask,
                    last=close,
                    log_every=log_every,
                    idx=idx,
                    total=len(data),
                )

                # Process bar signal (data is already sliced to trading period)
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
            self._signal_cache = None
            self._signal_cache_offset = 0
        else:
            # Build signal cache from the original full dataset
            self._signal_cache = self._build_signal_cache(original_data, strategy)
            # Account for warmup offset when accessing signal cache
            self._signal_cache_offset = warmup_bars

            if step_data is None or len(step_data) == 0:
                logger.error("step_data is required for the selected data_modelling")
                return

            # Slice step_data to trading period for efficiency
            # original_step_data = step_data
            if trading_start is not None:
                mask = step_data.index >= trading_start
                if mask.any():
                    step_data = step_data[mask].copy()
                    if not suppress_logs:
                        warmup_steps = (~mask).sum()
                        logger.info(
                            f"Skipping {warmup_steps} warmup steps in step_data"
                        )

            if trading_end is not None:
                mask = step_data.index <= trading_end
                if mask.any():
                    step_data = step_data[mask].copy()

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
            self._signal_cache = None
            self._signal_cache_offset = 0

        # Close any remaining positions at the end of the run (MT5-style)
        self.close_all_positions(reason="Time exit")

        if save_db:
            self._save_backtest_to_db(metadata)

        if prev_fast_backtest is not None:
            self._simulator._fast_backtest = prev_fast_backtest
        if prev_commission is not None:
            self._simulator._backtest_commission_per_contract = prev_commission
        if prev_slippage is not None:
            self._simulator._backtest_slippage_points = prev_slippage

        if not suppress_logs:
            logger.info("\n" + "=" * 70)
            logger.info("Simulation completed")
        self._suppress_backtest_logs = prev_suppress_logs

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
        close_arr = None
        spread_arr = None
        try:
            close_arr = step_data["close"].to_numpy()
            if "spread" in step_data:
                spread_arr = step_data["spread"].to_numpy()
        except Exception:
            close_arr = None
            spread_arr = None
        for idx in range(len(step_data)):
            tick_time = step_data.index[idx]
            self._current_time = self._to_datetime(tick_time)
            if close_arr is not None:
                close = float(close_arr[idx])
                spread_points = (
                    float(spread_arr[idx]) if spread_arr is not None else spread_default
                )
            else:
                row = step_data.iloc[idx]
                close = float(row["close"])
                spread_points = float(row.get("spread", spread_default))
            spread = spread_points * point

            bid = close
            ask = close + spread

            self._on_tick(
                symbol=symbol,
                tick_time=tick_time,
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

    def _build_signal_cache(self, data: Any, strategy: Any) -> Optional[list]:
        """Build per-bar signal cache to avoid repeated get_signal() calls."""
        try:
            entry = (
                data["entry_signal"].fillna(0).astype(int).to_numpy()
                if "entry_signal" in data
                else None
            )
            exit_sig = (
                data["exit_signal"].fillna(0).astype(int).to_numpy()
                if "exit_signal" in data
                else None
            )
        except Exception:
            entry = None
            exit_sig = None

        if entry is None and exit_sig is None:
            return None

        cache: list[Optional[dict[str, Any]]] = [None] * len(data)
        for idx in range(len(data)):
            e = int(entry[idx]) if entry is not None else 0
            x = int(exit_sig[idx]) if exit_sig is not None else 0
            if e == 0 and x == 0:
                continue

            # Only fall back to strategy.get_signal if we need extras
            signal = strategy.get_signal(data, idx)
            if signal is None:
                cache[idx] = {"entry_signal": e, "exit_signal": x}
                continue

            signal["entry_signal"] = e
            signal["exit_signal"] = x
            cache[idx] = signal

        return cache

    # ----------------------------
    # Vectorized Engine (Close-Based)
    # ----------------------------
    def _run_vectorized(
        self,
        data: Any,
        strategy: Any,
        symbol: str,
        volume: float,
        point: float,
        spread_default: float,
        verbose: bool = False,
    ) -> None:
        """
        Run a vectorized backtest using close-only execution.

        Characteristics:
        - Processes the entire DataFrame using vectorized arrays
        - Uses close prices for entry/exit (no intra-bar SL/TP)
        - Simplified position tracking (single position at a time)
        - No mark-to-market updates

        Note: Data should already be sliced to the trading period before calling this function
        """
        if data is None or len(data) == 0:
            logger.error("No data provided for vectorized backtest")
            return

        if "close" not in data:
            logger.error("Vectorized backtest requires 'close' column")
            return

        arrays = self._vectorized_arrays(data, spread_default)
        self._vectorized_trade_buffer = [None] * len(data)
        self._vectorized_trade_count = 0
        self._vectorized_process_signals(
            data=data,
            symbol=symbol,
            volume=volume,
            point=point,
            arrays=arrays,
            verbose=verbose,
        )
        self._vectorized_flush_trades()

    def _vectorized_process_signals(
        self,
        data: Any,
        symbol: str,
        volume: float,
        point: float,
        arrays: dict[str, Any],
        verbose: bool,
    ) -> None:
        """Process signals and manage simplified positions in vectorized mode."""
        close = arrays["close"]
        index = arrays["index"]
        spread_points = arrays["spread_points"]
        entry_signal = arrays["entry_signal"]
        exit_signal = arrays["exit_signal"]

        pos_action: Optional[str] = None
        pos_id: Optional[int] = None
        entry_idx: Optional[int] = None
        entry_price: float = 0.0
        entry_time: Optional[object] = None
        entry_sl: float = 0.0
        entry_tp: float = 0.0

        def _finalize_trade(close_idx: int, reason: str) -> None:
            nonlocal pos_action, pos_id, entry_idx, entry_price, entry_time
            nonlocal entry_sl, entry_tp

            if pos_action is None or pos_id is None or entry_idx is None:
                return
            self._vectorized_finalize_trade(
                symbol=symbol,
                volume=volume,
                point=point,
                close=close,
                index=index,
                spread_points=spread_points,
                close_idx=close_idx,
                reason=reason,
                pos_id=pos_id,
                action=pos_action,
                entry_idx=entry_idx,
                entry_price=entry_price,
                entry_time=entry_time,
                entry_sl=entry_sl,
                entry_tp=entry_tp,
            )

            pos_action = None
            pos_id = None
            entry_idx = None
            entry_price = 0.0
            entry_time = None
            entry_sl = 0.0
            entry_tp = 0.0

        for idx in range(len(data)):
            if (
                verbose
                and not getattr(self, "_suppress_backtest_logs", False)
                and idx % 500 == 0
            ):
                logger.info(f"Vectorized step {idx}/{len(data)}")

            if pos_action is None:
                sig = int(entry_signal[idx])
                # Data is already sliced to trading period, process all entry signals
                if sig in (1, -1):
                    (
                        pos_action,
                        pos_id,
                        entry_idx,
                        entry_price,
                        entry_time,
                        entry_sl,
                        entry_tp,
                    ) = self._vectorized_open_position(
                        data=data,
                        symbol=symbol,
                        volume=volume,
                        point=point,
                        spread_points=spread_points,
                        close=close,
                        index=index,
                        idx=idx,
                        sig=sig,
                    )
            else:
                exit_sig = int(exit_signal[idx])
                if (pos_action == "buy" and exit_sig == 1) or (
                    pos_action == "sell" and exit_sig == -1
                ):
                    _finalize_trade(idx, reason="Signal exit")

        if pos_action is not None and entry_idx is not None:
            _finalize_trade(len(data) - 1, reason="Time exit")

    def _vectorized_arrays(self, data: Any, spread_default: float) -> dict[str, Any]:
        """Prepare vectorized arrays used by the close-based engine."""
        close = data["close"].astype(float).to_numpy()
        index = data.index
        spread_points = (
            data["spread"].fillna(spread_default).astype(float).to_numpy()
            if "spread" in data
            else np.full(len(data), float(spread_default))
        )
        entry_signal = (
            data["entry_signal"].fillna(0).astype(int).to_numpy()
            if "entry_signal" in data
            else np.zeros(len(data), dtype=int)
        )
        exit_signal = (
            data["exit_signal"].fillna(0).astype(int).to_numpy()
            if "exit_signal" in data
            else np.zeros(len(data), dtype=int)
        )
        return {
            "close": close,
            "index": index,
            "spread_points": spread_points,
            "entry_signal": entry_signal,
            "exit_signal": exit_signal,
        }

    def _vectorized_open_position(
        self,
        data: Any,
        symbol: str,
        volume: float,
        point: float,
        spread_points: np.ndarray,
        close: np.ndarray,
        index: Any,
        idx: int,
        sig: int,
    ) -> tuple[str, int, int, float, object, float, float]:
        """Open a simplified position for the vectorized engine."""
        pos_action = "buy" if sig == 1 else "sell"
        entry_idx = idx
        entry_price = float(close[idx])
        entry_time = index[idx]
        row = data.iloc[idx]
        entry_sl = float(row.get("stop_loss", 0.0) or 0.0)
        entry_tp = float(row.get("take_profit", 0.0) or 0.0)

        bid = entry_price
        ask = entry_price + (float(spread_points[idx]) * point)
        tick = self._ensure_tick(symbol)
        tick.bid = float(bid)
        tick.ask = float(ask)
        tick.last = float(entry_price)

        pos_id = int(self._simulator._next_position_id)
        self._simulator._next_position_id += 1
        self._ensure_trade_record(
            pos_id=pos_id,
            action=pos_action,
            symbol=symbol,
            volume=float(volume),
            price=float(entry_price),
            sl=float(entry_sl),
            tp=float(entry_tp),
            comment="",
            requested_entry_price=float(entry_price),
            open_time=entry_time,
        )

        return (
            pos_action,
            pos_id,
            entry_idx,
            entry_price,
            entry_time,
            entry_sl,
            entry_tp,
        )

    def _vectorized_finalize_trade(
        self,
        symbol: str,
        volume: float,
        point: float,
        close: np.ndarray,
        index: Any,
        spread_points: np.ndarray,
        close_idx: int,
        reason: str,
        pos_id: int,
        action: str,
        entry_idx: int,
        entry_price: float,
        entry_time: object,
        entry_sl: float,
        entry_tp: float,
    ) -> None:
        """Finalize a vectorized trade and update records/account."""
        close_price = float(close[close_idx])
        close_time = index[close_idx]
        self._current_time = self._to_datetime(close_time)

        bid = close_price
        ask = close_price + (float(spread_points[close_idx]) * point)
        tick = self._ensure_tick(symbol)
        tick.bid = float(bid)
        tick.ask = float(ask)
        tick.last = float(close_price)

        profit = self._calc_profit(
            action=action,
            symbol=symbol,
            volume=float(volume),
            price_open=float(entry_price),
            price_close=float(close_price),
        )

        record = self._trade_records_open.get(pos_id)
        if record is None:
            self._ensure_trade_record(
                pos_id=pos_id,
                action=action,
                symbol=symbol,
                volume=float(volume),
                price=float(entry_price),
                sl=float(entry_sl),
                tp=float(entry_tp),
                comment="",
                requested_entry_price=float(entry_price),
                open_time=entry_time,
            )
            record = self._trade_records_open.get(pos_id)

        if record is not None:
            record.close_time = self._to_datetime(close_time)
            record.close_price = float(close_price)
            record.requested_exit_price = float(close_price)
            if reason == "Time exit":
                record.close_type = "TIME_EXIT"
                record.exit_reason = "TIMEOUT"
            else:
                record.close_type = "SIGNAL_EXIT"
                record.exit_reason = "STRATEGY_EXIT"

            record.profit_loss = float(profit)
            pip_size = self._pip_size(symbol)
            if pip_size > 0:
                if action == "buy":
                    record.profit_loss_pips = (
                        close_price - record.open_price
                    ) / pip_size
                else:
                    record.profit_loss_pips = (
                        record.open_price - close_price
                    ) / pip_size

            record.commission = 0.0
            record.swap = 0.0

            record.bars_in_trade = int(close_idx - entry_idx + 1)
            record.time_in_trade = float(
                (
                    self._to_datetime(close_time) - self._to_datetime(entry_time)
                ).total_seconds()
            )

            price_slice = close[entry_idx : close_idx + 1]
            if price_slice.size > 0:
                if action == "buy":
                    mfe_price = float(price_slice.max())
                    mae_price = float(price_slice.min())
                    record.mfe_pips = (
                        (mfe_price - entry_price) / pip_size if pip_size > 0 else 0.0
                    )
                    record.mae_pips = (
                        (mae_price - entry_price) / pip_size if pip_size > 0 else 0.0
                    )
                else:
                    mfe_price = float(price_slice.min())
                    mae_price = float(price_slice.max())
                    record.mfe_pips = (
                        (entry_price - mfe_price) / pip_size if pip_size > 0 else 0.0
                    )
                    record.mae_pips = (
                        (entry_price - mae_price) / pip_size if pip_size > 0 else 0.0
                    )

                record.mfe_usd = float(
                    self.mt5_client.order_calc_profit(
                        0 if action == "buy" else 1,
                        symbol,
                        float(volume),
                        float(entry_price),
                        float(mfe_price),
                    )
                )
                record.mae_usd = float(
                    self.mt5_client.order_calc_profit(
                        0 if action == "buy" else 1,
                        symbol,
                        float(volume),
                        float(entry_price),
                        float(mae_price),
                    )
                )

            if record.initial_risk_usd > 0:
                record.r_multiple = record.profit_loss / record.initial_risk_usd

            self._vectorized_store_trade(record)
            self._trade_records_open.pop(pos_id, None)
            self._trade_trackers.pop(pos_id, None)

        self._account_data.balance = float(self._account_data.balance + profit)
        self._account_data.equity = float(self._account_data.balance)
        self._account_data.margin = 0.0
        self._account_data.margin_free = float(self._account_data.balance)
        self._account_data.profit = 0.0
        self._account_data.commission_blocked = 0.0
        self._account_data.liabilities = 0.0

    def _vectorized_store_trade(self, record: Any) -> None:
        """Store a completed trade with a pre-allocated buffer when available."""
        buffer = getattr(self, "_vectorized_trade_buffer", None)
        if not isinstance(buffer, list):
            self._completed_trades.append(record)
            return

        idx = int(getattr(self, "_vectorized_trade_count", 0))
        if idx >= len(buffer):
            self._completed_trades.append(record)
            return

        buffer[idx] = record
        self._vectorized_trade_count = idx + 1

    def _vectorized_flush_trades(self) -> None:
        """Flush buffered vectorized trades into the completed trades list."""
        buffer = getattr(self, "_vectorized_trade_buffer", None)
        if not isinstance(buffer, list):
            return

        count = int(getattr(self, "_vectorized_trade_count", 0))
        for idx in range(count):
            record = buffer[idx]
            if record is not None:
                self._completed_trades.append(record)

        self._vectorized_trade_buffer = None
        self._vectorized_trade_count = 0
