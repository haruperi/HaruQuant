"""
CDealInfo class (MT5-specific).

This module mirrors the MQL5 Standard Library CDealInfo interface and
order/grouping for MT5 usage.
Reference: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/cdealinfo
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import MetaTrader5 as mt5


class CDealInfo:
    """
    Class for handling deal properties in MT5.

    This class is based on the MQL5 Standard Library CDealInfo API.
    """

    def __init__(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> None:
        """Initialize."""
        self._deal: dict[str, Any] = {}
        self._date_from = date_from
        self._date_to = date_to

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _set_deal(self, deal: Any) -> bool:
        if deal is None:
            self._deal = {}
            return False
        if hasattr(deal, "_asdict"):
            self._deal = deal._asdict()
        elif isinstance(deal, dict):
            self._deal = deal
        else:
            self._deal = {}
            return False
        return True

    def _deal_time(self, key: str) -> datetime:
        value = self._deal.get(key)
        if isinstance(value, datetime):
            return value
        if value:
            return datetime.fromtimestamp(int(value))
        return datetime.fromtimestamp(0)

    def _cached(self, default: Any, *keys: str) -> Any:
        for key in keys:
            if key in self._deal and self._deal[key] is not None:
                return self._deal[key]
        return default

    def _info_integer(self, prop: Optional[int]) -> Optional[int]:
        if prop is None:
            return None
        if hasattr(mt5, "history_deal_get_integer"):
            value = mt5.history_deal_get_integer(prop)
        return int(value) if value is not None else None
        return None

    def _info_double(self, prop: Optional[int]) -> Optional[float]:
        if prop is None:
            return None
        if hasattr(mt5, "history_deal_get_double"):
            value = mt5.history_deal_get_double(prop)
        return float(value) if value is not None else None
        return None

    def _info_string(self, prop: Optional[int]) -> Optional[str]:
        if prop is None:
            return None
        if hasattr(mt5, "history_deal_get_string"):
            value = mt5.history_deal_get_string(prop)
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
    # Class methods by groups (per MQL5 CDealInfo documentation)
    # ---------------------------------------------------------------------
    # Access to integer type properties
    def Ticket(self) -> int:
        """Get the ticket of a deal."""
        return self._int_prop("DEAL_TICKET", 0, "ticket")

    def Order(self) -> int:
        """Get the ticket of the order a deal was executed for."""
        return self._int_prop("DEAL_ORDER", 0, "order")

    def Time(self) -> datetime:
        """Get the time of deal."""
        return self._deal_time("time")

    def TimeMsc(self) -> int:
        """Receive the time of deal in milliseconds since 01.01.1970."""
        return self._int_prop("DEAL_TIME_MSC", 0, "time_msc")

    def DealType(self) -> int:
        """Get the deal type."""
        return self._int_prop("DEAL_TYPE", 0, "type")

    def DealTypeDescription(self) -> str:
        """Get the deal type as a string."""
        value = self.DealType()
        mapping = {
            getattr(mt5, "DEAL_TYPE_BUY", None): "Buy",
            getattr(mt5, "DEAL_TYPE_SELL", None): "Sell",
            getattr(mt5, "DEAL_TYPE_BALANCE", None): "Balance",
            getattr(mt5, "DEAL_TYPE_CREDIT", None): "Credit",
            getattr(mt5, "DEAL_TYPE_CHARGE", None): "Charge",
            getattr(mt5, "DEAL_TYPE_CORRECTION", None): "Correction",
            getattr(mt5, "DEAL_TYPE_BONUS", None): "Bonus",
            getattr(mt5, "DEAL_TYPE_COMMISSION", None): "Commission",
            getattr(mt5, "DEAL_TYPE_COMMISSION_DAILY", None): "Commission Daily",
            getattr(mt5, "DEAL_TYPE_COMMISSION_MONTHLY", None): "Commission Monthly",
            getattr(
                mt5, "DEAL_TYPE_COMMISSION_AGENT_DAILY", None
            ): "Commission Agent Daily",
            getattr(
                mt5, "DEAL_TYPE_COMMISSION_AGENT_MONTHLY", None
            ): "Commission Agent Monthly",
            getattr(mt5, "DEAL_TYPE_INTEREST", None): "Interest",
            getattr(mt5, "DEAL_TYPE_BUY_CANCELED", None): "Buy Canceled",
            getattr(mt5, "DEAL_TYPE_SELL_CANCELED", None): "Sell Canceled",
        }
        return mapping.get(value, "Unknown")

    def Entry(self) -> int:
        """Get the deal entry."""
        return self._int_prop("DEAL_ENTRY", 0, "entry")

    def EntryDescription(self) -> str:
        """Get the deal entry as a string."""
        value = self.Entry()
        mapping = {
            getattr(mt5, "DEAL_ENTRY_IN", None): "In",
            getattr(mt5, "DEAL_ENTRY_OUT", None): "Out",
            getattr(mt5, "DEAL_ENTRY_INOUT", None): "InOut",
            getattr(mt5, "DEAL_ENTRY_OUT_BY", None): "Out By",
            getattr(mt5, "DEAL_ENTRY_STATE", None): "State",
        }
        return mapping.get(value, "Unknown")

    def Magic(self) -> int:
        """Get the ID of expert that executed the deal."""
        return self._int_prop("DEAL_MAGIC", 0, "magic")

    def PositionId(self) -> int:
        """Get the position ID associated with the deal."""
        return self._int_prop("DEAL_POSITION_ID", 0, "position_id")

    # Access to double type properties
    def Volume(self) -> float:
        """Get the volume of a deal."""
        return self._double_prop("DEAL_VOLUME", 0.0, "volume")

    def Price(self) -> float:
        """Get the price of a deal."""
        return self._double_prop("DEAL_PRICE", 0.0, "price")

    def Commission(self) -> float:
        """Get the commission of a deal."""
        return self._double_prop("DEAL_COMMISSION", 0.0, "commission")

    def Swap(self) -> float:
        """Get the swap of a deal."""
        return self._double_prop("DEAL_SWAP", 0.0, "swap")

    def Profit(self) -> float:
        """Get the profit of a deal."""
        return self._double_prop("DEAL_PROFIT", 0.0, "profit")

    def Fee(self) -> float:
        """Get the fee of a deal."""
        return self._double_prop("DEAL_FEE", 0.0, "fee")

    # Access to text properties
    def Symbol(self) -> str:
        """Get the deal symbol."""
        return self._string_prop("DEAL_SYMBOL", "", "symbol")

    def Comment(self) -> str:
        """Get the deal comment."""
        return self._string_prop("DEAL_COMMENT", "", "comment")

    def ExternalId(self) -> str:
        """Get the external ID."""
        return self._string_prop("DEAL_EXTERNAL_ID", "", "external_id")

    # Access to MQL5 API functions
    def InfoInteger(self, prop: Any) -> Optional[int]:
        """Get the value of specified integer type property."""
        if isinstance(prop, int) and hasattr(mt5, "history_deal_get_integer"):
            value = mt5.history_deal_get_integer(prop)
            return int(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return int(value) if value is not None else None
        return None

    def InfoDouble(self, prop: Any) -> Optional[float]:
        """Get the value of specified double type property."""
        if isinstance(prop, int) and hasattr(mt5, "history_deal_get_double"):
            value = mt5.history_deal_get_double(prop)
            return float(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return float(value) if value is not None else None
        return None

    def InfoString(self, prop: Any) -> Optional[str]:
        """Get value of specified string type property."""
        if isinstance(prop, int) and hasattr(mt5, "history_deal_get_string"):
            value = mt5.history_deal_get_string(prop)
            return str(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return str(value) if value is not None else None
        return None

    # Selection
    def Select(self, ticket: int) -> bool:
        """Select the deal by ticket."""
        deals = mt5.history_deals_get(ticket=ticket)
        if not deals:
            return False
        return self._set_deal(deals[0])

    def SelectByIndex(self, index: int) -> bool:
        """Select the deal by index."""
        if self._date_from is None or self._date_to is None:
            return False
        deals = mt5.history_deals_get(self._date_from, self._date_to)
        if not deals:
            return False
        if index < 0 or index >= len(deals):
            return False
        return self._set_deal(deals[index])
