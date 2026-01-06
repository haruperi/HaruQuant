"""
OrderInfo class for accessing order information.

This module provides a platform-agnostic implementation of order information
access, inspired by MT5's OrderInfo.mqh but designed to work with any
trading platform through adapter patterns.

Copyright 2025, HaruQuant
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class OrderType(Enum):
    """Order type enumeration."""

    BUY = "buy"
    SELL = "sell"
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"
    BUY_STOP = "buy_stop"
    SELL_STOP = "sell_stop"
    BUY_STOP_LIMIT = "buy_stop_limit"
    SELL_STOP_LIMIT = "sell_stop_limit"
    CLOSE_BY = "close_by"
    UNKNOWN = "unknown"


class OrderState(Enum):
    """Order state enumeration."""

    STARTED = "started"
    PLACED = "placed"
    CANCELED = "canceled"
    PARTIAL = "partial"
    FILLED = "filled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REQUEST_ADD = "request_add"
    REQUEST_MODIFY = "request_modify"
    REQUEST_CANCEL = "request_cancel"
    UNKNOWN = "unknown"


class OrderTypeFilling(Enum):
    """Order filling type enumeration."""

    RETURN = "return"  # Return remainder
    IOC = "ioc"  # Immediate or Cancel (cancel remainder)
    FOK = "fok"  # Fill or Kill
    UNKNOWN = "unknown"


class OrderTypeTime(Enum):
    """Order expiration type enumeration."""

    GTC = "gtc"  # Good till cancelled
    DAY = "day"  # Good till day end
    SPECIFIED = "specified"  # Good till specified time
    SPECIFIED_DAY = "specified_day"  # Good till specified day
    UNKNOWN = "unknown"


class OrderDataProvider(Protocol):
    """
    Protocol for order data providers.

    Any trading platform adapter should implement this protocol
    to provide order information to the OrderInfo class.
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

    def select_order(self, ticket: int) -> bool:
        """Select order by ticket."""
        ...

    def select_by_index(self, index: int) -> bool:
        """Select order by index."""
        ...

    def get_total_orders(self) -> int:
        """Get total number of active orders."""
        ...

    def get_symbol_digits(self, symbol: str) -> int:
        """Get symbol digits for price formatting."""
        ...


class MT5OrderProvider(OrderDataProvider):
    """
    Implementation of OrderDataProvider using MT5Client.

    This class adapts an MT5Client instance to the OrderDataProvider protocol,
    providing access to active/pending order data from MT5.
    """

    def __init__(self, mt5_client: Any):
        """
        Initialize MT5OrderProvider.

        Args:
            mt5_client: Instance of MT5Client with active connection
        """
        self._client = mt5_client
        self._orders: List[Dict[str, Any]] = []
        self._current_index = -1
        self._refresh_orders()

    def _refresh_orders(self) -> None:
        """Refresh orders from MT5."""
        orders = self._client.get_orders()
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
        return datetime.fromtimestamp(int(self._get_current().get("time_setup", 0)))

    def get_time_setup_msc(self) -> int:
        """Get order setup time in milliseconds."""
        return int(self._get_current().get("time_setup_msc", 0))

    def get_time_done(self) -> datetime:
        """Get order done time."""
        return datetime.fromtimestamp(int(self._get_current().get("time_done", 0)))

    def get_time_done_msc(self) -> int:
        """Get order done time in milliseconds."""
        return int(self._get_current().get("time_done_msc", 0))

    def get_order_type(self) -> OrderType:
        """Get order type."""
        val = int(self._get_current().get("type", -1))
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
        val = int(self._get_current().get("state", -1))
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
        return datetime.fromtimestamp(
            int(self._get_current().get("time_expiration", 0))
        )

    def get_type_filling(self) -> OrderTypeFilling:
        """Get order filling type."""
        val = int(self._get_current().get("type_filling", -1))
        fill_map = {
            0: OrderTypeFilling.FOK,
            1: OrderTypeFilling.IOC,
            2: OrderTypeFilling.RETURN,
        }
        return fill_map.get(val, OrderTypeFilling.UNKNOWN)

    def get_type_time(self) -> OrderTypeTime:
        """Get order time type."""
        val = int(self._get_current().get("type_time", -1))
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

    def select_order(self, ticket: int) -> bool:
        """Select order by ticket."""
        for i, order in enumerate(self._orders):
            if order.get("ticket") == ticket:
                self._current_index = i
                return True
        return False

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


class BacktestOrderProvider(OrderDataProvider):
    """
    Implementation of OrderDataProvider for backtesting.

    This provider manages active and pending orders for backtesting
    without requiring an MT5 connection.
    """

    def __init__(self) -> None:
        """Initialize BacktestOrderProvider with empty order list."""
        self._orders: List[Dict[str, Any]] = []
        self._current_index = -1

    def add_order(
        self,
        ticket: int,
        time_setup: datetime,
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
        Add an order to the backtest.

        Args:
            ticket: Order ticket number
            time_setup: Order setup time
            order_type: Order type (BUY, SELL, BUY_LIMIT, etc.)
            state: Order state (PLACED, FILLED, CANCELED, etc.)
            symbol: Trading symbol
            volume_initial: Initial volume
            volume_current: Current volume
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
            "time_done": 0,
            "time_done_msc": 0,
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

    def select_order(self, ticket: int) -> bool:
        """Select order by ticket."""
        for i, order in enumerate(self._orders):
            if order.get("ticket") == ticket:
                self._current_index = i
                return True
        return False

    def select_by_magic(self, magic: int) -> bool:
        """Select order by magic number."""
        for i, order in enumerate(self._orders):
            if order.get("magic") == magic:
                self._current_index = i
                return True
        return False

    def update_order(self, ticket: int, **kwargs) -> bool:
        """
        Update an existing order.

        Args:
            ticket: Order ticket to update
            **kwargs: Fields to update (volume_current, price_current, state, etc.)

        Returns:
            True if order was found and updated, False otherwise
        """
        for order in self._orders:
            if order["ticket"] == ticket:
                order.update(kwargs)
                return True
        return False

    def remove_order(self, ticket: int) -> bool:
        """
        Remove an order (e.g., when filled or canceled).

        Args:
            ticket: Order ticket to remove

        Returns:
            True if order was found and removed, False otherwise
        """
        for i, order in enumerate(self._orders):
            if order["ticket"] == ticket:
                self._orders.pop(i)
                if self._current_index >= len(self._orders):
                    self._current_index = len(self._orders) - 1
                return True
        return False

    def clear_orders(self) -> None:
        """Clear all orders."""
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

    def select_by_ticket(self, ticket: int) -> bool:
        """Select order by ticket."""
        for i, order in enumerate(self._orders):
            if order["ticket"] == ticket:
                self._current_index = i
                return True
        return False

    def get_total_orders(self) -> int:
        """Get total number of orders."""
        return len(self._orders)

    def get_symbol_digits(self, symbol: str) -> int:
        """Get symbol digits (default to 5 for backtest)."""
        return 5


class OrderInfo:
    """
    Class for accessing order information.

    This class provides a clean interface to order information
    regardless of the underlying trading platform. It uses a data
    provider pattern to abstract platform-specific implementations.

    Usage:
        # With MT5 provider for live trading
        from apps.mt5 import MT5Client
        from apps.trade import OrderInfo, MT5OrderProvider

        client = MT5Client()
        client.initialize()
        provider = MT5OrderProvider(client)
        order = OrderInfo(provider)

        # Select an order
        if order.select(12345678):
            print(f"Ticket: {order.ticket()}")
            print(f"Type: {order.type_description()}")
            print(f"Volume: {order.volume_initial()}")
            print(f"State: {order.state_description()}")
    """

    def __init__(self, data_provider: OrderDataProvider):
        """
        Initialize OrderInfo.

        Args:
            data_provider: Platform-specific data provider implementing
                          OrderDataProvider protocol.
                          Use MT5OrderProvider for live trading.
        """
        self._provider = data_provider
        self._ticket: int = 0

        # State storage for CheckState functionality
        self._stored_type: Optional[OrderType] = None
        self._stored_state: Optional[OrderState] = None
        self._stored_expiration: Optional[datetime] = None
        self._stored_volume_curr: float = 0.0
        self._stored_price_open: float = 0.0
        self._stored_stop_loss: float = 0.0
        self._stored_take_profit: float = 0.0

    def total_orders(self) -> int:
        """
        Get total number of orders.

        Returns:
            Total count of orders.
        """
        return self._provider.get_total_orders()

    # Methods of access to protected data

    def ticket(self) -> int:
        """
        Get order ticket/ID.

        Returns:
            Order ticket number.
        """
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
            Current remaining volume in lots.
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
            f"#{self.ticket()} {type_desc} "
            f"{self.volume_initial():.2f} {symbol_name}"
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

    def select(self, ticket: Optional[int] = None) -> bool:
        """
        Select order by ticket.

        Args:
            ticket: Order ticket number. If None, uses current ticket.

        Returns:
            True if order exists and was selected, False otherwise.
        """
        if ticket is None:
            ticket = self._ticket

        if self._provider.select_order(ticket):
            self._ticket = ticket
            return True

        self._ticket = 0
        return False

    def select_by_index(self, index: int) -> bool:
        """
        Select order by index in the orders list.

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

    # State management methods

    def store_state(self) -> None:
        """
        Store current order state.

        Saves the current order's type, state, expiration, volume,
        price, stop loss, and take profit for later comparison.
        """
        self._stored_type = self.order_type()
        self._stored_state = self.state()
        self._stored_expiration = self.time_expiration()
        self._stored_volume_curr = self.volume_current()
        self._stored_price_open = self.price_open()
        self._stored_stop_loss = self.stop_loss()
        self._stored_take_profit = self.take_profit()

    def check_state(self) -> bool:
        """
        Check if order state has changed.

        Compares current order state with the state stored by
        store_state().

        Returns:
            True if order has changed, False if unchanged.
        """
        if self._stored_type is None:
            # No state stored yet
            return True

        if (
            self._stored_type == self.order_type()
            and self._stored_state == self.state()
            and self._stored_expiration == self.time_expiration()
            and self._stored_volume_curr == self.volume_current()
            and self._stored_price_open == self.price_open()
            and self._stored_stop_loss == self.stop_loss()
            and self._stored_take_profit == self.take_profit()
        ):
            return False

        return True

    def __repr__(self) -> str:
        """Return string representation of OrderInfo."""
        try:
            return (
                f"OrderInfo(ticket={self.ticket()}, "
                f"symbol={self.symbol()}, "
                f"type={self.order_type().value}, "
                f"state={self.state().value}, "
                f"volume={self.volume_current():.2f})"
            )
        except Exception:
            return "OrderInfo(no order selected)"
