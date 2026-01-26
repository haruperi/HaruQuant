"""
Trade simulator module (MT5-aligned, local execution).

Implements a lightweight trade simulator inspired by MQL5 practices while
remaining independent of live trading. Uses apps.ctrade for symbol/account
property access when MT5 is available.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import MetaTrader5 as mt5

from apps.ctrade import CSymbolInfo
from apps.sqlite import SQLiteDatabase


@dataclass(frozen=True)
class SymbolSnapshot:
    """Store a snapshot of symbol trading properties."""

    symbol: str
    digits: int
    point: float
    tick_value: float
    tick_size: float
    contract_size: float
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level: int
    freeze_level: int
    bid: float
    ask: float


class TradeSimulator:
    """
    Local trade simulator with MT5-aligned behavior.

    Uses CSymbolInfo for symbol properties and rates.
    """

    def __init__(
        self,
        simulator_name: str = "Simulator",
        deposit: float = 10000.0,
        leverage: str | float = "1:100",
        db: Optional[SQLiteDatabase] = None,
        toolbox_callback: Optional[
            Callable[[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]], None]
        ] = None,
    ) -> None:
        """Initialize the simulator with basic account configuration."""
        # ------------------------------------------------------------------

        # Simulator Metadata
        self.simulator_name = simulator_name
        self._leverage = self._parse_leverage(leverage)
        self._db = db
        self._toolbox_callback = toolbox_callback

        # Initialize variables
        self._next_id = 1
        self.magic_number: Optional[int] = None
        self.deviation_points: Optional[int] = None
        self.filling_type: Optional[int] = None
        self.last_error: str = ""

        # Account's information
        self.account_info = {
            "balance": float(deposit),
            "equity": float(deposit),
            "profit": 0.0,
            "margin": 0.0,
            "free_margin": float(deposit),
            "margin_level": 0.0,
            "leverage": float(self._leverage),
        }

        # Position's information
        self.position_info: dict[str, Any] = {
            "time": None,
            "id": 0,
            "magic": 0,
            "symbol": None,
            "type": None,
            "volume": 0.0,
            "open_price": 0.0,
            "price": 0.0,
            "spread": 0.0,
            "sl": 0.0,
            "tp": 0.0,
            "commission": 0.0,
            "margin_required": 0.0,
            "fee": 0.0,
            "swap": 0.0,
            "profit": 0.0,
            "comment": 0,
            "entry_reason": "",
            "session_id": None,
        }

        # Order's information
        self.order_info: dict[str, Any] = self.position_info.copy()
        self.order_info["expiry_date"] = None
        self.order_info["expiration_mode"] = ""

        # Deal's information
        self.deal_info: dict[str, Any] = self.position_info.copy()
        self.deal_info["reason"] = None
        self.deal_info["direction"] = None

        # Containers
        self.positions_container: list[dict[str, Any]] = (
            []
        )  # a list for storing all opened trades
        self.orders_container: list[dict[str, Any]] = (
            []
        )  # a list for storing all pending orders
        self.deals_container: list[dict[str, Any]] = (
            []
        )  # a list for storing all closed trades

        # Trade history folder
        self.simulations_folder: str = "data/simulations"
        os.makedirs(self.simulations_folder, exist_ok=True)

    # ------------------------------------------------------------------
    # Trading Simulator 101 (core containers and helpers)
    # ------------------------------------------------------------------
    def _parse_leverage(self, leverage: str | float) -> float:
        if isinstance(leverage, (int, float)):
            return float(leverage)
        if ":" in leverage:
            _, ratio = leverage.split(":", 1)
            ratio_value = float(ratio)
            return ratio_value if ratio_value > 0 else 1.0
        ratio_value = float(leverage)
        return ratio_value if ratio_value > 0 else 1.0

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _set_error(self, message: str) -> bool:
        self.last_error = message
        return False

    def set_magic_number(self, magic_number: int) -> None:
        """Set the simulator magic number."""
        self.magic_number = int(magic_number)

    def set_deviation_in_points(self, deviation_points: int) -> None:
        """Set the allowable slippage in points."""
        self.deviation_points = int(deviation_points)

    def run_toolbox(self) -> None:
        """Run the attached toolbox callback if provided."""
        if self._toolbox_callback is not None:
            self._toolbox_callback(
                self.account_info, self.positions_container, self.orders_container
            )

    def get_positions(self) -> list[dict[str, Any]]:
        """Return a copy of open positions."""
        return list(self.positions_container)

    def get_orders(self) -> list[dict[str, Any]]:
        """Return a copy of pending orders."""
        return list(self.orders_container)

    def get_deals(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        from_db: bool = False,
    ) -> list[dict[str, Any]]:
        """Return deal history from memory or optional sqlite storage."""
        if start_time is None or end_time is None:
            return list(self.deals_container) if not from_db else []
        if start_time > end_time:
            start_time, end_time = end_time, start_time
        if not from_db:
            return [
                deal
                for deal in self.deals_container
                if start_time <= deal["time"] <= end_time
            ]
        if self._db is None:
            return []
        return self._load_deals_from_db(start_time, end_time)

    def _symbol_snapshot(
        self,
        symbol: str,
        price_feed: Optional[dict[str, Any]] = None,
    ) -> SymbolSnapshot:
        info = CSymbolInfo(symbol)
        info.Refresh()
        info.RefreshRates()

        bid, ask = self._resolve_bid_ask(symbol, price_feed, info)

        return SymbolSnapshot(
            symbol=symbol,
            digits=int(info.Digits()),
            point=float(info.Point()),
            tick_value=float(info.TickValue()),
            tick_size=float(info.TickSize()),
            contract_size=float(info.ContractSize()),
            volume_min=float(info.LotsMin()),
            volume_max=float(info.LotsMax()),
            volume_step=float(info.LotsStep()),
            stops_level=int(info.StopsLevel()),
            freeze_level=int(info.FreezeLevel()),
            bid=bid,
            ask=ask,
        )

    def _resolve_bid_ask(
        self,
        symbol: str,
        price_feed: Optional[dict[str, Any]],
        info: CSymbolInfo,
    ) -> tuple[float, float]:
        if price_feed and symbol in price_feed:
            value = price_feed[symbol]
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return float(value[0]), float(value[1])
            if isinstance(value, dict):
                return float(value.get("bid", 0.0)), float(value.get("ask", 0.0))
            return float(value), float(value)
        return float(info.Bid()), float(info.Ask())

    def _save_deal(self, deal: dict[str, Any]) -> None:
        if self._db is None:
            return
        self._db.save_simulator_deal(deal)

    def _load_deals_from_db(
        self, start_time: datetime, end_time: datetime
    ) -> list[dict[str, Any]]:
        if self._db is None:
            return []
        return self._db.load_simulator_deals(start_time, end_time)

    # ------------------------------------------------------------------
    # Calculating Profits/Loss Made By a Position
    # ------------------------------------------------------------------
    def calculate_profit(
        self,
        action: str,
        symbol: str,
        volume: float,
        entry_price: float,
        exit_price: float,
        price_feed: Optional[dict[str, Any]] = None,
    ) -> float:
        """Calculate profit for a simulated position."""
        action = action.lower()
        if action not in ("buy", "sell"):
            return 0.0
        order_type = mt5.ORDER_TYPE_BUY if action == "buy" else mt5.ORDER_TYPE_SELL
        if hasattr(mt5, "order_calc_profit"):
            result = mt5.order_calc_profit(
                order_type, symbol, float(volume), float(entry_price), float(exit_price)
            )
            if result is not None:
                return float(result)

        snapshot = self._symbol_snapshot(symbol, price_feed)
        direction = 1.0 if action == "buy" else -1.0
        price_delta = (exit_price - entry_price) * direction

        if snapshot.tick_size > 0 and snapshot.tick_value > 0:
            ticks = price_delta / snapshot.tick_size
            return float(ticks * snapshot.tick_value * volume)

        if snapshot.contract_size > 0:
            return float(price_delta * snapshot.contract_size * volume)

        return 0.0

    # ------------------------------------------------------------------
    # Simulating a Position
    # ------------------------------------------------------------------
    def open_position(
        self,
        action: str,
        symbol: str,
        volume: float,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        price_feed: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Open a simulated position."""
        snapshot = self._symbol_snapshot(symbol, price_feed)
        open_price = self._resolve_open_price(action, snapshot, price)
        if open_price <= 0:
            self._set_error("Price is not available for the symbol.")
            return None

        if not self._validate_trade(action, snapshot, volume, open_price, sl, tp):
            return None

        margin_required = self._calc_margin(symbol, action, volume, open_price)
        if not self._ensure_margin(margin_required):
            return None

        position = self.position_info.copy()
        position.update(
            {
                "id": self._next_id,
                "magic": self.magic_number or 0,
                "symbol": symbol,
                "type": action.lower(),
                "volume": float(volume),
                "open_price": float(open_price),
                "price": float(open_price),
                "spread": float(snapshot.ask - snapshot.bid),
                "sl": float(sl),
                "tp": float(tp),
                "profit": 0.0,
                "swap": 0.0,
                "commission": 0.0,
                "fee": 0.0,
                "margin_required": float(margin_required),
                "comment": comment,
                "time": self._now(),
                "entry_reason": "market",
                "session_id": None,
            }
        )
        position["margin"] = float(margin_required)
        self.positions_container.append(position)
        self._next_id += 1
        self._record_deal(position, direction="opened", reason="Expert")
        self._recalculate_account()
        return position

    def _resolve_open_price(
        self, action: str, snapshot: SymbolSnapshot, price: float
    ) -> float:
        if price > 0:
            return float(price)
        if action.lower() == "buy":
            return float(snapshot.ask)
        return float(snapshot.bid)

    def buy(
        self,
        volume: float,
        symbol: str,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        price_feed: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Open a simulated buy position."""
        return self.open_position(
            "buy", symbol, volume, price, sl, tp, comment, price_feed
        )

    def sell(
        self,
        volume: float,
        symbol: str,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        price_feed: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Open a simulated sell position."""
        return self.open_position(
            "sell", symbol, volume, price, sl, tp, comment, price_feed
        )

    # ------------------------------------------------------------------
    # Trade Validations
    # ------------------------------------------------------------------
    def _validate_trade(
        self,
        action: str,
        snapshot: SymbolSnapshot,
        volume: float,
        price: float,
        sl: float,
        tp: float,
        check_deviation: bool = True,
    ) -> bool:
        action = action.lower()
        if not self._validate_action(action, snapshot):
            return False
        if not self._validate_volume(volume, snapshot):
            return False
        if not self._validate_stop_distances(price, sl, tp, snapshot):
            return False
        if not self._validate_deviation(action, price, snapshot, check_deviation):
            return False
        if not self._validate_stop_direction(action, price, sl, tp):
            return False
        return True

    def _validate_action(self, action: str, snapshot: SymbolSnapshot) -> bool:
        if action not in ("buy", "sell"):
            return self._set_error("Action must be 'buy' or 'sell'.")
        if not snapshot.symbol:
            return self._set_error("Symbol is required.")
        if not self._valid_prices(snapshot):
            return self._set_error("Invalid bid/ask price for the symbol.")
        return True

    def _validate_volume(self, volume: float, snapshot: SymbolSnapshot) -> bool:
        if volume <= 0:
            return self._set_error("Volume must be greater than zero.")
        if volume < snapshot.volume_min or volume > snapshot.volume_max:
            return self._set_error("Volume is outside allowed range.")
        if not self._volume_in_step(volume, snapshot.volume_min, snapshot.volume_step):
            return self._set_error("Volume does not align with the symbol step.")
        return True

    def _validate_stop_distances(
        self,
        price: float,
        sl: float,
        tp: float,
        snapshot: SymbolSnapshot,
    ) -> bool:
        if sl > 0 or tp > 0:
            min_distance = (
                max(snapshot.stops_level, snapshot.freeze_level) * snapshot.point
            )
            if sl > 0 and abs(price - sl) < min_distance:
                return self._set_error("Stop loss is too close to price.")
            if tp > 0 and abs(price - tp) < min_distance:
                return self._set_error("Take profit is too close to price.")
        return True

    def _validate_deviation(
        self,
        action: str,
        price: float,
        snapshot: SymbolSnapshot,
        check_deviation: bool,
    ) -> bool:
        if not check_deviation or self.deviation_points is None:
            return True
        actual_price = snapshot.ask if action == "buy" else snapshot.bid
        max_deviation = self.deviation_points * snapshot.point
        if abs(price - actual_price) > max_deviation:
            return self._set_error("Price is outside the allowed deviation range.")
        return True

    def _validate_stop_direction(
        self, action: str, price: float, sl: float, tp: float
    ) -> bool:
        if action == "buy":
            if sl > 0 and sl >= price:
                return self._set_error("Stop loss must be below the buy price.")
            if tp > 0 and tp <= price:
                return self._set_error("Take profit must be above the buy price.")
            return True
        if sl > 0 and sl <= price:
            return self._set_error("Stop loss must be above the sell price.")
        if tp > 0 and tp >= price:
            return self._set_error("Take profit must be below the sell price.")
        return True

    def _volume_in_step(self, volume: float, minimum: float, step: float) -> bool:
        if step <= 0:
            return True
        steps = round((volume - minimum) / step)
        aligned = minimum + steps * step
        return abs(aligned - volume) <= step * 1e-6

    def _valid_prices(self, snapshot: SymbolSnapshot) -> bool:
        return snapshot.bid > 0 and snapshot.ask > 0

    # ------------------------------------------------------------------
    # Modifying Positions
    # ------------------------------------------------------------------
    def modify_position(
        self,
        position_id: int,
        sl: float = 0.0,
        tp: float = 0.0,
        price_feed: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Modify the stop loss or take profit for a position."""
        position = self._find_position(position_id)
        if position is None:
            return self._set_error("Position not found.")

        snapshot = self._symbol_snapshot(position["symbol"], price_feed)
        if not self._validate_trade(
            position["type"],
            snapshot,
            position["volume"],
            position["open_price"],
            sl,
            tp,
            check_deviation=False,
        ):
            return False

        position["sl"] = float(sl)
        position["tp"] = float(tp)
        return True

    # ------------------------------------------------------------------
    # Market's Pending Orders
    # ------------------------------------------------------------------
    def _place_pending_order(
        self,
        order_type: str,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        expiry_date: Optional[datetime] = None,
        expiration_mode: str = "gtc",
        price_feed: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Place a pending order in the simulator."""
        order_type = order_type.lower()
        if order_type not in ("buy limit", "buy stop", "sell limit", "sell stop"):
            self._set_error("Invalid pending order type.")
            return None

        expiration_mode = expiration_mode.lower()
        if expiration_mode not in ("gtc", "daily", "daily_excluding_stops"):
            self._set_error("Invalid expiration mode.")
            return None

        snapshot = self._symbol_snapshot(symbol, price_feed)
        if open_price <= 0:
            self._set_error("Pending order price must be greater than zero.")
            return None

        if not self._validate_pending_order(
            order_type, snapshot, volume, open_price, sl, tp, expiry_date
        ):
            return None

        order = self.order_info.copy()
        order.update(
            {
                "id": self._next_id,
                "magic": self.magic_number or 0,
                "symbol": symbol,
                "type": order_type,
                "volume": float(volume),
                "open_price": float(open_price),
                "price": float(open_price),
                "spread": float(snapshot.ask - snapshot.bid),
                "sl": float(sl),
                "tp": float(tp),
                "comment": comment,
                "margin_required": self._calc_margin(
                    symbol,
                    "buy" if "buy" in order_type else "sell",
                    volume,
                    open_price,
                ),
                "expiry_date": expiry_date,
                "expiration_mode": expiration_mode,
                "time": self._now(),
                "entry_reason": "pending",
                "session_id": None,
            }
        )
        self.orders_container.append(order)
        self._next_id += 1
        return order

    def _validate_pending_order(
        self,
        order_type: str,
        snapshot: SymbolSnapshot,
        volume: float,
        open_price: float,
        sl: float,
        tp: float,
        expiry_date: Optional[datetime],
    ) -> bool:
        if order_type == "buy stop" and snapshot.ask >= open_price:
            return self._set_error("Buy stop price must be above ask.")
        if order_type == "buy limit" and snapshot.bid <= open_price:
            return self._set_error("Buy limit price must be below bid.")
        if order_type == "sell stop" and snapshot.bid <= open_price:
            return self._set_error("Sell stop price must be below bid.")
        if order_type == "sell limit" and snapshot.ask >= open_price:
            return self._set_error("Sell limit price must be above ask.")
        if not self._valid_prices(snapshot):
            return self._set_error("Invalid bid/ask price for the symbol.")

        min_distance = max(snapshot.stops_level, snapshot.freeze_level) * snapshot.point
        if order_type in ("buy limit", "buy stop"):
            if abs(open_price - snapshot.bid) < min_distance:
                return self._set_error("Pending buy order is too close to market.")
        else:
            if abs(open_price - snapshot.ask) < min_distance:
                return self._set_error("Pending sell order is too close to market.")

        if expiry_date is not None and expiry_date <= self._now():
            return self._set_error("Pending order expiry must be in the future.")

        action = "buy" if "buy" in order_type else "sell"
        return self._validate_trade(
            action, snapshot, volume, open_price, sl, tp, check_deviation=False
        )

    def buy_stop(
        self,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        expiry_date: Optional[datetime] = None,
        expiration_mode: str = "gtc",
        price_feed: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Place a buy stop order."""
        return self._place_pending_order(
            "buy stop",
            volume,
            symbol,
            open_price,
            sl,
            tp,
            comment,
            expiry_date,
            expiration_mode,
            price_feed,
        )

    def buy_limit(
        self,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        expiry_date: Optional[datetime] = None,
        expiration_mode: str = "gtc",
        price_feed: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Place a buy limit order."""
        return self._place_pending_order(
            "buy limit",
            volume,
            symbol,
            open_price,
            sl,
            tp,
            comment,
            expiry_date,
            expiration_mode,
            price_feed,
        )

    def sell_stop(
        self,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        expiry_date: Optional[datetime] = None,
        expiration_mode: str = "gtc",
        price_feed: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Place a sell stop order."""
        return self._place_pending_order(
            "sell stop",
            volume,
            symbol,
            open_price,
            sl,
            tp,
            comment,
            expiry_date,
            expiration_mode,
            price_feed,
        )

    def sell_limit(
        self,
        volume: float,
        symbol: str,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        expiry_date: Optional[datetime] = None,
        expiration_mode: str = "gtc",
        price_feed: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Place a sell limit order."""
        return self._place_pending_order(
            "sell limit",
            volume,
            symbol,
            open_price,
            sl,
            tp,
            comment,
            expiry_date,
            expiration_mode,
            price_feed,
        )

    # ------------------------------------------------------------------
    # Deleting Pending Orders
    # ------------------------------------------------------------------
    def delete_order(self, order_id: int) -> bool:
        """Delete a pending order by id."""
        for order in list(self.orders_container):
            if order["id"] == order_id:
                self.orders_container.remove(order)
                return True
        return self._set_error("Order not found.")

    # ------------------------------------------------------------------
    # Modifying Pending Orders
    # ------------------------------------------------------------------
    def modify_order(
        self,
        order_id: int,
        open_price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        expiry_date: Optional[datetime] = None,
        expiration_mode: Optional[str] = None,
        price_feed: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Modify a pending order."""
        order = None
        for candidate in self.orders_container:
            if candidate["id"] == order_id:
                order = candidate
                break
        if order is None:
            return self._set_error("Order not found.")

        snapshot = self._symbol_snapshot(order["symbol"], price_feed)
        if not self._validate_pending_order(
            order["type"], snapshot, order["volume"], open_price, sl, tp, expiry_date
        ):
            return False

        order["open_price"] = float(open_price)
        order["sl"] = float(sl)
        order["tp"] = float(tp)
        if expiry_date is not None:
            order["expiry_date"] = expiry_date
        if expiration_mode is not None:
            order["expiration_mode"] = expiration_mode.lower()
        return True

    # ------------------------------------------------------------------
    # Monitoring Pending Orders
    # ------------------------------------------------------------------
    def monitor_pending_orders(
        self, price_feed: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """Check pending orders for expiration or trigger conditions."""
        now = self._now()
        expired_orders: list[dict[str, Any]] = []
        triggered_orders: list[dict[str, Any]] = []

        for order in list(self.orders_container):
            if self._order_expired(order, now):
                expired_orders.append(order)
                continue

            snapshot = self._symbol_snapshot(order["symbol"], price_feed)
            order_type = order["type"]
            order["price"] = snapshot.ask if "buy" in order_type else snapshot.bid

            if self._trigger_pending_order(order, snapshot, price_feed):
                triggered_orders.append(order)

        for order in expired_orders + triggered_orders:
            if order in self.orders_container:
                self.orders_container.remove(order)

        return triggered_orders

    def _order_expired(self, order: dict[str, Any], now: datetime) -> bool:
        expiration_mode = order.get("expiration_mode", "gtc")
        expiry_date = order.get("expiry_date")
        return (
            expiration_mode in ("daily", "daily_excluding_stops")
            and expiry_date is not None
            and now >= expiry_date
        )

    def _trigger_pending_order(
        self,
        order: dict[str, Any],
        snapshot: SymbolSnapshot,
        price_feed: Optional[dict[str, Any]],
    ) -> bool:
        ask = snapshot.ask
        bid = snapshot.bid
        open_price = float(order["open_price"])
        order_type = order["type"]

        if (order_type == "buy limit" and ask <= open_price) or (
            order_type == "buy stop" and ask >= open_price
        ):
            return self._execute_pending_buy(order, ask, price_feed)
        if (order_type == "sell limit" and bid >= open_price) or (
            order_type == "sell stop" and bid <= open_price
        ):
            return self._execute_pending_sell(order, bid, price_feed)
        return False

    def _execute_pending_buy(
        self,
        order: dict[str, Any],
        price: float,
        price_feed: Optional[dict[str, Any]],
    ) -> bool:
        return (
            self.buy(
                order["volume"],
                order["symbol"],
                price,
                order["sl"],
                order["tp"],
                order.get("comment", ""),
                price_feed,
            )
            is not None
        )

    def _execute_pending_sell(
        self,
        order: dict[str, Any],
        price: float,
        price_feed: Optional[dict[str, Any]],
    ) -> bool:
        return (
            self.sell(
                order["volume"],
                order["symbol"],
                price,
                order["sl"],
                order["tp"],
                order.get("comment", ""),
                price_feed,
            )
            is not None
        )

    # ------------------------------------------------------------------
    # Monitoring the Account
    # ------------------------------------------------------------------
    def monitor_account(self, verbose: bool = False) -> dict[str, Any]:
        """Recalculate all account metrics based on current positions and optionally log them."""
        self._recalculate_account()
        if verbose:
            print(
                "Balance: {:.2f} | Equity: {:.2f} | Profit: {:.2f} | "
                "Margin: {:.2f} | Free margin: {:.2f} | Margin level: {:.2f}%".format(
                    self.account_info["balance"],
                    self.account_info["equity"],
                    self.account_info["profit"],
                    self.account_info["margin"],
                    self.account_info["free_margin"],
                    self.account_info["margin_level"],
                )
            )
        return dict(self.account_info)

    # ------------------------------------------------------------------
    # RealTime Trade Simulation in Python
    # ------------------------------------------------------------------
    def realtime_step(self, price_feed: Optional[dict[str, Any]] = None) -> None:
        """Run one realtime simulation step."""
        self.monitor_pending_orders(price_feed=price_feed)
        self.monitor_positions(price_feed=price_feed)
        self.monitor_account(verbose=False)
        self.run_toolbox()

    # ------------------------------------------------------------------
    # Monitoring Positions
    # ------------------------------------------------------------------
    def monitor_positions(
        self, price_feed: Optional[dict[str, Any]] = None, verbose: bool = False
    ) -> list[dict[str, Any]]:
        """Update positions with current prices and close at SL/TP when hit."""
        closed_positions: list[dict[str, Any]] = []

        for position in list(self.positions_container):
            snapshot = self._symbol_snapshot(position["symbol"], price_feed)
            current_price = snapshot.ask if position["type"] == "buy" else snapshot.bid
            position["price"] = float(current_price)
            position["profit"] = self.calculate_profit(
                position["type"],
                position["symbol"],
                position["volume"],
                position["open_price"],
                current_price,
                price_feed,
            )

            reason = self._close_reason(position)
            if reason:
                closed_positions.append(
                    self._close_position(position, current_price, reason)
                )
            if verbose:
                print(
                    "Sim -> Ticket : {} | Symbol : {} | Time : {} | Type : {} | Volume : {} | SL : {} | TP : {}".format(
                        position["id"],
                        position["symbol"],
                        position["time"],
                        position["type"],
                        position["volume"],
                        position["sl"],
                        position["tp"],
                    )
                )

        if closed_positions:
            self._recalculate_account()

        return closed_positions

    def _close_reason(self, position: dict[str, Any]) -> str:
        price = position["price"]
        if position["type"] == "buy":
            if position["sl"] > 0 and price <= position["sl"]:
                return "Stop Loss"
            if position["tp"] > 0 and price >= position["tp"]:
                return "Take Profit"
        else:
            if position["sl"] > 0 and price >= position["sl"]:
                return "Stop Loss"
            if position["tp"] > 0 and price <= position["tp"]:
                return "Take Profit"
        return ""

    def _close_position(
        self, position: dict[str, Any], price: float, reason: str
    ) -> dict[str, Any]:
        profit = self.calculate_profit(
            position["type"],
            position["symbol"],
            position["volume"],
            position["open_price"],
            price,
        )
        deal = self.deal_info.copy()
        deal.update(
            {
                "id": position["id"],
                "magic": position.get("magic", 0),
                "symbol": position["symbol"],
                "type": position["type"],
                "direction": "closed",
                "volume": position["volume"],
                "price": float(price),
                "spread": position.get("spread", 0.0),
                "sl": position.get("sl", 0.0),
                "tp": position.get("tp", 0.0),
                "commission": position.get("commission", 0.0),
                "margin_required": position.get("margin_required", 0.0),
                "fee": position.get("fee", 0.0),
                "swap": position.get("swap", 0.0),
                "profit": float(profit),
                "comment": position.get("comment", ""),
                "time": self._now(),
                "reason": reason,
                "entry_reason": position.get("entry_reason", ""),
                "session_id": position.get("session_id"),
            }
        )
        self.deals_container.append(deal)
        self._save_deal(deal)
        self.positions_container.remove(position)
        self.account_info["balance"] += float(profit)
        return deal

    def close_position(self, position_id: int, price: float = 0.0) -> bool:
        """Close a position manually."""
        position = self._find_position(position_id)
        if position is None:
            return self._set_error("Position not found.")

        close_price = price if price > 0 else position["price"]
        self._close_position(position, close_price, "Manual")
        self._recalculate_account()
        return True

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------
    def _find_position(self, position_id: int) -> Optional[dict[str, Any]]:
        for position in self.positions_container:
            if position["id"] == position_id:
                return position
        return None

    def _calc_margin(
        self, symbol: str, action: str, volume: float, price: float
    ) -> float:
        order_type = (
            mt5.ORDER_TYPE_BUY if action.lower() == "buy" else mt5.ORDER_TYPE_SELL
        )
        if hasattr(mt5, "order_calc_margin"):
            result = mt5.order_calc_margin(order_type, symbol, volume, price)
            if result is not None:
                return float(result)

        snapshot = self._symbol_snapshot(symbol)
        notional = snapshot.contract_size * volume * price
        leverage = self._leverage if self._leverage > 0 else 1.0
        return float(notional / leverage)

    def _ensure_margin(self, margin_required: float) -> bool:
        if margin_required <= 0:
            return True
        if margin_required > float(self.account_info.get("free_margin", 0.0)):
            return self._set_error("Not enough free margin to open the position.")
        return True

    def _record_deal(
        self, position: dict[str, Any], direction: str, reason: str
    ) -> None:
        deal = self.deal_info.copy()
        deal.update(
            {
                "id": position["id"],
                "magic": position.get("magic", 0),
                "symbol": position["symbol"],
                "type": position["type"],
                "direction": direction,
                "volume": position["volume"],
                "price": position.get("price", position.get("open_price", 0.0)),
                "spread": position.get("spread", 0.0),
                "sl": position.get("sl", 0.0),
                "tp": position.get("tp", 0.0),
                "commission": position.get("commission", 0.0),
                "margin_required": position.get("margin_required", 0.0),
                "fee": position.get("fee", 0.0),
                "swap": position.get("swap", 0.0),
                "profit": position.get("profit", 0.0),
                "comment": position.get("comment", ""),
                "time": position.get("time", self._now()),
                "reason": reason,
                "entry_reason": position.get("entry_reason", ""),
                "session_id": position.get("session_id"),
            }
        )
        self.deals_container.append(deal)
        self._save_deal(deal)

    def _recalculate_account(self) -> None:
        floating_profit = sum(
            pos.get("profit", 0.0) for pos in self.positions_container
        )
        margin_used = sum(pos.get("margin", 0.0) for pos in self.positions_container)
        balance = float(self.account_info["balance"])
        equity = balance + float(floating_profit)
        free_margin = equity - float(margin_used)
        margin_level = (equity / margin_used * 100.0) if margin_used > 0 else 0.0

        self.account_info.update(
            {
                "equity": equity,
                "profit": float(floating_profit),
                "margin": float(margin_used),
                "free_margin": float(free_margin),
                "margin_level": float(margin_level),
            }
        )
