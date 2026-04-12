"""Usage examples for C++-backed TradeValidator (haruquant.TradeValidator).

Run:
    python backend/scripts/examples/utils/usage_validator.py
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from apps.mt5 import MT5Utils, get_mt5_api
from apps.utils.logger import logger
from apps.utils import trade_validators as tv


class _SymbolInfoAdapter:
    """Adapter to expose C++-style method names expected by trade_validators."""

    def __init__(self, raw: Any):
        self.raw = raw

    def _value(self, method_name: str, attr_name: str, default: float = 0.0) -> float:
        method = getattr(self.raw, method_name, None)
        if callable(method):
            return float(method())
        value = getattr(self.raw, attr_name, default)
        return float(value if value is not None else default)

    def VolumeMin(self) -> float:
        return self._value("VolumeMin", "volume_min", 0.0)

    def VolumeMax(self) -> float:
        return self._value("VolumeMax", "volume_max", 1e9)

    def VolumeStep(self) -> float:
        return self._value("VolumeStep", "volume_step", 0.0)

    def VolumeLimit(self) -> float:
        return self._value("VolumeLimit", "volume_limit", 0.0)

    def TradeTickSize(self) -> float:
        return self._value("TradeTickSize", "trade_tick_size", 0.0)

    def Point(self) -> float:
        return self._value("Point", "point", 0.0)

    def Digits(self) -> int:
        method = getattr(self.raw, "Digits", None)
        if callable(method):
            return int(method())
        return int(getattr(self.raw, "digits", 0) or 0)

    def TradeStopsLevel(self) -> int:
        return int(self._value("TradeStopsLevel", "trade_stops_level", 0.0))

    def TradeFreezeLevel(self) -> int:
        return int(self._value("TradeFreezeLevel", "trade_freeze_level", 0.0))

    def Bid(self) -> float:
        return self._value("Bid", "bid", 0.0)

    def Ask(self) -> float:
        return self._value("Ask", "ask", 0.0)

    def TradeContractSize(self) -> float:
        return self._value("TradeContractSize", "trade_contract_size", 100000.0)


class _AccountInfoAdapter:
    """Adapter to expose C++-style account methods expected by trade_validators."""

    def __init__(self, raw: Any):
        self.raw = raw

    def _value(self, method_name: str, attr_name: str, default: float = 0.0) -> float:
        method = getattr(self.raw, method_name, None)
        if callable(method):
            return float(method())
        value = getattr(self.raw, attr_name, default)
        return float(value if value is not None else default)

    def MarginFree(self) -> float:
        return self._value("MarginFree", "margin_free", 0.0)

    def Margin(self) -> float:
        return self._value("Margin", "margin", 0.0)

    def MarginLevel(self) -> float:
        return self._value("MarginLevel", "margin_level", 0.0)

    def Equity(self) -> float:
        return self._value("Equity", "equity", 0.0)

    def LimitOrders(self) -> int:
        return int(self._value("LimitOrders", "limit_orders", 0.0))

    def Leverage(self) -> int:
        return int(self._value("Leverage", "leverage", 1.0))

    def GetState(self) -> Any:
        method = getattr(self.raw, "GetState", None)
        if callable(method):
            return method()
        return None


class TradeValidator:
    """Small compatibility wrapper matching legacy example API."""

    def __init__(self) -> None:
        self.rules = tv.ValidationRules()

    @staticmethod
    def _to_unix(value: Any) -> int:
        if isinstance(value, datetime):
            return int(value.timestamp())
        return int(value)

    def _ctx(self, kwargs: Dict[str, Any]) -> tv.ValidationContext:
        raw_symbol = kwargs.get("symbol_info")
        raw_account = kwargs.get("account_info") or kwargs.get("account")
        raw_tick = kwargs.get("tick") or raw_symbol

        symbol_info = _SymbolInfoAdapter(raw_symbol) if raw_symbol is not None else None
        account = _AccountInfoAdapter(raw_account) if raw_account is not None else None

        symbol_tick = None
        if raw_tick is not None:
            bid = float(getattr(raw_tick, "bid", 0.0) or 0.0)
            ask = float(getattr(raw_tick, "ask", 0.0) or 0.0)
            if bid > 0.0 and ask > 0.0:
                symbol_tick = tv.SymbolTickData(bid=bid, ask=ask)

        return tv.ValidationContext(
            symbol_exists=bool(kwargs.get("symbol_exists", True)),
            symbol_visible=bool(kwargs.get("symbol_visible", True)),
            symbol_select_ok=bool(kwargs.get("symbol_select_ok", True)),
            account=account,
            symbol_info=symbol_info,
            symbol_tick=symbol_tick,
        )

    def validate(self, validation_type: str, value: Any, **kwargs: Any) -> Tuple[bool, str]:
        ctx = self._ctx(kwargs)
        vt = str(validation_type).lower()

        try:
            if vt == "symbol":
                result = tv.validate_symbol(str(value), ctx)
            elif vt == "volume":
                if isinstance(value, str):
                    format_ok = tv.validate_volume_format(value, ctx, self.rules)
                    if not format_ok.ok:
                        return False, format_ok.message
                result = tv.validate_volume(float(value), ctx, self.rules)
            elif vt == "price":
                if isinstance(value, str):
                    format_ok = tv.validate_price_format(value, ctx)
                    if not format_ok.ok:
                        return False, format_ok.message
                result = tv.validate_price(float(value), ctx, self.rules)
            elif vt == "stop_loss":
                entry = kwargs.get("entry_price")
                result = tv.validate_stop_loss(
                    float(value),
                    float(entry) if entry is not None else None,
                    int(kwargs.get("order_type", 0)),
                    ctx,
                    self.rules,
                )
            elif vt == "take_profit":
                entry = kwargs.get("entry_price")
                result = tv.validate_take_profit(
                    float(value),
                    float(entry) if entry is not None else None,
                    int(kwargs.get("order_type", 0)),
                    ctx,
                    self.rules,
                )
            elif vt == "order_type":
                result = tv.validate_order_type(value)
            elif vt == "magic":
                result = tv.validate_magic(int(value), self.rules)
            elif vt in ("slippage", "deviation"):
                result = tv.validate_slippage(
                    int(value),
                    float(kwargs.get("requested_price", 0.0)),
                    int(kwargs.get("order_type", 0)),
                    ctx,
                    self.rules,
                )
            elif vt == "expiration_mode":
                result = tv.validate_expiration_mode(str(value))
            elif vt == "expiration":
                now_unix = int(datetime.now(timezone.utc).timestamp())
                result = tv.validate_expiration_unix(self._to_unix(value), now_unix)
            elif vt == "timeframe":
                result = tv.validate_timeframe(value)
            elif vt == "date_range":
                start_unix = self._to_unix(value)
                end = kwargs.get("end_date")
                end_unix = self._to_unix(end) if end is not None else None
                now_unix = int(datetime.now(timezone.utc).timestamp())
                result = tv.validate_date_range_unix(start_unix, end_unix, now_unix)
            elif vt == "trade_request":
                payload: Dict[str, Any] = dict(value)
                request = tv.TradeRequestPayload(
                    symbol=str(payload.get("symbol", "")),
                    volume=float(payload.get("volume", 0.0)),
                    type=int(payload.get("type", 0)),
                    price=float(payload["price"]) if payload.get("price") is not None else None,
                    sl=float(payload["sl"]) if payload.get("sl") is not None else None,
                    tp=float(payload["tp"]) if payload.get("tp") is not None else None,
                    magic=int(payload["magic"]) if payload.get("magic") is not None else None,
                    slippage=int(payload["slippage"]) if payload.get("slippage") is not None else None,
                    deviation=int(payload["deviation"]) if payload.get("deviation") is not None else None,
                )
                result = tv.validate_trade_request_payload(request, ctx, self.rules)
            elif vt == "credentials":
                creds = dict(value)
                result = tv.validate_credentials(
                    tv.CredentialsPayload(
                        login=int(creds.get("login", 0)),
                        password=str(creds.get("password", "")),
                        server=str(creds.get("server", "")),
                    )
                )
            elif vt == "margin":
                result = tv.validate_margin(float(value), ctx)
            elif vt == "ticket":
                result = tv.validate_ticket(int(value))
            elif vt == "max_orders":
                account_limit = kwargs.get("account_limit")
                if account_limit is not None:
                    account_limit = int(account_limit)
                result = tv.validate_max_orders(int(value), account_limit, ctx)
            elif vt == "symbol_volume":
                volume_limit = kwargs.get("volume_limit")
                if volume_limit is not None:
                    volume_limit = float(volume_limit)
                result = tv.validate_symbol_volume(float(value), volume_limit, ctx)
            else:
                return False, f"Unsupported validation type: {validation_type}"

            return result.ok, result.message
        except Exception as exc:
            return False, f"{validation_type} validation error: {exc}"

    def validate_multiple(self, validations: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        for row in validations:
            validation_type = row.get("type")
            value = row.get("value")
            kwargs = {k: v for k, v in row.items() if k not in ("type", "value")}
            ok, message = self.validate(str(validation_type), value, **kwargs)
            if not ok:
                errors.append(f"{validation_type}: {message}")
        return len(errors) == 0, errors

# Global Variables
eurusd = "EURUSD"
backend = "mt5"  # "mt5" or "tester"

# Derived globals
mt5 = get_mt5_api()
client = MT5Utils.get_connected_client()
mt5_account = client.account_info()
eurusd_info = client.symbol_info(eurusd)
validator = TradeValidator()

# Initialize backend
if backend == "mt5":
    simulator = mt5
    print("Using: MT5 backend")
else:
    from apps.trading.main import Engine, AccountInfo
    account = AccountInfo(mt5_account)
    simulator = Engine(account)
    # Simulator initialization might need custom seeding which isn't standard here anymore without C++, skipping
    print("Using: Python Simulator backend")


# Helper functions
def _header(name: str) -> None:
    print()
    print("=" * 72)
    print(name)
    print("=" * 72)


# Example functions
def f01_symbol() -> None:
    symbol = "EURUSD"
    exists = client.symbol_select(symbol, True)
    visible = client.symbol_select(symbol)
    ok, msg = validator.validate("symbol", symbol, symbol_exists=exists, symbol_visible=visible)
    print(f"symbol {symbol}: ok={ok}, message={msg}")


def f02_volume() -> None:
    lots = "0.10"
    ok, msg = validator.validate("volume", lots, symbol_info=eurusd_info)
    print(f"volume {lots}: ok={ok}, message={msg}")


def f03_price() -> None:
    price = "1.10020"
    ok, msg = validator.validate("price", price, symbol_info=eurusd_info)
    print(f"price {price}: ok={ok}, message={msg}")


def f04_stop_loss() -> None:
    ok, msg = validator.validate(
        "stop_loss",
        "1.09900",
        entry_price="1.10020",
        order_type=0,
        symbol_info=eurusd_info,
    )
    print(f"stop_loss 1.09900: ok={ok}, message={msg}")


def f05_take_profit() -> None:
    ok, msg = validator.validate(
        "take_profit",
        "1.10150",
        entry_price="1.10020",
        order_type=0,
        symbol_info=eurusd_info,
    )
    print(f"take_profit 1.10150: ok={ok}, message={msg}")


def f06_order_type() -> None:
    ok, msg = validator.validate("order_type", "BUY")
    print(f"order_type BUY: ok={ok}, message={msg}")


def f07_magic() -> None:
    ok, msg = validator.validate("magic", 123456)
    print(f"magic 123456: ok={ok}, message={msg}")


def f08_slippage() -> None:
    requested_price = f"{float(eurusd_info.ask):.{int(getattr(eurusd_info, 'digits', 5))}f}"
    ok, msg = validator.validate(
        "slippage",
        10,
        requested_price=requested_price,
        order_type=0,
        symbol_info=eurusd_info,
        tick=eurusd_info,
    )
    print(f"slippage 10 @ {requested_price}: ok={ok}, message={msg}")


def f09_expiration_mode() -> None:
    ok, msg = validator.validate("expiration_mode", "GTC")
    print(f"expiration_mode GTC: ok={ok}, message={msg}")


def f10_expiration() -> None:
    ok, msg = validator.validate("expiration", datetime.now(timezone.utc) + timedelta(days=1))
    print(f"expiration: ok={ok}, message={msg}")


def f11_timeframe() -> None:
    ok, msg = validator.validate("timeframe", "M15")
    print(f"timeframe M15: ok={ok}, message={msg}")


def f12_date_range() -> None:
    ok, msg = validator.validate(
        "date_range",
        datetime.now(timezone.utc) - timedelta(days=7),
        end_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    print(f"date_range: ok={ok}, message={msg}")


def f13_trade_request() -> None:
    requested_price = float(eurusd_info.ask)
    point = float(getattr(eurusd_info, "point", 0.00001))
    request = {
        "action": 1,
        "symbol": "EURUSD",
        "volume": 0.10,
        "type": 0,
        "price": requested_price,
        "sl": requested_price - (50.0 * point),
        "tp": requested_price + (50.0 * point),
        "magic": 123456,
        "slippage": 10,
    }
    ok, msg = validator.validate(
        "trade_request",
        request,
        symbol_exists=True,
        symbol_visible=True,
        symbol_info=eurusd_info,
        tick=eurusd_info,
    )
    print(f"trade_request: ok={ok}, message={msg}")


def f14_credentials() -> None:
    creds = {"login": 12345678, "password": "secret", "server": "MetaQuotes-Demo"}
    ok, msg = validator.validate("credentials", creds)
    print(f"credentials: ok={ok}, message={msg}")


def f15_margin() -> None:
    ok, msg = validator.validate("margin", 100.0, account_info=mt5_account)
    print(f"margin 100.0: ok={ok}, message={msg}")


def f16_ticket() -> None:
    ok, msg = validator.validate("ticket", 1001)
    print(f"ticket 1001: ok={ok}, message={msg}")


def f18_max_orders() -> None:
    ok, msg = validator.validate("max_orders", 12, account_info=mt5_account)
    print(f"max_orders 12: ok={ok}, message={msg}")


def f19_symbol_volume() -> None:
    ok, msg = validator.validate("symbol_volume", 5.0, symbol_info=eurusd_info)
    print(f"symbol_volume 5.0: ok={ok}, message={msg}")


def f20_complete_validation() -> None:
    now = datetime.now(timezone.utc)
    symbol = "EURUSD"
    exists = client.symbol_select(symbol, True)
    visible = client.symbol_select(symbol)
    requested_price = f"{float(eurusd_info.ask):.{int(getattr(eurusd_info, 'digits', 5))}f}"
    request_price = float(eurusd_info.ask)
    point = float(getattr(eurusd_info, "point", 0.00001))

    validations = [
        {"type": "symbol", "value": symbol, "symbol_exists": exists, "symbol_visible": visible},
        {"type": "volume", "value": "0.10", "symbol_info": eurusd_info},
        {"type": "price", "value": "1.10020", "symbol_info": eurusd_info},
        {
            "type": "stop_loss",
            "value": "1.09900",
            "entry_price": "1.10020",
            "order_type": 0,
            "symbol_info": eurusd_info,
        },
        {
            "type": "take_profit",
            "value": "1.10150",
            "entry_price": "1.10020",
            "order_type": 0,
            "symbol_info": eurusd_info,
        },
        {"type": "order_type", "value": "BUY"},
        {"type": "magic", "value": 123456},
        {
            "type": "slippage",
            "value": 10,
            "requested_price": requested_price,
            "order_type": 0,
            "symbol_info": eurusd_info,
            "tick": eurusd_info,
        },
        {"type": "expiration_mode", "value": "GTC"},
        {"type": "expiration", "value": now + timedelta(days=1)},
        {"type": "timeframe", "value": "M15"},
        {"type": "date_range", "value": now - timedelta(days=7), "end_date": now - timedelta(days=1)},
        {
            "type": "trade_request",
            "value": {
                "action": 1,
                "symbol": symbol,
                "volume": 0.10,
                "type": 0,
                "price": request_price,
                "sl": request_price - (50.0 * point),
                "tp": request_price + (50.0 * point),
                "magic": 123456,
                "slippage": 10,
            },
            "symbol_exists": True,
            "symbol_visible": True,
            "symbol_info": eurusd_info,
            "tick": eurusd_info,
        },
        {"type": "credentials", "value": {"login": 12345678, "password": "secret", "server": "MetaQuotes-Demo"}},
        {"type": "margin", "value": 100.0, "account_info": mt5_account},
        {"type": "ticket", "value": 1001},
        {"type": "max_orders", "value": 12, "account_info": mt5_account},
        {"type": "symbol_volume", "value": 5.0, "symbol_info": eurusd_info},
    ]
    all_ok, errors = validator.validate_multiple(validations)
    print(f"complete_validation: all_ok={all_ok}")
    if errors:
        for err in errors:
            print(f"  - {err}")


def main() -> None:

    _header("Single Validation Examples")
    f01_symbol()
    f02_volume()
    f03_price()
    f04_stop_loss()
    f05_take_profit()
    f06_order_type()
    f07_magic()
    f08_slippage()
    f09_expiration_mode()
    f10_expiration()
    f11_timeframe()
    f12_date_range()
    f13_trade_request()
    f14_credentials()
    f15_margin()
    f16_ticket()
    f18_max_orders()
    f19_symbol_volume()

    _header("Complete Validation Example")
    f20_complete_validation()


if __name__ == "__main__":
    main()
