"""
MT5Validator - Validation utilities for MetaTrader 5.

This module provides comprehensive validation functionality for trading parameters,
ensuring data integrity and preventing invalid operations.
"""

from datetime import datetime, timedelta
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import MetaTrader5 as mt5

from apps.logger import logger
from apps.mt5.data import TimeFrame


class OrderType(IntEnum):
    """Enumeration representing MT5 order types."""

    BUY = mt5.ORDER_TYPE_BUY
    SELL = mt5.ORDER_TYPE_SELL
    BUY_LIMIT = mt5.ORDER_TYPE_BUY_LIMIT
    SELL_LIMIT = mt5.ORDER_TYPE_SELL_LIMIT
    BUY_STOP = mt5.ORDER_TYPE_BUY_STOP
    SELL_STOP = mt5.ORDER_TYPE_SELL_STOP
    BUY_STOP_LIMIT = mt5.ORDER_TYPE_BUY_STOP_LIMIT
    SELL_STOP_LIMIT = mt5.ORDER_TYPE_SELL_STOP_LIMIT


class MT5Validator:
    """
    Validation utilities class.

    Provides comprehensive validation methods for:
    - Trading symbols
    - Volumes and prices
    - Stop loss and take profit levels
    - Order types and parameters
    - Timeframes and date ranges
    - Trade requests
    - Credentials and margins
    """

    def __init__(self, client=None):
        """
        Initialize MT5Validator instance.

        Args:
            client: MT5Client instance for connection management (optional)
        """
        self.client = client
        self._validation_rules = self._initialize_rules()

        logger.info("MT5Validator initialized")

    def _initialize_rules(self) -> Dict[str, Any]:
        """Initialize validation rules."""
        return {
            "volume": {
                "min": 0.01,
                "max": 100.0,
                "step": 0.01,
            },
            "price": {
                "min": 0.0,
                "max": 1000000.0,
            },
            "deviation": {
                "min": 0,
                "max": 100,
            },
            "magic": {
                "min": 0,
                "max": 2147483647,  # Max int32
            },
        }

    def _get_validation_dispatcher(
        self,
    ) -> Dict[str, Callable[..., Tuple[bool, str]]]:
        """
        Get dispatch dictionary mapping validation types to their handlers.

        Returns:
            Dictionary mapping validation types to handler functions
        """
        return {
            "symbol": lambda v, **kw: self._validate_symbol(v),
            "volume": lambda v, **kw: self._validate_volume(v, kw.get("symbol")),
            "price": lambda v, **kw: self._validate_price(v, kw.get("symbol")),
            "stop_loss": lambda v, **kw: self._validate_stop_loss(
                v, kw.get("entry_price"), kw.get("order_type"), kw.get("symbol")
            ),
            "take_profit": lambda v, **kw: self._validate_take_profit(
                v, kw.get("entry_price"), kw.get("order_type"), kw.get("symbol")
            ),
            "order_type": lambda v, **kw: self._validate_order_type(v),
            "magic": lambda v, **kw: self._validate_magic(v),
            "deviation": lambda v, **kw: self._validate_deviation(v),
            "expiration": lambda v, **kw: self._validate_expiration(v),
            "timeframe": lambda v, **kw: self._validate_timeframe(v),
            "date_range": lambda v, **kw: self._validate_date_range(
                v, kw.get("end_date")
            ),
            "trade_request": lambda v, **kw: self._validate_trade_request(v),
            "credentials": lambda v, **kw: self._validate_credentials(v),
            "margin": lambda v, **kw: self._validate_margin(v),
            "ticket": lambda v, **kw: self._validate_ticket(v),
        }

    def validate(self, validation_type: str, value: Any, **kwargs) -> Tuple[bool, str]:
        """
        Master validation method that routes to specific validators.

        Args:
            validation_type: Type of validation to perform
                           ('symbol', 'volume', 'price', 'stop_loss', 'take_profit',
                            'order_type', 'magic', 'deviation', 'expiration',
                            'timeframe', 'date_range', 'trade_request', 'credentials',
                            'margin', 'ticket')
            value: Value to validate
            **kwargs: Additional parameters for specific validators

        Returns:
            Tuple of (is_valid, error_message)

        Examples:
            >>> valid, msg = validator.validate('symbol', 'EURUSD')
            >>> valid, msg = validator.validate('volume', 0.1, symbol='EURUSD')
            >>> valid, msg = validator.validate('price', 1.1000, symbol='EURUSD')
        """
        try:
            dispatcher = self._get_validation_dispatcher()
            validator_func = dispatcher.get(validation_type)

            if validator_func is None:
                return False, f"Unknown validation type: {validation_type}"

            return validator_func(value, **kwargs)

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, str(e)

    def _validate_symbol(self, symbol: str) -> Tuple[bool, str]:
        """
        Validate trading symbol.

        Args:
            symbol: Symbol name

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not symbol or not isinstance(symbol, str):
                return False, "Symbol must be a non-empty string"

            # Check if symbol exists
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return False, f"Symbol '{symbol}' not found"

            # Check if symbol is visible
            if not symbol_info.visible and not mt5.symbol_select(symbol, True):
                return False, f"Symbol '{symbol}' cannot be selected"

            return True, "Symbol is valid"

        except Exception as e:
            return False, f"Symbol validation error: {e}"

    def _validate_volume_basic(self, volume: float) -> Tuple[bool, str]:
        """
        Validate basic volume constraints.

        Args:
            volume: Trade volume in lots

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(volume, (int, float)):
            return False, "Volume must be a number"

        if volume <= 0:
            return False, "Volume must be positive"

        return True, ""

    def _validate_volume_symbol_limits(
        self, volume: float, symbol_info: Any
    ) -> Tuple[bool, str]:
        """
        Validate volume against symbol-specific limits.

        Args:
            volume: Trade volume in lots
            symbol_info: Symbol info object from MT5

        Returns:
            Tuple of (is_valid, error_message)
        """
        if volume < symbol_info.volume_min:
            return (
                False,
                f"Volume {volume} below minimum {symbol_info.volume_min}",
            )

        if volume > symbol_info.volume_max:
            return (
                False,
                f"Volume {volume} above maximum {symbol_info.volume_max}",
            )

        return True, ""

    def _validate_volume_step(
        self, volume: float, symbol_info: Any
    ) -> Tuple[bool, str]:
        """
        Validate volume step alignment.

        Args:
            volume: Trade volume in lots
            symbol_info: Symbol info object from MT5

        Returns:
            Tuple of (is_valid, error_message)
        """
        if symbol_info.volume_step > 0:
            remainder = (volume - symbol_info.volume_min) % symbol_info.volume_step
            if remainder > 0.0001:  # Small tolerance for floating point
                return (
                    False,
                    f"Volume {volume} not aligned with step {symbol_info.volume_step}",
                )
        return True, ""

    def _validate_volume(
        self, volume: float, symbol: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate trade volume.

        Args:
            volume: Trade volume in lots
            symbol: Trading symbol (for symbol-specific limits)

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            valid, msg = self._validate_volume_basic(volume)
            if not valid:
                return False, msg

            # If symbol provided, check symbol-specific limits
            if symbol:
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is None:
                    return False, f"Cannot get info for symbol '{symbol}'"

                valid, msg = self._validate_volume_symbol_limits(volume, symbol_info)
                if not valid:
                    return False, msg

                valid, msg = self._validate_volume_step(volume, symbol_info)
                if not valid:
                    return False, msg

            return True, "Volume is valid"

        except Exception as e:
            return False, f"Volume validation error: {e}"

    def _validate_price(
        self, price: float, symbol: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate price value.

        Args:
            price: Price value
            symbol: Trading symbol

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not isinstance(price, (int, float)):
                return False, "Price must be a number"

            if price <= 0:
                return False, "Price must be positive"

            # Check general price range
            rules = self._validation_rules["price"]
            if price < rules["min"] or price > rules["max"]:
                return False, f"Price {price} outside valid range"

            # Symbol-specific validation
            if symbol:
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is None:
                    return False, f"Cannot get info for symbol '{symbol}'"

                # Check tick size alignment
                if symbol_info.trade_tick_size > 0:
                    remainder = price % symbol_info.trade_tick_size
                    if remainder > 0.00001:  # Tolerance
                        return (
                            False,
                            f"Price {price} not aligned with tick size {symbol_info.trade_tick_size}",
                        )

            return True, "Price is valid"

        except Exception as e:
            return False, f"Price validation error: {e}"

    def _convert_order_type_to_int(
        self, order_type: Union[str, int]
    ) -> Tuple[bool, int, str]:
        """
        Convert order type string to integer value.

        Args:
            order_type: Order type (string or int)

        Returns:
            Tuple of (success, order_type_int, error_message)
        """
        if isinstance(order_type, int):
            return True, order_type, ""
        try:
            return True, OrderType[order_type.upper()].value, ""
        except KeyError:
            return False, 0, f"Invalid order type: {order_type}"

    def _validate_price_relationship(
        self,
        level_price: float,
        entry_price: float,
        order_type: int,
        level_name: str,
        is_stop_loss: bool,
    ) -> Tuple[bool, str]:
        """
        Validate price relationship between level (SL/TP) and entry price.

        Args:
            level_price: Stop loss or take profit price
            entry_price: Entry price
            order_type: Order type as integer
            level_name: Name of level being validated ('stop loss' or 'take profit')
            is_stop_loss: True if validating stop loss, False for take profit

        Returns:
            Tuple of (is_valid, error_message)
        """
        buy_orders = [
            mt5.ORDER_TYPE_BUY,
            mt5.ORDER_TYPE_BUY_LIMIT,
            mt5.ORDER_TYPE_BUY_STOP,
        ]
        sell_orders = [
            mt5.ORDER_TYPE_SELL,
            mt5.ORDER_TYPE_SELL_LIMIT,
            mt5.ORDER_TYPE_SELL_STOP,
        ]

        if order_type in buy_orders:
            if is_stop_loss:
                if level_price >= entry_price:
                    return False, "Stop loss for BUY must be below entry price"
            else:
                if level_price <= entry_price:
                    return False, "Take profit for BUY must be above entry price"
        elif order_type in sell_orders:
            if is_stop_loss:
                if level_price <= entry_price:
                    return False, "Stop loss for SELL must be above entry price"
            else:
                if level_price >= entry_price:
                    return False, "Take profit for SELL must be below entry price"

        return True, ""

    def _validate_minimum_distance(
        self, level_price: float, entry_price: float, symbol: str, level_name: str
    ) -> Tuple[bool, str]:
        """
        Validate minimum distance from entry price based on symbol's stop level.

        Args:
            level_price: Stop loss or take profit price
            entry_price: Entry price
            symbol: Trading symbol
            level_name: Name of level being validated

        Returns:
            Tuple of (is_valid, error_message)
        """
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info and symbol_info.trade_stops_level > 0:
            min_distance = symbol_info.trade_stops_level * symbol_info.point
            actual_distance = abs(entry_price - level_price)
            if actual_distance < min_distance:
                return (
                    False,
                    f"{level_name.title()} too close to entry (min: {min_distance:.5f})",
                )
        return True, ""

    def _validate_stop_loss(
        self,
        stop_loss: float,
        entry_price: Optional[float] = None,
        order_type: Optional[Union[str, int]] = None,
        symbol: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Validate stop loss level.

        Args:
            stop_loss: Stop loss price
            entry_price: Entry price
            order_type: Order type
            symbol: Trading symbol

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if stop_loss == 0:
                return True, "No stop loss (valid)"

            # Validate price format
            valid, msg = self._validate_price(stop_loss, symbol)
            if not valid:
                return False, f"Invalid stop loss price: {msg}"

            # Check relationship with entry price if both provided
            if entry_price is not None and order_type is not None:
                success, order_type_int, error = self._convert_order_type_to_int(
                    order_type
                )
                if not success:
                    return False, error

                valid, msg = self._validate_price_relationship(
                    stop_loss, entry_price, order_type_int, "stop loss", True
                )
                if not valid:
                    return False, msg

            # Check minimum stop level if symbol and entry provided
            if symbol and entry_price:
                valid, msg = self._validate_minimum_distance(
                    stop_loss, entry_price, symbol, "stop loss"
                )
                if not valid:
                    return False, msg

            return True, "Stop loss is valid"

        except Exception as e:
            return False, f"Stop loss validation error: {e}"

    def _validate_take_profit(
        self,
        take_profit: float,
        entry_price: Optional[float] = None,
        order_type: Optional[Union[str, int]] = None,
        symbol: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Validate take profit level.

        Args:
            take_profit: Take profit price
            entry_price: Entry price
            order_type: Order type
            symbol: Trading symbol

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if take_profit == 0:
                return True, "No take profit (valid)"

            # Validate price format
            valid, msg = self._validate_price(take_profit, symbol)
            if not valid:
                return False, f"Invalid take profit price: {msg}"

            # Check relationship with entry price if both provided
            if entry_price is not None and order_type is not None:
                success, order_type_int, error = self._convert_order_type_to_int(
                    order_type
                )
                if not success:
                    return False, error

                valid, msg = self._validate_price_relationship(
                    take_profit, entry_price, order_type_int, "take profit", False
                )
                if not valid:
                    return False, msg

            # Check minimum stop level if symbol and entry provided
            if symbol and entry_price:
                valid, msg = self._validate_minimum_distance(
                    take_profit, entry_price, symbol, "take profit"
                )
                if not valid:
                    return False, msg

            return True, "Take profit is valid"

        except Exception as e:
            return False, f"Take profit validation error: {e}"

    def _validate_order_type(self, order_type: Union[str, int]) -> Tuple[bool, str]:
        """
        Validate order type.

        Args:
            order_type: Order type (string or MT5 constant)

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if isinstance(order_type, str):
                try:
                    OrderType[order_type.upper()]
                    return True, "Order type is valid"
                except KeyError:
                    return False, f"Invalid order type string: {order_type}"

            elif isinstance(order_type, int):
                valid_types = [
                    mt5.ORDER_TYPE_BUY,
                    mt5.ORDER_TYPE_SELL,
                    mt5.ORDER_TYPE_BUY_LIMIT,
                    mt5.ORDER_TYPE_SELL_LIMIT,
                    mt5.ORDER_TYPE_BUY_STOP,
                    mt5.ORDER_TYPE_SELL_STOP,
                    mt5.ORDER_TYPE_BUY_STOP_LIMIT,
                    mt5.ORDER_TYPE_SELL_STOP_LIMIT,
                ]
                if order_type in valid_types:
                    return True, "Order type is valid"
                else:
                    return False, f"Invalid order type constant: {order_type}"

            else:
                return False, "Order type must be string or integer"

        except Exception as e:
            return False, f"Order type validation error: {e}"

    def _validate_magic(self, magic: int) -> Tuple[bool, str]:
        """
        Validate magic number.

        Args:
            magic: Magic number

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not isinstance(magic, int):
                return False, "Magic number must be an integer"

            rules = self._validation_rules["magic"]
            if magic < rules["min"] or magic > rules["max"]:
                return False, f"Magic number {magic} outside valid range"

            return True, "Magic number is valid"

        except Exception as e:
            return False, f"Magic validation error: {e}"

    def _validate_deviation(self, deviation: int) -> Tuple[bool, str]:
        """
        Validate price deviation.

        Args:
            deviation: Price deviation in points

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not isinstance(deviation, int):
                return False, "Deviation must be an integer"

            rules = self._validation_rules["deviation"]
            if deviation < rules["min"] or deviation > rules["max"]:
                return False, f"Deviation {deviation} outside valid range"

            return True, "Deviation is valid"

        except Exception as e:
            return False, f"Deviation validation error: {e}"

    def _validate_expiration(self, expiration: datetime) -> Tuple[bool, str]:
        """
        Validate order expiration time.

        Args:
            expiration: Expiration datetime

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not isinstance(expiration, datetime):
                return False, "Expiration must be a datetime object"

            if expiration <= datetime.now():
                return False, "Expiration must be in the future"

            # Check if expiration is too far in future (e.g., > 1 year)
            max_future = datetime.now() + timedelta(days=365)
            if expiration > max_future:
                return False, "Expiration too far in the future (max 1 year)"

            return True, "Expiration is valid"

        except Exception as e:
            return False, f"Expiration validation error: {e}"

    def _validate_timeframe(
        self, timeframe: Union[str, int, TimeFrame]
    ) -> Tuple[bool, str]:
        """
        Validate timeframe.

        Args:
            timeframe: Timeframe (string, enum, or MT5 constant)

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if isinstance(timeframe, TimeFrame):
                return True, "Timeframe is valid"

            elif isinstance(timeframe, str):
                try:
                    TimeFrame[timeframe.upper()]
                    return True, "Timeframe is valid"
                except KeyError:
                    return False, f"Invalid timeframe string: {timeframe}"

            elif isinstance(timeframe, int):
                valid_timeframes = [
                    mt5.TIMEFRAME_M1,
                    mt5.TIMEFRAME_M5,
                    mt5.TIMEFRAME_M15,
                    mt5.TIMEFRAME_M30,
                    mt5.TIMEFRAME_H1,
                    mt5.TIMEFRAME_H4,
                    mt5.TIMEFRAME_D1,
                    mt5.TIMEFRAME_W1,
                    mt5.TIMEFRAME_MN1,
                ]
                if timeframe in valid_timeframes:
                    return True, "Timeframe is valid"
                else:
                    return False, f"Invalid timeframe constant: {timeframe}"

            else:
                return False, "Timeframe must be string, enum, or integer"

        except Exception as e:
            return False, f"Timeframe validation error: {e}"

    def _validate_date_range(
        self, start_date: datetime, end_date: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        Validate date range.

        Args:
            start_date: Start date
            end_date: End date (optional)

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not isinstance(start_date, datetime):
                return False, "Start date must be a datetime object"

            # Check if start is not too far in past (e.g., > 10 years)
            min_past = datetime.now() - timedelta(days=3650)
            if start_date < min_past:
                return False, "Start date too far in the past (max 10 years)"

            if end_date:
                if not isinstance(end_date, datetime):
                    return False, "End date must be a datetime object"

                if end_date <= start_date:
                    return False, "End date must be after start date"

                if end_date > datetime.now():
                    return False, "End date cannot be in the future"

            return True, "Date range is valid"

        except Exception as e:
            return False, f"Date range validation error: {e}"

    def _validate_required_fields(
        self, request: Dict, required_fields: List[str]
    ) -> Tuple[bool, str]:
        """
        Validate that all required fields are present in request.

        Args:
            request: Trade request dictionary
            required_fields: List of required field names

        Returns:
            Tuple of (is_valid, error_message)
        """
        for field in required_fields:
            if field not in request:
                return False, f"Missing required field: {field}"
        return True, ""

    def _validate_trade_request_core_fields(self, request: Dict) -> Tuple[bool, str]:
        """
        Validate core required fields of trade request.

        Args:
            request: Trade request dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        required_fields = ["action", "symbol", "volume", "type"]
        valid, msg = self._validate_required_fields(request, required_fields)
        if not valid:
            return False, msg

        # Validate symbol
        valid, msg = self._validate_symbol(request["symbol"])
        if not valid:
            return False, f"Invalid symbol: {msg}"

        # Validate volume
        valid, msg = self._validate_volume(request["volume"], request["symbol"])
        if not valid:
            return False, f"Invalid volume: {msg}"

        # Validate order type
        valid, msg = self._validate_order_type(request["type"])
        if not valid:
            return False, f"Invalid order type: {msg}"

        return True, ""

    def _validate_optional_price(self, request: Dict) -> Tuple[bool, str]:
        """Validate optional price field."""
        if "price" in request:
            valid, msg = self._validate_price(request["price"], request["symbol"])
            if not valid:
                return False, f"Invalid price: {msg}"
        return True, ""

    def _validate_optional_stop_loss(self, request: Dict) -> Tuple[bool, str]:
        """Validate optional stop loss field."""
        if "sl" in request and request["sl"] > 0:
            valid, msg = self._validate_stop_loss(
                request["sl"],
                request.get("price"),
                request["type"],
                request["symbol"],
            )
            if not valid:
                return False, f"Invalid stop loss: {msg}"
        return True, ""

    def _validate_optional_take_profit(self, request: Dict) -> Tuple[bool, str]:
        """Validate optional take profit field."""
        if "tp" in request and request["tp"] > 0:
            valid, msg = self._validate_take_profit(
                request["tp"],
                request.get("price"),
                request["type"],
                request["symbol"],
            )
            if not valid:
                return False, f"Invalid take profit: {msg}"
        return True, ""

    def _validate_optional_magic(self, request: Dict) -> Tuple[bool, str]:
        """Validate optional magic field."""
        if "magic" in request:
            valid, msg = self._validate_magic(request["magic"])
            if not valid:
                return False, f"Invalid magic: {msg}"
        return True, ""

    def _validate_optional_deviation(self, request: Dict) -> Tuple[bool, str]:
        """Validate optional deviation field."""
        if "deviation" in request:
            valid, msg = self._validate_deviation(request["deviation"])
            if not valid:
                return False, f"Invalid deviation: {msg}"
        return True, ""

    def _validate_trade_request_optional_fields(
        self, request: Dict
    ) -> Tuple[bool, str]:
        """
        Validate optional fields of trade request.

        Args:
            request: Trade request dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        validators = [
            self._validate_optional_price,
            self._validate_optional_stop_loss,
            self._validate_optional_take_profit,
            self._validate_optional_magic,
            self._validate_optional_deviation,
        ]

        for validator in validators:
            valid, msg = validator(request)
            if not valid:
                return False, msg

        return True, ""

    def _validate_trade_request(self, request: Dict) -> Tuple[bool, str]:
        """
        Validate complete trade request.

        Args:
            request: Trade request dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            valid, msg = self._validate_trade_request_core_fields(request)
            if not valid:
                return False, msg

            valid, msg = self._validate_trade_request_optional_fields(request)
            if not valid:
                return False, msg

            return True, "Trade request is valid"

        except Exception as e:
            return False, f"Trade request validation error: {e}"

    def _validate_credentials(self, credentials: Dict) -> Tuple[bool, str]:
        """
        Validate MT5 credentials.

        Args:
            credentials: Dictionary with login, password, server

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            required_fields = ["login", "password", "server"]
            for field in required_fields:
                if field not in credentials:
                    return False, f"Missing credential field: {field}"

            # Validate login
            if not isinstance(credentials["login"], int) or credentials["login"] <= 0:
                return False, "Login must be a positive integer"

            # Validate password
            if (
                not isinstance(credentials["password"], str)
                or len(credentials["password"]) == 0
            ):
                return False, "Password must be a non-empty string"

            # Validate server
            if (
                not isinstance(credentials["server"], str)
                or len(credentials["server"]) == 0
            ):
                return False, "Server must be a non-empty string"

            return True, "Credentials are valid"

        except Exception as e:
            return False, f"Credentials validation error: {e}"

    def _validate_margin(self, margin_required: float) -> Tuple[bool, str]:
        """
        Validate if sufficient margin is available.

        Args:
            margin_required: Required margin amount

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not isinstance(margin_required, (int, float)):
                return False, "Margin must be a number"

            if margin_required < 0:
                return False, "Margin cannot be negative"

            # Check account margin
            account_info = mt5.account_info()
            if account_info is None:
                return False, "Cannot get account information"

            free_margin = account_info.margin_free

            if margin_required > free_margin:
                return (
                    False,
                    f"Insufficient margin (required: {margin_required:.2f}, available: {free_margin:.2f})",
                )

            return True, "Sufficient margin available"

        except Exception as e:
            return False, f"Margin validation error: {e}"

    def _validate_ticket(self, ticket: int) -> Tuple[bool, str]:
        """
        Validate ticket number.

        Args:
            ticket: Ticket number

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not isinstance(ticket, int):
                return False, "Ticket must be an integer"

            if ticket <= 0:
                return False, "Ticket must be positive"

            return True, "Ticket is valid"

        except Exception as e:
            return False, f"Ticket validation error: {e}"

    def validate_multiple(
        self, validations: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Perform batch validation.

        Args:
            validations: List of validation dicts with 'type', 'value', and optional params

        Returns:
            Tuple of (all_valid, list of error messages)

        Examples:
            >>> validations = [
            ...     {'type': 'symbol', 'value': 'EURUSD'},
            ...     {'type': 'volume', 'value': 0.1, 'symbol': 'EURUSD'},
            ...     {'type': 'price', 'value': 1.1000}
            ... ]
            >>> all_valid, errors = validator.validate_multiple(validations)
        """
        errors = []

        try:
            for i, validation in enumerate(validations):
                validation_type = validation.get("type")
                value = validation.get("value")

                if not validation_type:
                    errors.append(f"Validation {i}: Missing type")
                    continue

                if value is None:
                    errors.append(f"Validation {i}: Missing value")
                    continue

                # Extract additional parameters
                params = {
                    k: v for k, v in validation.items() if k not in ["type", "value"]
                }

                # Perform validation
                valid, msg = self.validate(validation_type, value, **params)

                if not valid:
                    errors.append(f"Validation {i} ({validation_type}): {msg}")

            all_valid = len(errors) == 0
            return all_valid, errors

        except Exception as e:
            logger.error(f"Batch validation error: {e}")
            return False, [str(e)]

    def get_validation_rules(self) -> Dict[str, Any]:
        """
        Get current validation rules.

        Returns:
            Dictionary with validation rules

        Examples:
            >>> rules = validator.get_validation_rules()
            >>> print(rules['volume']['min'])
        """
        return self._validation_rules.copy()

    def update_validation_rule(self, rule_type: str, rule_name: str, value: Any):
        """
        Update a validation rule.

        Args:
            rule_type: Type of rule ('volume', 'price', etc.)
            rule_name: Specific rule name ('min', 'max', etc.)
            value: New value

        Examples:
            >>> validator.update_validation_rule('volume', 'min', 0.001)
        """
        if rule_type in self._validation_rules:
            if rule_name in self._validation_rules[rule_type]:
                self._validation_rules[rule_type][rule_name] = value
                logger.info(f"Updated rule: {rule_type}.{rule_name} = {value}")
            else:
                logger.warning(f"Rule name '{rule_name}' not found in '{rule_type}'")
        else:
            logger.warning(f"Rule type '{rule_type}' not found")
