"""
CHistoryOrderInfo class (MT5-specific).

This module mirrors the MQL5 Standard Library CHistoryOrderInfo interface and
order/grouping for MT5 usage.
Reference: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/chistoryorderinfo
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import MetaTrader5 as mt5


class CHistoryOrderInfo:
    """
    Class for handling history order properties in MT5.

    This class is based on the MQL5 Standard Library CHistoryOrderInfo API.
    """

    def __init__(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> None:
        """Initialize."""
        self._order: dict[str, Any] = {}
        self._date_from = date_from
        self._date_to = date_to

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _set_order(self, order: Any) -> bool:
        if order is None:
            self._order = {}
            return False
        if hasattr(order, "_asdict"):
            self._order = order._asdict()
        elif isinstance(order, dict):
            self._order = order
        else:
            self._order = {}
            return False
        return True

    def _order_time(self, key: str) -> datetime:
        value = self._order.get(key)
        if isinstance(value, datetime):
            return value
        if value:
            return datetime.fromtimestamp(int(value))
        return datetime.fromtimestamp(0)

    def _cached(self, default: Any, *keys: str) -> Any:
        for key in keys:
            if key in self._order and self._order[key] is not None:
                return self._order[key]
        return default

    def _info_integer(self, prop: Optional[int]) -> Optional[int]:
        if prop is None:
            return None
        if hasattr(mt5, "history_order_get_integer"):
            value = mt5.history_order_get_integer(prop)
        return int(value) if value is not None else None
        return None

    def _info_double(self, prop: Optional[int]) -> Optional[float]:
        if prop is None:
            return None
        if hasattr(mt5, "history_order_get_double"):
            value = mt5.history_order_get_double(prop)
        return float(value) if value is not None else None
        return None

    def _info_string(self, prop: Optional[int]) -> Optional[str]:
        if prop is None:
            return None
        if hasattr(mt5, "history_order_get_string"):
            value = mt5.history_order_get_string(prop)
        return str(value) if value is not None else None
        return None

    def _int_prop(self, const_name: str, default: int, *keys: str) -> int:
        prop = getattr(mt5, const_name, None)
        value = self._info_integer(prop)
        if value is not None:
            return int(value)
        return int(self._cached(default, *keys))

    def _double_prop(self, const_name: str, default: float, *keys: str) -> float:
        prop = getattr(mt5, const_name, None)
        value = self._info_double(prop)
        if value is not None:
            return float(value)
        return float(self._cached(default, *keys))

    def _string_prop(self, const_name: str, default: str, *keys: str) -> str:
        prop = getattr(mt5, const_name, None)
        value = self._info_string(prop)
        if value is not None:
            return str(value)
        return str(self._cached(default, *keys))

    # ---------------------------------------------------------------------
    # Class methods by groups (per MQL5 CHistoryOrderInfo documentation)
    # ---------------------------------------------------------------------
    # Access to integer type properties
    def TimeSetup(self) -> datetime:
        """Get the time of order placement."""
        return self._order_time("time_setup")

    def TimeSetupMsc(self) -> int:
        """Receive the time of placing an order in milliseconds since 01.01.1970."""
        return self._int_prop("ORDER_TIME_SETUP_MSC", 0, "time_setup_msc")

    def OrderType(self) -> int:
        """Get the order type."""
        return self._int_prop("ORDER_TYPE", 0, "type")

    def OrderTypeDescription(self) -> str:
        """Get the order type as a string."""
        value = self.OrderType()
        mapping = {
            getattr(mt5, "ORDER_TYPE_BUY", None): "Buy",
            getattr(mt5, "ORDER_TYPE_SELL", None): "Sell",
            getattr(mt5, "ORDER_TYPE_BUY_LIMIT", None): "Buy Limit",
            getattr(mt5, "ORDER_TYPE_SELL_LIMIT", None): "Sell Limit",
            getattr(mt5, "ORDER_TYPE_BUY_STOP", None): "Buy Stop",
            getattr(mt5, "ORDER_TYPE_SELL_STOP", None): "Sell Stop",
            getattr(mt5, "ORDER_TYPE_BUY_STOP_LIMIT", None): "Buy Stop Limit",
            getattr(mt5, "ORDER_TYPE_SELL_STOP_LIMIT", None): "Sell Stop Limit",
            getattr(mt5, "ORDER_TYPE_CLOSE_BY", None): "Close By",
        }
        return mapping.get(value, "Unknown")

    def State(self) -> int:
        """Get the order state."""
        return self._int_prop("ORDER_STATE", 0, "state")

    def StateDescription(self) -> str:
        """Get the order state as a string."""
        value = self.State()
        mapping = {
            getattr(mt5, "ORDER_STATE_STARTED", None): "Started",
            getattr(mt5, "ORDER_STATE_PLACED", None): "Placed",
            getattr(mt5, "ORDER_STATE_CANCELED", None): "Canceled",
            getattr(mt5, "ORDER_STATE_PARTIAL", None): "Partial",
            getattr(mt5, "ORDER_STATE_FILLED", None): "Filled",
            getattr(mt5, "ORDER_STATE_REJECTED", None): "Rejected",
            getattr(mt5, "ORDER_STATE_EXPIRED", None): "Expired",
            getattr(mt5, "ORDER_STATE_REQUEST_ADD", None): "Request Add",
            getattr(mt5, "ORDER_STATE_REQUEST_MODIFY", None): "Request Modify",
            getattr(mt5, "ORDER_STATE_REQUEST_CANCEL", None): "Request Cancel",
        }
        return mapping.get(value, "Unknown")

    def TimeExpiration(self) -> datetime:
        """Get the time of order expiration."""
        return self._order_time("time_expiration")

    def TimeDone(self) -> datetime:
        """Get the time of order execution or cancellation."""
        return self._order_time("time_done")

    def TimeDoneMsc(self) -> int:
        """Receive order execution or cancellation time in milliseconds since 01.01.1970."""
        return self._int_prop("ORDER_TIME_DONE_MSC", 0, "time_done_msc")

    def TypeFilling(self) -> int:
        """Get the type of order execution by remainder."""
        return self._int_prop("ORDER_TYPE_FILLING", 0, "type_filling")

    def TypeFillingDescription(self) -> str:
        """Get the type of order execution by remainder as a string."""
        value = self.TypeFilling()
        mapping = {
            getattr(mt5, "ORDER_FILLING_FOK", None): "FOK",
            getattr(mt5, "ORDER_FILLING_IOC", None): "IOC",
            getattr(mt5, "ORDER_FILLING_RETURN", None): "Return",
        }
        return mapping.get(value, "Unknown")

    def TypeTime(self) -> int:
        """Get the type of order at the time of the expiration."""
        return self._int_prop("ORDER_TYPE_TIME", 0, "type_time")

    def TypeTimeDescription(self) -> str:
        """Get the order type by expiration time as a string."""
        value = self.TypeTime()
        mapping = {
            getattr(mt5, "ORDER_TIME_GTC", None): "GTC",
            getattr(mt5, "ORDER_TIME_DAY", None): "Day",
            getattr(mt5, "ORDER_TIME_SPECIFIED", None): "Specified",
            getattr(mt5, "ORDER_TIME_SPECIFIED_DAY", None): "Specified Day",
        }
        return mapping.get(value, "Unknown")

    def Magic(self) -> int:
        """Get the ID of expert that placed the order."""
        return self._int_prop("ORDER_MAGIC", 0, "magic")

    def PositionId(self) -> int:
        """Get the ID of position."""
        return self._int_prop("ORDER_POSITION_ID", 0, "position_id")

    # Access to double type properties
    def VolumeInitial(self) -> float:
        """Get the initial volume of order."""
        return self._double_prop("ORDER_VOLUME_INITIAL", 0.0, "volume_initial")

    def VolumeCurrent(self) -> float:
        """Get the unfilled volume of order."""
        return self._double_prop("ORDER_VOLUME_CURRENT", 0.0, "volume_current")

    def PriceOpen(self) -> float:
        """Get the order price."""
        return self._double_prop("ORDER_PRICE_OPEN", 0.0, "price_open")

    def StopLoss(self) -> float:
        """Get the order's Stop Loss."""
        return self._double_prop("ORDER_SL", 0.0, "sl")

    def TakeProfit(self) -> float:
        """Get the order's Take Profit."""
        return self._double_prop("ORDER_TP", 0.0, "tp")

    def PriceCurrent(self) -> float:
        """Get the current price by order symbol."""
        return self._double_prop("ORDER_PRICE_CURRENT", 0.0, "price_current")

    def PriceStopLimit(self) -> float:
        """Get the price of a Limit order."""
        return self._double_prop("ORDER_PRICE_STOPLIMIT", 0.0, "price_stoplimit")

    # Access to text properties
    def Symbol(self) -> str:
        """Get the order symbol."""
        return self._string_prop("ORDER_SYMBOL", "", "symbol")

    def Comment(self) -> str:
        """Get the order comment."""
        return self._string_prop("ORDER_COMMENT", "", "comment")

    # Access to MQL5 API functions
    def InfoInteger(self, prop: Any) -> Optional[int]:
        """Get the value of specified integer type property."""
        if isinstance(prop, int) and hasattr(mt5, "history_order_get_integer"):
            value = mt5.history_order_get_integer(prop)
            return int(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return int(value) if value is not None else None
        return None

    def InfoDouble(self, prop: Any) -> Optional[float]:
        """Get the value of specified double type property."""
        if isinstance(prop, int) and hasattr(mt5, "history_order_get_double"):
            value = mt5.history_order_get_double(prop)
            return float(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return float(value) if value is not None else None
        return None

    def InfoString(self, prop: Any) -> Optional[str]:
        """Get value of specified string type property."""
        if isinstance(prop, int) and hasattr(mt5, "history_order_get_string"):
            value = mt5.history_order_get_string(prop)
            return str(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return str(value) if value is not None else None
        return None

    # Selection
    def Ticket(self, ticket: Optional[int] = None) -> int:
        """Get the ticket/selects the order."""
        if ticket is None:
            return int(self._cached(0, "ticket"))
        orders = mt5.history_orders_get(ticket=ticket)
        if not orders:
            return 0
        if self._set_order(orders[0]):
            return int(self._cached(0, "ticket"))
        return 0

    def SelectByIndex(self, index: int) -> bool:
        """Select the order by index."""
        if self._date_from is None or self._date_to is None:
            return False
        orders = mt5.history_orders_get(self._date_from, self._date_to)
        if not orders:
            return False
        if index < 0 or index >= len(orders):
            return False
        return self._set_order(orders[index])
