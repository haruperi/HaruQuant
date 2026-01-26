"""
Trade simulator module (MT5-aligned, local execution).

Implements a lightweight trade simulator inspired by MQL5 practices while
remaining independent of live trading. Uses apps.ctrade for symbol/account
property access when MT5 is available.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

import MetaTrader5 as mt5

from apps.ctrade import CSymbolInfo
from apps.logger import logger
from apps.simulator.market_data import MarketDataStore, ensure_utc, timeframe_seconds
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


@dataclass(frozen=True)
class AccountInfo:
    """Account information snapshot aligned with MT5 AccountInfo fields."""

    login: int
    trade_mode: int
    leverage: int
    limit_orders: int
    margin_so_mode: int
    trade_allowed: bool
    trade_expert: bool
    margin_mode: int
    currency_digits: int
    fifo_close: bool
    balance: float
    credit: float
    profit: float
    equity: float
    margin: float
    margin_free: float
    margin_level: float
    margin_so_call: float
    margin_so_so: float
    margin_initial: float
    margin_maintenance: float
    assets: float
    liabilities: float
    commission_blocked: float
    name: str
    server: str
    currency: str
    company: str


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
        data_store: Optional[MarketDataStore] = None,
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
        self._data_store = data_store or MarketDataStore()
        self._toolbox_callback = toolbox_callback

        # Initialize variables
        self._next_id = 1
        self._is_running = False
        self._is_tester = False
        self._symbol_info_cache: dict[str, dict[str, Any]] = {}
        self._tick_cache: dict[str, dict[str, Any]] = {}
        self.magic_number: Optional[int] = None
        self.deviation_points: Optional[int] = None
        self.filling_type: Optional[int] = None
        self.last_error: str = ""

        # Account's information (simulated, aligned with MT5)
        mt5_acc_info = mt5.account_info()
        leverage_value = int(self._leverage)
        self._account_state: dict[str, Any] = {
            # ---- identity / broker-controlled ----
            "login": 11223344,
            "trade_mode": int(getattr(mt5_acc_info, "trade_mode", 0)),
            "leverage": leverage_value,
            "limit_orders": int(getattr(mt5_acc_info, "limit_orders", 0)),
            "margin_so_mode": int(getattr(mt5_acc_info, "margin_so_mode", 0)),
            "trade_allowed": bool(getattr(mt5_acc_info, "trade_allowed", True)),
            "trade_expert": bool(getattr(mt5_acc_info, "trade_expert", True)),
            "margin_mode": int(getattr(mt5_acc_info, "margin_mode", 0)),
            "currency_digits": int(getattr(mt5_acc_info, "currency_digits", 2)),
            "fifo_close": bool(getattr(mt5_acc_info, "fifo_close", False)),
            # ---- simulator-controlled financials ----
            "balance": float(deposit),
            "credit": float(getattr(mt5_acc_info, "credit", 0.0)),
            "profit": 0.0,
            "equity": float(deposit),
            "margin": 0.0,
            "margin_free": float(deposit),
            "margin_level": 0.0,
            # ---- risk thresholds (copied from broker) ----
            "margin_so_call": float(getattr(mt5_acc_info, "margin_so_call", 0.0)),
            "margin_so_so": float(getattr(mt5_acc_info, "margin_so_so", 0.0)),
            "margin_initial": float(getattr(mt5_acc_info, "margin_initial", 0.0)),
            "margin_maintenance": float(
                getattr(mt5_acc_info, "margin_maintenance", 0.0)
            ),
            # ---- rarely used but keep parity ----
            "assets": float(getattr(mt5_acc_info, "assets", 0.0)),
            "liabilities": float(getattr(mt5_acc_info, "liabilities", 0.0)),
            "commission_blocked": float(
                getattr(mt5_acc_info, "commission_blocked", 0.0)
            ),
            # ---- descriptive ----
            "name": "John Doe",
            "server": "MetaTrader5-Simulator",
            "currency": str(getattr(mt5_acc_info, "currency", "USD")),
            "company": str(getattr(mt5_acc_info, "company", "")),
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

        # Request tracking (MT5-like)
        self._last_request: dict[str, Any] = {}
        self._last_result: dict[str, Any] = {}
        self._last_check: dict[str, Any] = {}

        # Orders history (simulator-only)
        self.orders_history_container: list[dict[str, Any]] = []

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

    def start(self, is_tester: bool = True) -> bool:
        """Start the simulator in tester mode or live passthrough mode."""
        self._is_running = True
        self._is_tester = bool(is_tester)
        return True

    def stop(self) -> None:
        """Stop the simulator."""
        self._is_running = False

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
                self._account_state, self.positions_container, self.orders_container
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
        cached_info = self.symbol_info(symbol) if self._is_tester else None
        bid, ask = self._resolve_bid_ask(symbol, price_feed, info)

        def _cached_float(key: str, default: float) -> float:
            if cached_info and key in cached_info and cached_info[key] is not None:
                return float(cached_info[key])
            return default

        def _cached_int(key: str, default: int) -> int:
            if cached_info and key in cached_info and cached_info[key] is not None:
                return int(cached_info[key])
            return default

        return SymbolSnapshot(
            symbol=symbol,
            digits=_cached_int("digits", int(info.Digits())),
            point=_cached_float("point", float(info.Point())),
            tick_value=_cached_float("trade_tick_value", float(info.TickValue())),
            tick_size=_cached_float("trade_tick_size", float(info.TickSize())),
            contract_size=_cached_float(
                "trade_contract_size", float(info.ContractSize())
            ),
            volume_min=_cached_float("volume_min", float(info.LotsMin())),
            volume_max=_cached_float("volume_max", float(info.LotsMax())),
            volume_step=_cached_float("volume_step", float(info.LotsStep())),
            stops_level=_cached_int("trade_stops_level", int(info.StopsLevel())),
            freeze_level=_cached_int("trade_freeze_level", int(info.FreezeLevel())),
            bid=bid,
            ask=ask,
        )

    def _resolve_bid_ask(
        self,
        symbol: str,
        price_feed: Optional[dict[str, Any]],
        info: CSymbolInfo,
    ) -> tuple[float, float]:
        if self._is_tester and symbol in self._tick_cache:
            cached = self._tick_cache[symbol]
            return float(cached.get("bid", 0.0)), float(cached.get("ask", 0.0))
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
    # Tester mode data handling (ticks, bars, and MT5 overloads)
    # ------------------------------------------------------------------
    def update_tick(self, symbol: str, tick: Any) -> None:
        """Update cached tick data for tester mode."""
        if tick is None:
            return
        if hasattr(tick, "_asdict"):
            tick_data = tick._asdict()
        elif isinstance(tick, dict):
            tick_data = dict(tick)
        else:
            return
        self._tick_cache[symbol] = tick_data

    def symbol_info_tick(self, symbol: str) -> Optional[dict[str, Any]]:
        """Return tick info, using tester cache when enabled."""
        if self._is_tester:
            return self._tick_cache.get(symbol)
        info = mt5.symbol_info_tick(symbol)
        return info._asdict() if info is not None else None

    def symbol_info(self, symbol: str) -> Optional[dict[str, Any]]:
        """Return symbol info, using cached data in tester mode."""
        if self._is_tester and symbol in self._symbol_info_cache:
            return dict(self._symbol_info_cache[symbol])
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        data = info._asdict()
        if self._is_tester:
            self._symbol_info_cache[symbol] = dict(data)
        return dict(data)

    def order_send(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a trade request using simulator logic when in tester mode."""
        self._last_request = dict(request)
        if not self._is_tester:
            result = mt5.order_send(request)
            self._last_result = result._asdict() if result is not None else {}
            self._last_check = {}
            return dict(self._last_result)

        check = self._check_request(request)
        self._last_check = dict(check)
        if check.get("retcode") != mt5.TRADE_RETCODE_DONE:
            self._last_result = {
                "retcode": check.get("retcode", mt5.TRADE_RETCODE_REJECT),
                "comment": check.get("comment", ""),
            }
            return dict(self._last_result)

        result = self._execute_request(request)
        self._last_result = dict(result)
        return dict(self._last_result)

    def _check_request(self, request: dict[str, Any]) -> dict[str, Any]:
        action = int(request.get("action", 0))
        if action == mt5.TRADE_ACTION_MODIFY:
            return self._check_modify_request(request)
        if action == mt5.TRADE_ACTION_REMOVE:
            return self._check_remove_request(request)

        symbol = str(request.get("symbol", ""))
        snapshot = self._symbol_snapshot(symbol) if symbol else None
        if snapshot is None or not symbol:
            return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": "Symbol required."}

        if self._reached_max_orders():
            return {
                "retcode": mt5.TRADE_RETCODE_REJECT,
                "comment": "Maximum number of orders reached.",
            }

        volume, price, sl, tp = self._request_prices(request)
        if action == mt5.TRADE_ACTION_DEAL:
            return self._check_deal_request(
                request, snapshot, symbol, volume, price, sl, tp
            )
        if action == mt5.TRADE_ACTION_PENDING:
            return self._check_pending_request(
                request, snapshot, symbol, volume, price, sl, tp
            )
        return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": "Unsupported action."}

    def _request_prices(
        self, request: dict[str, Any]
    ) -> tuple[float, float, float, float]:
        volume = float(request.get("volume", 0.0))
        price = float(request.get("price", 0.0))
        sl = float(request.get("sl", 0.0))
        tp = float(request.get("tp", 0.0))
        return volume, price, sl, tp

    def _check_deal_request(
        self,
        request: dict[str, Any],
        snapshot: SymbolSnapshot,
        symbol: str,
        volume: float,
        price: float,
        sl: float,
        tp: float,
    ) -> dict[str, Any]:
        order_type = int(request.get("type", mt5.ORDER_TYPE_BUY))
        action_name = "buy" if order_type == mt5.ORDER_TYPE_BUY else "sell"
        if not self._validate_trade(
            action_name, snapshot, volume, price or snapshot.ask, sl, tp
        ):
            return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": self.last_error}
        if not self._validate_volume_limit(symbol, volume):
            return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": self.last_error}
        margin_required = self._calc_margin_sim(
            action_name, symbol, volume, price or snapshot.ask
        )
        if not self._ensure_margin(margin_required):
            return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": self.last_error}
        return {"retcode": mt5.TRADE_RETCODE_DONE, "comment": "OK"}

    def _check_pending_request(
        self,
        request: dict[str, Any],
        snapshot: SymbolSnapshot,
        symbol: str,
        volume: float,
        price: float,
        sl: float,
        tp: float,
    ) -> dict[str, Any]:
        order_type = int(request.get("type", mt5.ORDER_TYPE_BUY_LIMIT))
        order_name = self._pending_order_type(order_type)
        if not order_name:
            return {
                "retcode": mt5.TRADE_RETCODE_REJECT,
                "comment": "Unsupported pending order type.",
            }
        expiration = self._expiration_to_datetime(request.get("expiration"))
        if not self._validate_pending_order(
            order_name, snapshot, volume, price, sl, tp, expiration
        ):
            return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": self.last_error}
        if not self._validate_volume_limit(symbol, volume):
            return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": self.last_error}
        return {"retcode": mt5.TRADE_RETCODE_DONE, "comment": "OK"}

    def _check_modify_request(self, request: dict[str, Any]) -> dict[str, Any]:
        order_id = request.get("order")
        position_id = request.get("position")
        if order_id is None and position_id is None:
            return {
                "retcode": mt5.TRADE_RETCODE_REJECT,
                "comment": "Missing order/position id.",
            }
        return {"retcode": mt5.TRADE_RETCODE_DONE, "comment": "OK"}

    def _check_remove_request(self, request: dict[str, Any]) -> dict[str, Any]:
        order_id = request.get("order")
        if order_id is None:
            return {
                "retcode": mt5.TRADE_RETCODE_REJECT,
                "comment": "Missing order id.",
            }
        return {"retcode": mt5.TRADE_RETCODE_DONE, "comment": "OK"}

    def _execute_request(self, request: dict[str, Any]) -> dict[str, Any]:
        action = int(request.get("action", 0))
        symbol = str(request.get("symbol", ""))
        volume, price, sl, tp = self._request_prices(request)
        comment = str(request.get("comment", ""))

        handlers = {
            mt5.TRADE_ACTION_DEAL: lambda: self._execute_deal_request(
                request, symbol, volume, price, sl, tp, comment
            ),
            mt5.TRADE_ACTION_PENDING: lambda: self._execute_pending_request(
                request, symbol, volume, price, sl, tp, comment
            ),
            mt5.TRADE_ACTION_MODIFY: lambda: self._execute_modify_request(
                request, price, sl, tp
            ),
            mt5.TRADE_ACTION_REMOVE: lambda: self._execute_remove_request(request),
        }
        handler = handlers.get(action)
        if handler is None:
            return {
                "retcode": mt5.TRADE_RETCODE_REJECT,
                "comment": "Unsupported action.",
            }
        return handler()

    def _execute_deal_request(
        self,
        request: dict[str, Any],
        symbol: str,
        volume: float,
        price: float,
        sl: float,
        tp: float,
        comment: str,
    ) -> dict[str, Any]:
        position_id = request.get("position")
        if position_id is not None:
            return self._execute_close_position(int(position_id))
        order_type = int(request.get("type", mt5.ORDER_TYPE_BUY))
        action_name = "buy" if order_type == mt5.ORDER_TYPE_BUY else "sell"
        return self._execute_open_position(
            action_name, symbol, volume, price, sl, tp, comment, request
        )

    def _execute_close_position(self, position_id: int) -> dict[str, Any]:
        if self._close_position_by_id(position_id):
            logger.info(
                f"{self.simulator_name}.tester | [tester.py:1251 - order_send() ] "
                f"=> Position: {position_id} closed!"
            )
            return {"retcode": mt5.TRADE_RETCODE_DONE, "order": position_id}
        return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": self.last_error}

    def _execute_open_position(
        self,
        action_name: str,
        symbol: str,
        volume: float,
        price: float,
        sl: float,
        tp: float,
        comment: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        position = self._open_position(
            action_name, symbol, volume, price, sl, tp, comment
        )
        if position is None:
            return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": self.last_error}
        magic = int(request.get("magic", position.get("magic", 0)))
        position["magic"] = magic
        logger.info(
            f"{self.simulator_name}.tester | [tester.py:1335 - order_send() ] "
            f"=> Position: {int(position['id'])} opened!"
        )
        return {
            "retcode": mt5.TRADE_RETCODE_DONE,
            "order": int(position["id"]),
            "deal": int(position["id"]),
            "comment": "OK",
        }

    def _execute_pending_request(
        self,
        request: dict[str, Any],
        symbol: str,
        volume: float,
        price: float,
        sl: float,
        tp: float,
        comment: str,
    ) -> dict[str, Any]:
        order_type = int(request.get("type", mt5.ORDER_TYPE_BUY_LIMIT))
        order_name = self._pending_order_type(order_type)
        if not order_name:
            return {
                "retcode": mt5.TRADE_RETCODE_REJECT,
                "comment": "Unsupported pending order type.",
            }
        order = self._place_pending_order(
            order_name,
            volume,
            symbol,
            price,
            sl,
            tp,
            comment,
            expiry_date=self._expiration_to_datetime(request.get("expiration")),
        )
        if order is None:
            return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": self.last_error}
        order["magic"] = int(request.get("magic", order.get("magic", 0)))
        self.orders_history_container.append(dict(order))
        return {
            "retcode": mt5.TRADE_RETCODE_DONE,
            "order": int(order["id"]),
            "comment": "OK",
        }

    def _execute_modify_request(
        self, request: dict[str, Any], price: float, sl: float, tp: float
    ) -> dict[str, Any]:
        order_id = request.get("order")
        if order_id is not None:
            return self._execute_modify_order(order_id, price, sl, tp, request)
        position_id = request.get("position")
        if position_id is not None:
            return self._execute_modify_position(position_id, sl, tp)
        return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": "Missing id."}

    def _execute_modify_order(
        self,
        order_id: int,
        price: float,
        sl: float,
        tp: float,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        if self._modify_order(
            int(order_id),
            open_price=price,
            sl=sl,
            tp=tp,
            expiry_date=self._expiration_to_datetime(request.get("expiration")),
            expiration_mode=request.get("type_time"),
        ):
            return {"retcode": mt5.TRADE_RETCODE_DONE, "order": int(order_id)}
        return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": self.last_error}

    def _execute_modify_position(
        self, position_id: int, sl: float, tp: float
    ) -> dict[str, Any]:
        if self._modify_position(int(position_id), sl=sl, tp=tp):
            return {"retcode": mt5.TRADE_RETCODE_DONE, "position": int(position_id)}
        return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": self.last_error}

    def _execute_remove_request(self, request: dict[str, Any]) -> dict[str, Any]:
        order_id = request.get("order")
        if order_id is not None and self._delete_order(int(order_id)):
            return {"retcode": mt5.TRADE_RETCODE_DONE, "order": int(order_id)}
        return {"retcode": mt5.TRADE_RETCODE_REJECT, "comment": self.last_error}

    def _pending_order_type(self, order_type: int) -> str:
        mapping = {
            mt5.ORDER_TYPE_BUY_LIMIT: "buy limit",
            mt5.ORDER_TYPE_BUY_STOP: "buy stop",
            mt5.ORDER_TYPE_SELL_LIMIT: "sell limit",
            mt5.ORDER_TYPE_SELL_STOP: "sell stop",
        }
        return mapping.get(order_type, "")

    def _expiration_to_datetime(self, expiration: Any) -> Optional[datetime]:
        if expiration is None:
            return None
        if isinstance(expiration, datetime):
            return expiration
        try:
            return datetime.fromtimestamp(int(expiration), tz=timezone.utc)
        except (TypeError, ValueError):
            return None

    def order_calc_profit(
        self,
        action: int,
        symbol: str,
        volume: float,
        price_open: float,
        price_close: float,
    ) -> float:
        """Calculate profit using simulator logic when in tester mode."""
        price_close = self._resolve_profit_close(action, symbol, price_close)
        if self._is_tester:
            return self._order_calc_profit_tester(
                action, symbol, volume, price_open, price_close
            )
        result = mt5.order_calc_profit(action, symbol, volume, price_open, price_close)
        return float(result) if result is not None else 0.0

    def _order_calc_profit_tester(
        self,
        action: int,
        symbol: str,
        volume: float,
        price_open: float,
        price_close: float,
    ) -> float:
        info = self.symbol_info(symbol) or {}
        contract_size = float(info.get("trade_contract_size", 0.0))
        calc_mode = int(info.get("trade_calc_mode", 0))

        direction = self._order_direction(action)
        if direction == 0:
            return 0.0

        price_delta = (price_close - price_open) * direction
        profit = 0.0

        if calc_mode in (
            mt5.SYMBOL_CALC_MODE_FOREX,
            mt5.SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE,
            mt5.SYMBOL_CALC_MODE_CFD,
            mt5.SYMBOL_CALC_MODE_CFDINDEX,
            mt5.SYMBOL_CALC_MODE_CFDLEVERAGE,
            mt5.SYMBOL_CALC_MODE_EXCH_STOCKS,
            mt5.SYMBOL_CALC_MODE_EXCH_STOCKS_MOEX,
        ):
            profit = price_delta * contract_size * volume
        elif calc_mode in (
            mt5.SYMBOL_CALC_MODE_FUTURES,
            mt5.SYMBOL_CALC_MODE_EXCH_FUTURES,
            mt5.SYMBOL_CALC_MODE_EXCH_FUTURES_FORTS,
        ):
            tick_value = float(info.get("trade_tick_value", 0.0))
            tick_size = float(info.get("trade_tick_size", 0.0))
            if tick_size <= 0:
                return 0.0
            profit = price_delta * volume * (tick_value / tick_size)
        elif calc_mode in (
            mt5.SYMBOL_CALC_MODE_EXCH_BONDS,
            mt5.SYMBOL_CALC_MODE_EXCH_BONDS_MOEX,
        ):
            face_value = float(info.get("trade_face_value", 0.0))
            accrued_interest = float(info.get("trade_accrued_interest", 0.0))
            profit = volume * contract_size * (
                price_close * face_value + accrued_interest
            ) - volume * contract_size * (price_open * face_value)
        elif calc_mode == mt5.SYMBOL_CALC_MODE_SERV_COLLATERAL:
            liquidity_rate = float(info.get("trade_liquidity_rate", 0.0))
            tick = self.symbol_info_tick(symbol) or {}
            market_price = tick.get("ask") if direction > 0 else tick.get("bid")
            if not market_price:
                market_price = price_close
            market_price = float(market_price)
            profit = volume * contract_size * market_price * liquidity_rate
        else:
            profit = price_delta * contract_size * volume

        return round(float(profit), 2)

    def _resolve_profit_close(
        self, action: int, symbol: str, price_close: float
    ) -> float:
        if price_close > 0:
            return price_close
        tick = self.symbol_info_tick(symbol) or {}
        if action in (mt5.ORDER_TYPE_BUY, mt5.POSITION_TYPE_BUY):
            return float(tick.get("bid", 0.0))
        return float(tick.get("ask", 0.0))

    def _order_direction(self, order_type: int) -> int:
        if order_type in (mt5.ORDER_TYPE_BUY, mt5.POSITION_TYPE_BUY):
            return 1
        if order_type in (mt5.ORDER_TYPE_SELL, mt5.POSITION_TYPE_SELL):
            return -1
        return 0

    def order_calc_margin(
        self,
        action: int,
        symbol: str,
        volume: float,
        price_open: float,
    ) -> float:
        """Calculate margin using simulator logic when in tester mode."""
        if volume <= 0 or price_open <= 0:
            return 0.0
        price_open = self._resolve_profit_close(action, symbol, price_open)
        if self._is_tester:
            return self._order_calc_margin_tester(action, symbol, volume, price_open)
        result = mt5.order_calc_margin(action, symbol, volume, price_open)
        return float(result) if result is not None else 0.0

    def _order_calc_margin_tester(
        self,
        action: int,
        symbol: str,
        volume: float,
        price_open: float,
    ) -> float:
        info = self.symbol_info(symbol) or {}
        return self._margin_from_info(info, volume, price_open)

    def _margin_from_info(
        self, info: dict[str, Any], volume: float, price_open: float
    ) -> float:
        contract_size = float(info.get("trade_contract_size", 0.0))
        leverage = max(int(self._account_state.get("leverage", 1)), 1)
        calc_mode = int(info.get("trade_calc_mode", 0))
        margin_rate = self._resolve_margin_rate(info, calc_mode)
        margin = self._margin_by_mode(
            calc_mode,
            volume,
            contract_size,
            price_open,
            leverage,
            margin_rate,
            info,
        )
        return round(float(margin), 2)

    def _resolve_margin_rate(self, info: dict[str, Any], calc_mode: int) -> float:
        margin_rate = float(info.get("margin_initial", 0.0))
        if margin_rate <= 0:
            margin_rate = float(info.get("margin_maintenance", 0.0))
        if margin_rate <= 0:
            margin_rate = 1.0
        if calc_mode in (
            mt5.SYMBOL_CALC_MODE_FOREX,
            mt5.SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE,
        ):
            return min(margin_rate, 1.0)
        return margin_rate

    def _margin_by_mode(
        self,
        calc_mode: int,
        volume: float,
        contract_size: float,
        price_open: float,
        leverage: int,
        margin_rate: float,
        info: dict[str, Any],
    ) -> float:
        if calc_mode == mt5.SYMBOL_CALC_MODE_FOREX:
            return (volume * contract_size * margin_rate) / leverage
        if calc_mode == mt5.SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE:
            return volume * contract_size * margin_rate
        if calc_mode in (
            mt5.SYMBOL_CALC_MODE_CFD,
            mt5.SYMBOL_CALC_MODE_CFDINDEX,
            mt5.SYMBOL_CALC_MODE_EXCH_STOCKS,
            mt5.SYMBOL_CALC_MODE_EXCH_STOCKS_MOEX,
        ):
            return volume * contract_size * price_open * margin_rate
        if calc_mode == mt5.SYMBOL_CALC_MODE_CFDLEVERAGE:
            return (volume * contract_size * price_open * margin_rate) / leverage
        if calc_mode in (
            mt5.SYMBOL_CALC_MODE_FUTURES,
            mt5.SYMBOL_CALC_MODE_EXCH_FUTURES,
            mt5.SYMBOL_CALC_MODE_EXCH_FUTURES_FORTS,
        ):
            return self._futures_margin(volume, margin_rate, info)
        if calc_mode in (
            mt5.SYMBOL_CALC_MODE_EXCH_BONDS,
            mt5.SYMBOL_CALC_MODE_EXCH_BONDS_MOEX,
        ):
            face_value = float(info.get("trade_face_value", 0.0))
            return volume * contract_size * face_value * price_open / 100.0
        if calc_mode == mt5.SYMBOL_CALC_MODE_SERV_COLLATERAL:
            return 0.0
        return (volume * contract_size * price_open) / leverage

    def _futures_margin(
        self, volume: float, margin_rate: float, info: dict[str, Any]
    ) -> float:
        initial_margin = float(info.get("margin_initial", 0.0))
        maintenance_margin = float(info.get("margin_maintenance", 0.0))
        base_margin = initial_margin if initial_margin > 0 else maintenance_margin
        return volume * base_margin * margin_rate

    def copy_rates_from_pos(
        self, symbol: str, timeframe: int, start_pos: int, count: int
    ) -> list[dict[str, Any]]:
        """Copy bars from the current tester time position."""
        if not self._is_tester:
            rates = mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)
            return self._rates_to_dicts(rates)
        tick = self._tick_cache.get(symbol)
        if not tick:
            return []
        tf_seconds = timeframe_seconds(timeframe)
        if tf_seconds <= 0:
            return []
        current_time = datetime.fromtimestamp(int(tick["time"]), tz=timezone.utc)
        start_time = current_time - (count + start_pos + 1) * timedelta(
            seconds=tf_seconds
        )
        bars = self._data_store.read_bars_range(
            symbol, timeframe, start_time, current_time
        )
        bars_sorted = sorted(bars, key=lambda row: row.get("time", 0), reverse=True)
        sliced = bars_sorted[start_pos : start_pos + count]
        return list(sliced)

    def copy_rates_from(
        self, symbol: str, timeframe: int, date_from: datetime, count: int
    ) -> list[dict[str, Any]]:
        """Copy bars starting from date_from."""
        if not self._is_tester:
            rates = mt5.copy_rates_from(symbol, timeframe, date_from, count)
            return self._rates_to_dicts(rates)
        tf_seconds = timeframe_seconds(timeframe)
        if tf_seconds <= 0:
            return []
        start_time = ensure_utc(date_from)
        end_time = start_time + timedelta(seconds=tf_seconds * count)
        bars = self._data_store.read_bars_range(symbol, timeframe, start_time, end_time)
        return list(sorted(bars, key=lambda row: row.get("time", 0))[:count])

    def copy_rates_range(
        self, symbol: str, timeframe: int, date_from: datetime, date_to: datetime
    ) -> list[dict[str, Any]]:
        """Copy bars within a date range."""
        if not self._is_tester:
            rates = mt5.copy_rates_range(symbol, timeframe, date_from, date_to)
            return self._rates_to_dicts(rates)
        return self._data_store.read_bars_range(symbol, timeframe, date_from, date_to)

    def copy_ticks_from(
        self, symbol: str, date_from: datetime, count: int, flags: int
    ) -> list[dict[str, Any]]:
        """Copy ticks starting from date_from."""
        if not self._is_tester:
            ticks = mt5.copy_ticks_from(symbol, date_from, count, flags)
            return self._rates_to_dicts(ticks)
        ticks = self._data_store.read_ticks_range(symbol, date_from, self._now())
        filtered = self._filter_ticks_by_flags(ticks, flags)
        return filtered[:count]

    def copy_ticks_range(
        self, symbol: str, date_from: datetime, date_to: datetime, flags: int
    ) -> list[dict[str, Any]]:
        """Copy ticks within a date range."""
        if not self._is_tester:
            ticks = mt5.copy_ticks_range(symbol, date_from, date_to, flags)
            return self._rates_to_dicts(ticks)
        ticks = self._data_store.read_ticks_range(symbol, date_from, date_to)
        return self._filter_ticks_by_flags(ticks, flags)

    def positions_total(self) -> int:
        """Return the total number of open positions."""
        if self._is_tester:
            return len(self.positions_container)
        return int(mt5.positions_total())

    def positions_get(self) -> Any:
        """Return open positions (simulator or MT5)."""
        if self._is_tester:
            return list(self.positions_container)
        return mt5.positions_get()

    def positions_profit_total(self) -> float:
        """Return total floating profit for open positions."""
        if self._is_tester:
            return float(
                sum(pos.get("profit", 0.0) for pos in self.positions_container)
            )
        total = 0.0
        positions = mt5.positions_get()
        if positions:
            total = float(sum(pos.profit for pos in positions))
        return total

    def positions_margin_total(self) -> float:
        """Return total margin used by open positions."""
        if self._is_tester:
            return float(
                sum(pos.get("margin_required", 0.0) for pos in self.positions_container)
            )
        total = 0.0
        positions = mt5.positions_get()
        if positions:
            total = float(
                sum(
                    self.order_calc_margin(
                        action=pos.type,
                        symbol=pos.symbol,
                        volume=float(pos.volume),
                        price_open=float(pos.price_open),
                    )
                    for pos in positions
                )
            )
        return total

    def orders_total(self) -> int:
        """Return the total number of open orders."""
        if self._is_tester:
            return len(self.orders_container)
        return int(mt5.orders_total())

    def orders_get(self) -> Any:
        """Return open orders (simulator or MT5)."""
        if self._is_tester:
            return list(self.orders_container)
        return mt5.orders_get()

    def history_deals_total(
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> int:
        """Return the number of historical deals in the date range."""
        if self._is_tester:
            return len(self._filter_deals(date_from, date_to))
        return len(self._history_deals_live(date_from, date_to))

    def history_deals_get(
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> Any:
        """Return historical deals in the date range."""
        if self._is_tester:
            return list(self._filter_deals(date_from, date_to))
        return self._history_deals_live(date_from, date_to)

    def history_orders_total(
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> int:
        """Return the number of historical orders in the date range."""
        if self._is_tester:
            return 0
        return len(self._history_orders_live(date_from, date_to))

    def history_orders_get(
        self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None
    ) -> Any:
        """Return historical orders in the date range."""
        if self._is_tester:
            return []
        return self._history_orders_live(date_from, date_to)

    def _history_orders_live(
        self, date_from: Optional[datetime], date_to: Optional[datetime]
    ) -> Any:
        if date_from is not None and date_to is not None:
            return mt5.history_orders_get(date_from, date_to)
        return mt5.history_orders_get()

    def _history_deals_live(
        self, date_from: Optional[datetime], date_to: Optional[datetime]
    ) -> Any:
        if date_from is not None and date_to is not None:
            return mt5.history_deals_get(date_from, date_to)
        return mt5.history_deals_get()

    def _filter_deals(
        self, date_from: Optional[datetime], date_to: Optional[datetime]
    ) -> list[dict[str, Any]]:
        if date_from is None or date_to is None:
            return list(self.deals_container)
        start = date_from
        end = date_to
        if start > end:
            start, end = end, start
        return [
            deal
            for deal in self.deals_container
            if isinstance(deal.get("time"), datetime) and start <= deal["time"] <= end
        ]

    def account_info(self) -> AccountInfo:
        """Return account info snapshot (tester uses simulator account)."""
        if self._is_tester:
            return self._build_account_info(self._account_state)
        info = mt5.account_info()
        if info is None:
            return self._build_account_info(self._account_state)
        return self._build_account_info(info._asdict())

    def get_account_info(self) -> AccountInfo:
        """Backward-compatible wrapper for account_info()."""
        return self.account_info()

    def _build_account_info(self, data: dict[str, Any]) -> AccountInfo:
        return AccountInfo(
            login=int(data.get("login", 0)),
            trade_mode=int(data.get("trade_mode", 0)),
            leverage=int(data.get("leverage", int(self._leverage))),
            limit_orders=int(data.get("limit_orders", 0)),
            margin_so_mode=int(data.get("margin_so_mode", 0)),
            trade_allowed=bool(data.get("trade_allowed", True)),
            trade_expert=bool(data.get("trade_expert", True)),
            margin_mode=int(data.get("margin_mode", 0)),
            currency_digits=int(data.get("currency_digits", 2)),
            fifo_close=bool(data.get("fifo_close", False)),
            balance=float(data.get("balance", 0.0)),
            credit=float(data.get("credit", 0.0)),
            profit=float(data.get("profit", 0.0)),
            equity=float(data.get("equity", 0.0)),
            margin=float(data.get("margin", 0.0)),
            margin_free=float(data.get("margin_free", 0.0)),
            margin_level=float(data.get("margin_level", 0.0)),
            margin_so_call=float(data.get("margin_so_call", 0.0)),
            margin_so_so=float(data.get("margin_so_so", 0.0)),
            margin_initial=float(data.get("margin_initial", 0.0)),
            margin_maintenance=float(data.get("margin_maintenance", 0.0)),
            assets=float(data.get("assets", 0.0)),
            liabilities=float(data.get("liabilities", 0.0)),
            commission_blocked=float(data.get("commission_blocked", 0.0)),
            name=str(data.get("name", "")),
            server=str(data.get("server", "")),
            currency=str(data.get("currency", "")),
            company=str(data.get("company", "")),
        )

    def _rates_to_dicts(self, rates: Any) -> list[dict[str, Any]]:
        if rates is None:
            return []
        if isinstance(rates, list):
            return [dict(row) if isinstance(row, dict) else dict(row) for row in rates]
        if getattr(rates, "dtype", None) is None or rates.dtype.names is None:
            return []
        return [
            {
                name: r[name].item() if hasattr(r[name], "item") else r[name]
                for name in rates.dtype.names
            }
            for r in rates
        ]

    def _filter_ticks_by_flags(
        self, ticks: list[dict[str, Any]], flags: int
    ) -> list[dict[str, Any]]:
        if flags is None or flags == getattr(mt5, "COPY_TICKS_ALL", flags):
            return ticks
        mask = int(flags)
        filtered = []
        for tick in ticks:
            tick_flags = tick.get("flags")
            if tick_flags is None:
                filtered.append(tick)
                continue
            if int(tick_flags) & mask:
                filtered.append(tick)
        return filtered

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
    def _open_position(
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

        margin_required = self._calc_margin_sim(action, symbol, volume, open_price)
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

    def _buy(
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
        return self._open_position(
            "buy", symbol, volume, price, sl, tp, comment, price_feed
        )

    def _sell(
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
        return self._open_position(
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

    def _validate_volume_limit(self, symbol: str, volume: float) -> bool:
        info = self.symbol_info(symbol) or {}
        volume_limit = float(info.get("volume_limit", 0.0))
        if volume_limit <= 0:
            return True
        current_volume = 0.0
        for pos in self.positions_container:
            if pos.get("symbol") == symbol:
                current_volume += float(pos.get("volume", 0.0))
        for order in self.orders_container:
            if order.get("symbol") == symbol:
                current_volume += float(order.get("volume", 0.0))
        if current_volume + volume > volume_limit:
            return self._set_error("Volume limit exceeded for symbol.")
        return True

    def _reached_max_orders(self) -> bool:
        limit = int(self._account_state.get("limit_orders", 0))
        if limit <= 0:
            return False
        return len(self.orders_container) >= limit

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
    def _modify_position(
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

    def _buy_stop(
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

    def _buy_limit(
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

    def _sell_stop(
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

    def _sell_limit(
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
    def _delete_order(self, order_id: int) -> bool:
        """Delete a pending order by id."""
        for order in list(self.orders_container):
            if order["id"] == order_id:
                self.orders_container.remove(order)
                return True
        return self._set_error("Order not found.")

    # ------------------------------------------------------------------
    # Modifying Pending Orders
    # ------------------------------------------------------------------
    def _modify_order(
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
            self._buy(
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
            self._sell(
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
                    self._account_state["balance"],
                    self._account_state["equity"],
                    self._account_state["profit"],
                    self._account_state["margin"],
                    self._account_state["margin_free"],
                    self._account_state["margin_level"],
                )
            )
        return dict(self._account_state)

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
                "entry": "out",
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
                "balance": self._account_state.get("balance", 0.0) + float(profit),
            }
        )
        self.deals_container.append(deal)
        self._save_deal(deal)
        self.positions_container.remove(position)
        self._account_state["balance"] += float(profit)
        return deal

    def _close_position_by_id(self, position_id: int, price: float = 0.0) -> bool:
        """Close a position manually."""
        position = self._find_position(position_id)
        if position is None:
            return self._set_error("Position not found.")

        close_price = price if price > 0 else position["price"]
        self._close_position(position, close_price, "Manual")
        self._recalculate_account()
        return True

    def close_position(self, position_id: int, price: float = 0.0) -> bool:
        """Use CTrade(api=sim) to manage positions (deprecated)."""
        return self._close_position_by_id(position_id, price)

    def open_position(self, *args: Any, **kwargs: Any) -> Optional[dict[str, Any]]:
        """Use CTrade(api=sim) to open positions (deprecated)."""
        return self._open_position(*args, **kwargs)

    def buy(self, *args: Any, **kwargs: Any) -> Optional[dict[str, Any]]:
        """Use CTrade(api=sim) to open buy positions (deprecated)."""
        return self._buy(*args, **kwargs)

    def sell(self, *args: Any, **kwargs: Any) -> Optional[dict[str, Any]]:
        """Use CTrade(api=sim) to open sell positions (deprecated)."""
        return self._sell(*args, **kwargs)

    def modify_position(self, *args: Any, **kwargs: Any) -> bool:
        """Use CTrade(api=sim) to modify positions (deprecated)."""
        return self._modify_position(*args, **kwargs)

    def delete_order(self, *args: Any, **kwargs: Any) -> bool:
        """Use CTrade(api=sim) to delete pending orders (deprecated)."""
        return self._delete_order(*args, **kwargs)

    def modify_order(self, *args: Any, **kwargs: Any) -> bool:
        """Use CTrade(api=sim) to modify pending orders (deprecated)."""
        return self._modify_order(*args, **kwargs)

    def buy_stop(self, *args: Any, **kwargs: Any) -> Optional[dict[str, Any]]:
        """Use CTrade(api=sim) to place buy stop orders (deprecated)."""
        return self._buy_stop(*args, **kwargs)

    def buy_limit(self, *args: Any, **kwargs: Any) -> Optional[dict[str, Any]]:
        """Use CTrade(api=sim) to place buy limit orders (deprecated)."""
        return self._buy_limit(*args, **kwargs)

    def sell_stop(self, *args: Any, **kwargs: Any) -> Optional[dict[str, Any]]:
        """Use CTrade(api=sim) to place sell stop orders (deprecated)."""
        return self._sell_stop(*args, **kwargs)

    def sell_limit(self, *args: Any, **kwargs: Any) -> Optional[dict[str, Any]]:
        """Use CTrade(api=sim) to place sell limit orders (deprecated)."""
        return self._sell_limit(*args, **kwargs)

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

    def _calc_margin_sim(
        self, action: str, symbol: str, volume: float, price: float
    ) -> float:
        if self._is_tester:
            order_type = (
                mt5.ORDER_TYPE_BUY if action.lower() == "buy" else mt5.ORDER_TYPE_SELL
            )
            return self._order_calc_margin_tester(order_type, symbol, volume, price)
        return self._calc_margin(symbol, action, volume, price)

    def _ensure_margin(self, margin_required: float) -> bool:
        if margin_required <= 0:
            return True
        if margin_required > float(self._account_state.get("margin_free", 0.0)):
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
                "entry": "in" if direction == "opened" else "out",
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
                "balance": self._account_state.get("balance", 0.0),
            }
        )
        self.deals_container.append(deal)
        self._save_deal(deal)

    def _recalculate_account(self) -> None:
        floating_profit = sum(
            pos.get("profit", 0.0) for pos in self.positions_container
        )
        margin_used = sum(pos.get("margin", 0.0) for pos in self.positions_container)
        balance = float(self._account_state["balance"])
        equity = balance + float(floating_profit)
        free_margin = equity - float(margin_used)
        margin_level = (equity / margin_used * 100.0) if margin_used > 0 else 0.0

        self._account_state.update(
            {
                "equity": equity,
                "profit": float(floating_profit),
                "margin": float(margin_used),
                "margin_free": float(free_margin),
                "margin_level": float(margin_level),
            }
        )
