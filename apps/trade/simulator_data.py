"""
Simulator Data Objects.

This module provides data objects that mirror the structure of MT5 API responses.
These objects can be used to inject custom data for backtesting or simulation,
mimicking the exact format expected by the trading application.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple

from apps.mt5 import get_mt5_api

mt5 = get_mt5_api()


def _get_mt5_val(attr: str, default: Any) -> Any:
    """Safely get value from MT5 account info or return default."""
    try:
        # Check if mt5 is initialized? mt5.account_info() returns None if not.
        info = mt5.account_info()
        if info is None:
            return default
        # Handle both dict-like and object-like access if necessary,
        # but getattr is safest for the named tuple structure usually returned.
        return getattr(info, attr, default)
    except Exception:
        return default


def _get_mt5_symbol_val(symbol: str, attr: str, default: Any) -> Any:
    """Safely get value from MT5 symbol info or return default."""
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            return default
        return getattr(info, attr, default)
    except Exception:
        return default


@dataclass
class AccountInfoSimulator:
    """
    Data structure mirroring MT5 AccountInfo.

    This class contains all fields returned by mt5.account_info() as default values.
    Values can be overridden by passing a custom AccountInfoSimulator object to the SimulatorClient.
    """

    # Integer properties
    login: int = 12345678
    trade_mode: int = field(
        default_factory=lambda: _get_mt5_val("trade_mode", 0)
    )  # 0: Demo, 1: Contest, 2: Real
    leverage: int = field(default_factory=lambda: _get_mt5_val("leverage", 100))
    limit_orders: int = field(default_factory=lambda: _get_mt5_val("limit_orders", 0))
    margin_so_mode: int = field(
        default_factory=lambda: _get_mt5_val("margin_so_mode", 0)
    )  # 0: Percent, 1: Money
    trade_allowed: bool = field(
        default_factory=lambda: _get_mt5_val("trade_allowed", True)
    )
    trade_expert: bool = field(
        default_factory=lambda: _get_mt5_val("trade_expert", True)
    )
    margin_mode: int = field(
        default_factory=lambda: _get_mt5_val("margin_mode", 0)
    )  # 0: Retail Hedging
    currency_digits: int = field(
        default_factory=lambda: _get_mt5_val("currency_digits", 2)
    )
    fifo_close: bool = field(default_factory=lambda: _get_mt5_val("fifo_close", False))

    # Double properties
    balance: float = 10000
    credit: float = 0
    profit: float = 0
    equity: float = 0
    margin: float = 0
    margin_free: float = 10000
    margin_level: float = 0
    margin_so_call: float = field(
        default_factory=lambda: _get_mt5_val("margin_so_call", 50.0)
    )
    margin_so_so: float = field(
        default_factory=lambda: _get_mt5_val("margin_so_so", 30.0)
    )
    margin_initial: float = 0
    margin_maintenance: float = 0
    assets: float = 0
    liabilities: float = 0
    commission_blocked: float = 0

    # String properties
    name: str = "Simulated Trader"
    server: str = "Sim-Server"
    currency: str = field(default_factory=lambda: _get_mt5_val("currency", "USD"))
    company: str = "Simulated Company"

    def _asdict(self) -> Dict[str, Any]:
        """Return the object as a dictionary."""
        return asdict(self)

    @classmethod
    def from_mt5_account(cls) -> "AccountInfoSimulator":
        """
        Create AccountInfoSimulator populated with current MT5 account info.

        Returns:
            AccountInfoSimulator object populated with live data, or default if not connected.
        """
        info = mt5.account_info()
        if info is None:
            return cls()

        data = info._asdict()
        return cls(**data)


@dataclass
class SymbolTickSimulator:
    """Data structure mirroring MT5 symbol_info_tick."""

    time: int = field(default_factory=lambda: 0)
    bid: float = field(default_factory=lambda: 0.0)
    ask: float = field(default_factory=lambda: 0.0)
    last: float = field(default_factory=lambda: 0.0)
    volume: int = field(default_factory=lambda: 0)
    time_msc: int = field(default_factory=lambda: 0)
    flags: int = field(default_factory=lambda: 0)
    volume_real: float = field(default_factory=lambda: 0.0)

    def _asdict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SymbolInfoSimulator:
    """Data structure mirroring MT5 symbol_info."""

    # Common properties
    symbol: str = "EURUSD"
    digits: int = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "digits", 5)
    )
    spread: int = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "spread", 10)
    )
    spread_float: bool = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "spread_float", True)
    )
    point: float = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "point", 0.00001)
    )

    # Trade properties
    trade_calc_mode: int = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "trade_calc_mode", 0)
    )
    trade_mode: int = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "trade_mode", 4)
    )  # Full access
    start_time: int = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "start_time", 0)
    )
    expiration_time: int = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "expiration_time", 0)
    )
    trade_stops_level: int = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "trade_stops_level", 0)
    )
    trade_freeze_level: int = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "trade_freeze_level", 0)
    )
    trade_exemode: int = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "trade_exemode", 1)
    )  # Instant

    # Volume properties
    volume_min: float = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "volume_min", 0.01)
    )
    volume_max: float = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "volume_max", 100.0)
    )
    volume_step: float = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "volume_step", 0.01)
    )
    volume_limit: float = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "volume_limit", 0.0)
    )

    # Value properties
    trade_tick_value: float = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "trade_tick_value", 1.0)
    )
    trade_tick_value_profit: float = field(
        default_factory=lambda: _get_mt5_symbol_val(
            "EURUSD", "trade_tick_value_profit", 1.0
        )
    )
    trade_tick_value_loss: float = field(
        default_factory=lambda: _get_mt5_symbol_val(
            "EURUSD", "trade_tick_value_loss", 1.0
        )
    )
    trade_tick_size: float = field(
        default_factory=lambda: _get_mt5_symbol_val(
            "EURUSD", "trade_tick_size", 0.00001
        )
    )
    trade_contract_size: float = field(
        default_factory=lambda: _get_mt5_symbol_val(
            "EURUSD", "trade_contract_size", 100000.0
        )
    )

    # Swap properties
    swap_mode: int = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "swap_mode", 1)
    )
    swap_long: float = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "swap_long", -1.0)
    )
    swap_short: float = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "swap_short", -1.0)
    )
    swap_rollover3days: int = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "swap_rollover3days", 3)
    )

    # Margin properties
    margin_initial: float = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "margin_initial", 0.0)
    )
    margin_maintenance: float = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "margin_maintenance", 0.0)
    )

    # Strings
    currency_base: str = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "currency_base", "EUR")
    )
    currency_profit: str = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "currency_profit", "USD")
    )
    currency_margin: str = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "currency_margin", "EUR")
    )
    description: str = field(
        default_factory=lambda: _get_mt5_symbol_val(
            "EURUSD", "description", "Euro vs US Dollar"
        )
    )
    path: str = field(
        default_factory=lambda: _get_mt5_symbol_val("EURUSD", "path", "Forex\\EURUSD")
    )

    # Dynamic fields for prices (often duplicates of tick)
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0

    select: bool = True
    visible: bool = True

    def _asdict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mt5_symbol(cls, symbol_name: str) -> "SymbolInfoSimulator":
        """Create from MT5 symbol info."""
        info = mt5.symbol_info(symbol_name)
        if info is None:
            # Fallback to default with provided name
            sim = cls()
            sim.symbol = symbol_name
            return sim

        data = info._asdict()
        from dataclasses import fields

        valid = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid}
        return cls(**filtered)


@dataclass
class TradeRecordSimulator:
    """Base class for trade records (Deals, Orders, Positions)."""

    ticket: int = 0
    time: int = 0
    time_msc: int = 0
    time_update: int = 0
    time_update_msc: int = 0
    type: int = 0
    magic: int = 0
    identifier: int = 0
    reason: int = 0
    volume: float = 0.0
    price_open: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    price_current: float = 0.0
    price_sl: float = 0.0
    price_tp: float = 0.0
    symbol: str = ""
    comment: str = ""
    external_id: str = ""

    def _asdict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DealInfoSimulator(TradeRecordSimulator):
    """Data structure for Deal Info."""

    commission: float = 0.0
    swap: float = 0.0
    profit: float = 0.0
    fee: float = 0.0
    entry: int = 0
    order: int = 0
    price: float = 0.0


@dataclass
class OrderInfoSimulator(TradeRecordSimulator):
    """Data structure for Order Info (Active)."""

    state: int = 0
    time_expiration: int = 0
    type_time: int = 0
    type_filling: int = 0
    volume_initial: float = 0.0
    volume_current: float = 0.0
    price_stoplimit: float = 0.0


@dataclass
class HistoryOrderInfoSimulator(OrderInfoSimulator):
    """Data structure for History Order Info."""

    time_done: int = 0
    time_done_msc: int = 0
    time_setup: int = 0
    time_setup_msc: int = 0


@dataclass
class PositionInfoSimulator(TradeRecordSimulator):
    """Data structure for Position Info."""

    volume: float = 0.0  # Re-declare? Inherited.
    swap: float = 0.0
    profit: float = 0.0


@dataclass
class TerminalInfoSimulator:
    """Data structure mirroring MT5 TerminalInfo."""

    community_account: bool = True
    community_connection: bool = True
    connected: bool = True
    dlls_allowed: bool = True
    trade_allowed: bool = True
    tradeapi_disabled: bool = False
    email_enabled: bool = False
    ftp_enabled: bool = False
    notifications_enabled: bool = False
    mqid: bool = False
    build: int = 2980
    maxbars: int = 100000
    codepage: int = 1251
    ping_last: int = 50000
    community_balance: float = 0.0
    retransmission: float = 0.0
    company: str = "Simulated Company"
    name: str = "Simulated Terminal"
    language: str = "English"
    path: str = "C:\\Data\\Simulated\\Terminal"
    data_path: str = "C:\\Data\\Simulated\\Terminal"
    commondata_path: str = "C:\\Data\\Simulated\\Common"

    def _asdict(self) -> Dict[str, Any]:
        return asdict(self)


class SimulatorClient:
    """
    Simulator API adapter.

    This class acts as a drop-in replacement for the `mt5` module,
    providing simulated data.
    """

    def __init__(
        self,
        account_data: Optional[AccountInfoSimulator] = None,
        symbols_data: Optional[Dict[str, SymbolInfoSimulator]] = None,
        ticks_data: Optional[Dict[str, SymbolTickSimulator]] = None,
        deals_data: Optional[Dict[int, DealInfoSimulator]] = None,
        orders_data: Optional[Dict[int, OrderInfoSimulator]] = None,
        history_orders_data: Optional[Dict[int, HistoryOrderInfoSimulator]] = None,
        positions_data: Optional[Dict[int, PositionInfoSimulator]] = None,
        terminal_data: Optional[TerminalInfoSimulator] = None,
    ):
        """Initialize simulator with data."""
        self._account_data = account_data if account_data else AccountInfoSimulator()
        self._symbols_data = symbols_data if symbols_data else {}
        self._ticks_data = ticks_data if ticks_data else {}
        self._deals_data = deals_data if deals_data else {}
        self._orders_data = orders_data if orders_data else {}
        self._history_orders_data = history_orders_data if history_orders_data else {}
        self._positions_data = positions_data if positions_data else {}
        self._terminal_data = (
            terminal_data if terminal_data else TerminalInfoSimulator()
        )

        # Initialize some default symbols if empty
        if not self._symbols_data:
            euro = SymbolInfoSimulator(symbol="EURUSD", bid=1.1000, ask=1.1002)
            gbp = SymbolInfoSimulator(symbol="GBPUSD", bid=1.2500, ask=1.2503)
            self._symbols_data["EURUSD"] = euro
            self._symbols_data["GBPUSD"] = gbp

    def version(self) -> Tuple[int, int, str]:
        """Get simulated terminal version."""
        return (500, 2980, "25 Mar 2021")

    def account_info(self) -> AccountInfoSimulator:
        """Get simulated account info."""
        return self._account_data

    def terminal_info(self) -> TerminalInfoSimulator:
        """Get simulated terminal info."""
        return self._terminal_data

    def symbol_info(self, symbol: str) -> Optional[SymbolInfoSimulator]:
        """Get simulated symbol info."""
        return self._symbols_data.get(symbol)

    def symbol_info_tick(self, symbol: str) -> Optional[SymbolTickSimulator]:
        """Get simulated symbol tick."""
        return self._ticks_data.get(symbol)

    def order_check(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate order check."""
        return {
            "retcode": 0,
            "balance": 10000.0,
            "equity": 10000.0,
            "profit": 0.0,
            "margin": 0.0,
            "margin_free": 10000.0,
            "margin_level": 0.0,
            "comment": "Simulated check",
        }

    def order_send(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate order send."""
        # Simple simulation: always success
        return {
            "retcode": 10009,  # TRADE_RETCODE_DONE
            "deal": 123456,
            "order": 654321,
            "volume": request.get("volume", 0.0),
            "price": request.get("price", 0.0),
            "bid": 0.0,
            "ask": 0.0,
            "comment": "Simulated executed",
            "request_id": 0,
            "retcode_external": 0,
        }

    def order_calc_margin(
        self, action: int, symbol: str, volume: float, price: float
    ) -> Optional[float]:
        """Calculate margin required for the order."""
        return volume * price * 0.01

    def order_calc_profit(
        self,
        action: int,
        symbol: str,
        volume: float,
        price_open: float,
        price_close: float,
    ) -> Optional[float]:
        """Calculate profit for the order."""
        diff = price_close - price_open
        if action == 1:  # SELL
            diff = -diff
        return volume * diff * 100000.0

    def history_deals_get(
        self, *args, **kwargs
    ) -> Optional[Tuple[DealInfoSimulator, ...]]:
        """
        Get history deals.

        Supports overloaded signatures:
        - history_deals_get(date_from, date_to, group="")
        - history_deals_get(ticket=...)
        - history_deals_get(position=...)
        """
        # If args provided, assume (from, to, group)
        if len(args) >= 2:
            return tuple(self._deals_data.values())

        ticket = kwargs.get("ticket")
        if ticket is not None:
            d = self._deals_data.get(ticket)
            return (d,) if d else None

        return tuple(self._deals_data.values())

    def orders_get(
        self,
        ticket: Optional[int] = None,
        symbol: Optional[str] = None,
        group: Optional[str] = None,
    ) -> Optional[Tuple[OrderInfoSimulator, ...]]:
        """Get active orders."""
        if ticket is not None:
            d = self._orders_data.get(ticket)
            return (d,) if d else None
        return tuple(self._orders_data.values())

    def history_orders_get(
        self, *args, **kwargs
    ) -> Optional[Tuple[HistoryOrderInfoSimulator, ...]]:
        """
        Get history orders.

        Supports overloaded signatures:
        - history_orders_get(date_from, date_to, group="")
        - history_orders_get(ticket=...)
        - history_orders_get(position=...)
        """
        if len(args) >= 2:
            return tuple(self._history_orders_data.values())

        ticket = kwargs.get("ticket")
        if ticket is not None:
            d = self._history_orders_data.get(ticket)
            return (d,) if d else None
        return tuple(self._history_orders_data.values())

    def positions_get(
        self,
        ticket: Optional[int] = None,
        symbol: Optional[str] = None,
        group: Optional[str] = None,
    ) -> Optional[Tuple[PositionInfoSimulator, ...]]:
        """Get positions."""
        if ticket is not None:
            d = self._positions_data.get(ticket)
            return (d,) if d else None
        return tuple(self._positions_data.values())

    def last_error(self) -> tuple[int, str]:
        """Get last error."""
        return (1, "Success")
