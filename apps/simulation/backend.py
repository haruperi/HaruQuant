"""
Backend selector and C++ adapter for the simulation engine.

Provides routing between the Python bar-by-bar loop and the C++ BacktestEngine,
controlled by the ``SIM_ENGINE`` environment variable.

Classes:
    SimBackend: Enum for backend selection (PYTHON / CPP).
    CppBacktestResult: Container for results returned by the C++ engine.

Functions:
    get_backend: Read ``SIM_ENGINE`` env var and return the selected backend.
    is_cpp_available: Check whether the ``hqt_engine.sim`` extension is importable.
    run_trading_timeframe_cpp: Execute a trading-timeframe backtest via C++.
"""

from __future__ import annotations

import atexit
from collections import namedtuple
import os
import warnings
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

from apps.utils.logger import logger
from apps.simulation.records import TradeRecord
from apps.utils.errors import (
    CppBridgeError,
    ErrorDescriptor,
    descriptor_from_payload,
    trade_exception_from_descriptor,
)

_CPP_LOG_BRIDGE_READY = False
_CPP_LOG_CLEANUP_REGISTERED = False

AccountInfoTuple = namedtuple(
    "AccountInfoTuple",
    [
        "login",
        "name",
        "server",
        "currency",
        "company",
        "trade_mode",
        "leverage",
        "trade_allowed",
        "trade_expert",
        "limit_orders",
        "balance",
        "credit",
        "profit",
        "equity",
        "margin",
        "margin_free",
        "margin_level",
        "margin_so_call",
        "margin_so_so",
        "margin_mode",
        "margin_so_mode",
    ],
)

SymbolInfoTuple = namedtuple(
    "SymbolInfoTuple",
    [
        "name",
        "digits",
        "spread",
        "spread_float",
        "point",
        "trade_calc_mode",
        "trade_mode",
        "trade_stops_level",
        "trade_freeze_level",
        "trade_exemode",
        "volume_min",
        "volume_max",
        "volume_step",
        "volume_limit",
        "trade_tick_value",
        "trade_tick_value_profit",
        "trade_tick_value_loss",
        "trade_tick_size",
        "trade_contract_size",
        "margin_initial",
        "swap_mode",
        "swap_long",
        "swap_short",
        "swap_rollover3days",
        "bid",
        "ask",
        "last",
        "select",
        "visible",
    ],
)


class CppMt5ApiFacade:
    """MT5-like API facade backed by hqt_engine.sim.TradeSimulator."""

    def __init__(self, simulator: Any) -> None:
        self._sim = simulator

    def account_info(self) -> AccountInfoTuple:
        acc = self._sim.account_info()
        return AccountInfoTuple(
            login=int(acc.login),
            name=str(acc.name),
            server=str(acc.server),
            currency=str(acc.currency),
            company=str(acc.company),
            trade_mode=0,
            leverage=int(acc.leverage),
            trade_allowed=bool(acc.trade_allowed),
            trade_expert=bool(acc.trade_expert),
            limit_orders=0,
            balance=float(acc.balance),
            credit=float(acc.credit),
            profit=float(acc.profit),
            equity=float(acc.equity),
            margin=float(acc.margin),
            margin_free=float(acc.margin_free),
            margin_level=float(acc.margin_level),
            margin_so_call=0.0,
            margin_so_so=0.0,
            margin_mode=int(acc.margin_mode),
            margin_so_mode=0,
        )

    def symbol_info(self, symbol: str) -> Optional[SymbolInfoTuple]:
        info = self._sim.symbol_info(symbol)
        if info is None:
            return None
        return SymbolInfoTuple(
            name=str(info.symbol),
            digits=int(info.digits),
            spread=int(info.spread),
            spread_float=bool(info.spread_float),
            point=float(info.point),
            trade_calc_mode=int(info.trade_calc_mode),
            trade_mode=int(info.trade_mode),
            trade_stops_level=int(info.trade_stops_level),
            trade_freeze_level=int(info.trade_freeze_level),
            trade_exemode=int(info.trade_exemode),
            volume_min=float(info.volume_min),
            volume_max=float(info.volume_max),
            volume_step=float(info.volume_step),
            volume_limit=float(info.volume_limit),
            trade_tick_value=float(info.trade_tick_value),
            trade_tick_value_profit=float(info.trade_tick_value_profit),
            trade_tick_value_loss=float(info.trade_tick_value_loss),
            trade_tick_size=float(info.trade_tick_size),
            trade_contract_size=float(info.trade_contract_size),
            margin_initial=float(info.margin_initial),
            swap_mode=int(info.swap_mode),
            swap_long=float(info.swap_long),
            swap_short=float(info.swap_short),
            swap_rollover3days=int(info.swap_rollover3days),
            bid=float(info.bid),
            ask=float(info.ask),
            last=float(info.last),
            select=bool(info.select),
            visible=bool(info.visible),
        )

    def order_calc_margin(self, order_type: int, symbol: str, volume: float, price: float) -> float:
        return float(self._sim.order_calc_margin(int(order_type), symbol, float(volume), float(price)))

    def order_calc_profit(
        self,
        order_type: int,
        symbol: str,
        volume: float,
        price_open: float,
        price_close: float,
    ) -> float:
        return float(
            self._sim.order_calc_profit(
                int(order_type),
                symbol,
                float(volume),
                float(price_open),
                float(price_close),
            )
        )


def create_cpp_mt5_api(simulator: Any) -> CppMt5ApiFacade:
    """Create an MT5-like API facade over a C++ TradeSimulator instance."""
    return CppMt5ApiFacade(simulator)


# ---------------------------------------------------------------------------
# Backend enum & helpers
# ---------------------------------------------------------------------------


class SimBackend(Enum):
    """Simulation backend selector."""

    PYTHON = "python"
    CPP = "cpp"


def get_backend() -> SimBackend:
    """Return the backend requested via the ``SIM_ENGINE`` environment variable.

    Defaults to :pyattr:`SimBackend.PYTHON` when the variable is unset or empty.
    Unknown values emit a warning and fall back to Python.
    """
    raw = os.environ.get("SIM_ENGINE", "").strip().lower()
    if not raw:
        return SimBackend.PYTHON
    try:
        return SimBackend(raw)
    except ValueError:
        warnings.warn(
            f"Unknown SIM_ENGINE value {raw!r}, falling back to Python backend",
            stacklevel=2,
        )
        return SimBackend.PYTHON


def is_cpp_available() -> bool:
    """Return ``True`` if the ``hqt_engine.sim`` C++ extension can be imported."""
    try:
        import hqt_engine.sim  # noqa: F401

        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


class CppBacktestResult:
    """Slots-based container for C++ backtest results."""

    __slots__ = (
        "completed_trades",
        "final_balance",
        "final_equity",
        "final_margin",
        "final_margin_free",
        "final_profit",
    )

    def __init__(
        self,
        completed_trades: List[TradeRecord],
        final_balance: float,
        final_equity: float,
        final_margin: float,
        final_margin_free: float,
        final_profit: float,
    ) -> None:
        self.completed_trades = completed_trades
        self.final_balance = final_balance
        self.final_equity = final_equity
        self.final_margin = final_margin
        self.final_margin_free = final_margin_free
        self.final_profit = final_profit


# ---------------------------------------------------------------------------
# C++ adapter
# ---------------------------------------------------------------------------


def run_trading_timeframe_cpp(
    data: Any,
    original_data: Any,
    strategy: Any,
    symbol: str,
    volume: float,
    symbol_info: Any,
    warmup_bars: int,
    account_data: Any,
) -> CppBacktestResult:
    """Run a trading-timeframe backtest through the C++ ``BacktestEngine``.

    Parameters
    ----------
    data:
        Sliced DataFrame (trading period only).
    original_data:
        Full DataFrame including warmup bars.
    strategy:
        Strategy instance (used for ``get_signal`` to obtain SL/TP).
    symbol:
        Trading symbol name.
    volume:
        Order volume (lots).
    symbol_info:
        ``SymbolInfoSimulator`` for the symbol.
    warmup_bars:
        Number of warmup bars that were trimmed from *original_data* to
        produce *data*.
    account_data:
        ``AccountInfoSimulator`` with current account state.

    Returns
    -------
    CppBacktestResult
    """
    _setup_cpp_logging_bridge()

    import hqt_engine.sim as csim

    bars = _build_bar_steps(data, original_data, strategy, warmup_bars)
    cpp_account = _to_cpp_account(account_data)
    cpp_symbol = _to_cpp_symbol_info(symbol_info)

    client = csim.TradeSimulator(cpp_account)
    client.set_symbol_info(cpp_symbol)

    # Seed an initial tick so the engine can process bar 0.
    if len(bars) > 0:
        first = bars[0]
        point = symbol_info.point
        spread = first.spread_points * point
        tick = csim.SymbolTickData()
        tick.time = int(first.time_msc // 1000)
        tick.time_msc = first.time_msc
        tick.bid = first.close
        tick.ask = first.close + spread
        tick.last = first.close
        tick.volume = 0
        tick.volume_real = 0.0
        tick.flags = 0
        client.set_symbol_tick(symbol, tick)

    engine = csim.BacktestEngine(client)
    try:
        engine.run_trading_timeframe(symbol, volume, bars)
    except Exception as exc:
        raise _translate_cpp_exception(exc, client) from exc

    # Harvest results.
    snapshot = engine.account_snapshot()
    cpp_trades = engine.completed_trades()
    py_trades = [_cpp_trade_to_py(t, symbol) for t in cpp_trades]

    return CppBacktestResult(
        completed_trades=py_trades,
        final_balance=snapshot.balance,
        final_equity=snapshot.equity,
        final_margin=snapshot.margin,
        final_margin_free=snapshot.margin_free,
        final_profit=snapshot.profit,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _setup_cpp_logging_bridge() -> None:
    """Attach C++ logging callback to the Python logger once per process."""
    global _CPP_LOG_BRIDGE_READY
    global _CPP_LOG_CLEANUP_REGISTERED

    if _CPP_LOG_BRIDGE_READY:
        return

    try:
        import hqt_engine
    except Exception:
        return

    if not hasattr(hqt_engine, "set_log_callback"):
        return

    def _cpp_log_callback(*args: Any) -> None:
        payload: dict[str, Any] | None = None
        level = "INFO"
        message = ""
        extra: dict[str, Any] = {}

        # New structured callback: callback(record_dict)
        if len(args) == 1 and isinstance(args[0], dict):
            payload = args[0]
            level = str(payload.get("level", {}).get("name", "INFO")).upper()
            message = str(payload.get("message", ""))
            if isinstance(payload.get("extra"), dict):
                extra.update(payload["extra"])
            extra["cpp_logger"] = payload.get("name")
            extra["cpp_module"] = payload.get("module")
            extra["cpp_function"] = payload.get("function")
            extra["cpp_line"] = payload.get("line")
            if isinstance(payload.get("file"), dict):
                extra["cpp_file"] = payload["file"].get("path")
            if isinstance(payload.get("time"), dict):
                extra["cpp_time"] = payload["time"].get("repr")
        # Legacy callback: callback(level, message)
        elif len(args) >= 2:
            level = str(args[0] or "INFO").upper()
            message = str(args[1] or "")

        text = f"[C++] {message}"
        if level == "DEBUG":
            logger.debug(text, extra=extra)
        elif level == "WARNING":
            logger.warning(text, extra=extra)
        elif level == "ERROR":
            logger.error(text, extra=extra)
        elif level == "CRITICAL":
            logger.critical(text, extra=extra)
        else:
            logger.info(text, extra=extra)

    try:
        hqt_engine.set_stderr_logging(False)
        hqt_engine.set_log_callback(_cpp_log_callback)
        hqt_engine.set_log_level(os.environ.get("HQT_CPP_LOG_LEVEL", "info"))
        if not _CPP_LOG_CLEANUP_REGISTERED:
            atexit.register(_teardown_cpp_logging_bridge)
            _CPP_LOG_CLEANUP_REGISTERED = True
        _CPP_LOG_BRIDGE_READY = True
    except Exception as exc:
        logger.warning(f"Failed to initialize C++ logging bridge: {exc}")


def _teardown_cpp_logging_bridge() -> None:
    """Best-effort teardown for C++->Python log callback."""
    global _CPP_LOG_BRIDGE_READY
    try:
        import hqt_engine

        if hasattr(hqt_engine, "set_log_callback"):
            hqt_engine.set_log_callback(None)
    except Exception:
        pass
    finally:
        _CPP_LOG_BRIDGE_READY = False


def _build_bar_steps(
    data: Any,
    original_data: Any,
    strategy: Any,
    warmup_bars: int,
) -> list:
    """Convert the sliced DataFrame into a list of ``BacktestBarStep``."""
    import hqt_engine.sim as csim

    # Extract numpy arrays for speed.
    close_arr = data["close"].to_numpy()
    spread_arr = (
        data["spread"].to_numpy() if "spread" in data.columns else None
    )

    # Read pre-computed signals from *original_data* (full dataset).
    entry_arr: Optional[Any] = None
    exit_arr: Optional[Any] = None
    try:
        if "entry_signal" in original_data.columns:
            entry_arr = original_data["entry_signal"].fillna(0).astype(int).to_numpy()
        if "exit_signal" in original_data.columns:
            exit_arr = original_data["exit_signal"].fillna(0).astype(int).to_numpy()
    except Exception:
        entry_arr = None
        exit_arr = None

    steps: list = []
    for idx in range(len(data)):
        orig_idx = idx + warmup_bars

        entry_signal = int(entry_arr[orig_idx]) if entry_arr is not None else 0
        exit_signal = int(exit_arr[orig_idx]) if exit_arr is not None else 0

        sl = 0.0
        tp = 0.0

        # When a signal exists, ask the strategy for SL/TP.
        if entry_signal != 0:
            try:
                sig = strategy.get_signal(original_data, orig_idx)
                if sig is not None:
                    sl = float(sig.get("stop_loss") or 0.0)
                    tp = float(sig.get("take_profit") or 0.0)
            except Exception:
                pass

        bar_time = data.index[idx]
        if hasattr(bar_time, "timestamp"):
            time_msc = int(bar_time.timestamp() * 1000)
        elif isinstance(bar_time, (int, float)):
            time_msc = int(bar_time * 1000)
        else:
            time_msc = 0

        step = csim.BacktestBarStep()
        step.time_msc = time_msc
        step.close = float(close_arr[idx])
        step.spread_points = float(spread_arr[idx]) if spread_arr is not None else float(getattr(data, "_spread_default", 10))
        step.entry_signal = entry_signal
        step.exit_signal = exit_signal
        step.sl = sl
        step.tp = tp
        steps.append(step)

    return steps


def _extract_retcode(raw: str) -> Optional[int]:
    """Extract retcode=<int> from an error string when present."""
    marker = "retcode="
    pos = raw.find(marker)
    if pos < 0:
        return None
    pos += len(marker)
    end = pos
    while end < len(raw) and raw[end].isdigit():
        end += 1
    if end == pos:
        return None
    try:
        return int(raw[pos:end])
    except Exception:
        return None


def _cpp_error_payload_from_code(code: int) -> Optional[dict[str, Any]]:
    """Query C++ bridge taxonomy payload for a retcode."""
    try:
        import hqt_engine
    except Exception:
        return None
    if not hasattr(hqt_engine, "error_from_retcode"):
        return None
    try:
        payload = hqt_engine.error_from_retcode(int(code))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _translate_cpp_exception(exc: Exception, client: Any) -> Exception:
    """Map raw C++ exception into typed Python exception."""
    exc_module = getattr(exc.__class__, "__module__", "")
    exc_name = getattr(exc.__class__, "__name__", "")
    if exc_module == "hqt_engine" and exc_name.endswith("Error"):
        return exc

    raw_message = str(exc)
    retcode = _extract_retcode(raw_message)
    detail = raw_message

    if retcode is None:
        try:
            code, msg = client.last_error()
            retcode = int(code)
            if msg:
                detail = str(msg)
        except Exception:
            retcode = None

    if retcode is not None and retcode not in (0, 1):
        payload = _cpp_error_payload_from_code(retcode)
        descriptor = descriptor_from_payload(payload, fallback_code=retcode)
        return trade_exception_from_descriptor(descriptor, detail=detail)

    descriptor = ErrorDescriptor(
        code=retcode if retcode is not None else -1,
        name="CPP_BRIDGE_ERROR",
        message="C++ bridge execution failed",
        domain="bridge",
        retryable=False,
    )
    return CppBridgeError(descriptor=descriptor, detail=detail)


def _to_cpp_account(account: Any) -> Any:
    """Map a Python ``AccountInfoSimulator`` to ``csim.AccountInfo``."""
    import hqt_engine.sim as csim

    cpp = csim.AccountInfo(
        float(getattr(account, "balance", 10000.0)),
        str(getattr(account, "currency", "USD")),
        int(getattr(account, "leverage", 100)),
    )
    cpp.login = int(getattr(account, "login", 12345678))
    cpp.leverage = int(getattr(account, "leverage", 100))
    cpp.margin_mode = int(getattr(account, "margin_mode", 0))
    cpp.trade_allowed = bool(getattr(account, "trade_allowed", True))
    cpp.trade_expert = bool(getattr(account, "trade_expert", True))
    cpp.name = str(getattr(account, "name", "Simulated Trader"))
    cpp.server = str(getattr(account, "server", "Sim-Server"))
    cpp.company = str(getattr(account, "company", "Simulated Company"))
    return cpp


def _to_cpp_symbol_info(sym: Any) -> Any:
    """Map a Python ``SymbolInfoSimulator`` to ``csim.SymbolInfo``."""
    import hqt_engine.sim as csim

    cpp = csim.SymbolInfo()
    cpp.symbol = str(getattr(sym, "symbol", "EURUSD"))
    cpp.digits = int(getattr(sym, "digits", 5))
    cpp.spread = int(getattr(sym, "spread", 10))
    cpp.spread_float = bool(getattr(sym, "spread_float", True))
    cpp.point = float(getattr(sym, "point", 0.00001))
    cpp.trade_calc_mode = int(getattr(sym, "trade_calc_mode", 0))
    cpp.trade_mode = int(getattr(sym, "trade_mode", 4))
    cpp.trade_stops_level = int(getattr(sym, "trade_stops_level", 0))
    cpp.trade_freeze_level = int(getattr(sym, "trade_freeze_level", 0))
    cpp.trade_exemode = int(getattr(sym, "trade_exemode", 1))
    cpp.volume_min = float(getattr(sym, "volume_min", 0.01))
    cpp.volume_max = float(getattr(sym, "volume_max", 100.0))
    cpp.volume_step = float(getattr(sym, "volume_step", 0.01))
    cpp.volume_limit = float(getattr(sym, "volume_limit", 0.0))
    cpp.trade_tick_value = float(getattr(sym, "trade_tick_value", 1.0))
    cpp.trade_tick_value_profit = float(getattr(sym, "trade_tick_value_profit", 1.0))
    cpp.trade_tick_value_loss = float(getattr(sym, "trade_tick_value_loss", 1.0))
    cpp.trade_tick_size = float(getattr(sym, "trade_tick_size", 0.00001))
    cpp.trade_contract_size = float(getattr(sym, "trade_contract_size", 100000.0))
    cpp.margin_initial = float(getattr(sym, "margin_initial", 0.0))
    cpp.swap_mode = int(getattr(sym, "swap_mode", 1))
    cpp.swap_long = float(getattr(sym, "swap_long", -1.0))
    cpp.swap_short = float(getattr(sym, "swap_short", -1.0))
    cpp.swap_rollover3days = int(getattr(sym, "swap_rollover3days", 3))
    cpp.bid = float(getattr(sym, "bid", 0.0))
    cpp.ask = float(getattr(sym, "ask", 0.0))
    cpp.select = bool(getattr(sym, "select", True))
    cpp.visible = bool(getattr(sym, "visible", True))
    return cpp


def _cpp_trade_to_py(cpp_trade: Any, symbol: str) -> TradeRecord:
    """Convert a C++ ``TradeRecord`` to a Python ``TradeRecord``."""
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None

    if cpp_trade.open_time_msc > 0:
        open_time = datetime.fromtimestamp(
            cpp_trade.open_time_msc / 1000.0, tz=timezone.utc
        ).replace(tzinfo=None)
    if cpp_trade.close_time_msc > 0:
        close_time = datetime.fromtimestamp(
            cpp_trade.close_time_msc / 1000.0, tz=timezone.utc
        ).replace(tzinfo=None)

    return TradeRecord(
        ticket=int(cpp_trade.ticket),
        symbol=symbol,
        type="buy" if cpp_trade.is_buy else "sell",
        size=float(cpp_trade.volume),
        open_price=float(cpp_trade.open_price),
        close_price=float(cpp_trade.close_price),
        stop_loss_price=float(cpp_trade.stop_loss),
        profit_target_price=float(cpp_trade.take_profit),
        open_time=open_time,
        close_time=close_time,
        time_in_trade=float(cpp_trade.time_in_trade_seconds),
        bars_in_trade=int(cpp_trade.bars_in_trade),
        initial_risk_usd=float(cpp_trade.initial_risk_usd),
        profit_loss=float(cpp_trade.profit_loss),
        mae_usd=float(cpp_trade.mae_usd),
        mfe_usd=float(cpp_trade.mfe_usd),
        r_multiple=float(cpp_trade.r_multiple),
    )


