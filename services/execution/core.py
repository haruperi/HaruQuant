"""
Core simulator components.
"""

import time
import uuid
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from typing import Any, Optional

from services.utils.logger import logger


class DotDict(dict):
    """Dictionary that supports dot notation access to attributes."""

    def __getattr__(self, item):
        if item in self:
            return self[item]
        raise AttributeError(f"No such attribute: {item}")

    def __setattr__(self, key, value):
        self[key] = value


class TerminalInfo(DotDict):
    """Container for Terminal information."""

    pass


class DealInfo(DotDict):
    """Container for Deal information."""

    pass


class PositionInfo(DotDict):
    """Container for Position information."""

    pass


class OrderInfo(DotDict):
    """Container for active Order information."""

    pass


class HistoryOrderInfo(DotDict):
    """Container for History Order information."""

    pass


class SymbolInfo(DotDict):
    """Container for Symbol information."""

    pass


@dataclass
class TradeRecord:
    """Completed trade record aligned to the backtest_trades save contract."""

    trade_id: Optional[str] = None
    ticket: int = 0
    symbol: str = ""
    type: str = "buy"
    magic_number: int = 0
    strategy_name: Optional[str] = None
    setup_id: Optional[str] = None
    sample_type: Optional[str] = None
    comment: str = ""

    signal_timeframe: Optional[str] = None
    execution_timeframe: Optional[str] = None
    session: Optional[str] = None
    day_of_week: Optional[int] = None
    hour_of_day: Optional[int] = None

    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    time_in_trade: float = 0.0
    bars_in_trade: int = 0

    open_price: float = 0.0
    orig_open_price: Optional[float] = None
    orig_open_time: Optional[datetime] = None
    requested_entry_price: float = 0.0
    spread_at_entry: float = 0.0
    atr_at_entry: Optional[float] = None
    size: float = 0.0

    close_price: float = 0.0
    requested_exit_price: float = 0.0
    close_type: str = "UNKNOWN"
    exit_reason: str = "UNKNOWN"

    stop_loss_price: float = 0.0
    profit_target_price: float = 0.0
    initial_risk_pips: float = 0.0
    initial_risk_usd: float = 0.0

    balance_at_entry: float = 0.0
    equity_at_entry: float = 0.0
    margin_used: float = 0.0
    free_margin: float = 0.0

    max_position_size: float = 0.0
    partial_close_count: int = 0
    trailing_stop_used: bool = False
    breakeven_triggered: bool = False

    slippage_usd: float = 0.0
    fill_price_deviation: float = 0.0
    execution_latency_ms: float = 0.0

    profit_loss: float = 0.0
    profit_loss_pips: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    r_multiple: float = 0.0
    buy_hold: float = 0.0
    buy_hold_pips: float = 0.0

    mae_usd: float = 0.0
    mae_pips: float = 0.0
    mfe_usd: float = 0.0
    mfe_pips: float = 0.0
    drawdown: float = 0.0

    market_regime: Optional[str] = None
    volatility_bucket: Optional[str] = None
    correlation_cluster: Optional[str] = None

    rule_violation: bool = False
    manual_intervention: bool = False

    def to_dict(self):
        return _serialize_payload(asdict(self))


@dataclass
class TradeTracker:
    """Runtime-only tracker for an open trade."""

    original_volume: float = 0.0
    bars_in_trade: int = 0
    mfe_usd: float = 0.0
    mae_usd: float = 0.0
    mfe_pips: float = 0.0
    mae_pips: float = 0.0


class CloseType:
    """Canonical close type enums for trade records."""

    SL = type("SL", (), {"value": "SL"})()
    TP = type("TP", (), {"value": "TP"})()
    TIME_EXIT = type("TIME_EXIT", (), {"value": "TIME_EXIT"})()
    SIGNAL_EXIT = type("SIGNAL_EXIT", (), {"value": "SIGNAL_EXIT"})()
    BREAKEVEN = type("BREAKEVEN", (), {"value": "BREAKEVEN"})()
    TRAILING_STOP = type("TRAILING_STOP", (), {"value": "TRAILING_STOP"})()
    MANUAL = type("MANUAL", (), {"value": "MANUAL"})()
    UNKNOWN = type("UNKNOWN", (), {"value": "UNKNOWN"})()


class ExitReason:
    """Exit reason enum for trade records."""

    STOP_LOSS = type("STOP_LOSS", (), {"value": "STOP_LOSS"})()
    TAKE_PROFIT = type("TAKE_PROFIT", (), {"value": "TAKE_PROFIT"})()
    SIGNAL = type("SIGNAL", (), {"value": "SIGNAL"})()
    TIME = type("TIME", (), {"value": "TIME"})()
    MANUAL = type("MANUAL", (), {"value": "MANUAL"})()
    ERROR = type("ERROR", (), {"value": "ERROR"})()
    UNKNOWN = type("UNKNOWN", (), {"value": "UNKNOWN"})()


@dataclass
class BacktestResult:
    """Backtest result container (legacy compatibility)."""

    trades: list = None
    equity_curve: list = None
    params: dict = None
    score: float = 0.0
    metrics: dict = None


@dataclass
class EquityPoint:
    """Equity curve point aligned to backtest_equity_curve storage."""

    timestamp: Optional[datetime] = None
    balance: float = 0.0
    equity: float = 0.0
    drawdown: float = 0.0
    exposure: float = 0.0

    def to_dict(self):
        return _serialize_payload(asdict(self))


@dataclass
class RunResult:
    """Packaged engine result payload for simulation runs."""

    trades: list[TradeRecord]
    equity_curve: list[EquityPoint]
    processed_ticks: int = 0
    final_balance: float = 0.0
    final_equity: float = 0.0

    def to_dict(self):
        return _serialize_payload(asdict(self))


def _serialize_datetime(value: Optional[datetime]):
    if value is None:
        return None
    return value.isoformat()


def _serialize_payload(payload: Any):
    if isinstance(payload, datetime):
        return _serialize_datetime(payload)
    if isinstance(payload, dict):
        return {key: _serialize_payload(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_serialize_payload(item) for item in payload]
    return payload


class SimulatorState:
    """Holds the current state for the backtest simulator."""

    def __init__(self, account_info=None):
        if account_info is not None:
            if hasattr(account_info, "_asdict"):
                self.trading_account = DotDict(account_info._asdict())
            elif isinstance(account_info, dict):
                self.trading_account = DotDict(account_info)
            else:
                self.trading_account = DotDict(vars(account_info))
        else:
            self.trading_account = DotDict()

        self.terminal_info = TerminalInfo()

        self.trading_symbols = []
        self.trading_deals = []
        self.trading_history_deals = []
        self.trading_orders = []
        self.trading_history_orders = []
        self.open_trade_records_by_ticket = {}
        self.open_trade_trackers_by_ticket = {}
        self.completed_trade_records = []
        self.completed_equity_curve = []
        self.equity_peak = None
        self.current_tick_epoch = None
        self.current_tick_datetime = None
        self.last_rollover_datetime = None
        self.execution_settings = DotDict()


def history_deals_get(
    state: SimulatorState, date_from=None, date_to=None, group=None, ticket=None
):
    """Retrieve historical deals from state."""
    deals = state.trading_history_deals
    if ticket is not None:
        deals = [d for d in deals if getattr(d, "ticket", None) == ticket]
        return tuple(deals)

    if date_from is not None and date_to is not None:
        # Convert datetime to timestamp if necessary
        t_from = (
            int(date_from.timestamp()) if hasattr(date_from, "timestamp") else date_from
        )
        t_to = int(date_to.timestamp()) if hasattr(date_to, "timestamp") else date_to
        deals = [d for d in deals if t_from <= getattr(d, "time", 0) <= t_to]

    if group is not None:
        suffix = group.replace("*", "")
        deals = [d for d in deals if suffix in getattr(d, "symbol", "")]

    return tuple(deals)


def history_deals_total(state: SimulatorState, date_from, date_to):
    return len(history_deals_get(state, date_from, date_to))


def positions_get(state: SimulatorState, symbol=None, group=None, ticket=None):
    positions = state.trading_deals
    if ticket is not None:
        positions = [
            p
            for p in positions
            if getattr(p, "ticket", None) == ticket
            or getattr(p, "identifier", None) == ticket
        ]
    elif symbol is not None:
        positions = [p for p in positions if getattr(p, "symbol", "") == symbol]
    elif group is not None:
        suffix = group.replace("*", "")
        positions = [p for p in positions if suffix in getattr(p, "symbol", "")]
    return tuple(positions)


def positions_total(state: SimulatorState):
    return len(state.trading_deals)


def orders_get(state: SimulatorState, symbol=None, group=None, ticket=None):
    orders = state.trading_orders
    if ticket is not None:
        orders = [o for o in orders if getattr(o, "ticket", None) == ticket]
    elif symbol is not None:
        orders = [o for o in orders if getattr(o, "symbol", "") == symbol]
    elif group is not None:
        suffix = group.replace("*", "")
        orders = [o for o in orders if suffix in getattr(o, "symbol", "")]
    return tuple(orders)


def orders_total(state: SimulatorState):
    return len(state.trading_orders)


def history_orders_get(
    state: SimulatorState, date_from=None, date_to=None, group=None, ticket=None
):
    orders = state.trading_history_orders
    if ticket is not None:
        orders = [o for o in orders if getattr(o, "ticket", None) == ticket]
        return tuple(orders)

    if date_from is not None and date_to is not None:
        t_from = (
            int(date_from.timestamp()) if hasattr(date_from, "timestamp") else date_from
        )
        t_to = int(date_to.timestamp()) if hasattr(date_to, "timestamp") else date_to
        orders = [o for o in orders if t_from <= getattr(o, "time_setup", 0) <= t_to]

    if group is not None:
        suffix = group.replace("*", "")
        orders = [o for o in orders if suffix in getattr(o, "symbol", "")]

    return tuple(orders)


def history_orders_total(state: SimulatorState, date_from, date_to):
    return len(history_orders_get(state, date_from, date_to))


def symbols_get(state: SimulatorState, group=None):
    syms = state.trading_symbols
    if group is not None:
        suffix = group.replace("*", "")
        syms = [s for s in syms if suffix in getattr(s, "name", "")]
    return tuple(syms)


def symbols_total(state: SimulatorState):
    return len(state.trading_symbols)


def symbol_info(state: SimulatorState, name: str):
    syms = [s for s in state.trading_symbols if getattr(s, "name", "") == name]
    return syms[0] if syms else None


def _volume_precision(volume_value) -> int:
    try:
        numeric_value = float(volume_value or 0.0)
    except Exception:
        return 2

    if numeric_value <= 0.0:
        return 2

    text = f"{numeric_value:.10f}".rstrip("0").rstrip(".")
    if "." not in text:
        return 0
    return len(text.split(".", 1)[1])


def _format_volume_for_symbol(sym_info, volume_value) -> str:
    volume_min = getattr(sym_info, "volume_min", 0.0)
    precision = _volume_precision(volume_min)
    return f"{float(volume_value):.{precision}f}"


def _state_now_epoch(state: SimulatorState) -> int:
    tick_epoch = getattr(state, "current_tick_epoch", None)
    if tick_epoch is not None:
        return int(tick_epoch)
    return int(time.time())


def _coerce_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if value is None:
        return datetime.utcnow()
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if hasattr(value, "timestamp"):
        return datetime.fromtimestamp(float(value.timestamp()))
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value))
    return datetime.utcnow()


def _state_now_datetime(state: SimulatorState) -> datetime:
    tick_dt = getattr(state, "current_tick_datetime", None)
    if tick_dt is not None:
        return _coerce_datetime(tick_dt)
    return datetime.utcnow()


def _position_ticket(position) -> int:
    return int(
        getattr(
            position,
            "ticket",
            getattr(position, "position_id", getattr(position, "identifier", 0)),
        )
        or 0
    )


def _pip_size(state: SimulatorState, symbol_name: str) -> float:
    sym_info = symbol_info(state, symbol_name)
    point = float(getattr(sym_info, "point", 0.00001) or 0.00001)
    return point * 10.0


def _spread_at_entry_pips(state: SimulatorState, symbol_name: str) -> float:
    sym_info = symbol_info(state, symbol_name)
    if sym_info is None:
        return 0.0
    pip_size = _pip_size(state, symbol_name)
    if pip_size <= 0.0:
        return 0.0
    ask = float(getattr(sym_info, "ask", 0.0) or 0.0)
    bid = float(getattr(sym_info, "bid", 0.0) or 0.0)
    if ask <= 0.0 or bid <= 0.0:
        return 0.0
    return float((ask - bid) / pip_size)


def _execution_settings(state: SimulatorState) -> DotDict:
    settings = getattr(state, "execution_settings", None)
    if isinstance(settings, DotDict):
        return settings
    if isinstance(settings, dict):
        return DotDict(settings)
    return DotDict()


def _commission_for_volume(state: SimulatorState, volume: float) -> float:
    commission_per_lot = float(getattr(state.trading_account, "commission", 0.0) or 0.0)
    if commission_per_lot == 0.0 or float(volume) <= 0.0:
        return 0.0
    return -abs(float(volume) * commission_per_lot)


def _resolve_slippage_points(state: SimulatorState, symbol_name: str) -> float:
    settings = _execution_settings(state)
    model = str(settings.get("slippage_model", "fixed") or "fixed").strip().lower()
    if model in {"", "none", "disabled"}:
        return 0.0
    if model == "fixed":
        return max(0.0, float(settings.get("slippage_points", 0.0) or 0.0))

    min_points = max(0.0, float(settings.get("slippage_min", 0.0) or 0.0))
    max_points = max(
        min_points, float(settings.get("slippage_max", min_points) or min_points)
    )
    if max_points <= min_points:
        return min_points

    seed = int(getattr(state, "current_tick_epoch", 0) or _state_now_epoch(state))
    symbol_seed = sum(ord(ch) for ch in str(symbol_name or ""))
    bucket = float((seed + symbol_seed) % 1000) / 999.0
    return min_points + ((max_points - min_points) * bucket)


def _apply_market_slippage(
    state: SimulatorState,
    sym_info,
    symbol_name: str,
    order_type: int,
    requested_price: float,
    market_price: float,
    volume: float,
) -> tuple[float, float, float]:
    point = float(getattr(sym_info, "point", 0.00001) or 0.00001)
    slippage_points = _resolve_slippage_points(state, symbol_name)
    if slippage_points <= 0.0 or point <= 0.0:
        return float(market_price), 0.0, 0.0

    price_delta = float(slippage_points * point)
    exec_price = (
        float(market_price + price_delta)
        if int(order_type) == 0
        else float(market_price - price_delta)
    )
    requested = float(requested_price if requested_price > 0.0 else market_price)
    fill_price_deviation = float(exec_price - requested)
    contract_size = float(
        getattr(sym_info, "trade_contract_size", 100000.0) or 100000.0
    )
    slippage_usd = float(abs(fill_price_deviation) * float(volume) * contract_size)
    return exec_price, fill_price_deviation, slippage_usd


def _trade_side_name(order_type: int) -> str:
    return "buy" if int(order_type) == 0 else "sell"


def _request_value(req_get, name: str, default=None):
    value = req_get(name, default)
    return default if value is None else value


def _build_trade_record(
    state: SimulatorState,
    request,
    position_ticket: int,
    order_type: int,
    symbol_name: str,
    volume: float,
    exec_price: float,
    requested_entry_price: float,
    sl: float,
    tp: float,
    margin_required: float,
    profit_calculator=None,
) -> TradeRecord:
    req_get = (
        request.get
        if isinstance(request, dict)
        else lambda k, d=None: getattr(request, k, d)
    )
    now_dt = _state_now_datetime(state)
    balance = float(getattr(state.trading_account, "balance", 0.0) or 0.0)
    equity = float(getattr(state.trading_account, "equity", balance) or balance)
    margin_before = float(getattr(state.trading_account, "margin", 0.0) or 0.0)
    margin_used = margin_before + float(margin_required)
    free_margin = equity - margin_used
    pip_size = _pip_size(state, symbol_name)

    record = TradeRecord(
        trade_id=str(uuid.uuid4()),
        ticket=int(position_ticket),
        symbol=str(symbol_name),
        type=_trade_side_name(order_type),
        magic_number=int(req_get("magic", 0) or 0),
        strategy_name=_request_value(req_get, "strategy_name", None),
        setup_id=_request_value(req_get, "setup_id", None),
        sample_type=_request_value(req_get, "sample_type", None),
        comment=str(req_get("comment", "") or ""),
        signal_timeframe=_request_value(req_get, "signal_timeframe", None),
        execution_timeframe=_request_value(req_get, "execution_timeframe", None),
        session=_request_value(req_get, "session", None),
        day_of_week=int(req_get("day_of_week", now_dt.weekday()) or now_dt.weekday()),
        hour_of_day=int(req_get("hour_of_day", now_dt.hour) or now_dt.hour),
        open_time=now_dt,
        open_price=float(exec_price),
        orig_open_price=float(exec_price),
        orig_open_time=now_dt,
        requested_entry_price=float(requested_entry_price),
        spread_at_entry=float(_spread_at_entry_pips(state, symbol_name)),
        atr_at_entry=_request_value(req_get, "atr_at_entry", None),
        size=float(volume),
        stop_loss_price=float(sl),
        profit_target_price=float(tp),
        balance_at_entry=balance,
        equity_at_entry=equity,
        margin_used=margin_used,
        free_margin=free_margin,
        max_position_size=float(volume),
        market_regime=_request_value(req_get, "market_regime", None),
        volatility_bucket=_request_value(req_get, "volatility_bucket", None),
        correlation_cluster=_request_value(req_get, "correlation_cluster", None),
    )

    if sl > 0.0 and pip_size > 0.0:
        if int(order_type) == 0:
            record.initial_risk_pips = float(
                max((record.open_price - float(sl)) / pip_size, 0.0)
            )
        else:
            record.initial_risk_pips = float(
                max((float(sl) - record.open_price) / pip_size, 0.0)
            )
        if profit_calculator is not None:
            calc_value = profit_calculator(
                int(order_type),
                symbol_name,
                float(volume),
                float(exec_price),
                float(sl),
            )
            if calc_value is None:
                raise RuntimeError(
                    "order_calc_profit returned None while strict profit calculation is required."
                )
            record.initial_risk_usd = float(abs(calc_value))

    return record


def _open_trade_tracking(
    state: SimulatorState,
    request,
    position_ticket: int,
    order_type: int,
    symbol_name: str,
    volume: float,
    exec_price: float,
    requested_entry_price: float,
    sl: float,
    tp: float,
    margin_required: float,
    profit_calculator=None,
) -> None:
    state.open_trade_records_by_ticket[int(position_ticket)] = _build_trade_record(
        state=state,
        request=request,
        position_ticket=position_ticket,
        order_type=order_type,
        symbol_name=symbol_name,
        volume=volume,
        exec_price=exec_price,
        requested_entry_price=requested_entry_price,
        sl=sl,
        tp=tp,
        margin_required=margin_required,
        profit_calculator=profit_calculator,
    )
    state.open_trade_trackers_by_ticket[int(position_ticket)] = TradeTracker(
        original_volume=float(volume)
    )


def _update_trade_tracking(
    state: SimulatorState, position, current_price: float, profit_usd: float
) -> None:
    ticket = _position_ticket(position)
    tracker = state.open_trade_trackers_by_ticket.get(ticket)
    record = state.open_trade_records_by_ticket.get(ticket)
    if tracker is None or record is None:
        return

    tracker.bars_in_trade += 1
    tracker.mfe_usd = max(float(tracker.mfe_usd), float(profit_usd))
    tracker.mae_usd = min(float(tracker.mae_usd), float(profit_usd))

    pip_size = _pip_size(state, record.symbol)
    if pip_size > 0.0:
        if record.type == "buy":
            pips = (float(current_price) - float(record.open_price)) / pip_size
        else:
            pips = (float(record.open_price) - float(current_price)) / pip_size
        tracker.mfe_pips = max(float(tracker.mfe_pips), float(pips))
        tracker.mae_pips = min(float(tracker.mae_pips), float(pips))


def _resolve_close_labels(close_reason: str, is_partial: bool) -> tuple[str, str]:
    reason = str(close_reason or "").strip().lower()
    if is_partial:
        return ("PARTIAL", "partial_close")
    if reason == "stop_loss":
        return ("SL", "stop_loss")
    if reason == "take_profit":
        return ("TP", "take_profit")
    if "pending trigger flip" in reason:
        return ("REVERSE", "opposite_pending_trigger")
    if "signal" in reason:
        return ("SIGNAL_EXIT", "signal_exit")
    if reason:
        return (reason.upper(), reason)
    return ("MANUAL_EXIT", "manual_exit")


def _finalize_trade_tracking(
    state: SimulatorState,
    position,
    close_volume: float,
    close_price: float,
    realized_profit: float,
    requested_exit_price: float,
    close_reason: str,
) -> TradeRecord | None:
    ticket = _position_ticket(position)
    base_record = state.open_trade_records_by_ticket.get(ticket)
    tracker = state.open_trade_trackers_by_ticket.get(ticket)
    if base_record is None or tracker is None:
        return None

    current_volume = float(getattr(position, "volume", 0.0) or 0.0)
    if current_volume <= 0.0 or close_volume <= 0.0:
        return None

    partial = close_volume < current_volume
    completed = replace(base_record)
    completed.size = float(close_volume)
    completed.close_time = _state_now_datetime(state)
    completed.close_price = float(close_price)
    completed.requested_exit_price = float(requested_exit_price)
    completed.time_in_trade = max(
        0.0,
        float(
            (
                completed.close_time - _coerce_datetime(completed.open_time)
            ).total_seconds()
        ),
    )
    completed.bars_in_trade = int(tracker.bars_in_trade)
    completed.commission = float(getattr(position, "commission", 0.0) or 0.0)
    completed.swap = float(getattr(position, "swap", 0.0) or 0.0)
    completed.profit_loss = (
        float(realized_profit) + completed.commission + completed.swap
    )
    completed.mae_usd = abs(min(float(tracker.mae_usd), 0.0))
    completed.mfe_usd = max(float(tracker.mfe_usd), 0.0)
    completed.mae_pips = abs(min(float(tracker.mae_pips), 0.0))
    completed.mfe_pips = max(float(tracker.mfe_pips), 0.0)
    completed.drawdown = float(completed.mae_usd)
    completed.close_type, completed.exit_reason = _resolve_close_labels(
        close_reason, partial
    )

    pip_size = _pip_size(state, completed.symbol)
    if pip_size > 0.0:
        if completed.type == "buy":
            completed.profit_loss_pips = float(
                (completed.close_price - completed.open_price) / pip_size
            )
        else:
            completed.profit_loss_pips = float(
                (completed.open_price - completed.close_price) / pip_size
            )

    if completed.initial_risk_usd > 0.0:
        completed.r_multiple = float(completed.profit_loss / completed.initial_risk_usd)

    if partial:
        remaining_volume = float(current_volume - close_volume)
        base_record.size = remaining_volume
        base_record.partial_close_count = int(base_record.partial_close_count) + 1
        volume_ratio = (
            remaining_volume / current_volume if current_volume > 0.0 else 0.0
        )
        base_record.initial_risk_usd = (
            float(base_record.initial_risk_usd) * volume_ratio
        )
        completed.partial_close_count = 1
    else:
        state.open_trade_records_by_ticket.pop(ticket, None)
        state.open_trade_trackers_by_ticket.pop(ticket, None)

    state.completed_trade_records.append(completed)
    return completed


def monitor_positions(
    state: SimulatorState,
    verbose: bool = False,
    allow_auto_close: bool = True,
    profit_calculator=None,
    strict_calc_access: bool = False,
) -> None:
    """Monitor open positions, update mark-to-market fields, and close on SL/TP."""
    _apply_swaps(state, verbose=verbose)
    now = _state_now_epoch(state)
    now_msc = now * 1000
    to_close = []

    for position in list(state.trading_deals):
        entry = str(getattr(position, "entry", 0))
        if entry != "0":
            continue

        symbol_name = str(getattr(position, "symbol", "") or "")
        if not symbol_name:
            continue

        sym_info = symbol_info(state, symbol_name)
        if sym_info is None:
            continue

        bid = float(getattr(sym_info, "bid", 0.0) or 0.0)
        ask = float(getattr(sym_info, "ask", 0.0) or 0.0)
        if bid <= 0.0 or ask <= 0.0:
            continue

        _type_val = getattr(position, "type", -1)
        try:
            order_type = int(_type_val)
        except (ValueError, TypeError):
            order_type = -1
        is_buy = order_type == 0
        is_sell = order_type == 1
        if not is_buy and not is_sell:
            continue

        entry_price = float(
            getattr(position, "price_open", getattr(position, "price", 0.0)) or 0.0
        )
        volume = float(getattr(position, "volume", 0.0) or 0.0)
        if entry_price <= 0.0 or volume <= 0.0:
            continue

        exit_price = bid if is_buy else ask

        profit = 0.0
        if profit_calculator is not None:
            calc_value = profit_calculator(
                order_type, symbol_name, volume, entry_price, exit_price
            )
            if calc_value is None:
                raise RuntimeError(
                    "order_calc_profit returned None while strict profit calculation is required."
                )
            profit = float(calc_value)
        elif strict_calc_access:
            raise RuntimeError(
                "order_calc_profit access is required but no profit_calculator was provided."
            )
        else:
            try:
                contract_size = float(
                    getattr(sym_info, "trade_contract_size", 100000.0) or 100000.0
                )
                delta = (
                    (exit_price - entry_price) if is_buy else (entry_price - exit_price)
                )
                profit = delta * volume * contract_size
            except Exception:
                profit = 0.0

        position.profit = float(profit)
        position.price_current = float(exit_price)
        position.time_update = now
        position.time_update_msc = now_msc
        _update_trade_tracking(state, position, exit_price, profit)

        if verbose:
            side_name = "BUY" if is_buy else "SELL"
            logger.debug(
                "[monitor_positions]",
                component="execution.core",
                side=side_name,
                ticket=int(getattr(position, "ticket", 0) or 0),
                symbol=symbol_name,
                entry=float(entry_price),
                current=float(exit_price),
                profit=float(profit),
            )

        sl = float(getattr(position, "sl", 0.0) or 0.0)
        tp = float(getattr(position, "tp", 0.0) or 0.0)
        should_close = False
        close_reason = ""

        if is_buy:
            if sl > 0.0 and bid <= sl:
                should_close = True
                close_reason = "stop_loss"
            elif tp > 0.0 and bid >= tp:
                should_close = True
                close_reason = "take_profit"
        else:
            if sl > 0.0 and ask >= sl:
                should_close = True
                close_reason = "stop_loss"
            elif tp > 0.0 and ask <= tp:
                should_close = True
                close_reason = "take_profit"

        if should_close and allow_auto_close:
            to_close.append((position, exit_price, profit, close_reason))
        elif should_close and verbose:
            logger.debug(
                "[monitor_positions] Close condition met (dry-run)",
                component="execution.core",
                ticket=int(getattr(position, "ticket", 0) or 0),
                reason=close_reason,
            )

    for position, close_price, profit, close_reason in to_close:
        if position not in state.trading_deals:
            continue

        vol = float(getattr(position, "volume", 0.0) or 0.0)
        close_comm = _commission_for_volume(state, vol)
        position.commission = (
            float(getattr(position, "commission", 0.0) or 0.0) + close_comm
        )

        _finalize_trade_tracking(
            state,
            position,
            vol,
            close_price,
            profit,
            close_price,
            close_reason,
        )

        balance = float(getattr(state.trading_account, "balance", 0.0) or 0.0)
        state.trading_account.balance = balance + float(profit) + close_comm

        closed_row = DealInfo(dict(position))
        closed_row.profit = float(profit)
        closed_row.price_current = float(close_price)
        closed_row.entry = 1
        closed_row.time_update = now
        closed_row.time_update_msc = now_msc
        if not getattr(closed_row, "comment", ""):
            closed_row.comment = str(close_reason)

        state.trading_history_deals.append(closed_row)
        state.trading_deals = [p for p in state.trading_deals if p is not position]

        if verbose:
            print(
                f"[monitor_positions] Closed {getattr(position, 'symbol', '')} "
                f"ticket={int(getattr(position, 'ticket', 0) or 0)} "
                f"reason={close_reason} profit={float(profit):.2f}"
            )


def monitor_pending_orders(
    state: SimulatorState,
    verbose: bool = False,
    allow_auto_trigger: bool = True,
    allow_auto_expire: bool = True,
    profit_calculator=None,
    margin_calculator=None,
    strict_calc_access: bool = False,
) -> None:
    """Monitor pending orders, expire them, and trigger matched entries."""
    now = _state_now_epoch(state)
    now_msc = now * 1000

    to_expire = []
    to_trigger = []

    def utc_day_key(ts: int) -> int:
        if ts <= 0:
            return 0
        return int(ts // 86400)

    for order in list(state.trading_orders):
        if str(getattr(order, "action", "")) != "order_open":
            continue

        pending_type = int(getattr(order, "type", -1) or -1)
        is_buy_limit = pending_type == 2
        is_sell_limit = pending_type == 3
        is_buy_stop = pending_type == 4
        is_sell_stop = pending_type == 5
        if not (is_buy_limit or is_sell_limit or is_buy_stop or is_sell_stop):
            continue

        type_time = int(getattr(order, "type_time", 0) or 0)
        expiration = int(getattr(order, "time_expiration", 0) or 0)
        expired = False
        if type_time == 1:
            setup = int(getattr(order, "time_setup", 0) or 0)
            expired = utc_day_key(setup) > 0 and utc_day_key(setup) != utc_day_key(now)
        elif type_time in (2, 3):
            expired = expiration > 0 and now >= expiration

        if expired:
            to_expire.append(order)
            continue

        symbol_name = str(getattr(order, "symbol", "") or "")
        if not symbol_name:
            continue
        sym_info = symbol_info(state, symbol_name)
        if sym_info is None:
            continue

        bid = float(getattr(sym_info, "bid", 0.0) or 0.0)
        ask = float(getattr(sym_info, "ask", 0.0) or 0.0)
        if bid <= 0.0 or ask <= 0.0:
            continue

        trigger_price = float(
            getattr(order, "price_open", getattr(order, "price_current", 0.0)) or 0.0
        )
        if trigger_price <= 0.0:
            continue

        triggered = False
        if is_buy_limit:
            triggered = ask <= trigger_price
        elif is_sell_limit:
            triggered = bid >= trigger_price
        elif is_buy_stop:
            triggered = ask >= trigger_price
        elif is_sell_stop:
            triggered = bid <= trigger_price

        if triggered:
            to_trigger.append(order)

    if not allow_auto_expire and verbose and to_expire:
        for order in to_expire:
            print(
                f"[monitor_pending_orders] Expire condition met (dry-run) "
                f"ticket={int(getattr(order, 'ticket', 0) or 0)}"
            )

    for order in to_expire:
        if not allow_auto_expire:
            continue
        if order not in state.trading_orders:
            continue
        hist_row = HistoryOrderInfo(dict(order))
        hist_row.state = 6
        hist_row.time_done = now
        hist_row.time_done_msc = now_msc
        state.trading_history_orders.append(hist_row)
        state.trading_orders = [o for o in state.trading_orders if o is not order]
        if verbose:
            print(
                f"[monitor_pending_orders] Expired order "
                f"ticket={int(getattr(order, 'ticket', 0) or 0)}"
            )

    if not allow_auto_trigger and verbose and to_trigger:
        for order in to_trigger:
            print(
                f"[monitor_pending_orders] Trigger condition met (dry-run) "
                f"ticket={int(getattr(order, 'ticket', 0) or 0)}"
            )

    processed_tickets = set()
    for order in to_trigger:
        if not allow_auto_trigger:
            continue
        if order not in state.trading_orders:
            continue

        ticket = int(getattr(order, "ticket", 0) or 0)
        if ticket in processed_tickets:
            continue
        processed_tickets.add(ticket)

        pending_type = int(getattr(order, "type", -1) or -1)
        deal_side = 0 if pending_type in (2, 4) else 1

        volume = float(getattr(order, "volume_current", 0.0) or 0.0)
        if volume <= 0.0:
            volume = float(getattr(order, "volume_initial", 0.0) or 0.0)
        symbol_name = str(getattr(order, "symbol", "") or "")
        if volume <= 0.0 or not symbol_name:
            continue

        request = DotDict(
            action=1,
            magic=int(getattr(order, "magic", 0) or 0),
            symbol=symbol_name,
            volume=volume,
            type=deal_side,
            price=0.0,
            sl=float(getattr(order, "sl", 0.0) or 0.0),
            tp=float(getattr(order, "tp", 0.0) or 0.0),
            type_filling=int(getattr(order, "type_filling", 0) or 0),
            type_time=int(getattr(order, "type_time", 0) or 0),
            comment=str(getattr(order, "comment", "") or ""),
        )

        result = order_send(
            state,
            request,
            profit_calculator=profit_calculator,
            margin_calculator=margin_calculator,
            strict_calc_access=strict_calc_access,
            verbose=verbose,
        )

        hist_row = HistoryOrderInfo(dict(order))
        hist_row.time_done = now
        hist_row.time_done_msc = now_msc
        hist_row.state = 4 if int(getattr(result, "retcode", 0) or 0) == 10009 else 5
        state.trading_history_orders.append(hist_row)
        state.trading_orders = [o for o in state.trading_orders if o is not order]

        if verbose:
            print(
                f"[monitor_pending_orders] Triggered order "
                f"ticket={ticket} retcode={int(getattr(result, 'retcode', 0) or 0)}"
            )


def _record_equity_point(state: SimulatorState, balance: float, equity: float) -> None:
    peak = getattr(state, "equity_peak", None)
    if peak is None:
        peak = float(equity)
    else:
        peak = max(float(peak), float(equity))
    state.equity_peak = peak
    point = EquityPoint(
        timestamp=_state_now_datetime(state),
        balance=float(balance),
        equity=float(equity),
        drawdown=float(max(peak - float(equity), 0.0)),
        exposure=float(
            sum(
                float(getattr(p, "volume", 0.0) or 0.0)
                for p in state.trading_deals
                if str(getattr(p, "entry", 0)) == "0"
            )
        ),
    )
    state.completed_equity_curve.append(point)


_FX_MARGIN_CURRENCIES = {
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "AUD",
    "NZD",
    "CAD",
    "CHF",
    "SGD",
    "HKD",
    "NOK",
    "SEK",
    "DKK",
    "PLN",
    "CZK",
    "HUF",
    "TRY",
    "ZAR",
    "MXN",
    "CNH",
}


def _is_margin_tier_symbol(symbol_name: str) -> bool:
    symbol = str(symbol_name or "").upper()
    if not symbol:
        return False
    if symbol.startswith("XAUUSD"):
        return True
    match = re.match(r"^([A-Z]{3})([A-Z]{3})", symbol)
    if not match:
        return False
    base, quote = match.groups()
    return base in _FX_MARGIN_CURRENCIES and quote in _FX_MARGIN_CURRENCIES


def _position_notional(state: SimulatorState, position) -> float:
    symbol_name = str(getattr(position, "symbol", "") or "")
    sym_info = symbol_info(state, symbol_name)
    contract_size = float(
        getattr(sym_info, "trade_contract_size", 100000.0) or 100000.0
    )
    market_price = float(
        getattr(
            position,
            "price_current",
            getattr(position, "price_open", getattr(position, "price", 0.0)),
        )
        or 0.0
    )
    return float(
        abs(float(getattr(position, "volume", 0.0) or 0.0))
        * contract_size
        * market_price
    )


def _apply_margin_tier_policy(state: SimulatorState) -> None:
    policy = getattr(state.execution_settings, "margin_tier_policy", None)
    if not policy or not bool(getattr(policy, "enabled", False)):
        return

    threshold = float(getattr(policy, "threshold_notional", 500000.0) or 500000.0)
    base_leverage = float(getattr(policy, "base_leverage", 1000.0) or 1000.0)
    excess_leverage = float(getattr(policy, "excess_leverage", 500.0) or 500.0)
    if threshold <= 0.0 or base_leverage <= 0.0 or excess_leverage <= 0.0:
        return

    grouped_positions: dict[str, list[Any]] = {}
    for position in state.trading_deals:
        if str(getattr(position, "entry", 0)) != "0":
            continue
        symbol_name = str(getattr(position, "symbol", "") or "")
        if not _is_margin_tier_symbol(symbol_name):
            continue
        grouped_positions.setdefault(symbol_name, []).append(position)

    for symbol_name, positions in grouped_positions.items():
        notionals = {
            int(getattr(pos, "ticket", 0) or 0): _position_notional(state, pos)
            for pos in positions
        }
        total_notional = float(sum(notionals.values()) or 0.0)
        if total_notional <= 0.0:
            for position in positions:
                position.margin_required = 0.0
            continue

        tier_one_margin = min(total_notional, threshold) / base_leverage
        tier_two_margin = max(total_notional - threshold, 0.0) / excess_leverage
        total_margin = float(tier_one_margin + tier_two_margin)

        for position in positions:
            ticket = int(getattr(position, "ticket", 0) or 0)
            position_notional = float(notionals.get(ticket, 0.0) or 0.0)
            share = position_notional / total_notional if total_notional > 0.0 else 0.0
            position.margin_required = float(total_margin * share)


def _apply_swaps(state: SimulatorState, verbose: bool = False) -> None:
    """Check for daily rollover and apply swaps to open positions."""
    now_dt = _state_now_datetime(state)
    if state.last_rollover_datetime is None:
        state.last_rollover_datetime = now_dt
        return

    # Check if we crossed 00:00 (daily rollover)
    if now_dt.date() <= state.last_rollover_datetime.date():
        return

    # Rollover occurred - count how many midnight rollovers we crossed
    num_days = (now_dt.date() - state.last_rollover_datetime.date()).days

    for d in range(num_days):
        rollover_dt = state.last_rollover_datetime + timedelta(days=d + 1)
        day_of_week = rollover_dt.weekday()  # Python: 0=Mon, 2=Wed

        for position in state.trading_deals:
            # Only process open positions (entry=0)
            if str(getattr(position, "entry", 0)) != "0":
                continue

            symbol_name = str(getattr(position, "symbol", "") or "")
            sym_info = symbol_info(state, symbol_name)
            if sym_info is None:
                continue

            swap_long = float(getattr(sym_info, "swap_long", 0.0) or 0.0)
            swap_short = float(getattr(sym_info, "swap_short", 0.0) or 0.0)
            swap_mode = int(getattr(sym_info, "swap_mode", 0) or 0)

            # Swaps disabled
            if swap_mode == 0:
                continue

            rollover3days = int(
                getattr(sym_info, "swap_rollover3days", 3) or 3
            )  # MQL5: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
            # Triple swap is applied when holding over the night of 'rollover3days'.
            # For example, if rollover3days is 3 (Wednesday), it's applied when crossing from Wednesday to Thursday.
            # In our simulation, when we cross to Thursday, rollover_dt.weekday() will be 3 (Thursday).
            # So py_rollover3days should be (mql_day + 1) % 7?
            # Wait: MQL 3 (Wed) -> crosses to Thu -> Python 3 (Thu). Correct.
            # MQL 0 (Sun) -> crosses to Mon -> Python 0 (Mon). Correct.
            # MQL 6 (Sat) -> crosses to Sun -> Python 6 (Sun). Correct.
            # So the Python weekday we are looking for is exactly the MQL day index.
            py_rollover3days = rollover3days

            multiplier = 3.0 if day_of_week == py_rollover3days else 1.0

            order_type = int(getattr(position, "type", 0) or 0)
            swap_value = swap_long if order_type == 0 else swap_short
            volume = float(getattr(position, "volume", 0.0) or 0.0)

            daily_swap = 0.0
            if swap_mode == 1:  # Points
                point = float(getattr(sym_info, "point", 0.00001) or 0.00001)
                contract_size = float(
                    getattr(sym_info, "trade_contract_size", 100000.0) or 100000.0
                )
                # Swap in points formula: Volume * SwapValue * Point * ContractSize
                daily_swap = volume * swap_value * point * contract_size
            elif swap_mode == 2:  # Currency
                # Swap in currency: multiplier * volume * swap_value (assuming swap_value is per lot)
                daily_swap = volume * swap_value
            elif swap_mode == 3:  # Interest
                # TODO: Implement interest-based swap calculation if needed
                pass

            total_applied = daily_swap * multiplier
            position.swap = float(getattr(position, "swap", 0.0) or 0.0) + total_applied

            # Update balance immediately for applied swap (MT5 behavior)
            balance = float(getattr(state.trading_account, "balance", 0.0) or 0.0)
            state.trading_account.balance = balance + total_applied

            if verbose and abs(total_applied) > 1e-8:
                logger.info(
                    f"[swap] Applied swap to {symbol_name} ticket={_position_ticket(position)}: "
                    f"{total_applied:.2f} (mode={swap_mode}, multiplier={multiplier})"
                )

    state.last_rollover_datetime = now_dt


def monitor_account(state: SimulatorState, verbose: bool = False) -> None:
    """Monitor account aggregates from open positions."""
    _apply_swaps(state, verbose=verbose)
    _apply_margin_tier_policy(state)
    total_unrealized_profit = 0.0
    used_margin = 0.0

    for position in state.trading_deals:
        entry = str(getattr(position, "entry", 0))
        if entry != "0":
            continue
        total_unrealized_profit += float(getattr(position, "profit", 0.0) or 0.0)
        used_margin += float(getattr(position, "margin_required", 0.0) or 0.0)

    balance = float(getattr(state.trading_account, "balance", 0.0) or 0.0)
    equity = balance + total_unrealized_profit
    margin_free = equity - used_margin
    margin_level = (equity / used_margin) * 100.0 if used_margin > 0.0 else 0.0

    state.trading_account.profit = float(total_unrealized_profit)
    state.trading_account.equity = float(equity)
    state.trading_account.margin = float(used_margin)
    state.trading_account.margin_free = float(margin_free)
    state.trading_account.margin_level = float(margin_level)
    _record_equity_point(state, balance, equity)

    if verbose:
        print(
            "sim -> account | "
            f"balance {balance:.2f} | "
            f"profit {total_unrealized_profit:.2f} | "
            f"equity {equity:.2f} | "
            f"margin {used_margin:.2f} | "
            f"margin_free {margin_free:.2f} | "
            f"margin_level {margin_level:.2f}"
        )


def order_send(
    state: SimulatorState,
    request,
    profit_calculator=None,
    margin_calculator=None,
    strict_calc_access: bool = False,
    verbose: bool = False,
) -> DotDict:
    """
    Process a TradeRequest and update the SimulatorState.
    """
    req_get = (
        request.get
        if isinstance(request, dict)
        else lambda k, d=None: getattr(request, k, d)
    )

    result = DotDict(
        request=request,
        volume=req_get("volume", 0.0),
        retcode=10009,
        deal=0,
        order=0,
        price=0.0,
        comment="Request executed",
        bid=0.0,
        ask=0.0,
    )

    action = req_get("action", 0)
    if action == 0:
        action = 1

    is_market_deal = action == 1
    is_pending = action == 5
    is_sltp = action == 6
    is_modify = action == 7
    is_remove = action == 8

    if (
        not is_market_deal
        and not is_pending
        and not is_sltp
        and not is_modify
        and not is_remove
    ):
        result.retcode = 10013
        result.comment = "Unsupported trade action in tester order_send()"
        return result

    if is_sltp:
        position_ticket = int(req_get("position", 0) or 0)
        symbol_name = req_get("symbol", "")
        sl_value = float(req_get("sl", 0.0))
        tp_value = float(req_get("tp", 0.0))

        positions = state.trading_deals
        if position_ticket > 0:
            positions = [
                p
                for p in positions
                if getattr(p, "ticket", None) == position_ticket
                or getattr(p, "position_id", None) == position_ticket
                or getattr(p, "identifier", None) == position_ticket
            ]
        if symbol_name:
            positions = [
                p for p in positions if getattr(p, "symbol", "") == symbol_name
            ]

        if not positions:
            result.retcode = 10013
            result.comment = "Position not found"
            return result

        now = _state_now_epoch(state)
        for position in positions:
            position.sl = sl_value
            position.tp = tp_value
            position.time_update = now
            position.time_update_msc = now * 1000
            ticket = _position_ticket(position)
            record = state.open_trade_records_by_ticket.get(ticket)
            if record is not None:
                record.stop_loss_price = float(sl_value)
                record.profit_target_price = float(tp_value)

        first = positions[0]
        result.retcode = 10009
        result.deal = int(getattr(first, "ticket", 0))
        result.order = int(getattr(first, "order", 0))
        result.price = float(
            getattr(first, "price_current", getattr(first, "price", 0.0))
        )
        result.comment = "Request executed"
        if verbose:
            print(
                f"[order_send] Modified SL/TP symbol={symbol_name} "
                f"position={position_ticket} sl={sl_value} tp={tp_value}"
            )
        return result

    if is_modify:
        order_ticket = int(req_get("order", 0) or 0)
        if order_ticket <= 0:
            result.retcode = 10013
            result.comment = "Order ticket is required"
            return result

        pending_order = next(
            (
                o
                for o in state.trading_orders
                if int(getattr(o, "ticket", 0)) == order_ticket
            ),
            None,
        )
        if pending_order is None:
            result.retcode = 10013
            result.comment = "Order not found"
            return result

        price = req_get("price", None)
        sl = req_get("sl", None)
        tp = req_get("tp", None)
        stoplimit = req_get("stoplimit", None)
        expiration = req_get("expiration", None)
        type_time = req_get("type_time", None)

        if price is not None:
            pending_order.price_open = float(price)
            pending_order.price_current = float(price)
        if sl is not None:
            pending_order.sl = float(sl)
        if tp is not None:
            pending_order.tp = float(tp)
        if stoplimit is not None:
            pending_order.price_stoplimit = float(stoplimit)
        if expiration is not None:
            pending_order.time_expiration = int(expiration)
        if type_time is not None:
            pending_order.type_time = int(type_time)

        result.retcode = 10009
        result.order = order_ticket
        result.price = float(getattr(pending_order, "price_open", 0.0))
        result.comment = "Request executed"
        if verbose:
            print(
                f"[order_send] Modified pending order={order_ticket} "
                f"symbol={getattr(pending_order, 'symbol', '')} "
                f"price={float(getattr(pending_order, 'price_open', 0.0) or 0.0)}"
            )
        return result

    if is_remove:
        order_ticket = int(req_get("order", 0) or 0)
        if order_ticket <= 0:
            result.retcode = 10013
            result.comment = "Order ticket is required"
            return result

        pending_order = next(
            (
                o
                for o in state.trading_orders
                if int(getattr(o, "ticket", 0)) == order_ticket
            ),
            None,
        )
        if pending_order is None:
            result.retcode = 10013
            result.comment = "Order not found"
            return result

        state.trading_orders = [
            o
            for o in state.trading_orders
            if int(getattr(o, "ticket", 0)) != order_ticket
        ]
        result.retcode = 10009
        result.order = order_ticket
        result.comment = "Request executed"
        if verbose:
            print(f"[order_send] Removed pending order={order_ticket}")
        return result

    symbol_name = req_get("symbol", "")
    sym_info = symbol_info(state, symbol_name)
    if not sym_info:
        result.retcode = 10013
        result.comment = "Unknown symbol"
        return result

    if float(result.volume) <= 0.0:
        result.retcode = 10014
        result.comment = "Volume must be > 0"
        return result

    bid = float(getattr(sym_info, "bid", 0.0) or 0.0)
    ask = float(getattr(sym_info, "ask", 0.0) or 0.0)
    last = float(getattr(sym_info, "last", 0.0) or 0.0)
    result.bid = bid
    result.ask = ask

    order_type = int(req_get("type", 0) or 0)
    is_buy = order_type == 0
    is_sell = order_type == 1

    def next_ticket(item_list) -> int:
        if not item_list:
            return 0
        return max((int(getattr(x, "ticket", 0)) for x in item_list), default=0)

    def next_ticket_from_lists(*item_lists) -> int:
        return max((next_ticket(item_list) for item_list in item_lists), default=0) + 1

    contract_size = float(
        getattr(sym_info, "trade_contract_size", 100000.0) or 100000.0
    )

    if is_pending:
        if order_type not in (2, 3, 4, 5):
            result.retcode = 10013
            result.comment = (
                "Only BUY_LIMIT/SELL_LIMIT/BUY_STOP/SELL_STOP are supported"
            )
            return result

        pending_price = float(req_get("price", 0.0) or 0.0)
        if pending_price <= 0.0:
            pending_price = float(req_get("stoplimit", 0.0) or 0.0)
        if pending_price <= 0.0:
            result.retcode = 10015
            result.comment = "Pending price is invalid"
            return result

        now = _state_now_epoch(state)
        order_ticket = next_ticket_from_lists(
            state.trading_orders, state.trading_history_orders
        )

        order_row = OrderInfo(
            action="order_open",
            ticket=order_ticket,
            time_setup=now,
            time_setup_msc=now * 1000,
            time_done=0,
            time_done_msc=0,
            time_expiration=req_get("expiration", 0),
            type=order_type,
            type_time=req_get("type_time", 0),
            type_filling=req_get("type_filling", 0),
            state=1,
            magic=req_get("magic", 0),
            reason=0,
            position_id=0,
            position_by_id=0,
            volume_initial=float(result.volume),
            volume_current=float(result.volume),
            price_open=pending_price,
            sl=req_get("sl", 0.0),
            tp=req_get("tp", 0.0),
            price_current=pending_price,
            price_stoplimit=req_get("stoplimit", 0.0),
            symbol=symbol_name,
            comment=req_get("comment", ""),
            external_id=req_get("external_id", ""),
            setup_id=req_get("setup_id", ""),
            group_id=req_get("group_id", ""),
            strategy_id=req_get("strategy_id", ""),
            margin_required=0.0,
        )
        state.trading_orders.append(order_row)

        result.retcode = 10008
        result.order = order_ticket
        result.price = pending_price
        result.comment = "Order placed"
        if verbose:
            print(
                f"[order_send] Placed pending order={order_ticket} "
                f"symbol={symbol_name} type={order_type} volume={_format_volume_for_symbol(sym_info, result.volume)} "
                f"price={float(pending_price):.5f}"
            )
        return result

    close_position_ticket = int(req_get("position", 0) or 0)
    if close_position_ticket > 0:
        open_positions = [
            p
            for p in state.trading_deals
            if int(getattr(p, "ticket", 0)) == close_position_ticket
            or int(getattr(p, "position_id", 0)) == close_position_ticket
            or int(getattr(p, "identifier", 0)) == close_position_ticket
        ]
        if not open_positions:
            result.retcode = 10013
            result.comment = "Position not found"
            return result

        position = open_positions[0]
        close_volume = float(req_get("volume", 0.0) or 0.0)
        current_volume = float(getattr(position, "volume", 0.0) or 0.0)
        if close_volume <= 0.0 or close_volume > current_volume:
            result.retcode = 10014
            result.comment = "Volume must be > 0 and <= position volume"
            return result

        requested_exit_price = float(req_get("price", 0.0) or 0.0)
        market_exit_price = requested_exit_price
        if market_exit_price <= 0.0:
            market_exit_price = ask if is_buy else bid
        if market_exit_price <= 0.0:
            market_exit_price = last
        if market_exit_price <= 0.0:
            result.retcode = 10015
            result.comment = "Price is invalid and no market quote is available"
            return result
        exec_price, _, _ = _apply_market_slippage(
            state,
            sym_info,
            symbol_name,
            order_type,
            requested_exit_price,
            market_exit_price,
            close_volume,
        )

        now = _state_now_epoch(state)
        order_ticket = next_ticket_from_lists(
            state.trading_orders, state.trading_history_orders
        )
        deal_ticket = next_ticket_from_lists(
            state.trading_deals, state.trading_history_deals
        )
        close_commission = _commission_for_volume(state, close_volume)

        history_order = HistoryOrderInfo(
            ticket=order_ticket,
            time_setup=now,
            time_setup_msc=now * 1000,
            time_done=now,
            time_done_msc=now * 1000,
            time_expiration=req_get("expiration", 0),
            type=order_type,
            type_time=req_get("type_time", 0),
            type_filling=req_get("type_filling", 0),
            state=4,
            magic=req_get("magic", 0),
            reason=0,
            position_id=int(
                getattr(position, "position_id", getattr(position, "ticket", 0))
            ),
            position_by_id=req_get("position_by", 0),
            volume_initial=close_volume,
            volume_current=0.0,
            price_open=exec_price,
            sl=req_get("sl", getattr(position, "sl", 0.0)),
            tp=req_get("tp", getattr(position, "tp", 0.0)),
            price_current=exec_price,
            price_stoplimit=req_get("stoplimit", 0.0),
            symbol=symbol_name,
            comment=req_get("comment", ""),
            external_id="",
            margin_required=0.0,
        )
        state.trading_history_orders.append(history_order)

        entry_price = float(
            getattr(position, "price_open", getattr(position, "price", exec_price))
            or exec_price
        )
        raw_position_type = getattr(position, "type", order_type)
        if raw_position_type is None:
            raw_position_type = order_type
        position_type = int(raw_position_type)
        if profit_calculator is not None:
            calc_value = profit_calculator(
                position_type, symbol_name, close_volume, entry_price, exec_price
            )
            if calc_value is None:
                raise RuntimeError(
                    "order_calc_profit returned None while strict profit calculation is required."
                )
            realized_profit = float(calc_value)
        elif strict_calc_access:
            raise RuntimeError(
                "order_calc_profit access is required but no profit_calculator was provided."
            )
        else:
            is_position_buy = position_type == 0
            delta = (
                (exec_price - entry_price)
                if is_position_buy
                else (entry_price - exec_price)
            )
            realized_profit = float(delta * close_volume * contract_size)

        close_deal = DealInfo(
            ticket=deal_ticket,
            order=order_ticket,
            time=now,
            time_msc=now * 1000,
            time_update=now,
            time_update_msc=now * 1000,
            type=order_type,
            entry=1,
            magic=req_get("magic", 0),
            reason=0,
            position_id=int(
                getattr(position, "position_id", getattr(position, "ticket", 0))
            ),
            volume=close_volume,
            price=exec_price,
            price_open=entry_price,
            price_current=exec_price,
            sl=float(getattr(position, "sl", 0.0)),
            tp=float(getattr(position, "tp", 0.0)),
            margin_required=0.0,
            commission=close_commission,
            swap=0.0,
            profit=realized_profit,
            fee=0.0,
            symbol=symbol_name,
            comment=req_get("comment", ""),
            external_id="",
        )
        state.trading_history_deals.append(close_deal)

        _finalize_trade_tracking(
            state,
            position,
            close_volume,
            exec_price,
            realized_profit,
            float(
                requested_exit_price
                if requested_exit_price > 0.0
                else market_exit_price
            ),
            str(req_get("comment", "") or "manual_exit"),
        )

        position.commission = float(
            getattr(position, "commission", 0.0) or 0.0
        ) + float(close_commission)
        balance = float(getattr(state.trading_account, "balance", 0.0) or 0.0)
        state.trading_account.balance = (
            balance + realized_profit + float(close_commission)
        )

        remaining = current_volume - close_volume
        if remaining <= 0.0:
            state.trading_deals = [p for p in state.trading_deals if p is not position]
        else:
            position.volume = remaining
            current_margin = float(getattr(position, "margin_required", 0.0) or 0.0)
            if current_volume > 0.0 and current_margin > 0.0:
                position.margin_required = current_margin * (remaining / current_volume)
            position.time_update = now
            position.time_update_msc = now * 1000

        result.retcode = 10009
        result.deal = deal_ticket
        result.order = order_ticket
        result.price = exec_price
        result.comment = "Request executed"
        if verbose:
            print(
                f"[order_send] Closed position={close_position_ticket} "
                f"symbol={symbol_name} volume={_format_volume_for_symbol(sym_info, close_volume)} "
                f"price={float(exec_price):.5f} profit={float(realized_profit):.2f}"
            )
        return result

    if not is_buy and not is_sell:
        result.retcode = 10013
        result.comment = "Only BUY/SELL are supported in tester order_send()"
        return result

    requested_entry_price = float(req_get("price", 0.0) or 0.0)
    market_entry_price = requested_entry_price
    if market_entry_price <= 0.0:
        market_entry_price = ask if is_buy else bid
    if market_entry_price <= 0.0:
        market_entry_price = last
    if market_entry_price <= 0.0:
        result.retcode = 10015
        result.comment = "Price is invalid and no market quote is available"
        return result
    exec_price, fill_price_deviation, slippage_usd = _apply_market_slippage(
        state,
        sym_info,
        symbol_name,
        order_type,
        requested_entry_price,
        market_entry_price,
        float(result.volume),
    )

    now = _state_now_epoch(state)
    order_ticket = next_ticket_from_lists(
        state.trading_orders, state.trading_history_orders
    )
    deal_ticket = next_ticket_from_lists(
        state.trading_deals, state.trading_history_deals
    )
    position_ticket = deal_ticket
    open_commission = _commission_for_volume(state, float(result.volume))

    if margin_calculator is not None:
        calc_value = margin_calculator(
            order_type, symbol_name, float(result.volume), float(exec_price)
        )
        if calc_value is None:
            raise RuntimeError(
                "order_calc_margin returned None while strict margin calculation is required."
            )
        margin_required = float(calc_value)
    elif strict_calc_access:
        raise RuntimeError(
            "order_calc_margin access is required but no margin_calculator was provided."
        )
    else:
        account_leverage = float(getattr(state.trading_account, "leverage", 0.0) or 0.0)
        if account_leverage <= 0.0:
            account_leverage = 100.0
        notional = float(result.volume) * contract_size * float(exec_price)
        margin_required = (
            float(notional / account_leverage) if account_leverage > 0.0 else 0.0
        )

    order_row = HistoryOrderInfo(
        ticket=order_ticket,
        time_setup=now,
        time_setup_msc=now * 1000,
        time_done=now,
        time_done_msc=now * 1000,
        time_expiration=req_get("expiration", 0),
        type=order_type,
        type_time=req_get("type_time", 0),
        type_filling=req_get("type_filling", 0),
        state=4,
        magic=req_get("magic", 0),
        reason=0,
        position_id=position_ticket,
        position_by_id=req_get("position_by", 0),
        volume_initial=result.volume,
        volume_current=0.0,
        price_open=exec_price,
        sl=req_get("sl", 0.0),
        tp=req_get("tp", 0.0),
        price_current=exec_price,
        price_stoplimit=req_get("stoplimit", 0.0),
        symbol=symbol_name,
        comment=req_get("comment", ""),
        external_id="",
        margin_required=margin_required,
    )
    state.trading_history_orders.append(order_row)

    deal_row = DealInfo(
        ticket=deal_ticket,
        order=order_ticket,
        time=now,
        time_msc=now * 1000,
        time_update=now,
        time_update_msc=now * 1000,
        type=order_type,
        entry=0,
        magic=req_get("magic", 0),
        reason=0,
        position_id=position_ticket,
        volume=result.volume,
        price=exec_price,
        price_open=exec_price,
        price_current=exec_price,
        sl=req_get("sl", 0.0),
        tp=req_get("tp", 0.0),
        margin_required=margin_required,
        commission=open_commission,
        swap=0.0,
        profit=0.0,
        fee=0.0,
        symbol=symbol_name,
        comment=req_get("comment", ""),
        external_id=req_get("external_id", ""),
        setup_id=req_get("setup_id", ""),
        group_id=req_get("group_id", ""),
        strategy_id=req_get("strategy_id", ""),
    )
    state.trading_deals.append(deal_row)

    if requested_entry_price <= 0.0:
        requested_entry_price = float(market_entry_price)
    _open_trade_tracking(
        state,
        request,
        position_ticket,
        order_type,
        symbol_name,
        float(result.volume),
        float(exec_price),
        requested_entry_price,
        float(req_get("sl", 0.0) or 0.0),
        float(req_get("tp", 0.0) or 0.0),
        float(margin_required),
        profit_calculator=profit_calculator,
    )
    record = state.open_trade_records_by_ticket.get(int(position_ticket))
    if record is not None:
        record.fill_price_deviation = float(fill_price_deviation)
        record.slippage_usd = float(slippage_usd)

    balance = float(getattr(state.trading_account, "balance", 0.0) or 0.0)
    state.trading_account.balance = balance + float(open_commission)

    result.retcode = 10009
    result.deal = deal_ticket
    result.order = order_ticket
    result.price = exec_price
    result.comment = "Request executed"
    if verbose:
        side_name = "BUY" if is_buy else "SELL"
        print(
            f"[order_send] Opened {side_name} position={position_ticket} "
            f"symbol={symbol_name} volume={_format_volume_for_symbol(sym_info, result.volume)} "
            f"price={float(exec_price):.5f} margin={float(margin_required):.2f}"
        )
    return result
