"""Usage examples for C++-backed TradeValidator (haruquant.TradeValidator).

Run:
    python examples/utils/usage_validator.py
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from apps.mt5 import MT5Utils, Trade, get_mt5_api
from apps.utils.logger import logger
from apps.utils.trade_validators import TradeValidator

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
        validator.validate(
            "date_range",
            datetime.now(timezone.utc) - timedelta(days=7),
            end_date=datetime.now(timezone.utc) - timedelta(days=1),
        ),
    )


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
