"""
AccountInfo class.

This module mirrors the MQL5 Standard Library AccountInfo interface and
order/grouping for MT5 usage.
Reference: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/caccountinfo
"""

from __future__ import annotations

from typing import Any, Optional

from apps.mt5 import get_mt5_api

mt5 = get_mt5_api()


class AccountInfo:
    """
    Class for handling account properties in MT5.

    This class is based on the MQL5 Standard Library AccountInfo API.
    """

    def __init__(self, api: Optional[Any] = None) -> None:
        """Initialize."""
        self._api = api if api is not None else get_mt5_api()
        self._account_info: dict[str, Any] = {}

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _fetch_account_info(self) -> bool:
        info = self._api.account_info()
        if info is None:
            self._account_info = {}
            return False
        self._account_info = info._asdict()
        return True

    def _ensure_info(self) -> None:
        if not self._account_info:
            self._fetch_account_info()

    def _cached(self, default: Any, *keys: str) -> Any:
        self._ensure_info()
        for key in keys:
            if key in self._account_info and self._account_info[key] is not None:
                return self._account_info[key]
        return default

    def _info_integer(self, prop: Optional[int]) -> Optional[int]:
        if prop is None:
            return None
        if hasattr(self._api, "account_info_integer"):
            value = self._api.account_info_integer(prop)
        return int(value) if value is not None else None
        return None

    def _info_double(self, prop: Optional[int]) -> Optional[float]:
        if prop is None:
            return None
        if hasattr(self._api, "account_info_double"):
            value = self._api.account_info_double(prop)
        return float(value) if value is not None else None
        return None

    def _info_string(self, prop: Optional[int]) -> Optional[str]:
        if prop is None:
            return None
        if hasattr(self._api, "account_info_string"):
            value = self._api.account_info_string(prop)
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
    # Account Info
    # ---------------------------------------------------------------------
    def Login(self) -> int:
        """Get the account number."""
        return self._int_prop("ACCOUNT_LOGIN", 0, "login")

    def Name(self) -> str:
        """Get the client name."""
        return self._string_prop("ACCOUNT_NAME", "", "name")

    def Server(self) -> str:
        """Get the trade server name."""
        return self._string_prop("ACCOUNT_SERVER", "", "server")

    def Currency(self) -> str:
        """Get the deposit currency name."""
        return self._string_prop("ACCOUNT_CURRENCY", "", "currency")

    def Company(self) -> str:
        """Get the company name that serves an account."""
        return self._string_prop("ACCOUNT_COMPANY", "", "company")

    # ---------------------------------------------------------------------
    # Account Mode
    # ---------------------------------------------------------------------
    def TradeMode(self) -> int:
        """Get the trade mode."""
        return self._int_prop("ACCOUNT_TRADE_MODE", 0, "trade_mode")

    def TradeModeDescription(self) -> str:
        """Get the trade mode as a string."""
        value = self.TradeMode()
        mapping = {
            getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None): "Demo",
            getattr(mt5, "ACCOUNT_TRADE_MODE_CONTEST", None): "Contest",
            getattr(mt5, "ACCOUNT_TRADE_MODE_REAL", None): "Real",
        }
        return mapping.get(value, "Unknown")

    def Leverage(self) -> int:
        """Get the amount of given leverage."""
        return self._int_prop("ACCOUNT_LEVERAGE", 0, "leverage")

    # ---------------------------------------------------------------------
    # Permissions
    # ---------------------------------------------------------------------
    def TradeAllowed(self) -> bool:
        """Get the flag of trade allowance."""
        return bool(self._int_prop("ACCOUNT_TRADE_ALLOWED", 0, "trade_allowed"))

    def TradeExpert(self) -> bool:
        """Get the flag of automated trade allowance."""
        return bool(self._int_prop("ACCOUNT_TRADE_EXPERT", 0, "trade_expert"))

    def LimitOrders(self) -> int:
        """Get the maximal number of allowed pending orders."""
        return self._int_prop("ACCOUNT_LIMIT_ORDERS", 0, "limit_orders")

    # ---------------------------------------------------------------------
    # Balance and Equity
    # ---------------------------------------------------------------------
    def Balance(self) -> float:
        """Get the balance of account."""
        return self._double_prop("ACCOUNT_BALANCE", 0.0, "balance")

    def Credit(self) -> float:
        """Get the amount of given credit."""
        return self._double_prop("ACCOUNT_CREDIT", 0.0, "credit")

    def Profit(self) -> float:
        """Get the amount of current profit on account."""
        return self._double_prop("ACCOUNT_PROFIT", 0.0, "profit")

    def Equity(self) -> float:
        """Get the amount of current equity on account."""
        return self._double_prop("ACCOUNT_EQUITY", 0.0, "equity")

    # ---------------------------------------------------------------------
    # Margin Information
    # ---------------------------------------------------------------------
    def Margin(self) -> float:
        """Get the amount of reserved margin."""
        return self._double_prop("ACCOUNT_MARGIN", 0.0, "margin")

    def FreeMargin(self) -> float:
        """Get the amount of free margin."""
        return self._double_prop(
            "ACCOUNT_FREEMARGIN", 0.0, "margin_free", "free_margin"
        )

    def MarginLevel(self) -> float:
        """Get the level of margin."""
        return self._double_prop("ACCOUNT_MARGIN_LEVEL", 0.0, "margin_level")

    def MarginCall(self) -> float:
        """Get the level of margin for deposit."""
        return self._double_prop("ACCOUNT_MARGIN_SO_CALL", 0.0, "margin_so_call")

    def MarginStopOut(self) -> float:
        """Get the level of margin for Stop Out."""
        return self._double_prop("ACCOUNT_MARGIN_SO_SO", 0.0, "margin_so_so")

    def MarginMode(self) -> int:
        """Get margin calculation mode."""
        return self._int_prop("ACCOUNT_MARGIN_MODE", 0, "margin_mode")

    def MarginModeDescription(self) -> str:
        """Get margin calculation mode as a string."""
        value = self.MarginMode()
        mapping = {
            getattr(mt5, "ACCOUNT_MARGIN_MODE_RETAIL_NETTING", None): "Retail netting",
            getattr(mt5, "ACCOUNT_MARGIN_MODE_EXCHANGE", None): "Exchange",
            getattr(mt5, "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", None): "Retail hedging",
        }
        return mapping.get(value, "Unknown")

    def StopoutMode(self) -> int:
        """Get the mode of stop out setting."""
        return self._int_prop("ACCOUNT_MARGIN_SO_MODE", 0, "margin_so_mode")

    def StopoutModeDescription(self) -> str:
        """Get the mode of stop out setting as a string."""
        value = self.StopoutMode()
        mapping = {
            getattr(mt5, "ACCOUNT_MARGIN_SO_MODE_PERCENT", None): "Percent",
            getattr(mt5, "ACCOUNT_MARGIN_SO_MODE_MONEY", None): "Money",
        }
        return mapping.get(value, "Unknown")

    # ---------------------------------------------------------------------
    # Trading Checks
    # ---------------------------------------------------------------------
    def OrderProfitCheck(
        self,
        symbol: str,
        order_type: int,
        volume: float,
        price_open: float,
        price_close: float,
    ) -> float:
        """Get the evaluated profit based on the parameters passed."""
        if hasattr(self._api, "order_calc_profit"):
            result = self._api.order_calc_profit(
                order_type, symbol, volume, price_open, price_close
            )
            return float(result or 0.0)
        return 0.0

    def MarginCheck(
        self, symbol: str, order_type: int, volume: float, price: float
    ) -> float:
        """Get the amount of margin required to execute trade operation."""
        if hasattr(self._api, "order_calc_margin"):
            result = self._api.order_calc_margin(order_type, symbol, volume, price)
            return float(result or 0.0)
        return 0.0

    def FreeMarginCheck(
        self, symbol: str, order_type: int, volume: float, price: float
    ) -> float:
        """Get the amount of free margin left after execution of trade operation."""
        margin_required = self.MarginCheck(symbol, order_type, volume, price)
        free_margin = self.FreeMargin()
        return float(free_margin - margin_required)

    def MaxLotCheck(
        self, symbol: str, order_type: int, price: float, percent: float
    ) -> float:
        """Get the maximal possible volume of trade operation."""
        if percent <= 0:
            return 0.0
        margin_per_lot = self.MarginCheck(symbol, order_type, 1.0, price)
        if margin_per_lot <= 0:
            return 0.0
        usable = self.FreeMargin() * (percent / 100.0)
        return float(usable / margin_per_lot)

    # ---------------------------------------------------------------------
    # Account Settings
    # ---------------------------------------------------------------------
    def InfoInteger(self, prop: Any) -> Optional[int]:
        """Get the value of specified integer type property."""
        if isinstance(prop, int) and hasattr(self._api, "account_info_integer"):
            value = self._api.account_info_integer(prop)
            return int(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return int(value) if value is not None else None
        return None

    def InfoDouble(self, prop: Any) -> Optional[float]:
        """Get the value of specified double type property."""
        if isinstance(prop, int) and hasattr(self._api, "account_info_double"):
            value = self._api.account_info_double(prop)
            return float(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return float(value) if value is not None else None
        return None

    def InfoString(self, prop: Any) -> Optional[str]:
        """Get the value of specified string type property."""
        if isinstance(prop, int) and hasattr(self._api, "account_info_string"):
            value = self._api.account_info_string(prop)
            return str(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return str(value) if value is not None else None
        return None
