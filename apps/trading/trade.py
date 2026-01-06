"""
Trade class for executing trading operations.

This module provides a platform-agnostic implementation of trading operations,
inspired by MT5's Trade.mqh but designed to work with any trading platform
through adapter patterns.

Copyright 2025, HaruQuant
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Protocol

from apps.logger import logger

# Import existing types
from .order_info import OrderType, OrderTypeFilling, OrderTypeTime


class TradeAction(Enum):
    """Trade action enumeration."""

    DEAL = "deal"  # Place a trade (market execution)
    PENDING = "pending"  # Place a pending order
    SLTP = "sltp"  # Modify stop loss and take profit
    MODIFY = "modify"  # Modify pending order parameters
    REMOVE = "remove"  # Delete pending order
    CLOSE_BY = "close_by"  # Close position by an opposite one


class TradeRetcode(Enum):
    """Trade operation return codes."""

    # Success codes
    DONE = 10009  # Request completed
    DONE_PARTIAL = 10010  # Request completed partially
    PLACED = 10008  # Order placed

    # Rejection codes
    REQUOTE = 10004  # Requote
    REJECT = 10006  # Request rejected
    CANCEL = 10007  # Request canceled by trader

    # Error codes
    ERROR = 10011  # Request processing error
    TIMEOUT = 10012  # Request canceled by timeout
    INVALID = 10013  # Invalid request
    INVALID_VOLUME = 10014  # Invalid volume in the request
    INVALID_PRICE = 10015  # Invalid price in the request
    INVALID_STOPS = 10016  # Invalid stops in the request
    TRADE_DISABLED = 10017  # Trade is disabled
    MARKET_CLOSED = 10018  # Market is closed
    NO_MONEY = 10019  # Not enough money to complete the request
    PRICE_CHANGED = 10020  # Prices changed
    PRICE_OFF = 10021  # No quotes to process the request
    INVALID_EXPIRATION = 10022  # Invalid order expiration date
    ORDER_CHANGED = 10023  # Order state changed
    TOO_MANY_REQUESTS = 10024  # Too frequent requests
    NO_CHANGES = 10025  # No changes in request
    SERVER_DISABLES_AT = 10026  # Autotrading disabled by server
    CLIENT_DISABLES_AT = 10027  # Autotrading disabled by client
    LOCKED = 10028  # Request locked for processing
    FROZEN = 10029  # Order or position frozen
    INVALID_FILL = 10030  # Invalid order filling type
    CONNECTION = 10031  # No connection with the trade server
    ONLY_REAL = 10032  # Operation is allowed only for live accounts
    LIMIT_ORDERS = 10033  # Number of pending orders reached limit
    LIMIT_VOLUME = 10034  # Volume of orders and positions reached limit
    INVALID_ORDER = 10035  # Incorrect or prohibited order type
    POSITION_CLOSED = 10036  # Position already closed
    CLOSE_ORDER_EXIST = 10038  # Close volume exceeds the current position volume
    LIMIT_POSITIONS = 10039  # Number of positions reached limit


class LogLevel(Enum):
    """Logging level enumeration."""

    NO = 0  # No logging
    ERRORS = 1  # Log only errors
    ALL = 2  # Log all operations


@dataclass
class TradeRequest:
    """Trade request structure."""

    action: TradeAction = TradeAction.DEAL
    magic: int = 0
    order: int = 0
    symbol: str = ""
    volume: float = 0.0
    price: float = 0.0
    stoplimit: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    deviation: int = 0
    type: OrderType = OrderType.BUY
    type_filling: OrderTypeFilling = OrderTypeFilling.FOK
    type_time: OrderTypeTime = OrderTypeTime.GTC
    expiration: Optional[datetime] = None
    comment: str = ""
    position: int = 0  # Position ticket (for hedging)
    position_by: int = 0  # Opposite position ticket (for close by)


@dataclass
class TradeResult:
    """Trade result structure."""

    retcode: TradeRetcode = TradeRetcode.ERROR
    deal: int = 0
    order: int = 0
    volume: float = 0.0
    price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    comment: str = ""
    request_id: int = 0
    retcode_external: int = 0


@dataclass
class TradeCheckResult:
    """Trade check result structure."""

    retcode: TradeRetcode = TradeRetcode.ERROR
    balance: float = 0.0
    equity: float = 0.0
    profit: float = 0.0
    margin: float = 0.0
    margin_free: float = 0.0
    margin_level: float = 0.0
    comment: str = ""


class TradeProvider(Protocol):
    """
    Protocol for trade execution providers.

    Any trading platform adapter should implement this protocol
    to provide trade execution capabilities.
    """

    def order_send(self, request: TradeRequest) -> TradeResult:
        """Execute a trade request."""
        ...

    def order_send_async(self, request: TradeRequest) -> TradeResult:
        """Execute a trade request asynchronously."""
        ...

    def order_check(self, request: TradeRequest) -> TradeCheckResult:
        """Check if a trade request is valid."""
        ...

    def get_symbol_info(self, symbol: str, property_name: str) -> Optional[float]:
        """Get symbol information."""
        ...

    def get_account_info(self, property_name: str) -> Optional[float]:
        """Get account information."""
        ...

    def position_select(self, symbol: str) -> bool:
        """Select position by symbol."""
        ...

    def position_select_by_ticket(self, ticket: int) -> bool:
        """Select position by ticket."""
        ...

    def position_get_integer(self, property_name: str) -> int:
        """Get integer position property."""
        ...

    def position_get_double(self, property_name: str) -> float:
        """Get double position property."""
        ...

    def position_get_string(self, property_name: str) -> str:
        """Get string position property."""
        ...

    def positions_total(self) -> int:
        """Get total number of open positions."""
        ...

    def position_get_symbol(self, index: int) -> str:
        """Get position symbol by index."""
        ...

    def order_select(self, ticket: int) -> bool:
        """Select order by ticket."""
        ...

    def is_stopped(self) -> bool:
        """Check if the program is stopped."""
        ...


class MT5TradeProvider:
    """
    Implementation of TradeProvider using MT5Client.

    Provides trade execution capabilities through MetaTrader 5.
    """

    def __init__(self, client):
        """
        Initialize MT5TradeProvider.

        Args:
            client: MT5Client instance for MT5 API access.
        """
        from apps.mt5.client import MT5Client

        self._client: MT5Client = client
        self._current_position: Optional[Any] = None
        self._current_order: Optional[Any] = None

    def order_send(self, request: TradeRequest) -> TradeResult:
        """Execute a trade request."""
        try:
            import MetaTrader5 as mt5

            # Convert TradeRequest to MT5 request format
            mt5_request = {
                "action": self._map_action(request.action),
                "magic": request.magic,
                "symbol": request.symbol,
                "volume": request.volume,
                "price": request.price,
                "stoplimit": request.stoplimit,
                "sl": request.sl,
                "tp": request.tp,
                "deviation": request.deviation,
                "type": self._map_order_type(request.type),
                "type_filling": self._map_filling_type(request.type_filling),
                "type_time": self._map_time_type(request.type_time),
                "comment": request.comment,
            }

            if request.position > 0:
                mt5_request["position"] = request.position

            if request.action in (TradeAction.MODIFY, TradeAction.REMOVE):
                mt5_request["order"] = request.order
            elif request.action == TradeAction.CLOSE_BY:
                mt5_request["position_by"] = request.position_by

            # Add expiration if specified
            if request.expiration:
                mt5_request["expiration"] = int(request.expiration.timestamp())

            # Send order
            result = mt5.order_send(mt5_request)

            if result is None:
                return TradeResult(
                    retcode=TradeRetcode.ERROR, comment="MT5 order_send returned None"
                )

            # Convert MT5 result to TradeResult
            return TradeResult(
                retcode=self._map_retcode(result.retcode),
                deal=result.deal,
                order=result.order,
                volume=result.volume,
                price=result.price,
                bid=result.bid,
                ask=result.ask,
                comment=result.comment,
                request_id=result.request_id,
                retcode_external=result.retcode_external,
            )

        except Exception as e:
            logger.error(f"Error sending order: {e}")
            return TradeResult(retcode=TradeRetcode.ERROR, comment=str(e))

    def order_send_async(self, request: TradeRequest) -> TradeResult:
        """Execute a trade request asynchronously."""
        # MT5 doesn't have true async, so we use the same method
        return self.order_send(request)

    def order_check(self, request: TradeRequest) -> TradeCheckResult:
        """Check if a trade request is valid."""
        try:
            import MetaTrader5 as mt5

            # Convert TradeRequest to MT5 request format
            mt5_request = {
                "action": self._map_action(request.action),
                "magic": request.magic,
                "symbol": request.symbol,
                "volume": request.volume,
                "price": request.price,
                "sl": request.sl,
                "tp": request.tp,
                "deviation": request.deviation,
                "type": self._map_order_type(request.type),
                "type_filling": self._map_filling_type(request.type_filling),
                "type_time": self._map_time_type(request.type_time),
            }

            # Check order
            result = mt5.order_check(mt5_request)

            if result is None:
                return TradeCheckResult(
                    retcode=TradeRetcode.ERROR, comment="MT5 order_check returned None"
                )

            # Convert MT5 result to TradeCheckResult
            return TradeCheckResult(
                retcode=self._map_retcode(result.retcode),
                balance=result.balance,
                equity=result.equity,
                profit=result.profit,
                margin=result.margin,
                margin_free=result.margin_free,
                margin_level=result.margin_level,
                comment=result.comment,
            )

        except Exception as e:
            logger.error(f"Error checking order: {e}")
            return TradeCheckResult(retcode=TradeRetcode.ERROR, comment=str(e))

    def get_symbol_info(self, symbol: str, property_name: str) -> Optional[float]:
        """Get symbol information."""
        try:
            import MetaTrader5 as mt5

            info = mt5.symbol_info(symbol)
            if info is None:
                return None

            return getattr(info, property_name.lower(), None)

        except Exception as e:
            logger.error(f"Error getting symbol info: {e}")
            return None

    def get_account_info(self, property_name: str) -> Optional[float]:
        """Get account information."""
        try:
            import MetaTrader5 as mt5

            info = mt5.account_info()
            if info is None:
                return None

            if property_name == "MARGIN_MODE":
                return float(info.margin_mode)

            return getattr(info, property_name.lower(), None)

        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None

    def position_select(self, symbol: str) -> bool:
        """Select position by symbol."""
        try:
            import MetaTrader5 as mt5

            positions = mt5.positions_get(symbol=symbol)
            if positions and len(positions) > 0:
                self._current_position = positions[0]
                return True
            self._current_position = None
            return False

        except Exception as e:
            logger.error(f"Error selecting position: {e}")
            return False

    def position_select_by_ticket(self, ticket: int) -> bool:
        """Select position by ticket."""
        try:
            import MetaTrader5 as mt5

            positions = mt5.positions_get(ticket=ticket)
            if positions and len(positions) > 0:
                self._current_position = positions[0]
                return True
            self._current_position = None
            return False

        except Exception as e:
            logger.error(f"Error selecting position by ticket: {e}")
            return False

    def position_get_integer(self, property_name: str) -> int:
        """Get integer position property."""
        if self._current_position is None:
            return 0

        return getattr(self._current_position, property_name.lower(), 0)

    def position_get_double(self, property_name: str) -> float:
        """Get double position property."""
        if self._current_position is None:
            return 0.0

        return getattr(self._current_position, property_name.lower(), 0.0)

    def position_get_string(self, property_name: str) -> str:
        """Get string position property."""
        if self._current_position is None:
            return ""

        return getattr(self._current_position, property_name.lower(), "")

    def positions_total(self) -> int:
        """Get total number of open positions."""
        try:
            import MetaTrader5 as mt5

            total = mt5.positions_total()
            return total if total is not None else 0

        except Exception as e:
            logger.error(f"Error getting positions total: {e}")
            return 0

    def position_get_symbol(self, index: int) -> str:
        """Get position symbol by index."""
        try:
            import MetaTrader5 as mt5

            positions = mt5.positions_get()
            if positions and 0 <= index < len(positions):
                return str(positions[index].symbol)
            return ""

        except Exception as e:
            logger.error(f"Error getting position symbol: {e}")
            return ""

    def order_select(self, ticket: int) -> bool:
        """Select order by ticket."""
        try:
            import MetaTrader5 as mt5

            orders = mt5.orders_get(ticket=ticket)
            if orders and len(orders) > 0:
                self._current_order = orders[0]
                return True
            self._current_order = None
            return False

        except Exception as e:
            logger.error(f"Error selecting order: {e}")
            return False

    def is_stopped(self) -> bool:
        """Check if the program is stopped."""
        # For MT5, we can check if terminal is connected
        return not self._client.is_connected()

    # Helper methods for mapping enums

    def _map_action(self, action: TradeAction) -> int:
        """Map TradeAction to MT5 action code."""
        import MetaTrader5 as mt5

        action_map = {
            TradeAction.DEAL: mt5.TRADE_ACTION_DEAL,
            TradeAction.PENDING: mt5.TRADE_ACTION_PENDING,
            TradeAction.SLTP: mt5.TRADE_ACTION_SLTP,
            TradeAction.MODIFY: mt5.TRADE_ACTION_MODIFY,
            TradeAction.REMOVE: mt5.TRADE_ACTION_REMOVE,
            TradeAction.CLOSE_BY: mt5.TRADE_ACTION_CLOSE_BY,
        }

        return int(action_map.get(action, mt5.TRADE_ACTION_DEAL))

    def _map_order_type(self, order_type: OrderType) -> int:
        """Map OrderType to MT5 order type code."""
        import MetaTrader5 as mt5

        type_map = {
            OrderType.BUY: mt5.ORDER_TYPE_BUY,
            OrderType.SELL: mt5.ORDER_TYPE_SELL,
            OrderType.BUY_LIMIT: mt5.ORDER_TYPE_BUY_LIMIT,
            OrderType.SELL_LIMIT: mt5.ORDER_TYPE_SELL_LIMIT,
            OrderType.BUY_STOP: mt5.ORDER_TYPE_BUY_STOP,
            OrderType.SELL_STOP: mt5.ORDER_TYPE_SELL_STOP,
            OrderType.BUY_STOP_LIMIT: mt5.ORDER_TYPE_BUY_STOP_LIMIT,
            OrderType.SELL_STOP_LIMIT: mt5.ORDER_TYPE_SELL_STOP_LIMIT,
            OrderType.CLOSE_BY: mt5.ORDER_TYPE_CLOSE_BY,
        }

        return int(type_map.get(order_type, mt5.ORDER_TYPE_BUY))

    def _map_filling_type(self, filling: OrderTypeFilling) -> int:
        """Map OrderTypeFilling to MT5 filling type code."""
        import MetaTrader5 as mt5

        filling_map = {
            OrderTypeFilling.FOK: mt5.ORDER_FILLING_FOK,
            OrderTypeFilling.IOC: mt5.ORDER_FILLING_IOC,
            OrderTypeFilling.RETURN: mt5.ORDER_FILLING_RETURN,
        }

        return int(filling_map.get(filling, mt5.ORDER_FILLING_FOK))

    def _map_time_type(self, time_type: OrderTypeTime) -> int:
        """Map OrderTypeTime to MT5 time type code."""
        import MetaTrader5 as mt5

        time_map = {
            OrderTypeTime.GTC: mt5.ORDER_TIME_GTC,
            OrderTypeTime.DAY: mt5.ORDER_TIME_DAY,
            OrderTypeTime.SPECIFIED: mt5.ORDER_TIME_SPECIFIED,
            OrderTypeTime.SPECIFIED_DAY: mt5.ORDER_TIME_SPECIFIED_DAY,
        }

        return int(time_map.get(time_type, mt5.ORDER_TIME_GTC))

    def _map_retcode(self, retcode: int) -> TradeRetcode:
        """Map MT5 retcode to TradeRetcode."""
        # Map common MT5 return codes
        retcode_map = {
            10009: TradeRetcode.DONE,
            10010: TradeRetcode.DONE_PARTIAL,
            10008: TradeRetcode.PLACED,
            10004: TradeRetcode.REQUOTE,
            10006: TradeRetcode.REJECT,
            10007: TradeRetcode.CANCEL,
            10011: TradeRetcode.ERROR,
            10012: TradeRetcode.TIMEOUT,
            10013: TradeRetcode.INVALID,
            10014: TradeRetcode.INVALID_VOLUME,
            10015: TradeRetcode.INVALID_PRICE,
            10016: TradeRetcode.INVALID_STOPS,
            10017: TradeRetcode.TRADE_DISABLED,
            10018: TradeRetcode.MARKET_CLOSED,
            10019: TradeRetcode.NO_MONEY,
            10020: TradeRetcode.PRICE_CHANGED,
            10021: TradeRetcode.PRICE_OFF,
            10022: TradeRetcode.INVALID_EXPIRATION,
            10023: TradeRetcode.ORDER_CHANGED,
            10024: TradeRetcode.TOO_MANY_REQUESTS,
            10025: TradeRetcode.NO_CHANGES,
            10026: TradeRetcode.SERVER_DISABLES_AT,
            10027: TradeRetcode.CLIENT_DISABLES_AT,
            10028: TradeRetcode.LOCKED,
            10029: TradeRetcode.FROZEN,
            10030: TradeRetcode.INVALID_FILL,
            10031: TradeRetcode.CONNECTION,
            10032: TradeRetcode.ONLY_REAL,
            10033: TradeRetcode.LIMIT_ORDERS,
            10034: TradeRetcode.LIMIT_VOLUME,
            10035: TradeRetcode.INVALID_ORDER,
            10036: TradeRetcode.POSITION_CLOSED,
            10038: TradeRetcode.CLOSE_ORDER_EXIST,
            10039: TradeRetcode.LIMIT_POSITIONS,
        }

        return retcode_map.get(retcode, TradeRetcode.ERROR)


class BacktestTradeProvider:
    """
    Implementation of TradeProvider for backtesting.

    Simulates trade execution with in-memory state management.
    """

    def __init__(self, initial_balance: float = 10000.0):
        """
        Initialize BacktestTradeProvider.

        Args:
            initial_balance: Starting account balance for simulation.
        """
        self._positions: Dict[int, Dict[str, Any]] = {}
        self._orders: Dict[int, Dict[str, Any]] = {}
        self._next_ticket = 1000
        self._current_position: Optional[Dict[str, Any]] = None
        self._current_order: Optional[Dict[str, Any]] = None

        # Account state
        self._balance = initial_balance
        self._equity = initial_balance
        self._margin = 0.0
        self._margin_free = initial_balance
        self._profit = 0.0

        # Symbol prices (for simulation)
        self._symbol_prices: Dict[str, Dict[str, float]] = {}

        self._stopped = False

    def set_symbol_price(self, symbol: str, bid: float, ask: float) -> None:
        """Set current prices for a symbol."""
        self._symbol_prices[symbol] = {"bid": bid, "ask": ask}

    def order_send(self, request: TradeRequest) -> TradeResult:
        """Execute a trade request (simulated)."""
        try:
            # Generate ticket
            ticket = self._next_ticket
            self._next_ticket += 1

            # Simulate execution based on action
            if request.action == TradeAction.DEAL:
                # Market execution
                return self._execute_market_order(request, ticket)
            elif request.action == TradeAction.PENDING:
                # Pending order
                return self._place_pending_order(request, ticket)
            elif request.action == TradeAction.SLTP:
                # Modify SL/TP
                return self._modify_sltp(request)
            elif request.action == TradeAction.REMOVE:
                # Remove pending order
                return self._remove_order(request)
            else:
                return TradeResult(
                    retcode=TradeRetcode.INVALID,
                    comment=f"Unsupported action: {request.action}",
                )

        except Exception as e:
            logger.error(f"Error in backtest order_send: {e}")
            return TradeResult(retcode=TradeRetcode.ERROR, comment=str(e))

    def _execute_market_order(self, request: TradeRequest, ticket: int) -> TradeResult:
        """Execute a market order."""
        # Get current price
        if request.symbol not in self._symbol_prices:
            return TradeResult(
                retcode=TradeRetcode.PRICE_OFF,
                comment=f"No price data for {request.symbol}",
            )

        prices = self._symbol_prices[request.symbol]

        # Determine execution price
        if request.type == OrderType.BUY:
            price = prices["ask"]
        elif request.type == OrderType.SELL:
            price = prices["bid"]
        else:
            return TradeResult(
                retcode=TradeRetcode.INVALID_ORDER,
                comment="Invalid order type for market execution",
            )

        # Check if closing position
        if request.position > 0 and request.position in self._positions:
            # Closing existing position
            position = self._positions[request.position]
            # Calculate profit
            if position["type"] == 0:  # BUY position
                profit = (
                    (price - position["price_open"]) * request.volume * 100000
                )  # Simplified
            else:  # SELL position
                profit = (position["price_open"] - price) * request.volume * 100000

            # Update account balance (realized profit)
            self._balance += profit
            # Equity equals balance when no open positions
            self._equity = self._balance

            # Remove position
            del self._positions[request.position]

            return TradeResult(
                retcode=TradeRetcode.DONE,
                deal=ticket,
                order=ticket,
                volume=request.volume,
                price=price,
                bid=prices["bid"],
                ask=prices["ask"],
                comment="Position closed",
            )

        # Opening new position
        position_data = {
            "ticket": ticket,
            "time": int(datetime.now().timestamp()),
            "type": 0 if request.type == OrderType.BUY else 1,
            "magic": request.magic,
            "identifier": ticket,
            "volume": request.volume,
            "price_open": price,
            "price_current": price,
            "sl": request.sl,
            "tp": request.tp,
            "profit": 0.0,
            "swap": 0.0,
            "symbol": request.symbol,
            "comment": request.comment,
            "external_id": "",
        }

        self._positions[ticket] = position_data

        return TradeResult(
            retcode=TradeRetcode.DONE,
            deal=ticket,
            order=ticket,
            volume=request.volume,
            price=price,
            bid=prices["bid"],
            ask=prices["ask"],
            comment="Position opened",
        )

    def _place_pending_order(self, request: TradeRequest, ticket: int) -> TradeResult:
        """Place a pending order."""
        order_data = {
            "ticket": ticket,
            "time_setup": int(datetime.now().timestamp()),
            "type": self._map_order_type_to_int(request.type),
            "state": 1,  # PLACED
            "magic": request.magic,
            "volume_initial": request.volume,
            "volume_current": request.volume,
            "price_open": request.price,
            "sl": request.sl,
            "tp": request.tp,
            "symbol": request.symbol,
            "comment": request.comment,
        }

        self._orders[ticket] = order_data

        return TradeResult(
            retcode=TradeRetcode.PLACED,
            order=ticket,
            volume=request.volume,
            price=request.price,
            comment="Pending order placed",
        )

    def _modify_sltp(self, request: TradeRequest) -> TradeResult:
        """Modify stop loss and take profit."""
        if request.position in self._positions:
            position = self._positions[request.position]
            position["sl"] = request.sl
            position["tp"] = request.tp

            return TradeResult(retcode=TradeRetcode.DONE, comment="SL/TP modified")

        return TradeResult(
            retcode=TradeRetcode.INVALID_ORDER, comment="Position not found"
        )

    def _remove_order(self, request: TradeRequest) -> TradeResult:
        """Remove a pending order."""
        if request.order in self._orders:
            del self._orders[request.order]
            return TradeResult(retcode=TradeRetcode.DONE, comment="Order removed")

        return TradeResult(
            retcode=TradeRetcode.INVALID_ORDER, comment="Order not found"
        )

    def order_send_async(self, request: TradeRequest) -> TradeResult:
        """Execute a trade request asynchronously (same as sync in backtest)."""
        return self.order_send(request)

    def order_check(self, request: TradeRequest) -> TradeCheckResult:
        """Check if a trade request is valid."""
        # In backtest, we always return success for simplicity
        return TradeCheckResult(
            retcode=TradeRetcode.DONE,
            balance=self._balance,
            equity=self._equity,
            profit=self._profit,
            margin=self._margin,
            margin_free=self._margin_free,
            margin_level=100.0 if self._margin > 0 else 0.0,
            comment="Check passed",
        )

    def get_symbol_info(self, symbol: str, property_name: str) -> Optional[float]:
        """Get symbol information."""
        if symbol not in self._symbol_prices:
            return None

        prices = self._symbol_prices[symbol]
        property_map = {
            "bid": prices["bid"],
            "ask": prices["ask"],
            "point": 0.00001,
            "digits": 5.0,
            "trade_tick_size": 0.00001,
            "trade_contract_size": 100000.0,
        }

        return property_map.get(property_name.lower())

    def get_account_info(self, property_name: str) -> Optional[float]:
        """Get account information."""
        property_map = {
            "MARGIN_MODE": 0.0,  # Netting
            "balance": self._balance,
            "equity": self._equity,
            "margin": self._margin,
            "margin_free": self._margin_free,
            "margin_level": 100.0 if self._margin > 0 else 0.0,
            "profit": self._profit,
        }

        return property_map.get(property_name)

    def position_select(self, symbol: str) -> bool:
        """Select position by symbol."""
        for position in self._positions.values():
            if position["symbol"] == symbol:
                self._current_position = position
                return True
        return False

    def position_select_by_ticket(self, ticket: int) -> bool:
        """Select position by ticket."""
        if ticket in self._positions:
            self._current_position = self._positions[ticket]
            return True
        return False

    def position_get_integer(self, property_name: str) -> int:
        """Get integer position property."""
        if self._current_position is None:
            return 0

        property_map = {
            "ticket": self._current_position.get("ticket", 0),
            "time": self._current_position.get("time", 0),
            "type": self._current_position.get("type", 0),
            "magic": self._current_position.get("magic", 0),
            "identifier": self._current_position.get("identifier", 0),
        }

        return int(property_map.get(property_name, 0))

    def position_get_double(self, property_name: str) -> float:
        """Get double position property."""
        if self._current_position is None:
            return 0.0

        property_map = {
            "volume": self._current_position.get("volume", 0.0),
            "price_open": self._current_position.get("price_open", 0.0),
            "price_current": self._current_position.get("price_current", 0.0),
            "sl": self._current_position.get("sl", 0.0),
            "tp": self._current_position.get("tp", 0.0),
            "profit": self._current_position.get("profit", 0.0),
            "swap": self._current_position.get("swap", 0.0),
        }

        return float(property_map.get(property_name, 0.0))

    def position_get_string(self, property_name: str) -> str:
        """Get string position property."""
        if self._current_position is None:
            return ""

        property_map = {
            "symbol": self._current_position.get("symbol", ""),
            "comment": self._current_position.get("comment", ""),
            "external_id": self._current_position.get("external_id", ""),
        }

        return str(property_map.get(property_name, ""))

    def positions_total(self) -> int:
        """Get total number of open positions."""
        return len(self._positions)

    def position_get_symbol(self, index: int) -> str:
        """Get position symbol by index."""
        positions = list(self._positions.values())
        if 0 <= index < len(positions):
            return str(positions[index]["symbol"])
        return ""

    def order_select(self, ticket: int) -> bool:
        """Select order by ticket."""
        if ticket in self._orders:
            self._current_order = self._orders[ticket]
            return True
        return False

    def is_stopped(self) -> bool:
        """Check if the program is stopped."""
        return self._stopped

    def stop(self) -> None:
        """Stop the backtest."""
        self._stopped = True

    def _map_order_type_to_int(self, order_type: OrderType) -> int:
        """Map OrderType to integer code."""
        type_map = {
            OrderType.BUY: 0,
            OrderType.SELL: 1,
            OrderType.BUY_LIMIT: 2,
            OrderType.SELL_LIMIT: 3,
            OrderType.BUY_STOP: 4,
            OrderType.SELL_STOP: 5,
            OrderType.BUY_STOP_LIMIT: 6,
            OrderType.SELL_STOP_LIMIT: 7,
        }
        return type_map.get(order_type, 0)


class Trade:
    """
    Class for executing trading operations.

    This class provides a clean interface to trading operations
    regardless of the underlying trading platform.

    Usage:
        # With a platform-specific provider
        provider = MT5TradeProvider()
        trade = Trade(provider)

        # Configure
        trade.set_expert_magic_number(12345)
        trade.set_deviation_in_points(10)

        # Execute trades
        if trade.buy(1.0, "EURUSD", sl=1.0950, tp=1.1050):
            print(f"Order placed: #{trade.result_order()}")
        else:
            print(f"Failed: {trade.result_retcode_description()}")
    """

    def __init__(self, provider: TradeProvider):
        """
        Initialize Trade.

        Args:
            provider: Platform-specific trade provider implementing
                     TradeProvider protocol.
        """
        self._provider = provider

        # Request and result structures
        self._request = TradeRequest()
        self._result = TradeResult()
        self._check_result = TradeCheckResult()

        # Configuration
        self._async_mode = False
        self._magic = 0
        self._deviation = 10
        self._type_filling = OrderTypeFilling.FOK
        self._log_level = LogLevel.ERRORS

        # Determine margin mode
        self._margin_mode = "netting"  # Can be "netting" or "hedging"
        self._set_margin_mode()

    def _set_margin_mode(self) -> None:
        """Set margin mode from account info."""
        try:
            mode = self._provider.get_account_info("MARGIN_MODE")
            if mode == 2:  # ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
                self._margin_mode = "hedging"
        except Exception:
            logger.warning("Failed to get account margin mode.")

    # Configuration methods

    def set_async_mode(self, mode: bool) -> None:
        """
        Set asynchronous trading mode.

        Args:
            mode: True for async mode, False for sync mode.
        """
        self._async_mode = mode

    def set_expert_magic_number(self, magic: int) -> None:
        """
        Set expert magic number.

        Args:
            magic: Magic number to identify trades.
        """
        self._magic = magic

    def set_deviation_in_points(self, deviation: int) -> None:
        """
        Set maximum price deviation in points.

        Args:
            deviation: Maximum price deviation.
        """
        self._deviation = deviation

    def set_type_filling(self, filling: OrderTypeFilling) -> None:
        """
        Set order filling type.

        Args:
            filling: Order filling type.
        """
        self._type_filling = filling

    def set_log_level(self, log_level: LogLevel) -> None:
        """
        Set logging level.

        Args:
            log_level: Logging level.
        """
        self._log_level = log_level

    # Request accessors

    def request_action(self) -> TradeAction:
        """Get request action."""
        return self._request.action

    def request_magic(self) -> int:
        """Get request magic number."""
        return self._request.magic

    def request_order(self) -> int:
        """Get request order ticket."""
        return self._request.order

    def request_position(self) -> int:
        """Get request position ticket."""
        return self._request.position

    def request_symbol(self) -> str:
        """Get request symbol."""
        return self._request.symbol

    def request_volume(self) -> float:
        """Get request volume."""
        return self._request.volume

    def request_price(self) -> float:
        """Get request price."""
        return self._request.price

    def request_sl(self) -> float:
        """Get request stop loss."""
        return self._request.sl

    def request_tp(self) -> float:
        """Get request take profit."""
        return self._request.tp

    def request_type(self) -> OrderType:
        """Get request order type."""
        return self._request.type

    def request_type_filling(self) -> OrderTypeFilling:
        """Get request filling type."""
        return self._request.type_filling

    def request_comment(self) -> str:
        """Get request comment."""
        return self._request.comment

    # Result accessors

    def result_retcode(self) -> TradeRetcode:
        """Get result return code."""
        return self._result.retcode

    def result_retcode_description(self) -> str:
        """Get result return code as string."""
        return self._format_retcode(self._result.retcode)

    def result_deal(self) -> int:
        """Get result deal ticket."""
        return self._result.deal

    def result_order(self) -> int:
        """Get result order ticket."""
        return self._result.order

    def result_volume(self) -> float:
        """Get result volume."""
        return self._result.volume

    def result_price(self) -> float:
        """Get result price."""
        return self._result.price

    def result_comment(self) -> str:
        """Get result comment."""
        return self._result.comment

    def result(self) -> TradeResult:
        """Get the complete trade result."""
        return self._result

    def request(self) -> TradeRequest:
        """Get the complete trade request."""
        return self._request

    # Check result accessors

    def check_result_retcode(self) -> TradeRetcode:
        """Get check result return code."""
        return self._check_result.retcode

    def check_result_balance(self) -> float:
        """Get check result balance."""
        return self._check_result.balance

    def check_result_margin(self) -> float:
        """Get check result margin."""
        return self._check_result.margin

    # Position operations (to be continued in next part)

    def _clear_structures(self) -> None:
        """Clear request, result, and check result structures."""
        self._request = TradeRequest()
        self._result = TradeResult()
        self._check_result = TradeCheckResult()

    def _is_stopped(self, function: str) -> bool:
        """
        Check if program is stopped.

        Args:
            function: Function name for logging.

        Returns:
            True if stopped, False otherwise.
        """
        if not self._provider.is_stopped():
            return False

        if self._log_level != LogLevel.NO:
            logger.warning(f"{function}: Program is stopped. Trading is disabled")

        self._result.retcode = TradeRetcode.CLIENT_DISABLES_AT
        return True

    def _is_hedging(self) -> bool:
        """Check if account is in hedging mode."""
        return self._margin_mode == "hedging"

    @staticmethod
    def _format_retcode(retcode: TradeRetcode) -> str:
        """Format return code as string."""
        descriptions = {
            TradeRetcode.DONE: "done",
            TradeRetcode.DONE_PARTIAL: "done partially",
            TradeRetcode.PLACED: "placed",
            TradeRetcode.REQUOTE: "requote",
            TradeRetcode.REJECT: "rejected",
            TradeRetcode.CANCEL: "canceled",
            TradeRetcode.ERROR: "common error",
            TradeRetcode.TIMEOUT: "timeout",
            TradeRetcode.INVALID: "invalid request",
            TradeRetcode.INVALID_VOLUME: "invalid volume",
            TradeRetcode.INVALID_PRICE: "invalid price",
            TradeRetcode.INVALID_STOPS: "invalid stops",
            TradeRetcode.TRADE_DISABLED: "trade disabled",
            TradeRetcode.MARKET_CLOSED: "market closed",
            TradeRetcode.NO_MONEY: "not enough money",
            TradeRetcode.PRICE_CHANGED: "price changed",
            TradeRetcode.PRICE_OFF: "off quotes",
            TradeRetcode.INVALID_EXPIRATION: "invalid expiration",
            TradeRetcode.ORDER_CHANGED: "order changed",
            TradeRetcode.TOO_MANY_REQUESTS: "too many requests",
            TradeRetcode.NO_CHANGES: "no changes",
            TradeRetcode.SERVER_DISABLES_AT: "auto trading disabled by server",
            TradeRetcode.CLIENT_DISABLES_AT: "auto trading disabled by client",
            TradeRetcode.LOCKED: "locked",
            TradeRetcode.FROZEN: "frozen",
            TradeRetcode.INVALID_FILL: "invalid fill",
            TradeRetcode.CONNECTION: "no connection",
            TradeRetcode.ONLY_REAL: "only real",
            TradeRetcode.LIMIT_ORDERS: "limit orders",
            TradeRetcode.LIMIT_VOLUME: "limit volume",
            TradeRetcode.INVALID_ORDER: "invalid order",
            TradeRetcode.POSITION_CLOSED: "position closed",
            TradeRetcode.CLOSE_ORDER_EXIST: "close order already exists",
            TradeRetcode.LIMIT_POSITIONS: "limit positions",
        }
        return descriptions.get(retcode, f"unknown retcode {retcode.value}")

    # Position operations

    def position_open(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
    ) -> bool:
        """
        Open a position.

        Args:
            symbol: Trading symbol.
            order_type: Order type (BUY or SELL).
            volume: Volume in lots.
            price: Execution price.
            sl: Stop loss price.
            tp: Take profit price.
            comment: Order comment.

        Returns:
            True if successful, False otherwise.
        """
        if self._is_stopped("position_open"):
            return False

        self._clear_structures()

        # Validate order type
        if order_type not in [OrderType.BUY, OrderType.SELL]:
            self._result.retcode = TradeRetcode.INVALID
            self._result.comment = "Invalid order type"
            return False

        # Build request
        self._request.action = TradeAction.DEAL
        self._request.symbol = symbol
        self._request.magic = self._magic
        self._request.volume = volume
        self._request.type = order_type
        self._request.price = price
        self._request.sl = sl
        self._request.tp = tp
        self._request.deviation = self._deviation
        self._request.type_filling = self._type_filling
        self._request.comment = comment

        # Execute
        return self._order_send()

    def position_modify(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
        sl: float = 0.0,
        tp: float = 0.0,
    ) -> bool:
        """
        Modify position stop loss and take profit.

        Args:
            symbol: Trading symbol (for netting mode).
            ticket: Position ticket (for hedging mode).
            sl: New stop loss price.
            tp: New take profit price.

        Returns:
            True if successful, False otherwise.
        """
        if self._is_stopped("position_modify"):
            return False

        # Select position
        if ticket is not None:
            if not self._provider.position_select_by_ticket(ticket):
                return False
            symbol = self._provider.position_get_string("symbol")
        elif symbol is not None:
            if not self._select_position(symbol):
                return False
            ticket = self._provider.position_get_integer("ticket")
        else:
            return False

        self._clear_structures()

        # Build request
        self._request.action = TradeAction.SLTP
        self._request.symbol = symbol
        self._request.magic = self._magic
        self._request.sl = sl
        self._request.tp = tp
        self._request.position = ticket

        # Execute
        return self._order_send()

    def position_close(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
        deviation: Optional[int] = None,
    ) -> bool:
        """
        Close a position.

        Args:
            symbol: Trading symbol (for netting mode).
            ticket: Position ticket (for hedging mode).
            deviation: Maximum price deviation.

        Returns:
            True if successful, False otherwise.
        """
        if self._is_stopped("position_close"):
            return False

        if deviation is None:
            deviation = self._deviation

        # Select position
        if ticket is not None:
            if not self._provider.position_select_by_ticket(ticket):
                return False
            symbol = self._provider.position_get_string("symbol")
        elif symbol is not None:
            if not self._select_position(symbol):
                return False
            ticket = self._provider.position_get_integer("ticket")
        else:
            return False

        self._clear_structures()

        # Determine opposite order type
        position_type = self._provider.position_get_integer("type")
        if position_type == 0:  # POSITION_TYPE_BUY
            order_type = OrderType.SELL
            price = self._provider.get_symbol_info(symbol, "bid") or 0.0
        else:
            order_type = OrderType.BUY
            price = self._provider.get_symbol_info(symbol, "ask") or 0.0

        volume = self._provider.position_get_double("volume")

        # Build request
        self._request.action = TradeAction.DEAL
        self._request.symbol = symbol
        self._request.volume = volume
        self._request.type = order_type
        self._request.price = price
        self._request.magic = self._magic
        self._request.deviation = deviation
        self._request.position = ticket
        self._request.type_filling = self._type_filling

        # Execute
        return self._order_send()

    def position_close_partial(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
        volume: float = 0.0,
        deviation: Optional[int] = None,
    ) -> bool:
        """
        Close part of a position (hedging mode only).

        Args:
            symbol: Trading symbol.
            ticket: Position ticket.
            volume: Volume to close.
            deviation: Maximum price deviation.

        Returns:
            True if successful, False otherwise.
        """
        if not self._is_hedging():
            return False

        if self._is_stopped("position_close_partial"):
            return False

        if deviation is None:
            deviation = self._deviation

        # Select position
        if ticket is not None:
            if not self._provider.position_select_by_ticket(ticket):
                return False
            symbol = self._provider.position_get_string("symbol")
        elif symbol is not None:
            if not self._select_position(symbol):
                return False
            ticket = self._provider.position_get_integer("ticket")
        else:
            return False

        self._clear_structures()

        # Determine opposite order type
        position_type = self._provider.position_get_integer("type")
        if position_type == 0:  # POSITION_TYPE_BUY
            order_type = OrderType.SELL
            price = self._provider.get_symbol_info(symbol, "bid") or 0.0
        else:
            order_type = OrderType.BUY
            price = self._provider.get_symbol_info(symbol, "ask") or 0.0

        # Check volume
        position_volume = self._provider.position_get_double("volume")
        if volume > position_volume:
            volume = position_volume

        # Build request
        self._request.action = TradeAction.DEAL
        self._request.symbol = symbol
        self._request.volume = volume
        self._request.type = order_type
        self._request.price = price
        self._request.magic = self._magic
        self._request.deviation = deviation
        self._request.position = ticket
        self._request.type_filling = self._type_filling

        # Execute
        return self._order_send()

    def position_close_by(self, ticket: int, ticket_by: int) -> bool:
        """
        Close position by opposite position (hedging mode only).

        Args:
            ticket: Position ticket to close.
            ticket_by: Opposite position ticket.

        Returns:
            True if successful, False otherwise.
        """
        if not self._is_hedging():
            return False

        if self._is_stopped("position_close_by"):
            return False

        self._clear_structures()

        # Build request
        self._request.action = TradeAction.CLOSE_BY
        self._request.position = ticket
        self._request.position_by = ticket_by
        self._request.magic = self._magic

        # Execute
        return self._order_send()

    # Order operations

    def order_open(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        limit_price: float,
        price: float,
        sl: float = 0.0,
        tp: float = 0.0,
        type_time: OrderTypeTime = OrderTypeTime.GTC,
        expiration: Optional[datetime] = None,
        comment: str = "",
    ) -> bool:
        """
        Place a pending order.

        Args:
            symbol: Trading symbol.
            order_type: Order type (LIMIT, STOP, etc.).
            volume: Volume in lots.
            limit_price: Limit price (for stop limit orders).
            price: Order price.
            sl: Stop loss price.
            tp: Take profit price.
            type_time: Order time type.
            expiration: Order expiration time.
            comment: Order comment.

        Returns:
            True if successful, False otherwise.
        """
        if self._is_stopped("order_open"):
            return False

        # Validate order type
        if order_type in [OrderType.BUY, OrderType.SELL]:
            self._result.retcode = TradeRetcode.INVALID
            self._result.comment = "Invalid order type"
            return False

        self._clear_structures()

        # Build request
        self._request.action = TradeAction.PENDING
        self._request.symbol = symbol
        self._request.magic = self._magic
        self._request.volume = volume
        self._request.type = order_type
        self._request.stoplimit = limit_price
        self._request.price = price
        self._request.sl = sl
        self._request.tp = tp
        self._request.type_time = type_time
        self._request.expiration = expiration
        self._request.type_filling = self._type_filling
        self._request.comment = comment

        # Execute
        return self._order_send()

    def order_modify(
        self,
        ticket: int,
        price: float,
        sl: float,
        tp: float,
        type_time: OrderTypeTime = OrderTypeTime.GTC,
        expiration: Optional[datetime] = None,
        stoplimit: float = 0.0,
    ) -> bool:
        """
        Modify a pending order.

        Args:
            ticket: Order ticket.
            price: New order price.
            sl: New stop loss.
            tp: New take profit.
            type_time: New time type.
            expiration: New expiration time.
            stoplimit: New stop limit price.

        Returns:
            True if successful, False otherwise.
        """
        if self._is_stopped("order_modify"):
            return False

        if not self._provider.order_select(ticket):
            return False

        self._clear_structures()

        # Build request
        self._request.action = TradeAction.MODIFY
        self._request.magic = self._magic
        self._request.order = ticket
        self._request.price = price
        self._request.stoplimit = stoplimit
        self._request.sl = sl
        self._request.tp = tp
        self._request.type_time = type_time
        self._request.expiration = expiration

        # Execute
        return self._order_send()

    def order_delete(self, ticket: int) -> bool:
        """
        Delete a pending order.

        Args:
            ticket: Order ticket.

        Returns:
            True if successful, False otherwise.
        """
        if self._is_stopped("order_delete"):
            return False

        self._clear_structures()

        # Build request
        self._request.action = TradeAction.REMOVE
        self._request.magic = self._magic
        self._request.order = ticket

        # Execute
        return self._order_send()

    # Convenience methods

    def buy(
        self,
        volume: float,
        symbol: Optional[str] = None,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
    ) -> bool:
        """
        Open a buy position.

        Args:
            volume: Volume in lots.
            symbol: Trading symbol.
            price: Execution price (0 = market price).
            sl: Stop loss price.
            tp: Take profit price.
            comment: Order comment.

        Returns:
            True if successful, False otherwise.
        """
        if volume <= 0:
            self._result.retcode = TradeRetcode.INVALID_VOLUME
            return False

        if symbol is None:
            symbol = "EURUSD"  # Default symbol

        if price == 0.0:
            price_from_symbol = self._provider.get_symbol_info(symbol, "ask")
            if price_from_symbol is not None:
                price = price_from_symbol
            else:
                price = 0.0

        return self.position_open(symbol, OrderType.BUY, volume, price, sl, tp, comment)

    def sell(
        self,
        volume: float,
        symbol: Optional[str] = None,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
    ) -> bool:
        """
        Open a sell position.

        Args:
            volume: Volume in lots.
            symbol: Trading symbol.
            price: Execution price (0 = market price).
            sl: Stop loss price.
            tp: Take profit price.
            comment: Order comment.

        Returns:
            True if successful, False otherwise.
        """
        if volume <= 0:
            self._result.retcode = TradeRetcode.INVALID_VOLUME
            return False

        if symbol is None:
            symbol = "EURUSD"  # Default symbol

        if price == 0.0:
            price_from_symbol = self._provider.get_symbol_info(symbol, "bid")
            if price_from_symbol is not None:
                price = price_from_symbol
            else:
                price = 0.0

        return self.position_open(
            symbol, OrderType.SELL, volume, price, sl, tp, comment
        )

    def buy_limit(
        self,
        volume: float,
        price: float,
        symbol: Optional[str] = None,
        sl: float = 0.0,
        tp: float = 0.0,
        type_time: OrderTypeTime = OrderTypeTime.GTC,
        expiration: Optional[datetime] = None,
        comment: str = "",
    ) -> bool:
        """Place a buy limit order."""
        if volume <= 0:
            self._result.retcode = TradeRetcode.INVALID_VOLUME
            return False

        if symbol is None:
            symbol = "EURUSD"

        return self.order_open(
            symbol,
            OrderType.BUY_LIMIT,
            volume,
            0.0,
            price,
            sl,
            tp,
            type_time,
            expiration,
            comment,
        )

    def buy_stop(
        self,
        volume: float,
        price: float,
        symbol: Optional[str] = None,
        sl: float = 0.0,
        tp: float = 0.0,
        type_time: OrderTypeTime = OrderTypeTime.GTC,
        expiration: Optional[datetime] = None,
        comment: str = "",
    ) -> bool:
        """Place a buy stop order."""
        if volume <= 0:
            self._result.retcode = TradeRetcode.INVALID_VOLUME
            return False

        if symbol is None:
            symbol = "EURUSD"

        return self.order_open(
            symbol,
            OrderType.BUY_STOP,
            volume,
            0.0,
            price,
            sl,
            tp,
            type_time,
            expiration,
            comment,
        )

    def sell_limit(
        self,
        volume: float,
        price: float,
        symbol: Optional[str] = None,
        sl: float = 0.0,
        tp: float = 0.0,
        type_time: OrderTypeTime = OrderTypeTime.GTC,
        expiration: Optional[datetime] = None,
        comment: str = "",
    ) -> bool:
        """Place a sell limit order."""
        if volume <= 0:
            self._result.retcode = TradeRetcode.INVALID_VOLUME
            return False

        if symbol is None:
            symbol = "EURUSD"

        return self.order_open(
            symbol,
            OrderType.SELL_LIMIT,
            volume,
            0.0,
            price,
            sl,
            tp,
            type_time,
            expiration,
            comment,
        )

    def sell_stop(
        self,
        volume: float,
        price: float,
        symbol: Optional[str] = None,
        sl: float = 0.0,
        tp: float = 0.0,
        type_time: OrderTypeTime = OrderTypeTime.GTC,
        expiration: Optional[datetime] = None,
        comment: str = "",
    ) -> bool:
        """Place a sell stop order."""
        if volume <= 0:
            self._result.retcode = TradeRetcode.INVALID_VOLUME
            return False

        if symbol is None:
            symbol = "EURUSD"

        return self.order_open(
            symbol,
            OrderType.SELL_STOP,
            volume,
            0.0,
            price,
            sl,
            tp,
            type_time,
            expiration,
            comment,
        )

    # Helper methods

    def _select_position(self, symbol: str) -> bool:
        """Select position depending on netting/hedging mode."""
        if self._is_hedging():
            # In hedging mode, find position by symbol and magic
            total = self._provider.positions_total()
            for i in range(total):
                pos_symbol = self._provider.position_get_symbol(i)
                if pos_symbol == symbol:
                    self._provider.position_select(symbol)
                    pos_magic = self._provider.position_get_integer("magic")
                    if pos_magic == self._magic:
                        return True
            return False
        else:
            # In netting mode, simple select by symbol
            return self._provider.position_select(symbol)

    def _order_send(self) -> bool:
        """Execute trade request."""
        # Execute (async or sync)
        if self._async_mode:
            self._result = self._provider.order_send_async(self._request)
        else:
            self._result = self._provider.order_send(self._request)

        # Log if needed
        success = self._result.retcode in [
            TradeRetcode.DONE,
            TradeRetcode.DONE_PARTIAL,
            TradeRetcode.PLACED,
        ]

        if success:
            if self._log_level == LogLevel.ALL:
                logger.info(f"Trade executed: {self._format_request()}")
                logger.info(f"Result: {self._format_retcode(self._result.retcode)}")
        else:
            if self._log_level != LogLevel.NO:
                logger.error(f"Trade failed: {self._format_request()}")
                logger.error(f"Error: {self._format_retcode(self._result.retcode)}")

        return success

    def _format_request(self) -> str:
        """Format request as string for logging."""
        r = self._request
        if r.action in (TradeAction.DEAL, TradeAction.PENDING):
            return f"{r.type.value} {r.volume} {r.symbol} at {r.price}"
        elif r.action == TradeAction.SLTP:
            return f"modify {r.symbol} sl={r.sl} tp={r.tp}"
        elif r.action == TradeAction.MODIFY:
            return f"modify order #{r.order}"
        elif r.action == TradeAction.REMOVE:
            return f"delete order #{r.order}"
        elif r.action == TradeAction.CLOSE_BY:
            return f"close #{r.position} by #{r.position_by}"
        return "unknown action"

    def __repr__(self) -> str:
        """Return string representation of Trade."""
        return (
            f"Trade(magic={self._magic}, "
            f"deviation={self._deviation}, "
            f"filling={self._type_filling.value}, "
            f"mode={self._margin_mode})"
        )
