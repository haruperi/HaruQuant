"""
CPositionInfo class (MT5-specific).

This module mirrors the MQL5 Standard Library CPositionInfo interface and
order/grouping for MT5 usage.
Reference: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cpositioninfo
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import MetaTrader5 as mt5


class CPositionInfo:
    """
    Class for handling position properties in MT5.

    This class is based on the MQL5 Standard Library CPositionInfo API.
    """

    def __init__(self) -> None:
        """Initialize."""
        self._position: dict[str, Any] = {}
        self._stored_state: dict[str, Any] = {}

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _set_position(self, position: Any) -> bool:
        if position is None:
            self._position = {}
            return False
        if hasattr(position, "_asdict"):
            self._position = position._asdict()
        elif isinstance(position, dict):
            self._position = position
        else:
            self._position = {}
            return False
        return True

    def _pos_time(self, key: str) -> datetime:
        value = self._position.get(key)
        if isinstance(value, datetime):
            return value
        if value:
            return datetime.fromtimestamp(int(value))
        return datetime.fromtimestamp(0)

    def _cached(self, default: Any, *keys: str) -> Any:
        for key in keys:
            if key in self._position and self._position[key] is not None:
                return self._position[key]
        return default

    def _info_integer(self, prop: Optional[int]) -> Optional[int]:
        if prop is None:
            return None
        if hasattr(mt5, "position_get_integer"):
            value = mt5.position_get_integer(prop)
        return int(value) if value is not None else None
        return None

    def _info_double(self, prop: Optional[int]) -> Optional[float]:
        if prop is None:
            return None
        if hasattr(mt5, "position_get_double"):
            value = mt5.position_get_double(prop)
        return float(value) if value is not None else None
        return None

    def _info_string(self, prop: Optional[int]) -> Optional[str]:
        if prop is None:
            return None
        if hasattr(mt5, "position_get_string"):
            value = mt5.position_get_string(prop)
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
    # Class methods by groups (per MQL5 CPositionInfo documentation)
    # ---------------------------------------------------------------------
    # Access to integer type properties
    def Time(self) -> datetime:
        """Get the time of position opening."""
        return self._pos_time("time")

    def TimeMsc(self) -> int:
        """Receive the time of position opening in milliseconds since 01.01.1970."""
        return self._int_prop("POSITION_TIME_MSC", 0, "time_msc")

    def TimeUpdate(self) -> datetime:
        """Receive the time of position changing in seconds since 01.01.1970."""
        return self._pos_time("time_update")

    def TimeUpdateMsc(self) -> int:
        """Receive the time of position changing in milliseconds since 01.01.1970."""
        return self._int_prop("POSITION_TIME_UPDATE_MSC", 0, "time_update_msc")

    def PositionType(self) -> int:
        """Get the position type."""
        return self._int_prop("POSITION_TYPE", 0, "type")

    def TypeDescription(self) -> str:
        """Get the position type as a string."""
        value = self.PositionType()
        mapping = {
            getattr(mt5, "POSITION_TYPE_BUY", None): "Buy",
            getattr(mt5, "POSITION_TYPE_SELL", None): "Sell",
        }
        return mapping.get(value, "Unknown")

    def Magic(self) -> int:
        """Get the ID of expert that opened the position."""
        return self._int_prop("POSITION_MAGIC", 0, "magic")

    def Identifier(self) -> int:
        """Get the ID of position."""
        return self._int_prop("POSITION_IDENTIFIER", 0, "identifier")

    # Access to double type properties
    def Volume(self) -> float:
        """Get the volume of position."""
        return self._double_prop("POSITION_VOLUME", 0.0, "volume")

    def PriceOpen(self) -> float:
        """Get the price of position opening."""
        return self._double_prop("POSITION_PRICE_OPEN", 0.0, "price_open")

    def StopLoss(self) -> float:
        """Get the price of position's Stop Loss."""
        return self._double_prop("POSITION_SL", 0.0, "sl")

    def TakeProfit(self) -> float:
        """Get the price of position's Take Profit."""
        return self._double_prop("POSITION_TP", 0.0, "tp")

    def PriceCurrent(self) -> float:
        """Get the current price by position symbol."""
        return self._double_prop("POSITION_PRICE_CURRENT", 0.0, "price_current")

    def Commission(self) -> float:
        """Get the amount of commission by position."""
        return self._double_prop("POSITION_COMMISSION", 0.0, "commission")

    def Swap(self) -> float:
        """Get the amount of swap by position."""
        return self._double_prop("POSITION_SWAP", 0.0, "swap")

    def Profit(self) -> float:
        """Get the amount of current profit by position."""
        return self._double_prop("POSITION_PROFIT", 0.0, "profit")

    # Access to text properties
    def Symbol(self) -> str:
        """Get the name of position symbol."""
        return self._string_prop("POSITION_SYMBOL", "", "symbol")

    def Comment(self) -> str:
        """Get the comment of the position."""
        return self._string_prop("POSITION_COMMENT", "", "comment")

    # Access to MQL5 API functions
    def InfoInteger(self, prop: Any) -> Optional[int]:
        """Get the value of specified integer type property."""
        if isinstance(prop, int) and hasattr(mt5, "position_get_integer"):
            value = mt5.position_get_integer(prop)
            return int(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return int(value) if value is not None else None
        return None

    def InfoDouble(self, prop: Any) -> Optional[float]:
        """Get the value of specified double type property."""
        if isinstance(prop, int) and hasattr(mt5, "position_get_double"):
            value = mt5.position_get_double(prop)
            return float(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return float(value) if value is not None else None
        return None

    def InfoString(self, prop: Any) -> Optional[str]:
        """Get the value of specified string type property."""
        if isinstance(prop, int) and hasattr(mt5, "position_get_string"):
            value = mt5.position_get_string(prop)
            return str(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return str(value) if value is not None else None
        return None

    # Selection
    def Select(self, symbol: str) -> bool:
        """Select the position."""
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return False
        return self._set_position(positions[0])

    def SelectByIndex(self, index: int) -> bool:
        """Select the position by index."""
        positions = mt5.positions_get()
        if not positions:
            return False
        if index < 0 or index >= len(positions):
            return False
        return self._set_position(positions[index])

    def SelectByMagic(self, symbol: str, magic: int) -> bool:
        """Select a position with the specified symbol name and magic number."""
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return False
        for pos in positions:
            data = pos._asdict() if hasattr(pos, "_asdict") else pos
            if int(data.get("magic", 0)) == int(magic):
                return self._set_position(pos)
        return False

    def SelectByTicket(self, ticket: int) -> bool:
        """Select the position by ticket."""
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return False
        return self._set_position(positions[0])

    # State
    def StoreState(self) -> None:
        """Save the position parameters."""
        self._stored_state = dict(self._position)

    def CheckState(self) -> bool:
        """Check the current parameters against the saved parameters."""
        if not self._stored_state:
            return False
        return self._stored_state == self._position
