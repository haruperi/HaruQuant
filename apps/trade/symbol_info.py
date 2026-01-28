"""
SymbolInfo class (MT5-specific).

This module mirrors the MQL5 Standard Library SymbolInfo interface and
documentation for MT5 usage.
Reference: https://www.mql5.com/en/docs/standardlibrary/tradeclasses/csymbolinfo
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.mt5 import get_mt5_api

mt5 = get_mt5_api()


class SymbolInfo:
    """
    Class for handling symbol properties in MT5.

    This class is based on the MQL5 Standard Library SymbolInfo API.
    """

    def __init__(self, symbol: str = "", api: Optional[Any] = None) -> None:
        """
        Create a SymbolInfo instance.

        Args:
            symbol: Symbol name (e.g., "EURUSD"). Can be set later via Name().
        """
        self._api = api if api is not None else get_mt5_api()
        self._symbol: str = symbol
        self._symbol_info: dict[str, Any] = {}
        self._tick: dict[str, Any] = {}

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _fetch_symbol_info(self) -> bool:
        if not self._symbol:
            self._symbol_info = {}
            return False
        info = self._api.symbol_info(self._symbol)
        if info is None:
            self._symbol_info = {}
            return False
        self._symbol_info = info._asdict()
        return True

    def _fetch_tick(self) -> bool:
        if not self._symbol:
            self._tick = {}
            return False
        tick = self._api.symbol_info_tick(self._symbol)
        if tick is None:
            self._tick = {}
            return False
        self._tick = tick._asdict()
        return True

    def _cached(self, default: Any, *keys: str) -> Any:
        for key in keys:
            if key in self._symbol_info and self._symbol_info[key] is not None:
                return self._symbol_info[key]
        return default

    def _info_integer(self, prop: Optional[int]) -> Optional[int]:
        if prop is None:
            return None
        if hasattr(self._api, "symbol_info_integer"):
            value = self._api.symbol_info_integer(self._symbol, prop)
        return int(value) if value is not None else None
        return None

    def _info_double(self, prop: Optional[int]) -> Optional[float]:
        if prop is None:
            return None
        if hasattr(self._api, "symbol_info_double"):
            value = self._api.symbol_info_double(self._symbol, prop)
        return float(value) if value is not None else None
        return None

    def _info_string(self, prop: Optional[int]) -> Optional[str]:
        if prop is None:
            return None
        if hasattr(self._api, "symbol_info_string"):
            value = self._api.symbol_info_string(self._symbol, prop)
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

    def _tick_value(self, key: str, default: float = 0.0) -> float:
        if key in self._tick and self._tick[key] is not None:
            return float(self._tick[key])
        return default

    def _tick_time(self) -> datetime:
        value = self._tick.get("time")
        if isinstance(value, datetime):
            return value
        if value:
            return datetime.fromtimestamp(int(value))
        return datetime.fromtimestamp(0)

    # ---------------------------------------------------------------------
    # Symbol Identification
    # ---------------------------------------------------------------------
    def Name(self, name: Optional[str] = None) -> Any:
        """Get/set symbol name."""
        if name is None:
            return self._symbol
        self._symbol = name
        self._symbol_info = {}
        self._tick = {}
        return True

    def Description(self) -> str:
        """Get the string description of symbol."""
        return self._string_prop("SYMBOL_DESCRIPTION", "", "description")

    def Path(self) -> str:
        """Get the path in symbols tree."""
        return self._string_prop("SYMBOL_PATH", "", "path")

    def CurrencyBase(self) -> str:
        """Get the name of symbol base currency."""
        return self._string_prop("SYMBOL_CURRENCY_BASE", "", "currency_base")

    def CurrencyProfit(self) -> str:
        """Get the profit currency name."""
        return self._string_prop("SYMBOL_CURRENCY_PROFIT", "", "currency_profit")

    def CurrencyMargin(self) -> str:
        """Get the margin currency name."""
        return self._string_prop("SYMBOL_CURRENCY_MARGIN", "", "currency_margin")

    def Bank(self) -> str:
        """Get the name of current quote source."""
        return self._string_prop("SYMBOL_BANK", "", "bank")

    # ---------------------------------------------------------------------
    # Symbol Controlling
    # ---------------------------------------------------------------------
    def Refresh(self) -> bool:
        """Refresh the symbol data."""
        return self._fetch_symbol_info()

    def RefreshRates(self) -> bool:
        """Refresh the symbol quotes."""
        return self._fetch_tick()

    def Select(self, select: Optional[bool] = None) -> bool:
        """Get/set the Market Watch symbol flag."""
        if select is None:
            return bool(self._int_prop("SYMBOL_SELECT", 0, "select", "visible"))
        return bool(self._api.symbol_select(self._symbol, bool(select)))

    def IsSynchronized(self) -> bool:
        """Check the symbol synchronization with server."""
        return bool(self._symbol_info) and bool(self._tick)

    # ---------------------------------------------------------------------
    # Pricing and Tick Data
    # ---------------------------------------------------------------------
    def Bid(self) -> float:
        """Get the current Bid price."""
        return self._tick_value("bid", 0.0)

    def BidHigh(self) -> float:
        """Get the maximal Bid price for a day."""
        return self._double_prop("SYMBOL_BIDHIGH", 0.0, "bidhigh", "bid_high")

    def BidLow(self) -> float:
        """Get the minimal Bid price for a day."""
        return self._double_prop("SYMBOL_BIDLOW", 0.0, "bidlow", "bid_low")

    def Ask(self) -> float:
        """Get the current Ask price."""
        return self._tick_value("ask", 0.0)

    def AskHigh(self) -> float:
        """Get the maximal Ask price for a day."""
        return self._double_prop("SYMBOL_ASKHIGH", 0.0, "askhigh", "ask_high")

    def AskLow(self) -> float:
        """Get the minimal Ask price for a day."""
        return self._double_prop("SYMBOL_ASKLOW", 0.0, "asklow", "ask_low")

    def Last(self) -> float:
        """Get the current Last price."""
        return self._tick_value("last", 0.0)

    def LastHigh(self) -> float:
        """Get the maximal Last price for a day."""
        return self._double_prop("SYMBOL_LASTHIGH", 0.0, "lasthigh", "last_high")

    def LastLow(self) -> float:
        """Get the minimal Last price for a day."""
        return self._double_prop("SYMBOL_LASTLOW", 0.0, "lastlow", "last_low")

    def Time(self) -> datetime:
        """Get the time of last quote."""
        return self._tick_time()

    def Spread(self) -> int:
        """Get the amount of spread (in points)."""
        return self._int_prop("SYMBOL_SPREAD", 0, "spread")

    def SpreadFloat(self) -> bool:
        """Get the flag of floating spread."""
        return bool(self._int_prop("SYMBOL_SPREAD_FLOAT", 0, "spread_float"))

    def TicksBookDepth(self) -> int:
        """Get the depth of ticks saving."""
        return self._int_prop("SYMBOL_TICKS_BOOKDEPTH", 0, "ticks_bookdepth")

    # ---------------------------------------------------------------------
    # Volumes
    # ---------------------------------------------------------------------
    def Volume(self) -> float:
        """Get the volume of last deal."""
        if "volume_real" in self._tick:
            return float(self._tick.get("volume_real") or 0.0)
        return float(self._tick.get("volume") or 0.0)

    def VolumeHigh(self) -> int:
        """Get the maximal volume for a day."""
        return self._int_prop("SYMBOL_VOLUMEHIGH", 0, "volume_high", "volumehigh")

    def VolumeLow(self) -> int:
        """Get the minimal volume for a day."""
        return self._int_prop("SYMBOL_VOLUMELOW", 0, "volume_low", "volumelow")

    # ---------------------------------------------------------------------
    # Trade Settings and Modes
    # ---------------------------------------------------------------------
    def TradeCalcMode(self) -> int:
        """Get the mode of contract cost calculation."""
        return self._int_prop("SYMBOL_TRADE_CALC_MODE", 0, "trade_calc_mode")

    def TradeCalcModeDescription(self) -> str:
        """Get the mode of contract cost calculation as a string."""
        value = self.TradeCalcMode()
        mapping = {
            getattr(mt5, "SYMBOL_CALC_MODE_FOREX", None): "Forex",
            getattr(mt5, "SYMBOL_CALC_MODE_FUTURES", None): "Futures",
            getattr(mt5, "SYMBOL_CALC_MODE_CFD", None): "CFD",
            getattr(mt5, "SYMBOL_CALC_MODE_CFDINDEX", None): "CFD indices",
            getattr(mt5, "SYMBOL_CALC_MODE_CFDLEVERAGE", None): "CFD leverage",
            getattr(mt5, "SYMBOL_CALC_MODE_EXCH_STOCKS", None): "Exchange stocks",
            getattr(mt5, "SYMBOL_CALC_MODE_EXCH_FUTURES", None): "Exchange futures",
            getattr(mt5, "SYMBOL_CALC_MODE_EXCH_FUTURES_FORTS", None): "FORTS futures",
        }
        return mapping.get(value, "Unknown")

    def TradeMode(self) -> int:
        """Get the type of order execution."""
        return self._int_prop("SYMBOL_TRADE_MODE", 0, "trade_mode")

    def TradeModeDescription(self) -> str:
        """Get the type of order execution as a string."""
        value = self.TradeMode()
        mapping = {
            getattr(mt5, "SYMBOL_TRADE_MODE_DISABLED", None): "Disabled",
            getattr(mt5, "SYMBOL_TRADE_MODE_LONGONLY", None): "Long only",
            getattr(mt5, "SYMBOL_TRADE_MODE_SHORTONLY", None): "Short only",
            getattr(mt5, "SYMBOL_TRADE_MODE_CLOSEONLY", None): "Close only",
            getattr(mt5, "SYMBOL_TRADE_MODE_FULL", None): "Full access",
        }
        return mapping.get(value, "Unknown")

    def TradeExecution(self) -> int:
        """Get the trade execution mode."""
        return self._int_prop("SYMBOL_TRADE_EXEMODE", 0, "trade_exemode")

    def TradeExecutionDescription(self) -> str:
        """Get the execution mode as a string."""
        value = self.TradeExecution()
        mapping = {
            getattr(mt5, "SYMBOL_TRADE_EXECUTION_REQUEST", None): "Request",
            getattr(mt5, "SYMBOL_TRADE_EXECUTION_INSTANT", None): "Instant",
            getattr(mt5, "SYMBOL_TRADE_EXECUTION_MARKET", None): "Market",
            getattr(mt5, "SYMBOL_TRADE_EXECUTION_EXCHANGE", None): "Exchange",
        }
        return mapping.get(value, "Unknown")

    def TradeTimeFlags(self) -> int:
        """Get the flags of allowed expiration modes."""
        return self._int_prop("SYMBOL_TRADE_TIME_FLAGS", 0, "trade_time_flags")

    def TradeFillFlags(self) -> int:
        """Get the flags of allowed filling modes."""
        return self._int_prop("SYMBOL_TRADE_FILL_FLAGS", 0, "trade_fill_flags")

    # ---------------------------------------------------------------------
    # Margins and Swaps
    # ---------------------------------------------------------------------
    def MarginInitial(self) -> float:
        """Get the value of initial margin."""
        return self._double_prop("SYMBOL_MARGIN_INITIAL", 0.0, "margin_initial")

    def MarginMaintenance(self) -> float:
        """Get the value of maintenance margin."""
        return self._double_prop("SYMBOL_MARGIN_MAINTENANCE", 0.0, "margin_maintenance")

    def MarginLong(self) -> float:
        """Get the rate of margin charging for long positions."""
        return self._double_prop("SYMBOL_MARGIN_LONG", 0.0, "margin_long")

    def MarginShort(self) -> float:
        """Get the rate of margin charging for short positions."""
        return self._double_prop("SYMBOL_MARGIN_SHORT", 0.0, "margin_short")

    def MarginLimit(self) -> float:
        """Get the rate of margin charging for Limit orders."""
        return self._double_prop("SYMBOL_MARGIN_LIMIT", 0.0, "margin_limit")

    def MarginStop(self) -> float:
        """Get the rate of margin charging for Stop orders."""
        return self._double_prop("SYMBOL_MARGIN_STOP", 0.0, "margin_stop")

    def MarginStopLimit(self) -> float:
        """Get the rate of margin charging for StopLimit orders."""
        return self._double_prop("SYMBOL_MARGIN_STOPLIMIT", 0.0, "margin_stoplimit")

    def SwapMode(self) -> int:
        """Get the swap calculation mode."""
        return self._int_prop("SYMBOL_SWAP_MODE", 0, "swap_mode")

    def SwapModeDescription(self) -> str:
        """Get the swap calculation mode as a string."""
        value = self.SwapMode()
        mapping = {
            getattr(mt5, "SYMBOL_SWAP_MODE_DISABLED", None): "Disabled",
            getattr(mt5, "SYMBOL_SWAP_MODE_POINTS", None): "Points",
            getattr(mt5, "SYMBOL_SWAP_MODE_CURRENCY_SYMBOL", None): "Currency symbol",
            getattr(mt5, "SYMBOL_SWAP_MODE_CURRENCY_MARGIN", None): "Currency margin",
            getattr(mt5, "SYMBOL_SWAP_MODE_CURRENCY_DEPOSIT", None): "Currency deposit",
            getattr(mt5, "SYMBOL_SWAP_MODE_INTEREST_CURRENT", None): "Interest current",
            getattr(mt5, "SYMBOL_SWAP_MODE_INTEREST_OPEN", None): "Interest open",
            getattr(mt5, "SYMBOL_SWAP_MODE_REOPEN_CURRENT", None): "Reopen current",
            getattr(mt5, "SYMBOL_SWAP_MODE_REOPEN_BID", None): "Reopen bid",
        }
        return mapping.get(value, "Unknown")

    def SwapRollover3Days(self) -> int:
        """Get the day of triple swap charge."""
        return self._int_prop("SYMBOL_SWAP_ROLLOVER3DAYS", 0, "swap_rollover3days")

    def SwapRollover3DaysDescription(self) -> str:
        """Get the day of triple swap charge as a string."""
        value = self.SwapRollover3Days()
        mapping = {
            0: "Sunday",
            1: "Monday",
            2: "Tuesday",
            3: "Wednesday",
            4: "Thursday",
            5: "Friday",
            6: "Saturday",
        }
        return mapping.get(value, "Unknown")

    def SwapLong(self) -> float:
        """Get the value of long position swap."""
        return self._double_prop("SYMBOL_SWAP_LONG", 0.0, "swap_long")

    def SwapShort(self) -> float:
        """Get the value of short position swap."""
        return self._double_prop("SYMBOL_SWAP_SHORT", 0.0, "swap_short")

    # ---------------------------------------------------------------------
    # Levels and Quantization
    # ---------------------------------------------------------------------
    def StopsLevel(self) -> int:
        """Get the minimal indent for orders (in points)."""
        return self._int_prop("SYMBOL_TRADE_STOPS_LEVEL", 0, "trade_stops_level")

    def FreezeLevel(self) -> int:
        """Get the distance of freezing trade operations (in points)."""
        return self._int_prop("SYMBOL_TRADE_FREEZE_LEVEL", 0, "trade_freeze_level")

    def Digits(self) -> int:
        """Get the number of digits after period."""
        return self._int_prop("SYMBOL_DIGITS", 0, "digits")

    def Point(self) -> float:
        """Get the value of one point."""
        return self._double_prop("SYMBOL_POINT", 0.0, "point")

    def TickValue(self) -> float:
        """Get the tick value (minimal change of price)."""
        return self._double_prop("SYMBOL_TRADE_TICK_VALUE", 0.0, "trade_tick_value")

    def TickValueProfit(self) -> float:
        """Get the calculated tick price for a profitable position."""
        return self._double_prop(
            "SYMBOL_TRADE_TICK_VALUE_PROFIT", 0.0, "trade_tick_value_profit"
        )

    def TickValueLoss(self) -> float:
        """Get the calculated tick price for a losing position."""
        return self._double_prop(
            "SYMBOL_TRADE_TICK_VALUE_LOSS", 0.0, "trade_tick_value_loss"
        )

    def TickSize(self) -> float:
        """Get the minimal change of price."""
        return self._double_prop("SYMBOL_TRADE_TICK_SIZE", 0.0, "trade_tick_size")

    def PipSize(self) -> float:
        """Return the pip size for the symbol."""
        return self.Point() * 10

    def NormalizePrice(self, price: float) -> float:
        """Return the value of price, normalized using the symbol properties."""
        digits = self.Digits()
        if digits <= 0:
            return float(price)
        return round(float(price), digits)

    # ---------------------------------------------------------------------
    # Contract Sizes and Session Data
    # ---------------------------------------------------------------------
    def ContractSize(self) -> float:
        """Get the amount of trade contract."""
        return self._double_prop(
            "SYMBOL_TRADE_CONTRACT_SIZE", 0.0, "trade_contract_size"
        )

    def LotsMin(self) -> float:
        """Get the minimal volume to close a deal."""
        return self._double_prop("SYMBOL_VOLUME_MIN", 0.0, "volume_min")

    def LotsMax(self) -> float:
        """Get the maximal volume to close a deal."""
        return self._double_prop("SYMBOL_VOLUME_MAX", 0.0, "volume_max")

    def LotsStep(self) -> float:
        """Get the minimal step of volume change to close a deal."""
        return self._double_prop("SYMBOL_VOLUME_STEP", 0.0, "volume_step")

    def LotsLimit(self) -> float:
        """Get the maximal allowed volume of opened position and pending orders."""
        return self._double_prop("SYMBOL_VOLUME_LIMIT", 0.0, "volume_limit")

    def SessionDeals(self) -> int:
        """Get the number of deals in the current session."""
        return self._int_prop("SYMBOL_SESSION_DEALS", 0, "session_deals")

    def SessionBuyOrders(self) -> int:
        """Get the number of Buy orders at the moment."""
        return self._int_prop("SYMBOL_SESSION_BUY_ORDERS", 0, "session_buy_orders")

    def SessionSellOrders(self) -> int:
        """Get the number of Sell orders at the moment."""
        return self._int_prop("SYMBOL_SESSION_SELL_ORDERS", 0, "session_sell_orders")

    def SessionTurnover(self) -> float:
        """Get the summary of turnover of the current session."""
        return self._double_prop("SYMBOL_SESSION_TURNOVER", 0.0, "session_turnover")

    def SessionInterest(self) -> float:
        """Get the summary of open interest of the current session."""
        return self._double_prop("SYMBOL_SESSION_INTEREST", 0.0, "session_interest")

    def SessionBuyOrdersVolume(self) -> float:
        """Get the current volume of Buy orders."""
        return self._double_prop(
            "SYMBOL_SESSION_BUY_ORDERS_VOLUME", 0.0, "session_buy_orders_volume"
        )

    def SessionSellOrdersVolume(self) -> float:
        """Get the current volume of Sell orders."""
        return self._double_prop(
            "SYMBOL_SESSION_SELL_ORDERS_VOLUME", 0.0, "session_sell_orders_volume"
        )

    def SessionOpen(self) -> float:
        """Get the open price of the current session."""
        return self._double_prop("SYMBOL_SESSION_OPEN", 0.0, "session_open")

    def SessionClose(self) -> float:
        """Get the close price of the current session."""
        return self._double_prop("SYMBOL_SESSION_CLOSE", 0.0, "session_close")

    def SessionAW(self) -> float:
        """Get the average weighted price of the current session."""
        return self._double_prop("SYMBOL_SESSION_AW", 0.0, "session_aw")

    def SessionPriceSettlement(self) -> float:
        """Get the settlement price of the current session."""
        return self._double_prop(
            "SYMBOL_SESSION_PRICE_SETTLEMENT", 0.0, "session_price_settlement"
        )

    def SessionPriceLimitMin(self) -> float:
        """Get the minimal price of the current session."""
        return self._double_prop(
            "SYMBOL_SESSION_PRICE_LIMIT_MIN", 0.0, "session_price_limit_min"
        )

    def SessionPriceLimitMax(self) -> float:
        """Get the maximal price of the current session."""
        return self._double_prop(
            "SYMBOL_SESSION_PRICE_LIMIT_MAX", 0.0, "session_price_limit_max"
        )

    # ---------------------------------------------------------------------
    # Generic Access
    # ---------------------------------------------------------------------
    def InfoInteger(self, prop: Any) -> Optional[int]:
        """Get the value of specified integer type property."""
        if isinstance(prop, int) and hasattr(self._api, "symbol_info_integer"):
            value = self._api.symbol_info_integer(self._symbol, prop)
            return int(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return int(value) if value is not None else None
        return None

    def InfoDouble(self, prop: Any) -> Optional[float]:
        """Get the value of specified double type property."""
        if isinstance(prop, int) and hasattr(self._api, "symbol_info_double"):
            value = self._api.symbol_info_double(self._symbol, prop)
            return float(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return float(value) if value is not None else None
        return None

    def InfoString(self, prop: Any) -> Optional[str]:
        """Get the value of specified string type property."""
        if isinstance(prop, int) and hasattr(self._api, "symbol_info_string"):
            value = self._api.symbol_info_string(self._symbol, prop)
            return str(value) if value is not None else None
        if isinstance(prop, str):
            value = self._cached(None, prop)
            return str(value) if value is not None else None
        return None
