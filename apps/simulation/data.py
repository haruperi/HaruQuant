"""
Simulator Data Objects.

This module provides data objects that mirror the structure of MT5 API responses.
These objects can be used to inject custom data for backtesting or simulation,
mimicking the exact format expected by the trading application.

Classes:
    AccountInfoSimulator: Data structure mirroring MT5 AccountInfo.
    SymbolTickSimulator: Data structure mirroring MT5 symbol_info_tick.
    SymbolInfoSimulator: Data structure mirroring MT5 symbol_info.
    TradeRecordSimulator: Data structure mirroring MT5 TradeRecord.
    DealInfoSimulator: Data structure mirroring MT5 DealInfo.
    OrderInfoSimulator: Data structure mirroring MT5 OrderInfo.
    HistoryOrderInfoSimulator: Data structure mirroring MT5 HistoryOrderInfo.
    PositionInfoSimulator: Data structure mirroring MT5 PositionInfo.
    TerminalInfoSimulator: Data structure mirroring MT5 TerminalInfo.
    SimulatorClient: Client for simulating MT5 API.

Functions:
    _get_mt5_val: Safely get value from MT5 account info or return default.
    _get_mt5_symbol_val: Safely get value from MT5 symbol info or return default.

"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from apps.logger import logger
from apps.mt5 import get_mt5_api
from apps.simulation.utils import PositionArrayState
from apps.utils.error_description import TradeErrorDescriptions

mt5 = get_mt5_api()

if TYPE_CHECKING:
    from apps.utils.validate import TradeValidator


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
    commission_blocked: float = field(
        default_factory=lambda: _get_mt5_val("commission_blocked", 0.0)
    )

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
    # Simulator-specific convenience fields
    open_price: float = 0.0
    margin_required: float = 0.0
    expiry_date: Optional[object] = None
    expiration_mode: str = "gtc"


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

    volume: float = 0.0
    commission: float = 0.0
    fee: float = 0.0
    swap: float = 0.0
    profit: float = 0.0
    margin_required: float = 0.0

    def _asdict(self) -> Dict[str, Any]:
        """Return the object as a dictionary with 'id' field for Trade class compatibility."""
        data = asdict(self)
        # Add 'id' field that Trade class expects (maps to ticket/identifier)
        data["id"] = data.get("ticket") or data.get("identifier", 0)
        return data


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

    A Low-Level API (SimulatorClient mimics MT5 API)
    providing raw API methods that the real MT5 provides.

    This class acts as a drop-in replacement for the `mt5` module,
    providing simulated data.

    Any Business Logic (PositionInfo, OrderInfo, etc.) should be implemented in the High-Level API classes.
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
        mt5_client=None,
    ):
        """Initialize simulator with data."""
        self._account_data = (
            account_data if account_data is not None else AccountInfoSimulator()
        )
        self._symbols_data = symbols_data if symbols_data is not None else {}
        self._ticks_data = ticks_data if ticks_data is not None else {}
        self._deals_data = deals_data if deals_data is not None else {}
        self._orders_data = orders_data if orders_data is not None else {}
        self._history_orders_data = (
            history_orders_data if history_orders_data is not None else {}
        )
        self._positions_data = positions_data if positions_data is not None else {}
        self._terminal_data = (
            terminal_data if terminal_data else TerminalInfoSimulator()
        )
        self._mt5_client = mt5_client
        self._position_array_state: Optional[PositionArrayState] = None

        # Initialize some default symbols if empty
        if not self._symbols_data:
            euro = SymbolInfoSimulator(symbol="EURUSD", bid=1.1000, ask=1.1002)
            gbp = SymbolInfoSimulator(symbol="GBPUSD", bid=1.2500, ask=1.2503)
            self._symbols_data["EURUSD"] = euro
            self._symbols_data["GBPUSD"] = gbp

        # Internal counters for IDs
        self._next_position_id = 1
        self._next_order_id = 100000
        self._next_deal_id = 200000
        self._validator: Optional[TradeValidator] = None
        self._fast_backtest = False
        self._backtest_commission_per_contract = 0.0
        self._backtest_slippage_points = 0.0

    def _calc_close_costs(
        self,
        symbol_info: SymbolInfoSimulator,
        pos_type: int,
        volume: float,
        open_time: int,
        close_time: int,
    ) -> tuple[float, float, float]:
        """Compute commission, fee, and swap for a closed volume."""
        commission_per_contract = float(
            getattr(self, "_backtest_commission_per_contract", 0.0) or 0.0
        )
        commission = commission_per_contract * float(volume)
        if commission > 0:
            commission = -commission

        fee = 0.0
        swap = 0.0
        swap_mode = int(getattr(symbol_info, "swap_mode", 0) or 0)
        if swap_mode != 0 and open_time and close_time:
            swap_long = float(getattr(symbol_info, "swap_long", 0.0) or 0.0)
            swap_short = float(getattr(symbol_info, "swap_short", 0.0) or 0.0)
            swap_rate = swap_long if pos_type == mt5.ORDER_TYPE_BUY else swap_short
            rollover_day = int(getattr(symbol_info, "swap_rollover3days", -1) or -1)

            open_dt = datetime.utcfromtimestamp(int(open_time))
            close_dt = datetime.utcfromtimestamp(int(close_time))
            days = (close_dt.date() - open_dt.date()).days
            if days > 0:
                swap_days = 0
                for step in range(1, days + 1):
                    day = open_dt.date() + timedelta(days=step)
                    if rollover_day in range(7) and day.weekday() == rollover_day:
                        swap_days += 3
                    else:
                        swap_days += 1
                swap = float(swap_rate) * float(volume) * float(swap_days)

        return float(commission), float(fee), float(swap)

    def version(self) -> Tuple[int, int, str]:
        """Get simulated terminal version."""
        return (500, 2980, "25 Mar 2026")

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

    def symbol_select(self, symbol: str, select: bool) -> bool:
        """Select/deselect symbol in Market Watch (simulated)."""
        if symbol in self._symbols_data:
            self._symbols_data[symbol].select = select
            return True
        return False

    def order_check(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate order check."""
        logger.debug("Running order_check in simulator not real mt5")
        return {
            "retcode": 10009,  # TRADE_RETCODE_DONE
            "balance": self._account_data.balance,
            "equity": self._account_data.equity,
            "profit": 0.0,
            "margin": 0.0,
            "margin_free": self._account_data.margin_free,
            "margin_level": 0.0,
            "comment": "Simulated check",
        }

    def _archive_order(
        self,
        order: OrderInfoSimulator,
        state: int,
        done_time: int,
    ) -> None:
        """
        Move an active pending order into history.

        This mirrors MT5 behavior where closed/canceled/expired orders
        appear in history_orders_get.
        """
        data = asdict(order)
        history = HistoryOrderInfoSimulator(**data)
        history.state = int(state)
        history.time_done = int(done_time)
        history.time_done_msc = int(done_time * 1000)
        history.time_setup = int(data.get("time", done_time))
        history.time_setup_msc = int(data.get("time_msc", done_time * 1000))
        self._history_orders_data[int(history.ticket)] = history

    def order_send(self, request: Dict[str, Any]) -> Dict[str, Any]:  # noqa: C901
        """
        Simulate order send by updating data containers.

        This method mirrors MT5's order_send behavior:
        - Validates requests.
        - Applies MT5-style rules for prices, stops, lot sizes, and freezes.
        - Updates orders, positions, deals, and history containers.
        """
        import time

        logger.debug("Running order_send in simulator (MT5-like)")

        fast_backtest = bool(getattr(self, "_fast_backtest", False))
        validator: Optional[TradeValidator] = None
        if not fast_backtest:
            validator = self._validator
            if validator is None:
                from apps.utils.validate import TradeValidator

                new_validator = TradeValidator(mt5_instance=self)
                validator = new_validator
                self._validator = new_validator

            # Normalize request structure so all MT5 fields exist.
            # This mirrors MqlTradeRequest fields and keeps downstream logic stable.
            req = {
                "action": request.get("action"),
                "magic": request.get("magic", 0),
                "order": request.get("order", 0),
                "symbol": request.get("symbol", ""),
                "volume": request.get("volume", 0.0),
                "price": request.get("price", 0.0),
                "stoplimit": request.get("stoplimit", 0.0),
                "sl": request.get("sl", 0.0),
                "tp": request.get("tp", 0.0),
                "deviation": request.get("deviation", 0),
                "type": request.get("type", 0),
                "type_filling": request.get("type_filling", 0),
                "type_time": request.get("type_time", 0),
                "expiration": request.get("expiration", 0),
                "comment": request.get("comment", ""),
                "position": request.get("position", 0),
                "position_by": request.get("position_by", 0),
            }
        else:
            req = request

        def _response(retcode: int, comment: str, **kwargs: Any) -> Dict[str, Any]:
            """Build an MT5-like response structure."""
            base = {
                "retcode": int(retcode),
                "deal": 0,
                "order": 0,
                "volume": float(req.get("volume", 0.0) or 0.0),
                "price": float(req.get("price", 0.0) or 0.0),
                "bid": 0.0,
                "ask": 0.0,
                "comment": comment,
                "request_id": 0,
                "retcode_external": 0,
            }
            base.update(kwargs)
            return base

        def _validate(name: str, value: Any, **kwargs: Any) -> tuple[bool, str]:
            """Fast-backtest-safe validation wrapper."""
            if validator is None:
                return True, ""
            return validator.validate(name, value, **kwargs)

        # Quick environment checks (trade permissions).
        if (
            not self._terminal_data.trade_allowed
            or not self._account_data.trade_allowed
        ):
            return _response(10017, "Trade is disabled")
        if self._terminal_data.tradeapi_disabled:
            return _response(10027, "Autotrading disabled by client")

        action = req.get("action")
        if action is None:
            return _response(10013, "Invalid request: missing action")

        current_time = int(time.time())

        # Resolve symbol/tick info when a symbol is required.
        symbol = str(req.get("symbol") or "")
        symbol_info = self._symbols_data.get(symbol) if symbol else None
        tick = self._ticks_data.get(symbol) if symbol else None

        bid = float(getattr(tick, "bid", 0.0) or 0.0)
        ask = float(getattr(tick, "ask", 0.0) or 0.0)
        point = float(getattr(symbol_info, "point", 0.0) or 0.0)
        stops_level = float(getattr(symbol_info, "trade_stops_level", 0.0) or 0.0)
        min_stop_distance = stops_level * point if point > 0 else 0.0

        def _require_symbol_and_tick() -> Optional[Dict[str, Any]]:
            """Ensure symbol and tick exist for market-based checks."""
            if not symbol:
                return _response(10013, "Invalid request: missing symbol")
            if symbol_info is None or tick is None:
                return _response(10021, "No quotes to process the request")
            return None

        def _validate_volume(
            symbol_name: str, volume: float
        ) -> Optional[Dict[str, Any]]:
            """Validate volume, lot steps, and symbol volume limits."""
            valid, msg = _validate("volume", volume, symbol=symbol_name)
            if not valid:
                return _response(10014, f"Invalid volume: {msg}")

            # Check per-symbol volume limit (positions + pending).
            open_volume = sum(
                float(p.volume or 0.0)
                for p in self._positions_data.values()
                if p.symbol == symbol_name
            )
            pending_volume = sum(
                float(o.volume_current or 0.0)
                for o in self._orders_data.values()
                if o.symbol == symbol_name
            )
            valid, msg = _validate(
                "symbol_volume",
                open_volume + pending_volume + float(volume),
                symbol=symbol_name,
            )
            if not valid:
                return _response(10014, f"Invalid volume: {msg}")
            return None

        def _validate_sl_tp(
            order_type: int,
            entry_price: float,
            sl: float,
            tp: float,
            market_bid: float,
            market_ask: float,
        ) -> Optional[Dict[str, Any]]:
            """Validate SL/TP vs entry and ensure stops are not too close to market."""
            if sl:
                valid, msg = _validate(
                    "stop_loss",
                    sl,
                    entry_price=entry_price,
                    order_type=order_type,
                    symbol=symbol,
                )
                if not valid:
                    return _response(10016, f"Invalid stop loss: {msg}")
            if tp:
                valid, msg = _validate(
                    "take_profit",
                    tp,
                    entry_price=entry_price,
                    order_type=order_type,
                    symbol=symbol,
                )
                if not valid:
                    return _response(10016, f"Invalid take profit: {msg}")

            # Extra MT5-like rule: stops must not be too close to current market.
            if min_stop_distance > 0:
                is_buy = order_type in (
                    mt5.ORDER_TYPE_BUY,
                    mt5.ORDER_TYPE_BUY_LIMIT,
                    mt5.ORDER_TYPE_BUY_STOP,
                    mt5.ORDER_TYPE_BUY_STOP_LIMIT,
                )
                if sl:
                    dist = (market_bid - sl) if is_buy else (sl - market_ask)
                    if dist < min_stop_distance:
                        return _response(10016, "Stop loss too close to market")
                if tp:
                    dist = (tp - market_bid) if is_buy else (market_ask - tp)
                    if dist < min_stop_distance:
                        return _response(10016, "Take profit too close to market")
            return None

        # I) Placing Pending Orders
        if action == getattr(mt5, "TRADE_ACTION_PENDING", 5):
            # Required fields
            if not symbol:
                return _response(10013, "Invalid request: missing symbol")
            if req.get("type") is None:
                return _response(10013, "Invalid request: missing order type")

            invalid = _require_symbol_and_tick()
            if invalid:
                return invalid

            volume = float(req.get("volume") or 0.0)
            invalid = _validate_volume(symbol, volume)
            if invalid:
                return invalid

            # Validate max pending orders
            valid, msg = _validate(
                "max_orders",
                len(self._orders_data),
                account_limit=self._account_data.limit_orders,
            )
            if not valid:
                return _response(10013, msg)

            type_value = req.get("type")
            if type_value is None:
                return _response(10013, "Invalid request: missing order type")
            order_type = int(type_value)
            entry_price = float(req.get("price") or 0.0)
            if entry_price <= 0:
                return _response(10015, "Invalid price for pending order")

            valid, msg = _validate("price", entry_price, symbol=symbol)
            if not valid:
                return _response(10015, msg)

            # Ensure entry price relative to market (MT5 rules)
            if order_type == mt5.ORDER_TYPE_BUY_LIMIT and entry_price >= ask:
                return _response(10015, "Buy limit must be below Ask")
            if order_type == mt5.ORDER_TYPE_BUY_STOP and entry_price <= ask:
                return _response(10015, "Buy stop must be above Ask")
            if order_type == mt5.ORDER_TYPE_SELL_LIMIT and entry_price <= bid:
                return _response(10015, "Sell limit must be above Bid")
            if order_type == mt5.ORDER_TYPE_SELL_STOP and entry_price >= bid:
                return _response(10015, "Sell stop must be below Bid")

            # Stop-limit specific checks
            stoplimit = float(req.get("stoplimit") or 0.0)
            if order_type in (
                mt5.ORDER_TYPE_BUY_STOP_LIMIT,
                mt5.ORDER_TYPE_SELL_STOP_LIMIT,
            ):
                if stoplimit <= 0:
                    return _response(10015, "StopLimit price is required")
                valid, msg = _validate("price", stoplimit, symbol=symbol)
                if not valid:
                    return _response(10015, f"Invalid stoplimit price: {msg}")
                if (
                    order_type == mt5.ORDER_TYPE_BUY_STOP_LIMIT
                    and stoplimit > entry_price
                ):
                    return _response(
                        10015, "Buy stop limit: stoplimit must be <= stop price"
                    )
                if (
                    order_type == mt5.ORDER_TYPE_SELL_STOP_LIMIT
                    and stoplimit < entry_price
                ):
                    return _response(
                        10015, "Sell stop limit: stoplimit must be >= stop price"
                    )

            # Validate SL/TP relative to entry and market distance
            invalid = _validate_sl_tp(
                order_type, entry_price, float(req["sl"]), float(req["tp"]), bid, ask
            )
            if invalid:
                return invalid

            # Freeze level check for pending orders
            valid, msg = _validate(
                "freeze_level",
                entry_price,
                stop_price=0.0,
                order_type=order_type,
                symbol=symbol,
            )
            if not valid:
                return _response(10029, msg)

            # Validate expiration
            expiration = req.get("expiration")
            expiration_ts = None
            if isinstance(expiration, (int, float)) and expiration:
                expiration_ts = int(expiration)
            else:
                ts_func = getattr(expiration, "timestamp", None)
                if callable(ts_func):
                    expiration_ts = int(ts_func())
            if expiration_ts is not None and expiration_ts <= current_time:
                return _response(10022, "Expiration must be in the future")

            # Create pending order
            order_id = self._next_order_id
            self._next_order_id += 1
            margin_required = self.order_calc_margin(
                order_type, symbol, volume, entry_price
            )
            order_info = OrderInfoSimulator(
                ticket=order_id,
                time=current_time,
                time_msc=current_time * 1000,
                type=order_type,
                magic=int(req.get("magic") or 0),
                volume=volume,
                volume_initial=volume,
                volume_current=volume,
                price_open=entry_price,
                price_stoplimit=stoplimit,
                sl=float(req.get("sl") or 0.0),
                tp=float(req.get("tp") or 0.0),
                symbol=symbol,
                comment=str(req.get("comment") or ""),
                type_time=int(req.get("type_time") or 0),
                type_filling=int(req.get("type_filling") or 0),
                margin_required=float(margin_required or 0.0),
                open_price=entry_price,
                expiry_date=expiration,
                expiration_mode="gtc" if not expiration_ts else "specified",
            )
            if expiration_ts:
                order_info.time_expiration = int(expiration_ts)

            self._orders_data[order_id] = order_info

            return _response(
                10009,
                "Order placed",
                order=order_id,
                price=entry_price,
                bid=bid,
                ask=ask,
            )

        # II) Opening Positions (Market)
        if action == getattr(mt5, "TRADE_ACTION_DEAL", 1) and not req.get("position"):
            invalid = _require_symbol_and_tick()
            if invalid:
                return invalid

            volume = float(req.get("volume") or 0.0)
            invalid = _validate_volume(symbol, volume)
            if invalid:
                return invalid

            order_type = int(req.get("type") or 0)
            if order_type not in (mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL):
                return _response(10013, "Invalid order type for market execution")

            market_price = ask if order_type == mt5.ORDER_TYPE_BUY else bid
            price = float(req.get("price") or 0.0)
            if price <= 0:
                price = market_price

            slippage_points = float(
                getattr(self, "_backtest_slippage_points", 0.0) or 0.0
            )
            if slippage_points > 0 and point > 0:
                slippage = slippage_points * point
                if order_type == mt5.ORDER_TYPE_BUY:
                    price = float(price + slippage)
                else:
                    price = float(price - slippage)

            # Validate entry price
            valid, msg = _validate("price", price, symbol=symbol)
            if not valid:
                return _response(10015, msg)

            # Enforce deviation if a price was provided
            deviation_pts = int(req.get("deviation") or 0)
            if (
                deviation_pts > 0
                and point > 0
                and abs(price - market_price) > deviation_pts * point
            ):
                return _response(10020, "Prices changed")

            # Validate SL/TP rules
            invalid = _validate_sl_tp(
                order_type, price, float(req["sl"]), float(req["tp"]), bid, ask
            )
            if invalid:
                return invalid

            # Margin check
            margin_required = self.order_calc_margin(order_type, symbol, volume, price)
            valid, msg = _validate("margin", margin_required)
            if not valid:
                return _response(10019, msg)

            # Create position
            position_id = self._next_position_id
            self._next_position_id += 1

            self._positions_data[position_id] = PositionInfoSimulator(
                ticket=position_id,
                time=current_time,
                time_msc=current_time * 1000,
                time_update=current_time,
                time_update_msc=current_time * 1000,
                type=order_type,
                magic=int(req.get("magic") or 0),
                identifier=position_id,
                volume=volume,
                price_open=price,
                sl=float(req.get("sl") or 0.0),
                tp=float(req.get("tp") or 0.0),
                price_current=price,
                symbol=symbol,
                comment=str(req.get("comment") or ""),
                swap=0.0,
                profit=0.0,
                margin_required=float(margin_required or 0.0),
            )

            # Create deal record (entry)
            deal_id = self._next_deal_id
            self._next_deal_id += 1
            self._deals_data[deal_id] = DealInfoSimulator(
                ticket=deal_id,
                time=current_time,
                time_msc=current_time * 1000,
                type=order_type,
                magic=int(req.get("magic") or 0),
                identifier=position_id,
                volume=volume,
                price_open=price,
                price=price,
                symbol=symbol,
                comment=str(req.get("comment") or ""),
                commission=0.0,
                swap=0.0,
                profit=0.0,
                fee=0.0,
                entry=getattr(mt5, "DEAL_ENTRY_IN", 0),
                order=0,
            )

            # Update account margins
            self._account_data.margin = float(
                self._account_data.margin + (margin_required or 0.0)
            )
            self._account_data.margin_free = float(
                self._account_data.margin_free - (margin_required or 0.0)
            )

            position_state = getattr(self, "_position_array_state", None)
            if position_state is not None:
                position_state.add_or_update(
                    pos_id=position_id,
                    pos_data=self._positions_data[position_id],
                )

            return _response(
                10009,
                "Position opened",
                deal=deal_id,
                order=position_id,
                price=price,
                bid=bid,
                ask=ask,
            )

        # III) Closing Positions
        if action == getattr(mt5, "TRADE_ACTION_DEAL", 1) and req.get("position"):
            position_id = int(req.get("position") or 0)
            position = self._positions_data.get(position_id)
            if position is None:
                return _response(10013, "Position not found")

            symbol = position.symbol
            symbol_info = self._symbols_data.get(symbol)
            tick = self._ticks_data.get(symbol)
            if symbol_info is None or tick is None:
                return _response(10021, "No quotes to process the request")

            bid = float(getattr(tick, "bid", 0.0) or 0.0)
            ask = float(getattr(tick, "ask", 0.0) or 0.0)
            point = float(getattr(symbol_info, "point", 0.0) or 0.0)

            pos_type = int(position.type)
            close_type = int(req.get("type") or 0)

            # Check opposite side for close
            if pos_type == mt5.ORDER_TYPE_BUY and close_type != mt5.ORDER_TYPE_SELL:
                return _response(10013, "Close request must be SELL for BUY position")
            if pos_type == mt5.ORDER_TYPE_SELL and close_type != mt5.ORDER_TYPE_BUY:
                return _response(10013, "Close request must be BUY for SELL position")

            market_price = bid if pos_type == mt5.ORDER_TYPE_BUY else ask
            price = float(req.get("price") or 0.0)
            if price <= 0:
                price = market_price

            # Validate price with deviation
            deviation_pts = int(req.get("deviation") or 0)
            if (
                deviation_pts > 0
                and point > 0
                and abs(price - market_price) > deviation_pts * point
            ):
                return _response(10020, "Prices changed")

            # Validate close volume (supports partial closes)
            close_volume = float(req.get("volume") or 0.0)
            if close_volume <= 0:
                return _response(10036, "Invalid close volume")
            if close_volume > float(position.volume or 0.0):
                return _response(10036, "Close volume exceeds position volume")

            # Profit calculation for closed volume
            original_volume = float(position.volume or 0.0)
            profit = self.order_calc_profit(
                0 if pos_type == mt5.ORDER_TYPE_BUY else 1,
                symbol,
                float(close_volume),
                float(position.price_open or 0.0),
                price,
            )
            commission, fee, swap = self._calc_close_costs(
                symbol_info=symbol_info,
                pos_type=pos_type,
                volume=float(close_volume),
                open_time=int(position.time or current_time),
                close_time=int(current_time),
            )

            # Update or remove position
            margin_required = float(position.margin_required or 0.0)
            remaining_volume = original_volume - close_volume
            if remaining_volume > 0:
                position.volume = remaining_volume
                if original_volume > 0:
                    position.margin_required = float(
                        margin_required * (remaining_volume / original_volume)
                    )
                position.time_update = current_time
                position.time_update_msc = current_time * 1000
                position_state = getattr(self, "_position_array_state", None)
                if position_state is not None:
                    position_state.update_volume_margin(
                        pos_id=position_id,
                        volume=position.volume,
                        margin=position.margin_required,
                    )
            else:
                self._positions_data.pop(position_id, None)
                position_state = getattr(self, "_position_array_state", None)
                if position_state is not None:
                    position_state.remove(position_id)

            # Create deal record (exit)
            deal_id = self._next_deal_id
            self._next_deal_id += 1
            self._deals_data[deal_id] = DealInfoSimulator(
                ticket=deal_id,
                time=current_time,
                time_msc=current_time * 1000,
                type=close_type,
                magic=int(position.magic or 0),
                identifier=position_id,
                volume=close_volume,
                price_open=float(position.price_open or 0.0),
                price=price,
                symbol=symbol,
                comment=str(req.get("comment") or ""),
                commission=float(commission),
                swap=float(swap),
                profit=float(profit),
                fee=float(fee),
                entry=getattr(mt5, "DEAL_ENTRY_OUT", 1),
                order=0,
            )

            # Release margin + update balance
            margin_release = (
                margin_required * (close_volume / original_volume)
                if original_volume > 0
                else 0.0
            )
            self._account_data.margin = float(
                max(self._account_data.margin - margin_release, 0.0)
            )
            self._account_data.margin_free = float(
                self._account_data.margin_free + margin_release
            )
            self._account_data.balance = float(
                self._account_data.balance + profit + commission + fee + swap
            )

            return _response(
                10009,
                "Position closed",
                deal=deal_id,
                order=position_id,
                price=price,
                bid=bid,
                ask=ask,
                volume=close_volume,
            )

        # IV) Modifying Positions (SL/TP)
        if action == getattr(mt5, "TRADE_ACTION_SLTP", 2):
            position_id = int(req.get("position") or 0)
            position = self._positions_data.get(position_id)
            if position is None:
                return _response(10013, "Position not found")

            symbol = position.symbol
            symbol_info = self._symbols_data.get(symbol)
            tick = self._ticks_data.get(symbol)
            if symbol_info is None or tick is None:
                return _response(10021, "No quotes to process the request")

            bid = float(getattr(tick, "bid", 0.0) or 0.0)
            ask = float(getattr(tick, "ask", 0.0) or 0.0)

            pos_type = int(position.type)
            entry_price = float(position.price_open or 0.0)
            new_sl = float(req.get("sl") or 0.0)
            new_tp = float(req.get("tp") or 0.0)

            # Validate SL/TP vs entry and market distance
            invalid = _validate_sl_tp(pos_type, entry_price, new_sl, new_tp, bid, ask)
            if invalid:
                return invalid

            # Freeze level checks for SL and TP
            if new_sl:
                valid, msg = _validate(
                    "freeze_level",
                    entry_price,
                    stop_price=new_sl,
                    order_type=pos_type,
                    symbol=symbol,
                )
                if not valid:
                    return _response(10029, msg)
            if new_tp:
                valid, msg = _validate(
                    "freeze_level",
                    entry_price,
                    stop_price=new_tp,
                    order_type=pos_type,
                    symbol=symbol,
                )
                if not valid:
                    return _response(10029, msg)

            position.sl = new_sl
            position.tp = new_tp
            position.time_update = current_time
            position.time_update_msc = current_time * 1000
            position_state = getattr(self, "_position_array_state", None)
            if position_state is not None:
                position_state.update_sl_tp(position_id, new_sl, new_tp)
            return _response(
                10009, "Position modified", order=position_id, bid=bid, ask=ask
            )

        # V) Deleting Pending Orders
        if action == getattr(mt5, "TRADE_ACTION_REMOVE", 4):
            order_ticket = int(req.get("order") or 0)
            order = self._orders_data.get(order_ticket)
            if order is None:
                return _response(10013, "Order not found")
            self._archive_order(
                order,
                getattr(mt5, "ORDER_STATE_CANCELED", 4),
                current_time,
            )
            self._orders_data.pop(order_ticket, None)
            return _response(10009, "Order removed", order=order_ticket)

        # VI) Modifying Pending Orders
        if action == getattr(mt5, "TRADE_ACTION_MODIFY", 3):
            order_ticket = int(req.get("order") or 0)
            stored = self._orders_data.get(order_ticket)
            if stored is None:
                return _response(10013, "Order not found")

            symbol = stored.symbol
            symbol_info = self._symbols_data.get(symbol)
            tick = self._ticks_data.get(symbol)
            if symbol_info is None or tick is None:
                return _response(10021, "No quotes to process the request")

            bid = float(getattr(tick, "bid", 0.0) or 0.0)
            ask = float(getattr(tick, "ask", 0.0) or 0.0)

            order_type = int(stored.type)
            new_price = float(req.get("price") or stored.price_open or 0.0)
            new_sl = float(req.get("sl") or stored.sl or 0.0)
            new_tp = float(req.get("tp") or stored.tp or 0.0)

            valid, msg = _validate("price", new_price, symbol=symbol)
            if not valid:
                return _response(10015, msg)

            # Ensure entry price relative to market
            if order_type == mt5.ORDER_TYPE_BUY_LIMIT and new_price >= ask:
                return _response(10015, "Buy limit must be below Ask")
            if order_type == mt5.ORDER_TYPE_BUY_STOP and new_price <= ask:
                return _response(10015, "Buy stop must be above Ask")
            if order_type == mt5.ORDER_TYPE_SELL_LIMIT and new_price <= bid:
                return _response(10015, "Sell limit must be above Bid")
            if order_type == mt5.ORDER_TYPE_SELL_STOP and new_price >= bid:
                return _response(10015, "Sell stop must be below Bid")
            if order_type == mt5.ORDER_TYPE_BUY_STOP_LIMIT and new_price <= ask:
                return _response(10015, "Buy stop limit must be above Ask")
            if order_type == mt5.ORDER_TYPE_SELL_STOP_LIMIT and new_price >= bid:
                return _response(10015, "Sell stop limit must be below Bid")

            # Validate SL/TP vs entry and market distance
            invalid = _validate_sl_tp(order_type, new_price, new_sl, new_tp, bid, ask)
            if invalid:
                return invalid

            # Freeze level check for pending orders (entry price check vs market)
            valid, msg = _validate(
                "freeze_level",
                new_price,
                stop_price=0.0,
                order_type=order_type,
                symbol=symbol,
            )
            if not valid:
                return _response(10029, msg)

            # Expiration update
            expiration = req.get("expiration")
            expiration_ts = None
            if isinstance(expiration, (int, float)) and expiration:
                expiration_ts = int(expiration)
            else:
                ts_func = getattr(expiration, "timestamp", None)
                if callable(ts_func):
                    expiration_ts = int(ts_func())
            if expiration_ts is not None and expiration_ts <= current_time:
                return _response(10022, "Expiration must be in the future")

            stored.price_open = new_price
            stored.open_price = new_price
            stored.sl = new_sl
            stored.tp = new_tp
            stored.expiry_date = expiration if expiration_ts else stored.expiry_date
            if expiration_ts:
                stored.time_expiration = int(expiration_ts)

            return _response(
                10009, "Order modified", order=order_ticket, bid=bid, ask=ask
            )

        return _response(10013, "Invalid request action")

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
        logger.debug("Running history_deals_get in simulator not real mt5")
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
        logger.debug("Running orders_get in simulator not real mt5")
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
        logger.debug("Running history_orders_get in simulator not real mt5")
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
        logger.debug("Running positions_get in simulator not real mt5")
        if ticket is not None:
            d = self._positions_data.get(ticket)
            return (d,) if d else None

        if symbol is not None:
            # Filter positions by symbol
            matching = [p for p in self._positions_data.values() if p.symbol == symbol]
            return tuple(matching) if matching else None

        return tuple(self._positions_data.values())

    def last_error(self) -> tuple[int, str]:
        """Get last error."""
        return (1, "Success")

    def trade_retcode_description(self, retcode: int) -> str:
        """Get trade retcode description."""
        return TradeErrorDescriptions.error_description(retcode)

    def order_calc_margin(
        self, action: int, symbol: str, volume: float, price: float
    ) -> float:
        """Simulate order_calc_margin."""
        logger.debug(
            f"Running order_calc_margin in simulator not real mt5 for symbol {symbol}"
        )

        symbol_info = self.symbol_info(symbol)
        if symbol_info is None:
            return 0.0

        contract_size = getattr(symbol_info, "trade_contract_size", 0.0)
        margin_mode = getattr(symbol_info, "trade_calc_mode", 0)
        leverage = self._account_data.leverage or 100

        tick_size = getattr(symbol_info, "trade_tick_size", 0.0) or getattr(
            symbol_info, "point", 0.0001
        )
        tick_value = getattr(symbol_info, "trade_tick_value", 0.0)
        initial_margin = getattr(symbol_info, "margin_initial", 0.0)

        # SYMBOL_CALC_MODE_FOREX = 0
        if margin_mode == 0:
            return (volume * contract_size) / leverage
        # SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE = 1
        elif margin_mode == 1:
            return volume * contract_size
        # SYMBOL_CALC_MODE_CFD = 2
        elif margin_mode == 2:
            return volume * contract_size * price
        # SYMBOL_CALC_MODE_CFDLEVERAGE = 3
        elif margin_mode == 3:
            return (volume * contract_size * price) / leverage
        # SYMBOL_CALC_MODE_CFDINDEX = 4
        elif margin_mode == 4:
            if tick_size > 0:
                return volume * contract_size * price * tick_value / tick_size
        # SYMBOL_CALC_MODE_EXCH_STOCKS = 5, SYMBOL_CALC_MODE_EXCH_STOCKS_MOEX = 6
        elif margin_mode in (5, 6):
            return volume * contract_size * price
        # SYMBOL_CALC_MODE_FUTURES = 7, SYMBOL_CALC_MODE_EXCH_FUTURES = 8
        elif margin_mode in (7, 8):
            return volume * initial_margin

        # Default fallback
        return (volume * contract_size * price) / leverage

    def order_calc_profit(
        self,
        action: int,
        symbol: str,
        volume: float,
        price_open: float,
        price_close: float,
    ) -> float:
        """Simulate order_calc_profit."""
        logger.debug(
            f"Running order_calc_profit in simulator not real mt5 for symbol {symbol}"
        )

        symbol_info = self.symbol_info(symbol)
        if symbol_info is None:
            return 0.0

        direction = 1.0 if action == 0 else -1.0  # 0: BUY, 1: SELL
        price_delta = (price_close - price_open) * direction
        tick_size = getattr(symbol_info, "trade_tick_size", 0.0) or getattr(
            symbol_info, "point", 0.0
        )
        tick_value = getattr(symbol_info, "trade_tick_value", 0.0)

        if tick_size > 0 and tick_value > 0:
            return float((price_delta / tick_size) * tick_value * volume)

        contract_size = getattr(symbol_info, "trade_contract_size", 0.0)
        if contract_size > 0:
            return float(price_delta * contract_size * volume)

        return 0.0
