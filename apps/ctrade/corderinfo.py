"""
COrderInfo class (MT5-specific).

This module mirrors the MQL5 Standard Library COrderInfo interface and
order/grouping for MT5 usage.
Reference: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/corderinfo
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import MetaTrader5 as mt5


class COrderInfo:
    """
    Class for handling order properties in MT5.

    This class is based on the MQL5 Standard Library COrderInfo API.
    """

    def __init__(self) -> None:
        """Initialize."""
        self._order: dict[str, Any] = {}

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
        if hasattr(mt5, "order_get_integer"):
            value = mt5.order_get_integer(prop)
        return int(value) if value is not None else None
        return None

    def _info_double(self, prop: Optional[int]) -> Optional[float]:
        if prop is None:
            return None
        if hasattr(mt5, "order_get_double"):
            value = mt5.order_get_double(prop)
        return float(value) if value is not None else None
        return None

    def _info_string(self, prop: Optional[int]) -> Optional[str]:
        if prop is None:
            return None
        if hasattr(mt5, "order_get_string"):
            value = mt5.order_get_string(prop)
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
    # Class methods by groups (per MQL5 COrderInfo documentation)
    # ---------------------------------------------------------------------
    # Access to integer type properties
    def Ticket(self) -> int:
        """Get the ticket number."""
        return self._int_prop("ORDER_TICKET", 0, "ticket")

    def TimeSetup(self) -> datetime:
        """Get the order setup time."""
        return self._order_time("time_setup")

    def TimeSetupMsc(self) -> int:
        """Get the order setup time in milliseconds."""
        return self._int_prop("ORDER_TIME_SETUP_MSC", 0, "time_setup_msc")

    def TimeExpiration(self) -> datetime:
        """Get the order expiration time."""
        return self._order_time("time_expiration")

    def TimeDone(self) -> datetime:
        """Get the order completion time."""
        return self._order_time("time_done")

    def TimeDoneMsc(self) -> int:
        """Get the order completion time in milliseconds."""
        return self._int_prop("ORDER_TIME_DONE_MSC", 0, "time_done_msc")

    def Type(self) -> int:
        """Get the order type."""
        return self._int_prop("ORDER_TYPE", 0, "type")

    def State(self) -> int:
        """Get the order state."""
        return self._int_prop("ORDER_STATE", 0, "state")

    def TypeTime(self) -> int:
        """Get the order expiration type."""
        return self._int_prop("ORDER_TYPE_TIME", 0, "type_time")

    def TypeFilling(self) -> int:
        """Get the order filling type."""
        return self._int_prop("ORDER_TYPE_FILLING", 0, "type_filling")

    def Magic(self) -> int:
        """Get the magic number."""
        return self._int_prop("ORDER_MAGIC", 0, "magic")

    def PositionId(self) -> int:
        """Get the position ID."""
        return self._int_prop("ORDER_POSITION_ID", 0, "position_id")

    def PositionById(self) -> int:
        """Get the opposite position ID (close by)."""
        return self._int_prop("ORDER_POSITION_BY_ID", 0, "position_by_id")

    # Access to double type properties
    def VolumeInitial(self) -> float:
        """Get the initial volume of the order."""
        return self._double_prop("ORDER_VOLUME_INITIAL", 0.0, "volume_initial")

    def VolumeCurrent(self) -> float:
        """Get the current volume of the order."""
        return self._double_prop("ORDER_VOLUME_CURRENT", 0.0, "volume_current")

    def PriceOpen(self) -> float:
        """Get the open price of the order."""
        return self._double_prop("ORDER_PRICE_OPEN", 0.0, "price_open")

    def PriceCurrent(self) -> float:
        """Get the current price of the order."""
        return self._double_prop("ORDER_PRICE_CURRENT", 0.0, "price_current")

    def PriceStopLimit(self) -> float:
        """Get the Stop Limit order price."""
        return self._double_prop("ORDER_PRICE_STOPLIMIT", 0.0, "price_stoplimit")

    def StopLoss(self) -> float:
        """Get the Stop Loss value."""
        return self._double_prop("ORDER_SL", 0.0, "sl")

    def TakeProfit(self) -> float:
        """Get the Take Profit value."""
        return self._double_prop("ORDER_TP", 0.0, "tp")

    # Access to text properties
    def Symbol(self) -> str:
        """Get the order symbol."""
        return self._string_prop("ORDER_SYMBOL", "", "symbol")

    def Comment(self) -> str:
        """Get the order comment."""
        return self._string_prop("ORDER_COMMENT", "", "comment")

    def ExternalId(self) -> str:
        """Get the external ID."""
        return self._string_prop("ORDER_EXTERNAL_ID", "", "external_id")

    # Access to MQL5 API functions
    def InfoInteger(self, prop: Any) -> Optional[int]:
        """Get the value of specified integer type property."""
        if isinstance(prop, int) and hasattr(mt5, "order_get_integer"):
            value = mt5.order_get_integer(prop)
            return int(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return int(value) if value is not None else None
        return None

    def InfoDouble(self, prop: Any) -> Optional[float]:
        """Get the value of specified double type property."""
        if isinstance(prop, int) and hasattr(mt5, "order_get_double"):
            value = mt5.order_get_double(prop)
            return float(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return float(value) if value is not None else None
        return None

    def InfoString(self, prop: Any) -> Optional[str]:
        """Get the value of specified string type property."""
        if isinstance(prop, int) and hasattr(mt5, "order_get_string"):
            value = mt5.order_get_string(prop)
            return str(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return str(value) if value is not None else None
        return None

    # Access to order state (helpers)
    def TypeDescription(self) -> str:
        """Get the order type as a string."""
        value = self.Type()
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

    def TypeTimeDescription(self) -> str:
        """Get the order expiration type as a string."""
        value = self.TypeTime()
        mapping = {
            getattr(mt5, "ORDER_TIME_GTC", None): "GTC",
            getattr(mt5, "ORDER_TIME_DAY", None): "Day",
            getattr(mt5, "ORDER_TIME_SPECIFIED", None): "Specified",
            getattr(mt5, "ORDER_TIME_SPECIFIED_DAY", None): "Specified Day",
        }
        return mapping.get(value, "Unknown")

    def TypeFillingDescription(self) -> str:
        """Get the order filling type as a string."""
        value = self.TypeFilling()
        mapping = {
            getattr(mt5, "ORDER_FILLING_FOK", None): "FOK",
            getattr(mt5, "ORDER_FILLING_IOC", None): "IOC",
            getattr(mt5, "ORDER_FILLING_RETURN", None): "Return",
        }
        return mapping.get(value, "Unknown")

    # Selection
    def Select(self, ticket: int) -> bool:
        """Select order by ticket."""
        if hasattr(mt5, "order_select"):
            ok = mt5.order_select(ticket)
            if ok:
                return self._set_order(mt5.order_get(ticket))
            return False
        return False

    def SelectByIndex(self, index: int) -> bool:
        """Select order by index in the orders list."""
        orders = mt5.orders_get()
        if not orders:
            return False
        if index < 0 or index >= len(orders):
            return False
        return self._set_order(orders[index])

    def Total(self) -> int:
        """Get the number of orders."""
        orders = mt5.orders_get()
        if orders is None:
            return 0
        return len(orders)
