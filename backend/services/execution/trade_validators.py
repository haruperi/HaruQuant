"""
FILE: src/util/validators.py

PURPOSE:
Python port of `src/util/validators.cpp` used by runtime/bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this module.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Rule-level validators for symbol/volume/price/slippage/SLTP/expiration/account checks.
- Trade-level consolidated validators for open/modify/close position and pending-order flows.

DESIGN NOTES:
- Deterministic behavior (backtest + unit-test friendly).
- Prefer explicit validation and retcode-based failure signaling.
- Low coupling through typed-ish interfaces (Protocol/dataclasses).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Optional, Any
import math
import time

from backend.common.logger import logger

# =============================================================================
# Minimal shared types (adjust to match your actual domain models)
# =============================================================================

class ENUM_ORDER_TYPE(IntEnum):
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TYPE_BUY_STOP_LIMIT = 6
    ORDER_TYPE_SELL_STOP_LIMIT = 7


class ENUM_TRADE_REQUEST_ACTIONS(IntEnum):
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_SLTP = 6
    TRADE_ACTION_MODIFY = 7
    TRADE_ACTION_REMOVE = 8


@dataclass
class RuleValidationResult:
    ok: bool
    message: str = "OK"


@dataclass
class TradeValidationResult:
    ok: bool = True
    retcode: int = 10009
    comment: str = "OK"

    # optional computed fields (used by validate_trade_request)
    margin: float = 0.0
    margin_free: float = 0.0
    margin_level: float = 0.0
    required_margin: float = 0.0


@dataclass
class SymbolTickData:
    bid: float
    ask: float


@dataclass
class ValidationRules:
    # global/rule limits (tune to your defaults)
    volume_min: float = 0.0
    volume_max: float = 1e9
    volume_step: float = 0.0

    price_min: float = 0.0
    price_max: float = 1e12

    deviation_min: int = 0
    deviation_max: int = 10_000

    magic_min: int = 0
    magic_max: int = 2_147_483_647


@dataclass
class ValidationContext:
    # symbol checks
    symbol_exists: bool = True
    symbol_visible: bool = True
    symbol_select_ok: bool = True

    # dependencies
    account: Optional[Any] = None
    symbol_info: Optional[Any] = None
    symbol_tick: Optional[SymbolTickData] = None


# These payload dataclasses represent canonical trade request shapes.
# Replace/extend them to match your real API objects.
@dataclass
class TradeRequestPayload:
    symbol: str
    volume: float
    type: int  # order type (int)
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    magic: Optional[int] = None
    slippage: Optional[int] = None
    deviation: Optional[int] = None


@dataclass
class CredentialsPayload:
    login: int
    password: str
    server: str


# BacktestState-like structure: dict[str, dict[str, str]]
@dataclass
class BacktestState:
    Dictionary = Dict[str, str]
    trading_symbols: Dict[str, Dictionary] = field(default_factory=dict)
    trading_orders: Dict[str, Dictionary] = field(default_factory=dict)
    trading_deals: Dict[str, Dictionary] = field(default_factory=dict)


# =============================================================================
# Helpers (ported from anonymous namespace)
# =============================================================================

def _ok(message: str = "OK") -> RuleValidationResult:
    return RuleValidationResult(True, message)


def _fail(message: str) -> RuleValidationResult:
    return RuleValidationResult(False, message)


def _fail_trade(retcode: int, comment: str) -> TradeValidationResult:
    return TradeValidationResult(ok=False, retcode=retcode, comment=comment)


def _to_upper(value: str) -> str:
    return value.upper()


def _is_market_order_type(order_type: int) -> bool:
    return order_type in (
        int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL),
    )


def _is_pending_order_type(order_type: int) -> bool:
    return order_type in (
        int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT),
    )


def _is_buy_action(order_type: int) -> bool:
    return order_type in (
        int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT),
    )


def _is_sell_action(order_type: int) -> bool:
    return order_type in (
        int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP),
        int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT),
    )


def _trim_copy(s: str) -> str:
    return s.strip()


def _step_decimals(step: float) -> int:
    if not (step > 0.0) or not math.isfinite(step):
        return 0
    max_digits = 8
    scaled = step
    for digits in range(max_digits + 1):
        rounded = round(scaled)
        if abs(scaled - rounded) < 1e-8:
            return digits
        scaled *= 10.0
    return max_digits


def _is_plain_decimal_number(s: str) -> bool:
    # Accept plain decimal forms only; reject scientific notation.
    if not s:
        return False
    i = 0
    if s[0] in "+-":
        i = 1
    seen_digit = False
    seen_dot = False
    for c in s[i:]:
        if c.isdigit():
            seen_digit = True
            continue
        if c == "." and not seen_dot:
            seen_dot = True
            continue
        return False
    return seen_digit


def _now_unix_sec() -> int:
    return int(time.time())


def _parse_order_type_token(order_type: str) -> Optional[int]:
    token = _to_upper(order_type)
    mapping = {
        "BUY": int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY),
        "SELL": int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL),
        "BUY_LIMIT": int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT),
        "SELL_LIMIT": int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT),
        "BUY_STOP": int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP),
        "SELL_STOP": int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP),
        "BUY_STOP_LIMIT": int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT),
        "SELL_STOP_LIMIT": int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT),
    }
    return mapping.get(token)


def _parse_float_or(value: str, fallback: float = 0.0) -> float:
    if not value:
        return fallback
    try:
        return float(value)
    except Exception:
        return fallback


def _parse_int_or(value: str, fallback: int = 0) -> int:
    if not value:
        return fallback
    try:
        return int(value)
    except Exception:
        return fallback


def _calculate_margin(account: Any, symbol_info: Any, volume: float, price: float) -> float:
    leverage = float(max(1, int(account.Leverage())))
    notional = volume * float(symbol_info.TradeContractSize()) * price
    return notional / leverage


def _validate_price_relationship(
    level_price: float,
    entry_price: float,
    order_type: int,
    is_stop_loss: bool,
) -> RuleValidationResult:
    if _is_buy_action(order_type):
        if is_stop_loss and level_price >= entry_price:
            return _fail("Stop loss for BUY must be below entry price")
        if (not is_stop_loss) and level_price <= entry_price:
            return _fail("Take profit for BUY must be above entry price")
        return _ok()

    if _is_sell_action(order_type):
        if is_stop_loss and level_price <= entry_price:
            return _fail("Stop loss for SELL must be above entry price")
        if (not is_stop_loss) and level_price >= entry_price:
            return _fail("Take profit for SELL must be below entry price")
        return _ok()

    return _ok()


def _validate_stop_freeze_distance(
    level_price: float,
    entry_price: float,
    order_type: int,
    is_stop_loss: bool,
    symbol_info: Any,
    level_name: str,
) -> RuleValidationResult:
    point = float(symbol_info.Point())
    if not (point > 0.0) or not math.isfinite(point):
        return _fail("Invalid symbol point value")

    stops_level = int(symbol_info.TradeStopsLevel())
    freeze_level = int(symbol_info.TradeFreezeLevel())
    required_level = max(stops_level, freeze_level)
    if required_level <= 0:
        return _ok()

    required_distance = float(required_level) * point

    def distance_fail(side_text: str) -> RuleValidationResult:
        return _fail(
            f"{level_name} for {side_text} must be at least {required_level} points from entry"
        )

    if _is_buy_action(order_type):
        if is_stop_loss:
            if level_price > (entry_price - required_distance):
                return distance_fail("BUY")
            return _ok()
        if level_price < (entry_price + required_distance):
            return distance_fail("BUY")
        return _ok()

    if _is_sell_action(order_type):
        if is_stop_loss:
            if level_price < (entry_price + required_distance):
                return distance_fail("SELL")
            return _ok()
        if level_price > (entry_price - required_distance):
            return distance_fail("SELL")
        return _ok()

    return _fail("Unknown order type")


def _find_symbol_row(state: Optional[BacktestState], symbol: str) -> Optional[BacktestState.Dictionary]:
    if state is None or not symbol:
        return None
    if symbol in state.trading_symbols:
        return state.trading_symbols[symbol]
    target = _to_upper(symbol)
    for k, v in state.trading_symbols.items():
        if _to_upper(k) == target:
            return v
    return None


def _count_open_pending_orders(state: Optional[BacktestState]) -> int:
    if state is None:
        return 0
    count = 0
    for row in state.trading_orders.values():
        if row.get("action") == "order_open":
            count += 1
    return count


def _symbol_open_volume(state: Optional[BacktestState], symbol: str) -> float:
    # NOTE: Iterates trading_deals and checks entry type to find open positions.
    if state is None or not symbol:
        return 0.0
    target = _to_upper(symbol)
    total = 0.0
    for key, row in state.trading_deals.items():
        entry = row.get("entry", "0")
        if entry != "0":
            continue
        row_symbol = row.get("symbol") or key
        if _to_upper(row_symbol) != target:
            continue
        total += abs(_parse_float_or(row.get("volume", ""), 0.0))
    return total


def _find_order_row(state: Optional[BacktestState], ticket: int) -> Optional[BacktestState.Dictionary]:
    if state is None or ticket <= 0:
        return None
    ticket_str = str(ticket)
    if ticket_str in state.trading_orders:
        return state.trading_orders[ticket_str]
    for row in state.trading_orders.values():
        if row.get("ticket") == ticket_str:
            return row
    return None


# =============================================================================
# Public API (ported functions)
# =============================================================================

def validate_action_type(action: int, order_type: int) -> TradeValidationResult:
    if action == 1:
        if not _is_market_order_type(order_type):
            return _fail_trade(10013, "Invalid order type for market execution")
        return TradeValidationResult()
    if action == 5:
        if not _is_pending_order_type(order_type):
            return _fail_trade(10013, "Invalid pending order type")
        return TradeValidationResult()
    if action in (6, 7, 8):
        return TradeValidationResult()
    return _fail_trade(10013, "Invalid request: missing or unsupported action")


def validate_submission_inputs(
    symbol: str,
    volume: float,
    symbol_info: Optional[Any],
    bid: float,
    ask: float,
) -> TradeValidationResult:
    if not symbol:
        return _fail_trade(10013, "Invalid request: missing symbol")
    if volume <= 0.0:
        return _fail_trade(10014, "Invalid volume")
    if symbol_info is None:
        return _fail_trade(10021, "No quotes to process the request")
    if bid <= 0.0 or ask <= 0.0:
        return _fail_trade(10021, "No quotes to process the request")
    return TradeValidationResult()


def validate_trade_request(request: Any, account: Any, symbol_info: Optional[Any]) -> TradeValidationResult:
    out = TradeValidationResult()
    out.margin = float(account.Margin())
    out.margin_free = float(account.MarginFree())
    out.margin_level = float(account.MarginLevel())

    if symbol_info is None:
        return _fail_trade(10013, "Unknown symbol")

    if float(request.volume) <= 0.0:
        return _fail_trade(10014, "Invalid volume")

    if float(request.volume) < float(symbol_info.VolumeMin()) or float(request.volume) > float(symbol_info.VolumeMax()):
        return _fail_trade(10014, "Volume out of range")

    if int(request.action) in (int(ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_DEAL), int(ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_PENDING)):
        price = float(getattr(request, "price", 0.0))
        if price <= 0.0:
            t = int(request.type)
            price = float(symbol_info.Ask()) if t == int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY) else float(symbol_info.Bid())

        out.required_margin = _calculate_margin(account, symbol_info, float(request.volume), price)
        out.margin = float(account.Margin()) + out.required_margin
        out.margin_free = float(account.Equity()) - out.margin
        out.margin_level = (float(account.Equity()) / out.margin * 100.0) if out.margin > 0.0 else 0.0

        if out.margin_free < 0.0:
            return _fail_trade(10019, "Insufficient margin")

    out.ok = True
    out.retcode = 10009
    out.comment = "Request valid"
    return out


def validate_symbol(symbol: str, ctx: ValidationContext) -> RuleValidationResult:
    if not symbol:
        return _fail("Symbol must be a non-empty string")
    if not ctx.symbol_exists:
        return _fail(f"Symbol '{symbol}' not found")
    if (not ctx.symbol_visible) and (not ctx.symbol_select_ok):
        return _fail(f"Symbol '{symbol}' cannot be selected")
    return _ok("Symbol is valid")


def validate_volume_basic(volume: float) -> RuleValidationResult:
    if not math.isfinite(volume):
        return _fail("Volume must be a number")
    if volume <= 0.0:
        return _fail("Volume must be positive")
    return _ok()


def validate_volume_symbol_limits(volume: float, symbol_info: Any) -> RuleValidationResult:
    if volume < float(symbol_info.VolumeMin()):
        return _fail(f"Volume {volume} below minimum {symbol_info.VolumeMin()}")
    if volume > float(symbol_info.VolumeMax()):
        return _fail(f"Volume {volume} above maximum {symbol_info.VolumeMax()}")
    return _ok()


def validate_volume_step(volume: float, symbol_info: Any) -> RuleValidationResult:
    step = float(symbol_info.VolumeStep())
    if step <= 0.0:
        return _ok()
    vol_min = float(symbol_info.VolumeMin())
    steps = round((volume - vol_min) / step)
    aligned = vol_min + (steps * step)
    if abs(volume - aligned) > 1e-8:
        return _fail(f"Volume {volume} not aligned with step {step}")
    return _ok()


def validate_volume_format(volume_text: str, ctx: ValidationContext, rules: ValidationRules) -> RuleValidationResult:
    text = _trim_copy(volume_text)
    if not _is_plain_decimal_number(text):
        return _fail("Volume must be a plain numeric string")

    dot = text.find(".")
    decimals = 0 if dot == -1 else (len(text) - dot - 1)

    step = float(ctx.symbol_info.VolumeStep()) if (ctx.symbol_info is not None and float(ctx.symbol_info.VolumeStep()) > 0.0) else float(rules.volume_step)
    allowed_decimals = _step_decimals(step)
    if decimals > allowed_decimals:
        return _fail(f"Volume format has {decimals} decimal places, max allowed is {allowed_decimals}")
    return _ok()


def validate_price_format(price_text: str, ctx: ValidationContext) -> RuleValidationResult:
    text = _trim_copy(price_text)
    if not _is_plain_decimal_number(text):
        return _fail("Price must be a plain numeric string")

    dot = text.find(".")
    decimals = 0 if dot == -1 else (len(text) - dot - 1)

    allowed_decimals = 8
    if ctx.symbol_info is not None:
        digits = int(getattr(ctx.symbol_info, "Digits")())
        if digits > 0:
            allowed_decimals = digits
        else:
            tick_size = float(ctx.symbol_info.TradeTickSize())
            point = float(ctx.symbol_info.Point())
            reference = tick_size if tick_size > 0.0 else point
            if reference > 0.0:
                allowed_decimals = _step_decimals(reference)

    if decimals > allowed_decimals:
        return _fail(f"Price format has {decimals} decimal places, max allowed is {allowed_decimals}")
    return _ok()


def validate_volume(volume: float, ctx: ValidationContext, rules: ValidationRules) -> RuleValidationResult:
    base = validate_volume_basic(volume)
    if not base.ok:
        return base

    rule_min = float(rules.volume_min)
    rule_max = float(rules.volume_max)
    rule_step = float(rules.volume_step)

    if volume < rule_min or volume > rule_max:
        return _fail(f"Volume {volume} outside valid range [{rule_min}, {rule_max}]")

    if rule_step > 0.0:
        steps = round((volume - rule_min) / rule_step)
        aligned = rule_min + (steps * rule_step)
        if abs(volume - aligned) > 1e-8:
            return _fail(f"Volume {volume} not aligned with step {rule_step}")

    if ctx.symbol_info is None:
        return _ok("Volume is valid")

    limits = validate_volume_symbol_limits(volume, ctx.symbol_info)
    if not limits.ok:
        return limits

    step_res = validate_volume_step(volume, ctx.symbol_info)
    if not step_res.ok:
        return step_res

    return _ok("Volume is valid")


def validate_price(price: float, ctx: ValidationContext, rules: ValidationRules) -> RuleValidationResult:
    if not math.isfinite(price):
        return _fail("Price must be a number")
    if price <= 0.0:
        return _fail("Price must be positive")
    if price < float(rules.price_min) or price > float(rules.price_max):
        return _fail(f"Price {price} outside valid range")

    if ctx.symbol_info is not None:
        tick_size = float(ctx.symbol_info.TradeTickSize())
        if tick_size > 0.0:
            ratio = price / tick_size
            nearest = round(ratio)
            if abs(ratio - nearest) > 1e-5:
                return _fail(f"Price {price} not aligned with tick size {tick_size}")

    return _ok("Price is valid")


def validate_order_type(order_type: Any) -> RuleValidationResult:
    if isinstance(order_type, str):
        if _parse_order_type_token(order_type) is None:
            return _fail(f"Invalid order type string: {order_type}")
        return _ok("Order type is valid")

    order_type_int = int(order_type)
    if _is_market_order_type(order_type_int) or _is_pending_order_type(order_type_int):
        return _ok("Order type is valid")
    return _fail(f"Invalid order type constant: {order_type_int}")


def validate_magic(magic: int, rules: ValidationRules) -> RuleValidationResult:
    if int(magic) < int(rules.magic_min) or int(magic) > int(rules.magic_max):
        return _fail(f"Magic number {magic} outside valid range")
    return _ok("Magic number is valid")


def validate_slippage(
    slippage_points: int,
    requested_price: float,
    order_type: int,
    ctx: ValidationContext,
    rules: ValidationRules,
) -> RuleValidationResult:
    if slippage_points < int(rules.deviation_min) or slippage_points > int(rules.deviation_max):
        return _fail(f"Slippage {slippage_points} outside valid range")
    if not math.isfinite(requested_price) or requested_price <= 0.0:
        return _fail("Requested price must be a positive number")
    if ctx.symbol_info is None or ctx.symbol_tick is None:
        return _fail("Symbol info or tick data not available")

    point = float(ctx.symbol_info.Point())
    if not (point > 0.0) or not math.isfinite(point):
        return _fail("Invalid symbol point value")

    if not (_is_buy_action(order_type) or _is_sell_action(order_type)):
        return _fail("Invalid order type for slippage validation")

    actual_price = float(ctx.symbol_tick.ask) if _is_buy_action(order_type) else float(ctx.symbol_tick.bid)
    if not (actual_price > 0.0) or not math.isfinite(actual_price):
        return _fail("Invalid market price from recent tick")

    allowable = float(slippage_points) * point
    diff = abs(requested_price - actual_price)
    if diff > allowable + 1e-12:
        return _fail(
            f"Requested price outside slippage range (requested={requested_price}, actual={actual_price}, max_diff={allowable})"
        )
    return _ok("Slippage is valid")


def validate_expiration_unix(expiration_unix_sec: int, now_unix_sec: int) -> RuleValidationResult:
    if expiration_unix_sec <= now_unix_sec:
        return _fail("Expiration must be in the future")
    max_future = now_unix_sec + (365 * 24 * 60 * 60)
    if expiration_unix_sec > max_future:
        return _fail("Expiration too far in the future (max 1 year)")
    return _ok("Expiration is valid")


def validate_expiration_mode(expiration_mode: str) -> RuleValidationResult:
    mode = _to_upper(expiration_mode)
    if mode in ("GTC", "DAILY", "DAILY_EXCLUDING_STOPS"):
        return _ok("Expiration mode is valid")
    return _fail(f"Invalid expiration mode: {expiration_mode}")


def validate_timeframe(timeframe: Any) -> RuleValidationResult:
    if isinstance(timeframe, str):
        valid = {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"}
        tf = _to_upper(timeframe)
        if tf in valid:
            return _ok("Timeframe is valid")
        return _fail(f"Invalid timeframe string: {timeframe}")

    # MT5 constants commonly used.
    valid_int = {1, 5, 15, 30, 16385, 16388, 16408, 32769, 49153}
    tfi = int(timeframe)
    if tfi in valid_int:
        return _ok("Timeframe is valid")
    return _fail(f"Invalid timeframe constant: {tfi}")


def validate_date_range_unix(start_unix_sec: int, end_unix_sec: Optional[int], now_unix_sec: int) -> RuleValidationResult:
    min_past = now_unix_sec - (3650 * 24 * 60 * 60)
    if start_unix_sec < min_past:
        return _fail("Start date too far in the past (max 10 years)")
    if end_unix_sec is not None:
        if end_unix_sec <= start_unix_sec:
            return _fail("End date must be after start date")
        if end_unix_sec > now_unix_sec:
            return _fail("End date cannot be in the future")
    return _ok("Date range is valid")


def validate_stop_loss(
    stop_loss: float,
    entry_price: Optional[float],
    order_type: Optional[int],
    ctx: ValidationContext,
    rules: ValidationRules,
) -> RuleValidationResult:
    if not (stop_loss > 0.0):
        return _fail("Stop loss must be greater than 0")
    price_ok = validate_price(stop_loss, ctx, rules)
    if not price_ok.ok:
        return _fail(f"Invalid stop loss price: {price_ok.message}")
    if entry_price is not None and order_type is not None:
        rel = _validate_price_relationship(stop_loss, entry_price, int(order_type), True)
        if not rel.ok:
            return rel
    if entry_price is not None and ctx.symbol_info is not None:
        dist = _validate_stop_freeze_distance(
            stop_loss, entry_price, int(order_type or 0), True, ctx.symbol_info, "Stop loss"
        )
        if not dist.ok:
            return dist
    return _ok("Stop loss is valid")


def validate_take_profit(
    take_profit: float,
    entry_price: Optional[float],
    order_type: Optional[int],
    ctx: ValidationContext,
    rules: ValidationRules,
) -> RuleValidationResult:
    if not (take_profit > 0.0):
        return _fail("Take profit must be greater than 0")
    price_ok = validate_price(take_profit, ctx, rules)
    if not price_ok.ok:
        return _fail(f"Invalid take profit price: {price_ok.message}")
    if entry_price is not None and order_type is not None:
        rel = _validate_price_relationship(take_profit, entry_price, int(order_type), False)
        if not rel.ok:
            return rel
    if entry_price is not None and ctx.symbol_info is not None:
        dist = _validate_stop_freeze_distance(
            take_profit, entry_price, int(order_type or 0), False, ctx.symbol_info, "Take profit"
        )
        if not dist.ok:
            return dist
    return _ok("Take profit is valid")


def validate_trade_request_payload(request: TradeRequestPayload, ctx: ValidationContext, rules: ValidationRules) -> RuleValidationResult:
    if not request.symbol:
        return _fail("Missing required field: symbol")

    symbol_ok = validate_symbol(request.symbol, ctx)
    if not symbol_ok.ok:
        return _fail(f"Invalid symbol: {symbol_ok.message}")

    volume_ok = validate_volume(float(request.volume), ctx, rules)
    if not volume_ok.ok:
        return _fail(f"Invalid volume: {volume_ok.message}")

    type_ok = validate_order_type(int(request.type))
    if not type_ok.ok:
        return _fail(f"Invalid order type: {type_ok.message}")

    if request.price is not None:
        price_ok = validate_price(float(request.price), ctx, rules)
        if not price_ok.ok:
            return _fail(f"Invalid price: {price_ok.message}")

    if request.sl is not None and float(request.sl) > 0.0:
        sl_ok = validate_stop_loss(float(request.sl), request.price, int(request.type), ctx, rules)
        if not sl_ok.ok:
            return _fail(f"Invalid stop loss: {sl_ok.message}")

    if request.tp is not None and float(request.tp) > 0.0:
        tp_ok = validate_take_profit(float(request.tp), request.price, int(request.type), ctx, rules)
        if not tp_ok.ok:
            return _fail(f"Invalid take profit: {tp_ok.message}")

    if request.magic is not None:
        mg = validate_magic(int(request.magic), rules)
        if not mg.ok:
            return _fail(f"Invalid magic: {mg.message}")

    slippage = request.slippage if request.slippage is not None else request.deviation
    if slippage is not None:
        requested_price = float(request.price or 0.0)
        if not (requested_price > 0.0) and ctx.symbol_tick is not None:
            requested_price = float(ctx.symbol_tick.ask) if _is_buy_action(int(request.type)) else float(ctx.symbol_tick.bid)
        slip = validate_slippage(int(slippage), requested_price, int(request.type), ctx, rules)
        if not slip.ok:
            return _fail(f"Invalid slippage: {slip.message}")

    return _ok("Trade request is valid")


def validate_credentials(credentials: CredentialsPayload) -> RuleValidationResult:
    if int(credentials.login) <= 0:
        return _fail("Login must be a positive integer")
    if not credentials.password:
        return _fail("Password must be a non-empty string")
    if not credentials.server:
        return _fail("Server must be a non-empty string")
    return _ok("Credentials are valid")


def validate_margin(margin_required: float, ctx: ValidationContext) -> RuleValidationResult:
    if not math.isfinite(margin_required):
        return _fail("Margin must be a number")
    if margin_required < 0.0:
        return _fail("Margin cannot be negative")
    if ctx.account is None:
        return _fail("Cannot get account information")
    free_margin = float(ctx.account.MarginFree())
    if margin_required > free_margin:
        return _fail(f"Insufficient margin (required: {margin_required}, available: {free_margin})")
    return _ok("Sufficient margin available")


def validate_ticket(ticket: int) -> RuleValidationResult:
    if int(ticket) <= 0:
        return _fail("Ticket must be positive")
    return _ok("Ticket is valid")


def validate_max_orders(open_orders: int, account_limit: Optional[int], ctx: ValidationContext) -> RuleValidationResult:
    if int(open_orders) < 0:
        return _fail("open_orders must be a non-negative integer")
    limit = int(account_limit or 0)
    if account_limit is None and ctx.account is not None:
        limit = int(ctx.account.LimitOrders())
    if limit > 0 and open_orders >= limit:
        return _fail(f"Pending Orders limit of {limit} is reached")
    return _ok("Order limit not reached")


def validate_symbol_volume(symbol_volume: float, volume_limit: Optional[float], ctx: ValidationContext) -> RuleValidationResult:
    if not math.isfinite(symbol_volume) or symbol_volume < 0.0:
        return _fail("symbol_volume must be a non-negative number")
    limit = float(volume_limit or 0.0)
    if volume_limit is None:
        if ctx.symbol_info is None:
            return _fail("volume_limit or symbol is required")
        limit = float(ctx.symbol_info.VolumeLimit())
    if limit > 0.0 and symbol_volume >= limit:
        return _fail(f"Symbol Volume limit of {limit} is reached")
    return _ok("Symbol volume within limit")


def open_position_validations(request: Any, account: Any, symbol_info: Optional[Any]) -> TradeValidationResult:
    ctx = ValidationContext(
        account=account,
        symbol_info=symbol_info,
        symbol_exists=(symbol_info is not None),
        symbol_visible=True,
        symbol_select_ok=True,
        symbol_tick=SymbolTickData(float(symbol_info.Bid()), float(symbol_info.Ask())) if symbol_info is not None else None,
    )
    rules = ValidationRules()
    state: Optional[BacktestState] = account.GetState()

    symbol_ok = validate_symbol(str(request.symbol), ctx)
    if not symbol_ok.ok:
        return _fail_trade(10013, symbol_ok.message)

    type_ok = validate_order_type(int(request.type))
    if not type_ok.ok:
        return _fail_trade(10013, type_ok.message)

    vol_ok = validate_volume(float(request.volume), ctx, rules)
    if not vol_ok.ok:
        return _fail_trade(10014, vol_ok.message)

    out = validate_action_type(int(request.action), int(request.type))
    if not out.ok:
        return out

    bid = float(symbol_info.Bid()) if symbol_info is not None else 0.0
    ask = float(symbol_info.Ask()) if symbol_info is not None else 0.0
    out = validate_submission_inputs(str(request.symbol), float(request.volume), symbol_info, bid, ask)
    if not out.ok:
        return out

    if float(getattr(request, "price", 0.0)) > 0.0:
        price_ok = validate_price(float(request.price), ctx, rules)
        if not price_ok.ok:
            return _fail_trade(10015, price_ok.message)

    if int(getattr(request, "deviation", 0)) > 0:
        requested_price = float(getattr(request, "price", 0.0))
        if not (requested_price > 0.0) and symbol_info is not None:
            requested_price = float(symbol_info.Ask()) if _is_buy_action(int(request.type)) else float(symbol_info.Bid())
        slip_ok = validate_slippage(int(request.deviation), requested_price, int(request.type), ctx, rules)
        if not slip_ok.ok:
            return _fail_trade(10015, slip_ok.message)

    if float(getattr(request, "sl", 0.0)) > 0.0:
        sl_ok = validate_stop_loss(
            float(request.sl),
            float(request.price) if float(getattr(request, "price", 0.0)) > 0.0 else None,
            int(request.type),
            ctx,
            rules,
        )
        if not sl_ok.ok:
            return _fail_trade(10016, sl_ok.message)

    if float(getattr(request, "tp", 0.0)) > 0.0:
        tp_ok = validate_take_profit(
            float(request.tp),
            float(request.price) if float(getattr(request, "price", 0.0)) > 0.0 else None,
            int(request.type),
            ctx,
            rules,
        )
        if not tp_ok.ok:
            return _fail_trade(10016, tp_ok.message)

    open_orders = _count_open_pending_orders(state)
    max_orders_ok = validate_max_orders(open_orders, int(account.LimitOrders()), ctx)
    if not max_orders_ok.ok:
        return _fail_trade(10033, max_orders_ok.message)

    sym_vol = _symbol_open_volume(state, str(request.symbol))
    sym_vol_ok = validate_symbol_volume(sym_vol, None, ctx)
    if not sym_vol_ok.ok:
        return _fail_trade(10034, sym_vol_ok.message)

    out = validate_trade_request(request, account, symbol_info)
    if not out.ok:
        return out

    margin_ok = validate_margin(out.required_margin, ctx)
    if not margin_ok.ok:
        return _fail_trade(10019, margin_ok.message)

    return out


def modify_position_validations(
    symbol: str, 
    ticket: int, 
    state: Optional[BacktestState], 
    sl: float = 0.0, 
    tp: float = 0.0, 
    symbol_info: Optional[Any] = None
) -> TradeValidationResult:
    has_ticket = int(ticket) > 0
    has_symbol = bool(symbol)
    if not has_ticket and not has_symbol:
        return _fail_trade(10013, "Provide symbol or ticket to modify position")

    if has_ticket:
        ticket_ok = validate_ticket(ticket)
        if not ticket_ok.ok:
            return _fail_trade(10013, ticket_ok.message)

    if state is None:
        return _fail_trade(10013, "Missing backtest state")

    found = False
    found_symbol = ""
    found_row = None

    # Helper: normalize a position object to a dict regardless of type
    def _pos_to_row(pos):
        if isinstance(pos, dict):
            return pos
        if hasattr(pos, "_asdict"):
            return pos._asdict()
        return {k: getattr(pos, k) for k in dir(pos) if not k.startswith("_")}

    # state.trading_deals is a list of objects in the simulator engine
    deals_iterable = state.trading_deals if isinstance(state.trading_deals, list) else list(state.trading_deals.values())

    for deal in deals_iterable:
        row = _pos_to_row(deal)
        entry = str(row.get("entry", "0"))
        if entry != "0":
            continue  # skip closed positions
        row_symbol = str(row.get("symbol", "") or "")
        row_ticket = str(row.get("ticket") or row.get("position_id") or row.get("identifier") or "")
        if has_symbol and not has_ticket:
            if row_symbol == symbol:
                found = True
                found_symbol = row_symbol
                found_row = row
                break
        else:
            if row_ticket == str(ticket):
                found = True
                found_symbol = row_symbol
                found_row = row
                break

    if not found:
        return _fail_trade(10036, "Position not found")
    if has_ticket and has_symbol and found_symbol and found_symbol != symbol:
        return _fail_trade(10013, "Ticket does not belong to the provided symbol")

    if symbol_info is not None and found_row is not None:
        ctx = ValidationContext(
            symbol_info=symbol_info,
            symbol_exists=True,
            symbol_visible=True,
            symbol_select_ok=True,
            symbol_tick=SymbolTickData(float(symbol_info.Bid()), float(symbol_info.Ask())),
        )
        rules = ValidationRules()
        
        entry_price = _parse_float_or(found_row.get("price_open", found_row.get("price", "")), 0.0)
        order_type_val = found_row.get("type", "")
        if isinstance(order_type_val, str) and not order_type_val.isdigit():
            order_type_int = 0 if order_type_val.lower() == "buy" else 1
        else:
            order_type_int = _parse_int_or(order_type_val, 0)
            
        current_price = float(symbol_info.Bid()) if order_type_int == 0 else float(symbol_info.Ask())
        reference_price = current_price if current_price > 0.0 else (entry_price if entry_price > 0.0 else None)
        
        if sl > 0.0:
            sl_ok = validate_stop_loss(float(sl), reference_price, order_type_int, ctx, rules)
            if not sl_ok.ok:
                return _fail_trade(10016, sl_ok.message)

        if tp > 0.0:
            tp_ok = validate_take_profit(float(tp), reference_price, order_type_int, ctx, rules)
            if not tp_ok.ok:
                return _fail_trade(10016, tp_ok.message)

    return TradeValidationResult()


def open_pending_order_validations(request: Any, account: Any, symbol_info: Optional[Any]) -> TradeValidationResult:
    ctx = ValidationContext(
        account=account,
        symbol_info=symbol_info,
        symbol_exists=(symbol_info is not None),
        symbol_visible=True,
        symbol_select_ok=True,
        symbol_tick=SymbolTickData(float(symbol_info.Bid()), float(symbol_info.Ask())) if symbol_info is not None else None,
    )
    rules = ValidationRules()
    state: Optional[BacktestState] = account.GetState()

    symbol_ok = validate_symbol(str(request.symbol), ctx)
    if not symbol_ok.ok:
        return _fail_trade(10013, symbol_ok.message)

    type_ok = validate_order_type(int(request.type))
    if not type_ok.ok:
        return _fail_trade(10013, type_ok.message)

    volume_ok = validate_volume(float(request.volume), ctx, rules)
    if not volume_ok.ok:
        return _fail_trade(10014, volume_ok.message)

    out = validate_action_type(int(ENUM_TRADE_REQUEST_ACTIONS.TRADE_ACTION_PENDING), int(request.type))
    if not out.ok:
        return out

    bid = float(symbol_info.Bid()) if symbol_info is not None else 0.0
    ask = float(symbol_info.Ask()) if symbol_info is not None else 0.0
    out = validate_submission_inputs(str(request.symbol), float(request.volume), symbol_info, bid, ask)
    if not out.ok:
        return out

    price_ok = validate_price(float(request.price), ctx, rules)
    if not price_ok.ok:
        return _fail_trade(10015, price_ok.message)

    if symbol_info is not None:
        bid_px = float(symbol_info.Bid())
        ask_px = float(symbol_info.Ask())
        t = int(request.type)
        px = float(request.price)

        if t == int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT) and px >= ask_px:
            return _fail_trade(10015, "BUY_LIMIT price must be below ask")
        if t == int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT) and px <= bid_px:
            return _fail_trade(10015, "SELL_LIMIT price must be above bid")
        if t == int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP) and px <= ask_px:
            return _fail_trade(10015, "BUY_STOP price must be above ask")
        if t == int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP) and px >= bid_px:
            return _fail_trade(10015, "SELL_STOP price must be below bid")
        if t == int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT) and px <= ask_px:
            return _fail_trade(10015, "BUY_STOP_LIMIT trigger must be above ask")
        if t == int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT) and px >= bid_px:
            return _fail_trade(10015, "SELL_STOP_LIMIT trigger must be below bid")

    if float(getattr(request, "sl", 0.0)) > 0.0:
        sl_ok = validate_stop_loss(float(request.sl), float(request.price), int(request.type), ctx, rules)
        if not sl_ok.ok:
            return _fail_trade(10016, sl_ok.message)

    if float(getattr(request, "tp", 0.0)) > 0.0:
        tp_ok = validate_take_profit(float(request.tp), float(request.price), int(request.type), ctx, rules)
        if not tp_ok.ok:
            return _fail_trade(10016, tp_ok.message)

    if int(getattr(request, "expiration", 0)) > 0:
        exp_ok = validate_expiration_unix(int(request.expiration), _now_unix_sec())
        if not exp_ok.ok:
            return _fail_trade(10022, exp_ok.message)

    open_orders = _count_open_pending_orders(state)
    max_orders_ok = validate_max_orders(open_orders, int(account.LimitOrders()), ctx)
    if not max_orders_ok.ok:
        return _fail_trade(10033, max_orders_ok.message)

    sym_vol = _symbol_open_volume(state, str(request.symbol))
    sym_vol_ok = validate_symbol_volume(sym_vol, None, ctx)
    if not sym_vol_ok.ok:
        return _fail_trade(10034, sym_vol_ok.message)

    out = validate_trade_request(request, account, symbol_info)
    if not out.ok:
        return out

    margin_ok = validate_margin(out.required_margin, ctx)
    if not margin_ok.ok:
        return _fail_trade(10019, margin_ok.message)

    return out


def modify_pending_order_validations(
    ticket: int,
    price: float,
    sl: float,
    tp: float,
    expiration: int,
    state: Optional[BacktestState],
    symbol_info: Optional[Any],
) -> TradeValidationResult:
    ticket_ok = validate_ticket(ticket)
    if not ticket_ok.ok:
        return _fail_trade(10013, ticket_ok.message)
    if state is None:
        return _fail_trade(10013, "Missing backtest state")

    order_row = _find_order_row(state, ticket)
    if order_row is None:
        return _fail_trade(10035, "Order not found")

    order_type = _parse_int_or(order_row.get("type", ""), int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT))
    type_ok = validate_order_type(order_type)
    if not type_ok.ok:
        return _fail_trade(10013, type_ok.message)

    entry_price = _parse_float_or(order_row.get("price", ""), 0.0)
    if not (entry_price > 0.0):
        entry_price = _parse_float_or(order_row.get("limit_price", ""), 0.0)
    if price > 0.0:
        entry_price = price

    if symbol_info is not None:
        ctx = ValidationContext(
            symbol_info=symbol_info,
            symbol_exists=True,
            symbol_visible=True,
            symbol_select_ok=True,
            symbol_tick=SymbolTickData(float(symbol_info.Bid()), float(symbol_info.Ask())),
        )
        rules = ValidationRules()

        if price > 0.0:
            px = validate_price(float(price), ctx, rules)
            if not px.ok:
                return _fail_trade(10015, px.message)

            bid_px = float(symbol_info.Bid())
            ask_px = float(symbol_info.Ask())

            if order_type == int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_LIMIT) and price >= ask_px:
                return _fail_trade(10015, "BUY_LIMIT price must be below ask")
            if order_type == int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_LIMIT) and price <= bid_px:
                return _fail_trade(10015, "SELL_LIMIT price must be above bid")
            if order_type == int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP) and price <= ask_px:
                return _fail_trade(10015, "BUY_STOP price must be above ask")
            if order_type == int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP) and price >= bid_px:
                return _fail_trade(10015, "SELL_STOP price must be below bid")
            if order_type == int(ENUM_ORDER_TYPE.ORDER_TYPE_BUY_STOP_LIMIT) and price <= ask_px:
                return _fail_trade(10015, "BUY_STOP_LIMIT trigger must be above ask")
            if order_type == int(ENUM_ORDER_TYPE.ORDER_TYPE_SELL_STOP_LIMIT) and price >= bid_px:
                return _fail_trade(10015, "SELL_STOP_LIMIT trigger must be below bid")

        entry_opt = entry_price if entry_price > 0.0 else None
        type_opt = int(order_type)

        if sl > 0.0:
            sl_ok = validate_stop_loss(float(sl), entry_opt, type_opt, ctx, rules)
            if not sl_ok.ok:
                return _fail_trade(10016, sl_ok.message)

        if tp > 0.0:
            tp_ok = validate_take_profit(float(tp), entry_opt, type_opt, ctx, rules)
            if not tp_ok.ok:
                return _fail_trade(10016, tp_ok.message)

    if int(expiration) > 0:
        exp_ok = validate_expiration_unix(int(expiration), _now_unix_sec())
        if not exp_ok.ok:
            return _fail_trade(10022, exp_ok.message)

    return TradeValidationResult()


def delete_pending_order_validations(ticket: int, state: Optional[BacktestState]) -> TradeValidationResult:
    ticket_ok = validate_ticket(ticket)
    if not ticket_ok.ok:
        return _fail_trade(10013, ticket_ok.message)
    if state is None:
        return _fail_trade(10013, "Missing backtest state")
    row = _find_order_row(state, ticket)
    if row is None:
        return _fail_trade(10035, "Order not found")
    return TradeValidationResult()


def close_position_validations(symbol: str, ticket: int, state: Optional[BacktestState]) -> TradeValidationResult:
    return modify_position_validations(symbol, ticket, state)


def close_partial_position_validations(symbol: str, ticket: int, volume: float, state: Optional[BacktestState]) -> TradeValidationResult:
    base = close_position_validations(symbol, ticket, state)
    if not base.ok:
        return base
    if not (volume > 0.0):
        return _fail_trade(10014, "Volume must be > 0 for partial close")
    if state is None:
        return _fail_trade(10013, "Missing backtest state")

    position_volume = 0.0
    has_volume = False
    ticket_str = str(ticket)

    # Find position volume from trading_deals where entry == "0"
    if symbol:
        for key, row in state.trading_deals.items():
            row_symbol = row.get("symbol") or key
            entry = row.get("entry", "0")
            if entry != "0" or row_symbol != symbol:
                continue
            if "volume" in row:
                position_volume = _parse_float_or(row.get("volume", ""), 0.0)
                has_volume = True
            break

    if not has_volume and ticket > 0:
        for _, row in state.trading_deals.items():
            entry = row.get("entry", "0")
            if row.get("ticket") != ticket_str or entry != "0":
                continue
            position_volume = _parse_float_or(row.get("volume", ""), 0.0)
            has_volume = True
            break

    if has_volume and (volume - position_volume) > 1e-12:
        return _fail_trade(10014, "Partial close volume exceeds position volume")

    resolved_symbol = symbol
    if not resolved_symbol and ticket > 0:
        for key, row in state.trading_deals.items():
            entry = row.get("entry", "0")
            if row.get("ticket") == ticket_str and entry == "0":
                resolved_symbol = row.get("symbol") or key
                break

    sym_row = _find_symbol_row(state, resolved_symbol)
    if sym_row is not None:
        min_vol = _parse_float_or(sym_row.get("volume_min", ""), 0.0)
        max_vol = _parse_float_or(sym_row.get("volume_max", ""), 0.0)
        step = _parse_float_or(sym_row.get("volume_step", ""), 0.0)

        if min_vol > 0.0 and volume < min_vol:
            return _fail_trade(10014, "Partial close volume below minimum")
        if max_vol > 0.0 and volume > max_vol:
            return _fail_trade(10014, "Partial close volume above maximum")
        if step > 0.0 and min_vol > 0.0:
            align_base = min_vol
            steps_n = round((volume - align_base) / step)
            aligned = align_base + (steps_n * step)
            if abs(volume - aligned) > 1e-8:
                return _fail_trade(10014, "Partial close volume not aligned with symbol step")

    return TradeValidationResult()