"""
SymbolInfo class for accessing symbol information.

This module provides a platform-agnostic implementation of symbol information
access, inspired by MT5's SymbolInfo.mqh but designed to work with any
trading platform through adapter patterns.

Copyright 2025, HaruQuant
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Protocol, Union

from apps.logger import logger


class SymbolTradeExecution(Enum):
    """Symbol trade execution mode enumeration."""

    REQUEST = "request"
    INSTANT = "instant"
    MARKET = "market"
    EXCHANGE = "exchange"
    UNKNOWN = "unknown"


class SymbolCalcMode(Enum):
    """Symbol calculation mode enumeration."""

    FOREX = "forex"
    CFD = "cfd"
    FUTURES = "futures"
    CFD_INDEX = "cfd_index"
    CFD_LEVERAGE = "cfd_leverage"
    EXCH_STOCKS = "exch_stocks"
    EXCH_FUTURES = "exch_futures"
    EXCH_FUTURES_FORTS = "exch_futures_forts"
    UNKNOWN = "unknown"


class SymbolTradeMode(Enum):
    """Symbol trade mode enumeration."""

    DISABLED = "disabled"
    LONG_ONLY = "long_only"
    SHORT_ONLY = "short_only"
    CLOSE_ONLY = "close_only"
    FULL = "full"
    UNKNOWN = "unknown"


class SymbolSwapMode(Enum):
    """Symbol swap mode enumeration."""

    DISABLED = "disabled"
    POINTS = "points"
    CURRENCY_SYMBOL = "currency_symbol"
    CURRENCY_MARGIN = "currency_margin"
    CURRENCY_DEPOSIT = "currency_deposit"
    INTEREST_CURRENT = "interest_current"
    INTEREST_OPEN = "interest_open"
    REOPEN_CURRENT = "reopen_current"
    REOPEN_BID = "reopen_bid"
    UNKNOWN = "unknown"


class DayOfWeek(Enum):
    """Day of week enumeration."""

    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6


class Tick:
    """Structure representing a tick."""

    def __init__(
        self,
        time: Optional[datetime] = None,
        bid: float = 0.0,
        ask: float = 0.0,
        last: float = 0.0,
        volume: int = 0,
    ):
        """Initialize Tick."""
        self.time = time or datetime.now()
        self.bid = bid
        self.ask = ask
        self.last = last
        self.volume = volume


class SymbolDataProvider(Protocol):
    """
    Protocol for symbol data providers.

    Any trading platform adapter should implement this protocol
    to provide symbol information to the SymbolInfo class.
    """

    def get_symbol_name(self) -> str:
        """Get symbol name."""
        ...

    def set_symbol_name(self, name: str) -> bool:
        """Set symbol name and refresh data."""
        ...

    def refresh_symbol_data(self) -> bool:
        """Refresh cached symbol data."""
        ...

    def refresh_tick(self) -> bool:
        """Refresh tick data."""
        ...

    def get_tick(self) -> Tick:
        """Get current tick."""
        ...

    # Integer properties
    def get_select(self) -> bool:
        """Check if symbol is selected in MarketWatch."""
        ...

    def set_select(self, select: bool) -> bool:
        """Select/deselect symbol in MarketWatch."""
        ...

    def is_synchronized(self) -> bool:
        """Check if symbol is synchronized."""
        ...

    def get_volume_high(self) -> int:
        """Get highest volume of the day."""
        ...

    def get_volume_low(self) -> int:
        """Get lowest volume of the day."""
        ...

    def get_spread(self) -> int:
        """Get current spread in points."""
        ...

    def get_spread_float(self) -> bool:
        """Check if spread is floating."""
        ...

    def get_ticks_book_depth(self) -> int:
        """Get depth of market."""
        ...

    def get_stops_level(self) -> int:
        """Get stops level in points."""
        ...

    def get_freeze_level(self) -> int:
        """Get freeze level in points."""
        ...

    def get_digits(self) -> int:
        """Get number of decimal places."""
        ...

    def get_order_mode(self) -> int:
        """Get allowed order types."""
        ...

    def get_trade_execution(self) -> SymbolTradeExecution:
        """Get trade execution mode."""
        ...

    def get_trade_calc_mode(self) -> SymbolCalcMode:
        """Get calculation mode."""
        ...

    def get_trade_mode(self) -> SymbolTradeMode:
        """Get trade mode."""
        ...

    def get_swap_mode(self) -> SymbolSwapMode:
        """Get swap mode."""
        ...

    def get_swap_rollover3days(self) -> DayOfWeek:
        """Get triple swap day."""
        ...

    def get_trade_time_flags(self) -> int:
        """Get trade time flags."""
        ...

    def get_trade_fill_flags(self) -> int:
        """Get trade fill flags."""
        ...

    # Double properties
    def get_point(self) -> float:
        """Get point value."""
        ...

    def get_tick_value(self) -> float:
        """Get tick value."""
        ...

    def get_tick_value_profit(self) -> float:
        """Get tick value for profit calculation."""
        ...

    def get_tick_value_loss(self) -> float:
        """Get tick value for loss calculation."""
        ...

    def get_tick_size(self) -> float:
        """Get tick size."""
        ...

    def get_contract_size(self) -> float:
        """Get contract size."""
        ...

    def get_lots_min(self) -> float:
        """Get minimum lot size."""
        ...

    def get_lots_max(self) -> float:
        """Get maximum lot size."""
        ...

    def get_lots_step(self) -> float:
        """Get lot step."""
        ...

    def get_lots_limit(self) -> float:
        """Get maximum aggregate volume."""
        ...

    def get_swap_long(self) -> float:
        """Get long swap value."""
        ...

    def get_swap_short(self) -> float:
        """Get short swap value."""
        ...

    def get_bid_high(self) -> float:
        """Get highest bid of the day."""
        ...

    def get_bid_low(self) -> float:
        """Get lowest bid of the day."""
        ...

    def get_ask_high(self) -> float:
        """Get highest ask of the day."""
        ...

    def get_ask_low(self) -> float:
        """Get lowest ask of the day."""
        ...

    def get_last_high(self) -> float:
        """Get highest last price of the day."""
        ...

    def get_last_low(self) -> float:
        """Get lowest last price of the day."""
        ...

    def get_margin_initial(self) -> float:
        """Get initial margin."""
        ...

    def get_margin_maintenance(self) -> float:
        """Get maintenance margin."""
        ...

    def get_margin_hedged_use_leg(self) -> bool:
        """Check if hedged margin uses larger leg."""
        ...

    def get_margin_hedged(self) -> float:
        """Get hedged margin."""
        ...

    # String properties
    def get_currency_base(self) -> str:
        """Get base currency."""
        ...

    def get_currency_profit(self) -> str:
        """Get profit currency."""
        ...

    def get_currency_margin(self) -> str:
        """Get margin currency."""
        ...

    def get_bank(self) -> str:
        """Get source of quotes."""
        ...

    def get_description(self) -> str:
        """Get symbol description."""
        ...

    def get_path(self) -> str:
        """Get symbol path in symbol tree."""
        ...

    # Time properties
    def get_start_time(self) -> datetime:
        """Get symbol start time (for futures)."""
        ...

    def get_expiration_time(self) -> datetime:
        """Get symbol expiration time (for futures)."""
        ...

    # Session properties
    def get_session_deals(self) -> int:
        """Get number of deals in current session."""
        ...

    def get_session_buy_orders(self) -> int:
        """Get number of buy orders in current session."""
        ...

    def get_session_sell_orders(self) -> int:
        """Get number of sell orders in current session."""
        ...

    def get_session_turnover(self) -> float:
        """Get turnover in current session."""
        ...

    def get_session_interest(self) -> float:
        """Get open interest."""
        ...

    def get_session_buy_orders_volume(self) -> float:
        """Get buy orders volume in current session."""
        ...

    def get_session_sell_orders_volume(self) -> float:
        """Get sell orders volume in current session."""
        ...

    def get_session_open(self) -> float:
        """Get session open price."""
        ...

    def get_session_close(self) -> float:
        """Get session close price."""
        ...

    def get_session_aw(self) -> float:
        """Get average weighted price."""
        ...

    def get_session_price_settlement(self) -> float:
        """Get settlement price."""
        ...

    def get_session_price_limit_min(self) -> float:
        """Get minimum price limit."""
        ...

    def get_session_price_limit_max(self) -> float:
        """Get maximum price limit."""
        ...

    # Direct API access
    def info_integer(self, prop_id: str) -> Optional[int]:
        """Get integer property by ID."""
        ...

    def info_double(self, prop_id: str) -> Optional[float]:
        """Get double property by ID."""
        ...

    def info_string(self, prop_id: str) -> Optional[str]:
        """Get string property by ID."""
        ...

    def info_margin_rate(self, order_type: str) -> tuple[float, float]:
        """Get margin rates for order type."""
        ...


class MT5SymbolProvider:
    """
    Implementation of SymbolDataProvider using MT5Client.

    This class adapts an MT5Client instance to the SymbolDataProvider protocol,
    providing access to symbol information from MT5.
    """

    def __init__(self, mt5_client, symbol_name: str):
        """
        Initialize MT5SymbolProvider.

        Args:
            mt5_client: Instance of MT5Client with active connection
            symbol_name: Symbol name (e.g., "EURUSD")
        """
        self._client = mt5_client
        self._symbol_name = symbol_name
        self._symbol_data: Dict[str, Any] = {}
        self._tick = Tick()
        self._refresh_symbol_data()

    def _refresh_symbol_data(self) -> None:
        """Refresh symbol data from MT5."""
        data = self._client.get_symbol_info(self._symbol_name)
        if data:
            self._symbol_data = data
        else:
            self._symbol_data = {}

    def get_symbol_name(self) -> str:
        """Get symbol name."""
        return self._symbol_name

    def set_symbol_name(self, name: str) -> bool:
        """Set symbol name and refresh data."""
        self._symbol_name = name
        self._refresh_symbol_data()
        return bool(self._symbol_data)

    def refresh_symbol_data(self) -> bool:
        """Refresh cached symbol data."""
        self._refresh_symbol_data()
        return bool(self._symbol_data)

    def refresh_tick(self) -> bool:
        """Refresh tick data."""
        try:
            import MetaTrader5 as mt5

            tick_data = mt5.symbol_info_tick(self._symbol_name)
            if tick_data:
                self._tick = Tick(
                    time=datetime.fromtimestamp(tick_data.time),
                    bid=tick_data.bid,
                    ask=tick_data.ask,
                    last=tick_data.last,
                    volume=tick_data.volume,
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error refreshing tick for {self._symbol_name}: {e}")
            return False

    def get_tick(self) -> Tick:
        """Get current tick."""
        return self._tick

    # Integer properties
    def get_select(self) -> bool:
        """Check if symbol is selected."""
        return bool(self._symbol_data.get("visible", False))

    def set_select(self, select: bool) -> bool:
        """Set symbol selection."""
        # MT5 symbol selection - would need MT5 API call
        return False

    def is_synchronized(self) -> bool:
        """Check if synchronized."""
        return True

    def get_volume_high(self) -> int:
        """Get volume high."""
        return int(self._symbol_data.get("volume_real", 0))

    def get_volume_low(self) -> int:
        """Get volume low."""
        return 0

    def get_spread(self) -> int:
        """Get spread."""
        return int(self._symbol_data.get("spread", 0))

    def get_spread_float(self) -> bool:
        """Check if spread is floating."""
        return bool(self._symbol_data.get("spread_float", True))

    def get_ticks_book_depth(self) -> int:
        """Get book depth."""
        return 0

    def get_stops_level(self) -> int:
        """Get stops level."""
        return int(self._symbol_data.get("trade_stops_level", 0))

    def get_freeze_level(self) -> int:
        """Get freeze level."""
        return int(self._symbol_data.get("trade_freeze_level", 0))

    def get_digits(self) -> int:
        """Get digits."""
        return int(self._symbol_data.get("digits", 5))

    def get_order_mode(self) -> int:
        """Get order mode."""
        return 0

    def get_trade_execution(self) -> SymbolTradeExecution:
        """Get trade execution mode."""
        mode = int(self._symbol_data.get("trade_exemode", -1))
        mode_map = {
            0: SymbolTradeExecution.REQUEST,
            1: SymbolTradeExecution.INSTANT,
            2: SymbolTradeExecution.MARKET,
            3: SymbolTradeExecution.EXCHANGE,
        }
        return mode_map.get(mode, SymbolTradeExecution.UNKNOWN)

    def get_trade_calc_mode(self) -> SymbolCalcMode:
        """Get calculation mode."""
        mode = int(self._symbol_data.get("trade_calc_mode", -1))
        mode_map = {
            0: SymbolCalcMode.FOREX,
            1: SymbolCalcMode.FUTURES,
            2: SymbolCalcMode.CFD,
            3: SymbolCalcMode.CFD_INDEX,
            4: SymbolCalcMode.CFD_LEVERAGE,
            5: SymbolCalcMode.EXCH_STOCKS,
            6: SymbolCalcMode.EXCH_FUTURES,
            32: SymbolCalcMode.EXCH_FUTURES_FORTS,
        }
        return mode_map.get(mode, SymbolCalcMode.UNKNOWN)

    def get_trade_mode(self) -> SymbolTradeMode:
        """Get trade mode."""
        mode = int(self._symbol_data.get("trade_mode", -1))
        mode_map = {
            0: SymbolTradeMode.DISABLED,
            1: SymbolTradeMode.LONG_ONLY,
            2: SymbolTradeMode.SHORT_ONLY,
            3: SymbolTradeMode.CLOSE_ONLY,
            4: SymbolTradeMode.FULL,
        }
        return mode_map.get(mode, SymbolTradeMode.UNKNOWN)

    def get_swap_mode(self) -> SymbolSwapMode:
        """Get swap mode."""
        mode = int(self._symbol_data.get("swap_mode", -1))
        mode_map = {
            0: SymbolSwapMode.DISABLED,
            1: SymbolSwapMode.POINTS,
            2: SymbolSwapMode.CURRENCY_SYMBOL,
            3: SymbolSwapMode.CURRENCY_MARGIN,
            4: SymbolSwapMode.CURRENCY_DEPOSIT,
            5: SymbolSwapMode.INTEREST_CURRENT,
            6: SymbolSwapMode.INTEREST_OPEN,
            7: SymbolSwapMode.REOPEN_CURRENT,
            8: SymbolSwapMode.REOPEN_BID,
        }
        return mode_map.get(mode, SymbolSwapMode.UNKNOWN)

    def get_swap_rollover3days(self) -> DayOfWeek:
        """Get triple swap day."""
        day = int(self._symbol_data.get("swap_rollover3days", 3))
        return DayOfWeek(day) if 0 <= day <= 6 else DayOfWeek.WEDNESDAY

    def get_trade_time_flags(self) -> int:
        """Get trade time flags."""
        return 0

    def get_trade_fill_flags(self) -> int:
        """Get trade fill flags."""
        return 0

    # Double properties
    def get_point(self) -> float:
        """Get point."""
        return float(self._symbol_data.get("point", 0.0))

    def get_tick_value(self) -> float:
        """Get tick value."""
        return float(self._symbol_data.get("trade_tick_value", 0.0))

    def get_tick_value_profit(self) -> float:
        """Get tick value profit."""
        return float(self._symbol_data.get("trade_tick_value_profit", 0.0))

    def get_tick_value_loss(self) -> float:
        """Get tick value loss."""
        return float(self._symbol_data.get("trade_tick_value_loss", 0.0))

    def get_tick_size(self) -> float:
        """Get tick size."""
        return float(self._symbol_data.get("trade_tick_size", 0.0))

    def get_contract_size(self) -> float:
        """Get contract size."""
        return float(self._symbol_data.get("trade_contract_size", 0.0))

    def get_lots_min(self) -> float:
        """Get lots min."""
        return float(self._symbol_data.get("volume_min", 0.0))

    def get_lots_max(self) -> float:
        """Get lots max."""
        return float(self._symbol_data.get("volume_max", 0.0))

    def get_lots_step(self) -> float:
        """Get lots step."""
        return float(self._symbol_data.get("volume_step", 0.0))

    def get_lots_limit(self) -> float:
        """Get lots limit."""
        return float(self._symbol_data.get("volume_limit", 0.0))

    def get_swap_long(self) -> float:
        """Get swap long."""
        return float(self._symbol_data.get("swap_long", 0.0))

    def get_swap_short(self) -> float:
        """Get swap short."""
        return float(self._symbol_data.get("swap_short", 0.0))

    def get_bid_high(self) -> float:
        """Get bid high."""
        return float(self._symbol_data.get("bidhigh", 0.0))

    def get_bid_low(self) -> float:
        """Get bid low."""
        return float(self._symbol_data.get("bidlow", 0.0))

    def get_ask_high(self) -> float:
        """Get ask high."""
        return float(self._symbol_data.get("askhigh", 0.0))

    def get_ask_low(self) -> float:
        """Get ask low."""
        return float(self._symbol_data.get("asklow", 0.0))

    def get_last_high(self) -> float:
        """Get last high."""
        return float(self._symbol_data.get("lasthigh", 0.0))

    def get_last_low(self) -> float:
        """Get last low."""
        return float(self._symbol_data.get("lastlow", 0.0))

    def get_margin_initial(self) -> float:
        """Get margin initial."""
        return float(self._symbol_data.get("margin_initial", 0.0))

    def get_margin_maintenance(self) -> float:
        """Get margin maintenance."""
        return float(self._symbol_data.get("margin_maintenance", 0.0))

    def get_margin_hedged_use_leg(self) -> bool:
        """Check if margin hedged use leg."""
        return bool(self._symbol_data.get("margin_hedged_use_leg", False))

    def get_margin_hedged(self) -> float:
        """Get margin hedged."""
        return float(self._symbol_data.get("margin_hedged", 0.0))

    # String properties
    def get_currency_base(self) -> str:
        """Get currency base."""
        return str(self._symbol_data.get("currency_base", ""))

    def get_currency_profit(self) -> str:
        """Get currency profit."""
        return str(self._symbol_data.get("currency_profit", ""))

    def get_currency_margin(self) -> str:
        """Get currency margin."""
        return str(self._symbol_data.get("currency_margin", ""))

    def get_bank(self) -> str:
        """Get bank."""
        return str(self._symbol_data.get("bank", ""))

    def get_description(self) -> str:
        """Get description."""
        return str(self._symbol_data.get("description", ""))

    def get_path(self) -> str:
        """Get path."""
        return str(self._symbol_data.get("path", ""))

    # Time properties
    def get_start_time(self) -> datetime:
        """Get start time."""
        return datetime.fromtimestamp(int(self._symbol_data.get("start_time", 0)))

    def get_expiration_time(self) -> datetime:
        """Get expiration time."""
        return datetime.fromtimestamp(int(self._symbol_data.get("expiration_time", 0)))

    # Session properties
    def get_session_deals(self) -> int:
        """Get session deals."""
        return int(self._symbol_data.get("session_deals", 0))

    def get_session_buy_orders(self) -> int:
        """Get session buy orders."""
        return int(self._symbol_data.get("session_buy_orders", 0))

    def get_session_sell_orders(self) -> int:
        """Get session sell orders."""
        return int(self._symbol_data.get("session_sell_orders", 0))

    def get_session_turnover(self) -> float:
        """Get session turnover."""
        return float(self._symbol_data.get("session_turnover", 0.0))

    def get_session_interest(self) -> float:
        """Get session interest."""
        return float(self._symbol_data.get("session_interest", 0.0))

    def get_session_buy_orders_volume(self) -> float:
        """Get session buy orders volume."""
        return float(self._symbol_data.get("session_buy_orders_volume", 0.0))

    def get_session_sell_orders_volume(self) -> float:
        """Get session sell orders volume."""
        return float(self._symbol_data.get("session_sell_orders_volume", 0.0))

    def get_session_open(self) -> float:
        """Get session open."""
        return float(self._symbol_data.get("session_open", 0.0))

    def get_session_close(self) -> float:
        """Get session close."""
        return float(self._symbol_data.get("session_close", 0.0))

    def get_session_aw(self) -> float:
        """Get session aw."""
        return float(self._symbol_data.get("session_aw", 0.0))

    def get_session_price_settlement(self) -> float:
        """Get session price settlement."""
        return float(self._symbol_data.get("session_price_settlement", 0.0))

    def get_session_price_limit_min(self) -> float:
        """Get session price limit min."""
        return float(self._symbol_data.get("session_price_limit_min", 0.0))

    def get_session_price_limit_max(self) -> float:
        """Get session price limit max."""
        return float(self._symbol_data.get("session_price_limit_max", 0.0))

    # Direct API access
    def info_integer(self, prop_id: str) -> Optional[int]:
        """Get info integer."""
        return self._symbol_data.get(prop_id)

    def info_double(self, prop_id: str) -> Optional[float]:
        """Get info double."""
        return self._symbol_data.get(prop_id)

    def info_string(self, prop_id: str) -> Optional[str]:
        """Get info string."""
        return self._symbol_data.get(prop_id)

    def info_margin_rate(self, order_type: str) -> tuple[float, float]:
        """Get info margin rate."""
        return (0.0, 0.0)


class BacktestSymbolProvider:
    """
    Implementation of SymbolDataProvider for backtesting.

    This provider can optionally fetch symbol information from MT5 once and cache it,
    or use sensible defaults for backtesting without MT5 connection.
    """

    def __init__(self, mt5_client=None, symbol_name: str = "EURUSD"):
        """
        Initialize BacktestSymbolProvider.

        Args:
            mt5_client: Optional MT5Client instance to fetch initial symbol data.
                       If None, uses default symbol specifications.
            symbol_name: Symbol name (e.g., "EURUSD")
        """
        self._symbol_name = symbol_name
        self._symbol_data: Dict[str, Any] = {}
        self._tick = Tick()

        # Try to fetch from MT5 if client provided
        if mt5_client is not None:
            data = mt5_client.get_symbol_info(symbol_name)
            if data:
                self._symbol_data = data
            else:
                self._symbol_data = self._get_default_symbol_data(symbol_name)
        else:
            # Use defaults for backtesting without MT5
            self._symbol_data = self._get_default_symbol_data(symbol_name)

    def _get_default_symbol_data(self, symbol_name: str) -> Dict[str, Any]:
        """
        Get default symbol specifications for common symbols.

        Supports forex pairs, JPY pairs, and cryptocurrency symbols.
        For custom specifications, use set_symbol_spec() after initialization.

        Args:
            symbol_name: Symbol name

        Returns:
            Dictionary with default symbol specifications
        """
        symbol_upper = symbol_name.upper()

        # Cryptocurrency presets (fractional volume support)
        crypto_presets: Dict[str, Dict[str, Any]] = {
            "BTCUSD": {
                "name": symbol_name,
                "digits": 2,
                "point": 0.01,
                "spread": 50,
                "trade_contract_size": 1.0,  # 1 BTC per lot
                "volume_min": 0.00000001,  # 1 satoshi
                "volume_max": 1000.0,
                "volume_step": 0.00000001,
                "trade_tick_size": 0.01,
                "trade_tick_value": 0.01,
                "currency_base": "BTC",
                "currency_profit": "USD",
                "currency_margin": "USD",
                "swap_mode": 0,  # Disabled for crypto
                "swap_long": 0.0,
                "swap_short": 0.0,
                "swap_rollover3days": 3,
            },
            "ETHUSD": {
                "name": symbol_name,
                "digits": 2,
                "point": 0.01,
                "spread": 30,
                "trade_contract_size": 1.0,  # 1 ETH per lot
                "volume_min": 0.00000001,
                "volume_max": 10000.0,
                "volume_step": 0.00000001,
                "trade_tick_size": 0.01,
                "trade_tick_value": 0.01,
                "currency_base": "ETH",
                "currency_profit": "USD",
                "currency_margin": "USD",
                "swap_mode": 0,
                "swap_long": 0.0,
                "swap_short": 0.0,
                "swap_rollover3days": 3,
            },
            "XRPUSD": {
                "name": symbol_name,
                "digits": 5,
                "point": 0.00001,
                "spread": 10,
                "trade_contract_size": 1.0,
                "volume_min": 0.001,
                "volume_max": 1000000.0,
                "volume_step": 0.001,
                "trade_tick_size": 0.00001,
                "trade_tick_value": 0.00001,
                "currency_base": "XRP",
                "currency_profit": "USD",
                "currency_margin": "USD",
                "swap_mode": 0,
                "swap_long": 0.0,
                "swap_short": 0.0,
                "swap_rollover3days": 3,
            },
            "SOLUSD": {
                "name": symbol_name,
                "digits": 2,
                "point": 0.01,
                "spread": 20,
                "trade_contract_size": 1.0,
                "volume_min": 0.0001,
                "volume_max": 100000.0,
                "volume_step": 0.0001,
                "trade_tick_size": 0.01,
                "trade_tick_value": 0.01,
                "currency_base": "SOL",
                "currency_profit": "USD",
                "currency_margin": "USD",
                "swap_mode": 0,
                "swap_long": 0.0,
                "swap_short": 0.0,
                "swap_rollover3days": 3,
            },
        }

        # Check for crypto symbol match
        if symbol_upper in crypto_presets:
            return crypto_presets[symbol_upper]

        # Common forex pairs (5 digits)
        forex_5_digit = {
            "name": symbol_name,
            "digits": 5,
            "point": 0.00001,
            "spread": 10,
            "trade_contract_size": 100000.0,
            "volume_min": 0.01,
            "volume_max": 100.0,
            "volume_step": 0.01,
            "trade_tick_size": 0.00001,
            "trade_tick_value": 1.0,
            "currency_base": symbol_name[:3] if len(symbol_name) >= 6 else "USD",
            "currency_profit": symbol_name[3:6] if len(symbol_name) >= 6 else "USD",
            "currency_margin": symbol_name[:3] if len(symbol_name) >= 6 else "USD",
            # Swap defaults (mode 1 = POINTS, typical forex swap values)
            "swap_mode": 1,  # SYMBOL_SWAP_MODE_POINTS
            "swap_long": -0.5,  # Default long swap in points (negative = cost)
            "swap_short": -0.5,  # Default short swap in points (negative = cost)
            "swap_rollover3days": 3,  # Wednesday (triple swap day)
        }

        # JPY pairs (3 digits)
        if "JPY" in symbol_name:
            forex_5_digit.update(
                {
                    "digits": 3,
                    "point": 0.001,
                    "trade_tick_size": 0.001,
                }
            )

        return forex_5_digit

    def set_tick(
        self,
        bid: float,
        ask: float,
        last: float = 0.0,
        volume: int = 0,
        time: Optional[datetime] = None,
    ) -> None:
        """
        Update tick data for backtesting.

        Args:
            bid: Bid price
            ask: Ask price
            last: Last price (defaults to bid)
            volume: Tick volume
            time: Tick time (defaults to now)
        """
        self._tick = Tick(
            time=time or datetime.now(),
            bid=bid,
            ask=ask,
            last=last or bid,
            volume=volume,
        )

    def set_symbol_spec(self, **kwargs: Any) -> None:
        """
        Override symbol specifications for custom assets.

        Use this to configure custom symbols not in the presets (forex, crypto),
        or to override specific properties for backtesting scenarios.

        Example:
            provider = BacktestSymbolProvider(symbol_name="CUSTOM")
            provider.set_symbol_spec(
                volume_min=0.00001,
                volume_max=10000.0,
                volume_step=0.00001,
                trade_contract_size=1.0,
            )

        Args:
            **kwargs: Symbol properties to override. Common properties:
                - volume_min: Minimum trade volume
                - volume_max: Maximum trade volume
                - volume_step: Volume increment step
                - trade_contract_size: Contract size per lot
                - digits: Price decimal places
                - point: Minimum price change
        """
        self._symbol_data.update(kwargs)

    def get_symbol_name(self) -> str:
        """Get symbol name."""
        return self._symbol_name

    def set_symbol_name(self, name: str) -> bool:
        """Set symbol name."""
        return False

    def refresh_symbol_data(self) -> bool:
        """Refresh symbol data."""
        return True

    def refresh_tick(self) -> bool:
        """Refresh tick data."""
        return True

    def get_tick(self) -> Tick:
        """Get current tick."""
        return self._tick

    # Delegate all other methods to cached _symbol_data (same as MT5SymbolProvider)
    def get_select(self) -> bool:
        """Check if symbol is selected in MarketWatch."""
        return bool(self._symbol_data.get("visible", False))

    def set_select(self, select: bool) -> bool:
        """Select or deselect symbol in MarketWatch."""
        return False

    def is_synchronized(self) -> bool:
        """Check if symbol is synchronized."""
        return True

    def get_volume_high(self) -> int:
        """Get highest volume of the day."""
        return int(self._symbol_data.get("volume_real", 0))

    def get_volume_low(self) -> int:
        """Get lowest volume of the day."""
        return 0

    def get_spread(self) -> int:
        """Get spread in points."""
        return int(self._symbol_data.get("spread", 0))

    def get_spread_float(self) -> bool:
        """Check if spread is floating."""
        return bool(self._symbol_data.get("spread_float", True))

    def get_ticks_book_depth(self) -> int:
        """Get depth of market."""
        return 0

    def get_stops_level(self) -> int:
        """Get stops level in points."""
        return int(self._symbol_data.get("trade_stops_level", 0))

    def get_freeze_level(self) -> int:
        """Get freeze level in points."""
        return int(self._symbol_data.get("trade_freeze_level", 0))

    def get_digits(self) -> int:
        """Get number of digits after decimal."""
        return int(self._symbol_data.get("digits", 5))

    def get_order_mode(self) -> int:
        """Get order execution flags."""
        return 0

    def get_trade_execution(self) -> SymbolTradeExecution:
        """Get trade execution mode."""
        mode = self._symbol_data.get("trade_exemode", -1)
        mode_map = {
            0: SymbolTradeExecution.REQUEST,
            1: SymbolTradeExecution.INSTANT,
            2: SymbolTradeExecution.MARKET,
            3: SymbolTradeExecution.EXCHANGE,
        }
        return mode_map.get(mode, SymbolTradeExecution.UNKNOWN)

    def get_trade_calc_mode(self) -> SymbolCalcMode:
        """Get trade calculation mode."""
        mode = self._symbol_data.get("trade_calc_mode", -1)
        mode_map = {
            0: SymbolCalcMode.FOREX,
            1: SymbolCalcMode.FUTURES,
            2: SymbolCalcMode.CFD,
            3: SymbolCalcMode.CFD_INDEX,
            4: SymbolCalcMode.CFD_LEVERAGE,
            5: SymbolCalcMode.EXCH_STOCKS,
            6: SymbolCalcMode.EXCH_FUTURES,
            32: SymbolCalcMode.EXCH_FUTURES_FORTS,
        }
        return mode_map.get(mode, SymbolCalcMode.UNKNOWN)

    def get_trade_mode(self) -> SymbolTradeMode:
        """Get trade mode."""
        mode = self._symbol_data.get("trade_mode", -1)
        mode_map = {
            0: SymbolTradeMode.DISABLED,
            1: SymbolTradeMode.LONG_ONLY,
            2: SymbolTradeMode.SHORT_ONLY,
            3: SymbolTradeMode.CLOSE_ONLY,
            4: SymbolTradeMode.FULL,
        }
        return mode_map.get(mode, SymbolTradeMode.UNKNOWN)

    def get_swap_mode(self) -> SymbolSwapMode:
        """Get swap mode."""
        mode = self._symbol_data.get("swap_mode", -1)
        mode_map = {
            0: SymbolSwapMode.DISABLED,
            1: SymbolSwapMode.POINTS,
            2: SymbolSwapMode.CURRENCY_SYMBOL,
            3: SymbolSwapMode.CURRENCY_MARGIN,
            4: SymbolSwapMode.CURRENCY_DEPOSIT,
            5: SymbolSwapMode.INTEREST_CURRENT,
            6: SymbolSwapMode.INTEREST_OPEN,
            7: SymbolSwapMode.REOPEN_CURRENT,
            8: SymbolSwapMode.REOPEN_BID,
        }
        return mode_map.get(mode, SymbolSwapMode.UNKNOWN)

    def get_swap_rollover3days(self) -> DayOfWeek:
        """Get day of triple swap."""
        day = self._symbol_data.get("swap_rollover3days", 3)
        return DayOfWeek(day) if 0 <= day <= 6 else DayOfWeek.WEDNESDAY

    def get_trade_time_flags(self) -> int:
        """Get trade time flags."""
        return 0

    def get_trade_fill_flags(self) -> int:
        """Get trade fill flags."""
        return 0

    # Double properties
    def get_point(self) -> float:
        """Get symbol point value."""
        return float(self._symbol_data.get("point", 0.0))

    def get_tick_value(self) -> float:
        """Get tick value."""
        return float(self._symbol_data.get("trade_tick_value", 0.0))

    def get_tick_value_profit(self) -> float:
        """Get tick value for profit."""
        return float(self._symbol_data.get("trade_tick_value_profit", 0.0))

    def get_tick_value_loss(self) -> float:
        """Get tick value for loss."""
        return float(self._symbol_data.get("trade_tick_value_loss", 0.0))

    def get_tick_size(self) -> float:
        """Get tick size."""
        return float(self._symbol_data.get("trade_tick_size", 0.0))

    def get_contract_size(self) -> float:
        """Get contract size."""
        return float(self._symbol_data.get("trade_contract_size", 0.0))

    def get_lots_min(self) -> float:
        """Get minimum lots."""
        return float(self._symbol_data.get("volume_min", 0.0))

    def get_lots_max(self) -> float:
        """Get maximum lots."""
        return float(self._symbol_data.get("volume_max", 0.0))

    def get_lots_step(self) -> float:
        """Get lots step."""
        return float(self._symbol_data.get("volume_step", 0.0))

    def get_lots_limit(self) -> float:
        """Get volume limit."""
        return float(self._symbol_data.get("volume_limit", 0.0))

    def get_swap_long(self) -> float:
        """Get long swap."""
        return float(self._symbol_data.get("swap_long", 0.0))

    def get_swap_short(self) -> float:
        """Get short swap."""
        return float(self._symbol_data.get("swap_short", 0.0))

    def get_bid_high(self) -> float:
        """Get high bid."""
        return float(self._symbol_data.get("bidhigh", 0.0))

    def get_bid_low(self) -> float:
        """Get low bid."""
        return float(self._symbol_data.get("bidlow", 0.0))

    def get_ask_high(self) -> float:
        """Get high ask."""
        return float(self._symbol_data.get("askhigh", 0.0))

    def get_ask_low(self) -> float:
        """Get low ask."""
        return float(self._symbol_data.get("asklow", 0.0))

    def get_last_high(self) -> float:
        """Get high last."""
        return float(self._symbol_data.get("lasthigh", 0.0))

    def get_last_low(self) -> float:
        """Get low last."""
        return float(self._symbol_data.get("lastlow", 0.0))

    def get_margin_initial(self) -> float:
        """Get initial margin."""
        return float(self._symbol_data.get("margin_initial", 0.0))

    def get_margin_maintenance(self) -> float:
        """Get maintenance margin."""
        return float(self._symbol_data.get("margin_maintenance", 0.0))

    def get_margin_hedged_use_leg(self) -> bool:
        """Check if hedged margin uses large leg."""
        return bool(self._symbol_data.get("margin_hedged_use_leg", False))

    def get_margin_hedged(self) -> float:
        """Get hedged margin."""
        return float(self._symbol_data.get("margin_hedged", 0.0))

    def get_currency_base(self) -> str:
        """Get base currency."""
        return str(self._symbol_data.get("currency_base", ""))

    def get_currency_profit(self) -> str:
        """Get profit currency."""
        return str(self._symbol_data.get("currency_profit", ""))

    def get_currency_margin(self) -> str:
        """Get margin currency."""
        return str(self._symbol_data.get("currency_margin", ""))

    def get_bank(self) -> str:
        """Get bank."""
        return str(self._symbol_data.get("bank", ""))

    def get_description(self) -> str:
        """Get description."""
        return str(self._symbol_data.get("description", ""))

    def get_path(self) -> str:
        """Get path in symbol tree."""
        return str(self._symbol_data.get("path", ""))

    def get_start_time(self) -> datetime:
        """Get symbol start time."""
        return datetime.fromtimestamp(int(self._symbol_data.get("start_time", 0)))

    def get_expiration_time(self) -> datetime:
        """Get symbol expiration time."""
        return datetime.fromtimestamp(int(self._symbol_data.get("expiration_time", 0)))

    def get_session_deals(self) -> int:
        """Get session deals."""
        return int(self._symbol_data.get("session_deals", 0))

    def get_session_buy_orders(self) -> int:
        """Get session buy orders."""
        return int(self._symbol_data.get("session_buy_orders", 0))

    def get_session_sell_orders(self) -> int:
        """Get session sell orders."""
        return int(self._symbol_data.get("session_sell_orders", 0))

    def get_session_turnover(self) -> float:
        """Get session turnover."""
        return float(self._symbol_data.get("session_turnover", 0.0))

    def get_session_interest(self) -> float:
        """Get session interest."""
        return float(self._symbol_data.get("session_interest", 0.0))

    def get_session_buy_orders_volume(self) -> float:
        """Get session buy orders volume."""
        return float(self._symbol_data.get("session_buy_orders_volume", 0.0))

    def get_session_sell_orders_volume(self) -> float:
        """Get session sell orders volume."""
        return float(self._symbol_data.get("session_sell_orders_volume", 0.0))

    def get_session_open(self) -> float:
        """Get session open price."""
        return float(self._symbol_data.get("session_open", 0.0))

    def get_session_close(self) -> float:
        """Get session close price."""
        return float(self._symbol_data.get("session_close", 0.0))

    def get_session_aw(self) -> float:
        """Get session average weighted price."""
        return float(self._symbol_data.get("session_aw", 0.0))

    def get_session_price_settlement(self) -> float:
        """Get session settlement price."""
        return float(self._symbol_data.get("session_price_settlement", 0.0))

    def get_session_price_limit_min(self) -> float:
        """Get session minimum price limit."""
        return float(self._symbol_data.get("session_price_limit_min", 0.0))

    def get_session_price_limit_max(self) -> float:
        """Get session maximum price limit."""
        return float(self._symbol_data.get("session_price_limit_max", 0.0))

    def info_integer(self, prop_id: str) -> Optional[int]:
        """Get symbol information integer property."""
        return self._symbol_data.get(prop_id)

    def info_double(self, prop_id: str) -> Optional[float]:
        """Get symbol information double property."""
        return self._symbol_data.get(prop_id)

    def info_string(self, prop_id: str) -> Optional[str]:
        """Get symbol information string property."""
        return self._symbol_data.get(prop_id)

    def info_margin_rate(self, order_type: str) -> tuple[float, float]:
        """Get symbol margin rate."""
        return (0.0, 0.0)


class SymbolInfo:
    """
    Class for accessing symbol information.

    This class provides a clean interface to symbol information
    regardless of the underlying trading platform. It uses a data
    provider pattern to abstract platform-specific implementations.

    Usage:
        # With MT5 provider for live trading
        from apps.mt5 import MT5Client
        from apps.trade import SymbolInfo, MT5SymbolProvider

        client = MT5Client()
        client.initialize()
        provider = MT5SymbolProvider(client, "EURUSD")
        symbol = SymbolInfo(provider)

        # Access symbol information
        print(f"Bid: {symbol.bid()}")
        print(f"Ask: {symbol.ask()}")
        print(f"Spread: {symbol.spread()}")
        print(f"Digits: {symbol.digits()}")
    """

    def __init__(self, data_provider: SymbolDataProvider):
        """
        Initialize SymbolInfo.

        Args:
            data_provider: Platform-specific data provider implementing
                          SymbolDataProvider protocol.
                          Use MT5SymbolProvider for live trading.
        """
        self._provider = data_provider

    # Name and refresh methods

    def name(self, symbol_name: Optional[str] = None) -> Union[str, bool]:
        """
        Get or set symbol name.

        Args:
            symbol_name: Symbol name to set. If None, returns current name.

        Returns:
            If setting: True if successful, False otherwise.
            If getting: Current symbol name.
        """
        if symbol_name is None:
            return self._provider.get_symbol_name()
        return self._provider.set_symbol_name(symbol_name)

    def refresh(self) -> bool:
        """
        Refresh cached symbol data.

        Returns:
            True if successful, False otherwise.
        """
        return self._provider.refresh_symbol_data()

    def refresh_rates(self) -> bool:
        """
        Refresh tick data.

        Returns:
            True if successful, False otherwise.
        """
        return self._provider.refresh_tick()

    # Selection methods

    def select(self, select: Optional[bool] = None) -> bool:
        """
        Get or set symbol selection in MarketWatch.

        Args:
            select: If True, add to MarketWatch. If False, remove.
                   If None, return current selection status.

        Returns:
            Selection status or success of operation.
        """
        if select is None:
            return self._provider.get_select()
        return self._provider.set_select(select)

    def is_synchronized(self) -> bool:
        """
        Check if symbol is synchronized.

        Returns:
            True if synchronized, False otherwise.
        """
        return self._provider.is_synchronized()

    # Volume properties

    def volume(self) -> int:
        """
        Get last tick volume.

        Returns:
            Volume of last tick.
        """
        tick = self._provider.get_tick()
        return tick.volume

    def volume_high(self) -> int:
        """
        Get highest volume of the day.

        Returns:
            Highest volume.
        """
        return self._provider.get_volume_high()

    def volume_low(self) -> int:
        """
        Get lowest volume of the day.

        Returns:
            Lowest volume.
        """
        return self._provider.get_volume_low()

    # Time properties

    def time(self) -> datetime:
        """
        Get time of last tick.

        Returns:
            Time of last tick.
        """
        tick = self._provider.get_tick()
        return tick.time

    # Spread and depth

    def spread(self) -> int:
        """
        Get current spread in points.

        Returns:
            Spread in points.
        """
        return self._provider.get_spread()

    def spread_float(self) -> bool:
        """
        Check if spread is floating.

        Returns:
            True if spread is floating, False if fixed.
        """
        return self._provider.get_spread_float()

    def ticks_book_depth(self) -> int:
        """
        Get depth of market.

        Returns:
            Maximum number of requests shown in Depth of Market.
        """
        return self._provider.get_ticks_book_depth()

    # Trade levels

    def stops_level(self) -> int:
        """
        Get minimum distance for stops in points.

        Returns:
            Stops level in points.
        """
        return self._provider.get_stops_level()

    def freeze_level(self) -> int:
        """
        Get distance for freezing trade operations in points.

        Returns:
            Freeze level in points.
        """
        return self._provider.get_freeze_level()

    # Bid properties

    def bid(self) -> float:
        """
        Get current bid price.

        Returns:
            Bid price.
        """
        tick = self._provider.get_tick()
        return tick.bid

    def bid_high(self) -> float:
        """
        Get highest bid of the day.

        Returns:
            Highest bid price.
        """
        return self._provider.get_bid_high()

    def bid_low(self) -> float:
        """
        Get lowest bid of the day.

        Returns:
            Lowest bid price.
        """
        return self._provider.get_bid_low()

    # Ask properties

    def ask(self) -> float:
        """
        Get current ask price.

        Returns:
            Ask price.
        """
        tick = self._provider.get_tick()
        return tick.ask

    def ask_high(self) -> float:
        """
        Get highest ask of the day.

        Returns:
            Highest ask price.
        """
        return self._provider.get_ask_high()

    def ask_low(self) -> float:
        """
        Get lowest ask of the day.

        Returns:
            Lowest ask price.
        """
        return self._provider.get_ask_low()

    # Last properties

    def last(self) -> float:
        """
        Get price of last deal.

        Returns:
            Last price.
        """
        tick = self._provider.get_tick()
        return tick.last

    def last_high(self) -> float:
        """
        Get highest last price of the day.

        Returns:
            Highest last price.
        """
        return self._provider.get_last_high()

    def last_low(self) -> float:
        """
        Get lowest last price of the day.

        Returns:
            Lowest last price.
        """
        return self._provider.get_last_low()

    # Order and trade modes

    def order_mode(self) -> int:
        """
        Get flags of allowed order types.

        Returns:
            Order mode flags.
        """
        return self._provider.get_order_mode()

    def trade_calc_mode(self) -> SymbolCalcMode:
        """
        Get calculation mode for margin and profit.

        Returns:
            SymbolCalcMode enum value.
        """
        return self._provider.get_trade_calc_mode()

    def trade_calc_mode_description(self) -> str:
        """
        Get calculation mode as descriptive string.

        Returns:
            Human-readable description of calculation mode.
        """
        mode = self.trade_calc_mode()
        descriptions = {
            SymbolCalcMode.FOREX: "Calculation of profit and margin for Forex",
            SymbolCalcMode.CFD: "Calculation of collateral and earnings for CFD",
            SymbolCalcMode.FUTURES: "Calculation of collateral and profits for futures",
            SymbolCalcMode.CFD_INDEX: "Calculation of collateral and earnings for CFD on indices",
            SymbolCalcMode.CFD_LEVERAGE: "Calculation of collateral and earnings for the CFD when trading with leverage",
            SymbolCalcMode.EXCH_STOCKS: "Calculation for exchange stocks",
            SymbolCalcMode.EXCH_FUTURES: "Calculation for exchange futures",
            SymbolCalcMode.EXCH_FUTURES_FORTS: "Calculation for FORTS futures",
            SymbolCalcMode.UNKNOWN: "Unknown calculation mode",
        }
        return descriptions.get(mode, "Unknown calculation mode")

    def trade_mode(self) -> SymbolTradeMode:
        """
        Get order execution type.

        Returns:
            SymbolTradeMode enum value.
        """
        return self._provider.get_trade_mode()

    def trade_mode_description(self) -> str:
        """
        Get trade mode as descriptive string.

        Returns:
            Human-readable description of trade mode.
        """
        mode = self.trade_mode()
        descriptions = {
            SymbolTradeMode.DISABLED: "Disabled",
            SymbolTradeMode.LONG_ONLY: "Long only",
            SymbolTradeMode.SHORT_ONLY: "Short only",
            SymbolTradeMode.CLOSE_ONLY: "Close only",
            SymbolTradeMode.FULL: "Full access",
            SymbolTradeMode.UNKNOWN: "Unknown trade mode",
        }
        return descriptions.get(mode, "Unknown trade mode")

    def trade_execution(self) -> SymbolTradeExecution:
        """
        Get trade execution mode.

        Returns:
            SymbolTradeExecution enum value.
        """
        return self._provider.get_trade_execution()

    def trade_execution_description(self) -> str:
        """
        Get trade execution mode as descriptive string.

        Returns:
            Human-readable description of execution mode.
        """
        mode = self.trade_execution()
        descriptions = {
            SymbolTradeExecution.REQUEST: "Trading on request",
            SymbolTradeExecution.INSTANT: "Trading on live streaming prices",
            SymbolTradeExecution.MARKET: "Execution of orders on the market",
            SymbolTradeExecution.EXCHANGE: "Exchange execution",
            SymbolTradeExecution.UNKNOWN: "Unknown trade execution",
        }
        return descriptions.get(mode, "Unknown trade execution")

    # Swap properties

    def swap_mode(self) -> SymbolSwapMode:
        """
        Get swap calculation model.

        Returns:
            SymbolSwapMode enum value.
        """
        return self._provider.get_swap_mode()

    def swap_mode_description(self) -> str:
        """
        Get swap mode as descriptive string.

        Returns:
            Human-readable description of swap mode.
        """
        mode = self.swap_mode()
        descriptions = {
            SymbolSwapMode.DISABLED: "No swaps",
            SymbolSwapMode.POINTS: "Swaps are calculated in points",
            SymbolSwapMode.CURRENCY_SYMBOL: "Swaps are calculated in base currency",
            SymbolSwapMode.CURRENCY_MARGIN: "Swaps are calculated in margin currency",
            SymbolSwapMode.CURRENCY_DEPOSIT: "Swaps are calculated in deposit currency",
            SymbolSwapMode.INTEREST_CURRENT: "Swaps are calculated as annual interest using the current price",
            SymbolSwapMode.INTEREST_OPEN: "Swaps are calculated as annual interest using the open price",
            SymbolSwapMode.REOPEN_CURRENT: "Swaps are charged by reopening positions at the close price",
            SymbolSwapMode.REOPEN_BID: "Swaps are charged by reopening positions at the Bid price",
            SymbolSwapMode.UNKNOWN: "Unknown swap mode",
        }
        return descriptions.get(mode, "Unknown swap mode")

    def swap_rollover3days(self) -> DayOfWeek:
        """
        Get day of week with triple swap.

        Returns:
            DayOfWeek enum value.
        """
        return self._provider.get_swap_rollover3days()

    def swap_rollover3days_description(self) -> str:
        """
        Get triple swap day as descriptive string.

        Returns:
            Day name.
        """
        day = self.swap_rollover3days()
        descriptions = {
            DayOfWeek.SUNDAY: "Sunday",
            DayOfWeek.MONDAY: "Monday",
            DayOfWeek.TUESDAY: "Tuesday",
            DayOfWeek.WEDNESDAY: "Wednesday",
            DayOfWeek.THURSDAY: "Thursday",
            DayOfWeek.FRIDAY: "Friday",
            DayOfWeek.SATURDAY: "Saturday",
        }
        return descriptions.get(day, "Unknown")

    def swap_long(self) -> float:
        """
        Get long swap value.

        Returns:
            Long position swap value.
        """
        return self._provider.get_swap_long()

    def swap_short(self) -> float:
        """
        Get short swap value.

        Returns:
            Short position swap value.
        """
        return self._provider.get_swap_short()

    # Futures dates

    def start_time(self) -> datetime:
        """
        Get symbol start time (for futures).

        Returns:
            Date of symbol trade beginning.
        """
        return self._provider.get_start_time()

    def expiration_time(self) -> datetime:
        """
        Get symbol expiration time (for futures).

        Returns:
            Date of symbol trade end.
        """
        return self._provider.get_expiration_time()

    # Margin properties

    def margin_initial(self) -> float:
        """
        Get initial margin.

        Returns:
            Initial margin value.
        """
        return self._provider.get_margin_initial()

    def margin_maintenance(self) -> float:
        """
        Get maintenance margin.

        Returns:
            Maintenance margin value.
        """
        return self._provider.get_margin_maintenance()

    def margin_hedged_use_leg(self) -> bool:
        """
        Check if hedged margin calculation uses larger leg.

        Returns:
            True if using larger leg, False otherwise.
        """
        return self._provider.get_margin_hedged_use_leg()

    def margin_hedged(self) -> float:
        """
        Get hedged margin.

        Returns:
            Hedged margin value.
        """
        return self._provider.get_margin_hedged()

    # Deprecated margin methods (left for backward compatibility)

    def margin_long(self) -> float:
        """Get long margin (deprecated)."""
        return 0.0

    def margin_short(self) -> float:
        """Get short margin (deprecated)."""
        return 0.0

    def margin_limit(self) -> float:
        """Get limit margin (deprecated)."""
        return 0.0

    def margin_stop(self) -> float:
        """Get stop margin (deprecated)."""
        return 0.0

    def margin_stop_limit(self) -> float:
        """Get stop limit margin (deprecated)."""
        return 0.0

    # Trade flags

    def trade_time_flags(self) -> int:
        """
        Get trade time flags.

        Returns:
            Flags for allowed order expiration modes.
        """
        return self._provider.get_trade_time_flags()

    def trade_fill_flags(self) -> int:
        """
        Get trade fill flags.

        Returns:
            Flags for allowed order filling modes.
        """
        return self._provider.get_trade_fill_flags()

    # Tick parameters

    def digits(self) -> int:
        """
        Get number of decimal places.

        Returns:
            Number of digits after decimal point.
        """
        return self._provider.get_digits()

    def point(self) -> float:
        """
        Get point value.

        Returns:
            Point size in quote currency.
        """
        return self._provider.get_point()

    def tick_value(self) -> float:
        """
        Get tick value in account currency.

        Returns:
            Tick value.
        """
        return self._provider.get_tick_value()

    def tick_value_profit(self) -> float:
        """
        Get tick value for profit calculation.

        Returns:
            Tick value for profitable positions.
        """
        return self._provider.get_tick_value_profit()

    def tick_value_loss(self) -> float:
        """
        Get tick value for loss calculation.

        Returns:
            Tick value for losing positions.
        """
        return self._provider.get_tick_value_loss()

    def tick_size(self) -> float:
        """
        Get tick size.

        Returns:
            Minimum price change.
        """
        return self._provider.get_tick_size()

    # Lot parameters

    def contract_size(self) -> float:
        """
        Get contract size.

        Returns:
            Trade contract size.
        """
        return self._provider.get_contract_size()

    def lots_min(self) -> float:
        """
        Get minimum lot size.

        Returns:
            Minimum volume for a deal.
        """
        return self._provider.get_lots_min()

    def lots_max(self) -> float:
        """
        Get maximum lot size.

        Returns:
            Maximum volume for a deal.
        """
        return self._provider.get_lots_max()

    def lots_step(self) -> float:
        """
        Get lot step.

        Returns:
            Minimal volume change step.
        """
        return self._provider.get_lots_step()

    def lots_limit(self) -> float:
        """
        Get maximum aggregate volume.

        Returns:
            Maximum allowed aggregate volume.
        """
        return self._provider.get_lots_limit()

    # Currency properties

    def currency_base(self) -> str:
        """
        Get base currency.

        Returns:
            Basic currency of a symbol.
        """
        return self._provider.get_currency_base()

    def currency_profit(self) -> str:
        """
        Get profit currency.

        Returns:
            Profit currency.
        """
        return self._provider.get_currency_profit()

    def currency_margin(self) -> str:
        """
        Get margin currency.

        Returns:
            Margin currency.
        """
        return self._provider.get_currency_margin()

    def bank(self) -> str:
        """
        Get source of current quote.

        Returns:
            Name of the bank providing quotes.
        """
        return self._provider.get_bank()

    def description(self) -> str:
        """
        Get symbol description.

        Returns:
            Symbol description.
        """
        return self._provider.get_description()

    def path(self) -> str:
        """
        Get symbol path in symbol tree.

        Returns:
            Path in the symbol tree.
        """
        return self._provider.get_path()

    # Session properties

    def session_deals(self) -> int:
        """
        Get number of deals in current session.

        Returns:
            Number of deals.
        """
        return self._provider.get_session_deals()

    def session_buy_orders(self) -> int:
        """
        Get number of buy orders in current session.

        Returns:
            Number of buy orders.
        """
        return self._provider.get_session_buy_orders()

    def session_sell_orders(self) -> int:
        """
        Get number of sell orders in current session.

        Returns:
            Number of sell orders.
        """
        return self._provider.get_session_sell_orders()

    def session_turnover(self) -> float:
        """
        Get turnover in current session.

        Returns:
            Total turnover.
        """
        return self._provider.get_session_turnover()

    def session_interest(self) -> float:
        """
        Get open interest.

        Returns:
            Open interest value.
        """
        return self._provider.get_session_interest()

    def session_buy_orders_volume(self) -> float:
        """
        Get buy orders volume in current session.

        Returns:
            Current volume of buy orders.
        """
        return self._provider.get_session_buy_orders_volume()

    def session_sell_orders_volume(self) -> float:
        """
        Get sell orders volume in current session.

        Returns:
            Current volume of sell orders.
        """
        return self._provider.get_session_sell_orders_volume()

    def session_open(self) -> float:
        """
        Get session open price.

        Returns:
            Open price.
        """
        return self._provider.get_session_open()

    def session_close(self) -> float:
        """
        Get session close price.

        Returns:
            Close price.
        """
        return self._provider.get_session_close()

    def session_aw(self) -> float:
        """
        Get average weighted price.

        Returns:
            Average weighted price.
        """
        return self._provider.get_session_aw()

    def session_price_settlement(self) -> float:
        """
        Get settlement price.

        Returns:
            Settlement price.
        """
        return self._provider.get_session_price_settlement()

    def session_price_limit_min(self) -> float:
        """
        Get minimum price limit.

        Returns:
            Minimum price for the session.
        """
        return self._provider.get_session_price_limit_min()

    def session_price_limit_max(self) -> float:
        """
        Get maximum price limit.

        Returns:
            Maximum price for the session.
        """
        return self._provider.get_session_price_limit_max()

    # Direct API access methods

    def info_integer(self, prop_id: str) -> Optional[int]:
        """
        Get integer property by ID.

        Args:
            prop_id: Property identifier.

        Returns:
            Property value or None if not available.
        """
        return self._provider.info_integer(prop_id)

    def info_double(self, prop_id: str) -> Optional[float]:
        """
        Get double property by ID.

        Args:
            prop_id: Property identifier.

        Returns:
            Property value or None if not available.
        """
        return self._provider.info_double(prop_id)

    def info_string(self, prop_id: str) -> Optional[str]:
        """
        Get string property by ID.

        Args:
            prop_id: Property identifier.

        Returns:
            Property value or None if not available.
        """
        return self._provider.info_string(prop_id)

    def info_margin_rate(self, order_type: str) -> tuple[float, float]:
        """
        Get margin rates for order type.

        Args:
            order_type: Order type identifier.

        Returns:
            Tuple of (initial_margin_rate, maintenance_margin_rate).
        """
        return self._provider.info_margin_rate(order_type)

    # Service methods

    def normalize_price(self, price: float) -> float:
        """
        Normalize price to symbol's precision.

        Args:
            price: Price to normalize.

        Returns:
            Normalized price.
        """
        tick_size = self.tick_size()
        digits = self.digits()

        if tick_size != 0:
            return round(round(price / tick_size) * tick_size, digits)

        return round(price, digits)

    def check_market_watch(self) -> bool:
        """
        Check if symbol is in MarketWatch and add if necessary.

        Returns:
            True if symbol is available, False otherwise.
        """
        if not self.select() and not self.select(True):
            logger.error(
                "SymbolInfo.check_market_watch: Error adding symbol to MarketWatch"
            )
            return False
        return True

    def __repr__(self) -> str:
        """Return string representation of SymbolInfo."""
        try:
            return (
                f"SymbolInfo(name={self.name()}, "
                f"bid={self.bid():.{self.digits()}f}, "
                f"ask={self.ask():.{self.digits()}f}, "
                f"spread={self.spread()})"
            )
        except Exception:
            return "SymbolInfo(no symbol selected)"
