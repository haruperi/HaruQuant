"""
HistoryOrderInfo class for accessing historical order information.

This module provides a platform-agnostic implementation of historical order
information access, inspired by MT5's HistoryOrderInfo.mqh but designed to
work with any trading platform through adapter patterns.

Historical orders are orders that have been completed (filled, canceled,
expired, or rejected) and are no longer active.

Copyright 2025, HaruQuant
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

# Reuse enums from order_info
from .order_info import OrderState, OrderType, OrderTypeFilling, OrderTypeTime


class HistoryOrderDataProvider(Protocol):
    """
    Protocol for historical order data providers.

    Any trading platform adapter should implement this protocol
    to provide historical order information to the HistoryOrderInfo class.
    """

    def get_ticket(self) -> int:
        """Get order ticket/ID."""
        ...

    def get_time_setup(self) -> datetime:
        """Get order setup time."""
        ...

    def get_time_setup_msc(self) -> int:
        """Get order setup time in milliseconds."""
        ...

    def get_time_done(self) -> datetime:
        """Get order done time."""
        ...

    def get_time_done_msc(self) -> int:
        """Get order done time in milliseconds."""
        ...

    def get_order_type(self) -> OrderType:
        """Get order type."""
        ...

    def get_state(self) -> OrderState:
        """Get order state."""
        ...

    def get_time_expiration(self) -> datetime:
        """Get order expiration time."""
        ...

    def get_type_filling(self) -> OrderTypeFilling:
        """Get order filling type."""
        ...

    def get_type_time(self) -> OrderTypeTime:
        """Get order time type."""
        ...

    def get_magic(self) -> int:
        """Get magic number."""
        ...

    def get_position_id(self) -> int:
        """Get position ID."""
        ...

    def get_position_by_id(self) -> int:
        """Get position by ID."""
        ...

    def get_volume_initial(self) -> float:
        """Get initial volume."""
        ...

    def get_volume_current(self) -> float:
        """Get current volume."""
        ...

    def get_price_open(self) -> float:
        """Get order price."""
        ...

    def get_stop_loss(self) -> float:
        """Get stop loss price."""
        ...

    def get_take_profit(self) -> float:
        """Get take profit price."""
        ...

    def get_price_current(self) -> float:
        """Get current market price."""
        ...

    def get_price_stoplimit(self) -> float:
        """Get stop limit price."""
        ...

    def get_symbol(self) -> str:
        """Get order symbol."""
        ...

    def get_comment(self) -> str:
        """Get order comment."""
        ...

    def get_external_id(self) -> str:
        """Get external order ID."""
        ...

    def select_by_index(self, index: int) -> bool:
        """Select order by index in history."""
        ...

    def get_total_orders(self) -> int:
        """Get total number of historical orders."""
        ...

    def get_symbol_digits(self, symbol: str) -> int:
        """Get symbol digits for price formatting."""
        ...


class MT5HistoryOrderProvider:
    """
    Implementation of HistoryOrderDataProvider using MT5Client.

    This class adapts an MT5Client instance to the HistoryOrderDataProvider protocol,
    providing access to historical order data from MT5.
    """

    def __init__(self, mt5_client, date_from=None, date_to=None):
        """
        Initialize MT5HistoryOrderProvider.

        Args:
            mt5_client: Instance of MT5Client with active connection
            date_from: Start date for order history (datetime or None for all)
            date_to: End date for order history (datetime or None for now)
        """
        self._client = mt5_client
        self._orders: List[Dict[str, Any]] = []
        self._current_index = -1
        self._refresh_orders(date_from, date_to)

    def _refresh_orders(self, date_from=None, date_to=None) -> None:
        """Refresh orders from MT5."""
        orders = self._client.fetch_history_orders(date_from=date_from, date_to=date_to)
        if orders:
            self._orders = orders
            if self._orders and self._current_index == -1:
                self._current_index = 0
        else:
            self._orders = []
            self._current_index = -1

    def _get_current(self) -> Dict[str, Any]:
        """Get current order data."""
        if 0 <= self._current_index < len(self._orders):
            return self._orders[self._current_index]
        return {}

    def get_ticket(self) -> int:
        """Get order ticket."""
        return int(self._get_current().get("ticket", 0))

    def get_time_setup(self) -> datetime:
        """Get order setup time."""
        return datetime.fromtimestamp(self._get_current().get("time_setup", 0))

    def get_time_setup_msc(self) -> int:
        """Get order setup time in milliseconds."""
        return int(self._get_current().get("time_setup_msc", 0))

    def get_time_done(self) -> datetime:
        """Get order done time."""
        return datetime.fromtimestamp(self._get_current().get("time_done", 0))

    def get_time_done_msc(self) -> int:
        """Get order done time in milliseconds."""
        return int(self._get_current().get("time_done_msc", 0))

    def get_order_type(self) -> OrderType:
        """Get order type."""
        val = self._get_current().get("type", -1)
        type_map = {
            0: OrderType.BUY,
            1: OrderType.SELL,
            2: OrderType.BUY_LIMIT,
            3: OrderType.SELL_LIMIT,
            4: OrderType.BUY_STOP,
            5: OrderType.SELL_STOP,
            6: OrderType.BUY_STOP_LIMIT,
            7: OrderType.SELL_STOP_LIMIT,
            8: OrderType.CLOSE_BY,
        }
        return type_map.get(val, OrderType.UNKNOWN)

    def get_state(self) -> OrderState:
        """Get order state."""
        val = self._get_current().get("state", -1)
        state_map = {
            0: OrderState.STARTED,
            1: OrderState.PLACED,
            2: OrderState.CANCELED,
            3: OrderState.PARTIAL,
            4: OrderState.FILLED,
            5: OrderState.REJECTED,
            6: OrderState.EXPIRED,
            7: OrderState.REQUEST_ADD,
            8: OrderState.REQUEST_MODIFY,
            9: OrderState.REQUEST_CANCEL,
        }
        return state_map.get(val, OrderState.UNKNOWN)

    def get_time_expiration(self) -> datetime:
        """Get order expiration time."""
        return datetime.fromtimestamp(self._get_current().get("time_expiration", 0))

    def get_type_filling(self) -> OrderTypeFilling:
        """Get order filling type."""
        val = self._get_current().get("type_filling", -1)
        fill_map = {
            0: OrderTypeFilling.FOK,
            1: OrderTypeFilling.IOC,
            2: OrderTypeFilling.RETURN,
        }
        return fill_map.get(val, OrderTypeFilling.UNKNOWN)

    def get_type_time(self) -> OrderTypeTime:
        """Get order time type."""
        val = self._get_current().get("type_time", -1)
        time_map = {
            0: OrderTypeTime.GTC,
            1: OrderTypeTime.DAY,
            2: OrderTypeTime.SPECIFIED,
            3: OrderTypeTime.SPECIFIED_DAY,
        }
        return time_map.get(val, OrderTypeTime.UNKNOWN)

    def get_magic(self) -> int:
        """Get magic number."""
        return int(self._get_current().get("magic", 0))

    def get_position_id(self) -> int:
        """Get position ID."""
        return int(self._get_current().get("position_id", 0))

    def get_position_by_id(self) -> int:
        """Get position by ID."""
        return int(self._get_current().get("position_by_id", 0))

    def get_volume_initial(self) -> float:
        """Get initial volume."""
        return float(self._get_current().get("volume_initial", 0.0))

    def get_volume_current(self) -> float:
        """Get current volume."""
        return float(self._get_current().get("volume_current", 0.0))

    def get_price_open(self) -> float:
        """Get open price."""
        return float(self._get_current().get("price_open", 0.0))

    def get_stop_loss(self) -> float:
        """Get stop loss price."""
        return float(self._get_current().get("sl", 0.0))

    def get_take_profit(self) -> float:
        """Get take profit price."""
        return float(self._get_current().get("tp", 0.0))

    def get_price_current(self) -> float:
        """Get current price."""
        return float(self._get_current().get("price_current", 0.0))

    def get_price_stoplimit(self) -> float:
        """Get stop limit price."""
        return float(self._get_current().get("price_stoplimit", 0.0))

    def get_symbol(self) -> str:
        """Get symbol name."""
        return str(self._get_current().get("symbol", ""))

    def get_comment(self) -> str:
        """Get order comment."""
        return str(self._get_current().get("comment", ""))

    def get_external_id(self) -> str:
        """Get external order ID."""
        return str(self._get_current().get("external_id", ""))

    def select_by_index(self, index: int) -> bool:
        """Select order by index."""
        if 0 <= index < len(self._orders):
            self._current_index = index
            return True
        return False

    def get_total_orders(self) -> int:
        """Get total number of orders."""
        return len(self._orders)

    def get_symbol_digits(self, symbol: str) -> int:
        """Get symbol digits from MT5."""
        symbol_info = self._client.get_symbol_info(symbol)
        if symbol_info:
            return int(symbol_info.get("digits", 5))
        return 5


class BacktestHistoryOrderProvider:
    """
    Implementation of HistoryOrderDataProvider for backtesting.

    This provider manages historical (completed) orders for backtesting
    without requiring an MT5 connection.
    """

    def __init__(self):
        """Initialize BacktestHistoryOrderProvider with empty order history."""
        self._orders: List[Dict[str, Any]] = []
        self._current_index = -1

    def add_order(
        self,
        ticket: int,
        time_setup: datetime,
        time_done: datetime,
        order_type: OrderType,
        state: OrderState,
        symbol: str,
        volume_initial: float,
        volume_current: float,
        price_open: float,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        price_current: float = 0.0,
        price_stoplimit: float = 0.0,
        time_expiration: Optional[datetime] = None,
        type_filling: OrderTypeFilling = OrderTypeFilling.FOK,
        type_time: OrderTypeTime = OrderTypeTime.GTC,
        magic: int = 0,
        position_id: int = 0,
        position_by_id: int = 0,
        comment: str = "",
        external_id: str = "",
    ) -> None:
        """
        Add a historical order to the backtest.

        Args:
            ticket: Order ticket number
            time_setup: Order setup time
            time_done: Order completion time
            order_type: Order type (BUY, SELL, BUY_LIMIT, etc.)
            state: Order state (FILLED, CANCELED, EXPIRED, etc.)
            symbol: Trading symbol
            volume_initial: Initial volume
            volume_current: Current volume (0 if fully filled)
            price_open: Order open price
            stop_loss: Stop loss price
            take_profit: Take profit price
            price_current: Current price
            price_stoplimit: Stop limit price
            time_expiration: Expiration time
            type_filling: Filling type
            type_time: Time type
            magic: Magic number
            position_id: Position ID
            position_by_id: Position by ID
            comment: Order comment
            external_id: External order ID
        """
        order_data = {
            "ticket": ticket,
            "time_setup": int(time_setup.timestamp()),
            "time_setup_msc": int(time_setup.timestamp() * 1000),
            "time_done": int(time_done.timestamp()),
            "time_done_msc": int(time_done.timestamp() * 1000),
            "type": self._map_order_type_to_int(order_type),
            "state": self._map_order_state_to_int(state),
            "time_expiration": (
                int(time_expiration.timestamp()) if time_expiration else 0
            ),
            "type_filling": self._map_filling_type_to_int(type_filling),
            "type_time": self._map_time_type_to_int(type_time),
            "magic": magic,
            "position_id": position_id,
            "position_by_id": position_by_id,
            "volume_initial": volume_initial,
            "volume_current": volume_current,
            "price_open": price_open,
            "sl": stop_loss,
            "tp": take_profit,
            "price_current": price_current,
            "price_stoplimit": price_stoplimit,
            "symbol": symbol,
            "comment": comment,
            "external_id": external_id,
        }
        self._orders.append(order_data)
        if self._current_index == -1 and self._orders:
            self._current_index = 0

    def _map_order_type_to_int(self, order_type: OrderType) -> int:
        """Map OrderType enum to integer code."""
        type_map = {
            OrderType.BUY: 0,
            OrderType.SELL: 1,
            OrderType.BUY_LIMIT: 2,
            OrderType.SELL_LIMIT: 3,
            OrderType.BUY_STOP: 4,
            OrderType.SELL_STOP: 5,
            OrderType.BUY_STOP_LIMIT: 6,
            OrderType.SELL_STOP_LIMIT: 7,
            OrderType.CLOSE_BY: 8,
        }
        return type_map.get(order_type, -1)

    def _map_order_state_to_int(self, state: OrderState) -> int:
        """Map OrderState enum to integer code."""
        state_map = {
            OrderState.STARTED: 0,
            OrderState.PLACED: 1,
            OrderState.CANCELED: 2,
            OrderState.PARTIAL: 3,
            OrderState.FILLED: 4,
            OrderState.REJECTED: 5,
            OrderState.EXPIRED: 6,
            OrderState.REQUEST_ADD: 7,
            OrderState.REQUEST_MODIFY: 8,
            OrderState.REQUEST_CANCEL: 9,
        }
        return state_map.get(state, -1)

    def _map_filling_type_to_int(self, filling: OrderTypeFilling) -> int:
        """Map OrderTypeFilling enum to integer code."""
        filling_map = {
            OrderTypeFilling.FOK: 0,
            OrderTypeFilling.IOC: 1,
            OrderTypeFilling.RETURN: 2,
        }
        return filling_map.get(filling, -1)

    def _map_time_type_to_int(self, time_type: OrderTypeTime) -> int:
        """Map OrderTypeTime enum to integer code."""
        time_map = {
            OrderTypeTime.GTC: 0,
            OrderTypeTime.DAY: 1,
            OrderTypeTime.SPECIFIED: 2,
            OrderTypeTime.SPECIFIED_DAY: 3,
        }
        return time_map.get(time_type, -1)

    def clear_orders(self) -> None:
        """Clear all historical orders."""
        self._orders = []
        self._current_index = -1

    def _get_current(self) -> Dict[str, Any]:
        """Get current order data."""
        if 0 <= self._current_index < len(self._orders):
            return self._orders[self._current_index]
        return {}

    def get_ticket(self) -> int:
        """Get order ticket."""
        return int(self._get_current().get("ticket", 0))

    def get_time_setup(self) -> datetime:
        """Get order setup time."""
        return datetime.fromtimestamp(self._get_current().get("time_setup", 0))

    def get_time_setup_msc(self) -> int:
        """Get order setup time in milliseconds."""
        return int(self._get_current().get("time_setup_msc", 0))

    def get_time_done(self) -> datetime:
        """Get order done time."""
        return datetime.fromtimestamp(self._get_current().get("time_done", 0))

    def get_time_done_msc(self) -> int:
        """Get order done time in milliseconds."""
        return int(self._get_current().get("time_done_msc", 0))

    def get_order_type(self) -> OrderType:
        """Get order type."""
        val = self._get_current().get("type", -1)
        if isinstance(val, OrderType):
            return val
        type_map = {
            0: OrderType.BUY,
            1: OrderType.SELL,
            2: OrderType.BUY_LIMIT,
            3: OrderType.SELL_LIMIT,
            4: OrderType.BUY_STOP,
            5: OrderType.SELL_STOP,
            6: OrderType.BUY_STOP_LIMIT,
            7: OrderType.SELL_STOP_LIMIT,
            8: OrderType.CLOSE_BY,
        }
        return type_map.get(val, OrderType.UNKNOWN)

    def get_state(self) -> OrderState:
        """Get order state."""
        val = self._get_current().get("state", -1)
        if isinstance(val, OrderState):
            return val
        state_map = {
            0: OrderState.STARTED,
            1: OrderState.PLACED,
            2: OrderState.CANCELED,
            3: OrderState.PARTIAL,
            4: OrderState.FILLED,
            5: OrderState.REJECTED,
            6: OrderState.EXPIRED,
            7: OrderState.REQUEST_ADD,
            8: OrderState.REQUEST_MODIFY,
            9: OrderState.REQUEST_CANCEL,
        }
        return state_map.get(val, OrderState.UNKNOWN)

    def get_time_expiration(self) -> datetime:
        """Get order expiration time."""
        return datetime.fromtimestamp(self._get_current().get("time_expiration", 0))

    def get_type_filling(self) -> OrderTypeFilling:
        """Get order filling type."""
        val = self._get_current().get("type_filling", -1)
        if isinstance(val, OrderTypeFilling):
            return val
        fill_map = {
            0: OrderTypeFilling.FOK,
            1: OrderTypeFilling.IOC,
            2: OrderTypeFilling.RETURN,
        }
        return fill_map.get(val, OrderTypeFilling.UNKNOWN)

    def get_type_time(self) -> OrderTypeTime:
        """Get order time type."""
        val = self._get_current().get("type_time", -1)
        if isinstance(val, OrderTypeTime):
            return val
        time_map = {
            0: OrderTypeTime.GTC,
            1: OrderTypeTime.DAY,
            2: OrderTypeTime.SPECIFIED,
            3: OrderTypeTime.SPECIFIED_DAY,
        }
        return time_map.get(val, OrderTypeTime.UNKNOWN)

    def get_magic(self) -> int:
        """Get magic number."""
        return int(self._get_current().get("magic", 0))

    def get_position_id(self) -> int:
        """Get position ID."""
        return int(self._get_current().get("position_id", 0))

    def get_position_by_id(self) -> int:
        """Get position by ID."""
        return int(self._get_current().get("position_by_id", 0))

    def get_volume_initial(self) -> float:
        """Get initial volume."""
        return float(self._get_current().get("volume_initial", 0.0))

    def get_volume_current(self) -> float:
        """Get current volume."""
        return float(self._get_current().get("volume_current", 0.0))

    def get_price_open(self) -> float:
        """Get open price."""
        return float(self._get_current().get("price_open", 0.0))

    def get_stop_loss(self) -> float:
        """Get stop loss price."""
        return float(self._get_current().get("sl", 0.0))

    def get_take_profit(self) -> float:
        """Get take profit price."""
        return float(self._get_current().get("tp", 0.0))

    def get_price_current(self) -> float:
        """Get current price."""
        return float(self._get_current().get("price_current", 0.0))

    def get_price_stoplimit(self) -> float:
        """Get stop limit price."""
        return float(self._get_current().get("price_stoplimit", 0.0))

    def get_symbol(self) -> str:
        """Get symbol name."""
        return str(self._get_current().get("symbol", ""))

    def get_comment(self) -> str:
        """Get order comment."""
        return str(self._get_current().get("comment", ""))

    def get_external_id(self) -> str:
        """Get external order ID."""
        return str(self._get_current().get("external_id", ""))

    def select_by_index(self, index: int) -> bool:
        """Select order by index."""
        if 0 <= index < len(self._orders):
            self._current_index = index
            return True
        return False

    def get_total_orders(self) -> int:
        """Get total number of orders."""
        return len(self._orders)

    def get_symbol_digits(self, symbol: str) -> int:
        """Get symbol digits (default to 5 for backtest)."""
        return 5


class HistoryOrderInfo:
    """
    Class for accessing historical order information.

    This class provides a clean interface to historical order information
    regardless of the underlying trading platform. Historical orders are
    orders that have been completed (filled, canceled, expired, rejected).

    Usage:
        # With MT5 provider for live trading
        from apps.mt5 import MT5Client
        from apps.trade import HistoryOrderInfo, MT5HistoryOrderProvider
        from datetime import datetime, timedelta

        client = MT5Client()
        client.initialize()
        provider = MT5HistoryOrderProvider(client, date_from=datetime.now() - timedelta(days=30))
        order = HistoryOrderInfo(provider)

        # Iterate through history
        for i in range(order.total_orders()):
            if order.select_by_index(i):
                print(f"Order: {order.format_order()}")
                print(f"State: {order.state_description()}")
    """

    def __init__(self, data_provider: HistoryOrderDataProvider):
        """
        Initialize HistoryOrderInfo.

        Args:
            data_provider: Platform-specific data provider implementing
                          HistoryOrderDataProvider protocol.
                          Use MT5HistoryOrderProvider for live trading.
        """
        self._provider = data_provider
        self._ticket: int = 0

    def total_orders(self) -> int:
        """
        Get total number of historical orders.

        Returns:
            Total count of historical orders.
        """
        return self._provider.get_total_orders()

    def ticket(self, ticket: Optional[int] = None) -> int:
        """
        Get or set order ticket/ID.

        Args:
            ticket: If provided, sets the ticket. If None, returns current ticket.

        Returns:
            Current order ticket number.
        """
        if ticket is not None:
            self._ticket = ticket
        return self._ticket

    # Fast access methods to integer order properties

    def time_setup(self) -> datetime:
        """
        Get order setup time.

        Returns:
            Order setup datetime.
        """
        return self._provider.get_time_setup()

    def time_setup_msc(self) -> int:
        """
        Get order setup time in milliseconds.

        Returns:
            Order setup time in milliseconds since epoch.
        """
        return self._provider.get_time_setup_msc()

    def time_done(self) -> datetime:
        """
        Get order done time.

        Returns:
            Order done datetime (when order was filled/cancelled).
        """
        return self._provider.get_time_done()

    def time_done_msc(self) -> int:
        """
        Get order done time in milliseconds.

        Returns:
            Order done time in milliseconds since epoch.
        """
        return self._provider.get_time_done_msc()

    def order_type(self) -> OrderType:
        """
        Get order type.

        Returns:
            OrderType enum value.
        """
        return self._provider.get_order_type()

    def type_description(self) -> str:
        """
        Get order type as a descriptive string.

        Returns:
            Human-readable description of order type.
        """
        return self.format_type(self.order_type())

    def state(self) -> OrderState:
        """
        Get order state.

        Returns:
            OrderState enum value.
        """
        return self._provider.get_state()

    def state_description(self) -> str:
        """
        Get order state as a descriptive string.

        Returns:
            Human-readable description of order state.
        """
        return self.format_status(self.state())

    def time_expiration(self) -> datetime:
        """
        Get order expiration time.

        Returns:
            Order expiration datetime (None if GTC).
        """
        return self._provider.get_time_expiration()

    def type_filling(self) -> OrderTypeFilling:
        """
        Get order filling type.

        Returns:
            OrderTypeFilling enum value.
        """
        return self._provider.get_type_filling()

    def type_filling_description(self) -> str:
        """
        Get order filling type as a descriptive string.

        Returns:
            Human-readable description of filling type.
        """
        return self.format_type_filling(self.type_filling())

    def type_time(self) -> OrderTypeTime:
        """
        Get order time type.

        Returns:
            OrderTypeTime enum value.
        """
        return self._provider.get_type_time()

    def type_time_description(self) -> str:
        """
        Get order time type as a descriptive string.

        Returns:
            Human-readable description of time type.
        """
        return self.format_type_time(self.type_time())

    def magic(self) -> int:
        """
        Get magic number.

        Returns:
            Magic number used to identify the order.
        """
        return self._provider.get_magic()

    def position_id(self) -> int:
        """
        Get position ID.

        Returns:
            Position ID that will be assigned to the position opened by this order.
        """
        return self._provider.get_position_id()

    def position_by_id(self) -> int:
        """
        Get position by ID.

        Returns:
            Position ID for close by orders.
        """
        return self._provider.get_position_by_id()

    # Fast access methods to double order properties

    def volume_initial(self) -> float:
        """
        Get initial order volume.

        Returns:
            Initial volume in lots.
        """
        return self._provider.get_volume_initial()

    def volume_current(self) -> float:
        """
        Get current order volume.

        Returns:
            Current remaining volume in lots (0 if fully filled).
        """
        return self._provider.get_volume_current()

    def price_open(self) -> float:
        """
        Get order price.

        Returns:
            Order price.
        """
        return self._provider.get_price_open()

    def stop_loss(self) -> float:
        """
        Get stop loss price.

        Returns:
            Stop loss price (0.0 if not set).
        """
        return self._provider.get_stop_loss()

    def take_profit(self) -> float:
        """
        Get take profit price.

        Returns:
            Take profit price (0.0 if not set).
        """
        return self._provider.get_take_profit()

    def price_current(self) -> float:
        """
        Get current market price.

        Returns:
            Current market price for the order's symbol.
        """
        return self._provider.get_price_current()

    def price_stoplimit(self) -> float:
        """
        Get stop limit price.

        Returns:
            Stop limit price (for stop limit orders).
        """
        return self._provider.get_price_stoplimit()

    # Fast access methods to string order properties

    def symbol(self) -> str:
        """
        Get order symbol.

        Returns:
            Trading symbol (e.g., "EURUSD").
        """
        return self._provider.get_symbol()

    def comment(self) -> str:
        """
        Get order comment.

        Returns:
            Order comment string.
        """
        return self._provider.get_comment()

    def external_id(self) -> str:
        """
        Get external order ID.

        Returns:
            External order ID from exchange.
        """
        return self._provider.get_external_id()

    # Info methods

    @staticmethod
    def format_type(order_type: OrderType) -> str:
        """
        Convert order type to text.

        Args:
            order_type: OrderType enum value.

        Returns:
            Human-readable order type string.
        """
        type_map = {
            OrderType.BUY: "buy",
            OrderType.SELL: "sell",
            OrderType.BUY_LIMIT: "buy limit",
            OrderType.SELL_LIMIT: "sell limit",
            OrderType.BUY_STOP: "buy stop",
            OrderType.SELL_STOP: "sell stop",
            OrderType.BUY_STOP_LIMIT: "buy stop limit",
            OrderType.SELL_STOP_LIMIT: "sell stop limit",
            OrderType.CLOSE_BY: "close by",
        }
        return type_map.get(order_type, f"unknown order type {order_type.value}")

    @staticmethod
    def format_status(state: OrderState) -> str:
        """
        Convert order state to text.

        Args:
            state: OrderState enum value.

        Returns:
            Human-readable order state string.
        """
        state_map = {
            OrderState.STARTED: "started",
            OrderState.PLACED: "placed",
            OrderState.CANCELED: "canceled",
            OrderState.PARTIAL: "partial",
            OrderState.FILLED: "filled",
            OrderState.REJECTED: "rejected",
            OrderState.EXPIRED: "expired",
            OrderState.REQUEST_ADD: "request adding",
            OrderState.REQUEST_MODIFY: "request modifying",
            OrderState.REQUEST_CANCEL: "request cancelling",
        }
        return state_map.get(state, f"unknown order status {state.value}")

    @staticmethod
    def format_type_filling(filling_type: OrderTypeFilling) -> str:
        """
        Convert order filling type to text.

        Args:
            filling_type: OrderTypeFilling enum value.

        Returns:
            Human-readable filling type string.
        """
        filling_map = {
            OrderTypeFilling.RETURN: "return remainder",
            OrderTypeFilling.IOC: "cancel remainder",
            OrderTypeFilling.FOK: "fill or kill",
        }
        return filling_map.get(
            filling_type, f"unknown type filling {filling_type.value}"
        )

    @staticmethod
    def format_type_time(time_type: OrderTypeTime) -> str:
        """
        Convert order time type to text.

        Args:
            time_type: OrderTypeTime enum value.

        Returns:
            Human-readable time type string.
        """
        time_map = {
            OrderTypeTime.GTC: "gtc",
            OrderTypeTime.DAY: "day",
            OrderTypeTime.SPECIFIED: "specified",
            OrderTypeTime.SPECIFIED_DAY: "specified day",
        }
        return time_map.get(time_type, f"unknown type time {time_type.value}")

    def format_order(self) -> str:
        """
        Format order parameters as text.

        Returns:
            Formatted string describing the order.
        """
        symbol_name = self.symbol()
        digits = self._provider.get_symbol_digits(symbol_name)

        # Get order type description
        type_desc = self.type_description()

        # Format basic order info
        result = (
            f"#{self._ticket} {type_desc} " f"{self.volume_initial():.2f} {symbol_name}"
        )

        # Format price
        price_str = self.format_price(self.price_open(), self.price_stoplimit(), digits)

        if price_str:
            result += f" at {price_str}"

        return result

    @staticmethod
    def format_price(price_order: float, price_trigger: float, digits: int) -> str:
        """
        Format order prices to text.

        Args:
            price_order: Order price.
            price_trigger: Trigger price (for stop limit orders).
            digits: Number of decimal places.

        Returns:
            Formatted price string.
        """
        if price_trigger and price_trigger != 0.0:
            # Stop limit order - show both prices
            price = f"{price_order:.{digits}f}"
            trigger = f"{price_trigger:.{digits}f}"
            return f"{price} ({trigger})"
        elif price_order and price_order != 0.0:
            return f"{price_order:.{digits}f}"
        else:
            return ""

    # Methods for selecting orders

    def select_by_index(self, index: int) -> bool:
        """
        Select order by index in the history.

        Args:
            index: Order index (0-based).

        Returns:
            True if order exists at index and was selected, False otherwise.
        """
        if self._provider.select_by_index(index):
            self._ticket = self._provider.get_ticket()
            return True

        self._ticket = 0
        return False

    def __repr__(self) -> str:
        """Return string representation of HistoryOrderInfo."""
        try:
            return (
                f"HistoryOrderInfo(ticket={self._ticket}, "
                f"symbol={self.symbol()}, "
                f"type={self.order_type().value}, "
                f"state={self.state().value}, "
                f"volume={self.volume_current():.2f})"
            )
        except Exception:
            return "HistoryOrderInfo(no order selected)"
