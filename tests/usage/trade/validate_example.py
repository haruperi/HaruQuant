"""
Example usage of TradeValidator.
"""

import os
import sys

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.logger import logger
from apps.mt5 import MT5Client, get_mt5_api
from apps.sqlite.users import UserManager
from apps.utils.validate import TradeValidator


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main():
    print("=" * 70)
    print("TradeValidator Example")
    print("=" * 70)
    print()

    creds = get_mt5_credentials()

    client = MT5Client()
    connected = client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"],
    )

    if not connected:
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    symbol = "EURUSD"
    mt5 = get_mt5_api()
    symbol_info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)

    if not symbol_info or not tick:
        print("Failed to fetch symbol or tick info.")
        client.shutdown()
        return

    validator = TradeValidator(client=client, logger_instance=logger)

    print("\nBasic validations")
    print("-" * 40)
    print(validator.validate("symbol", symbol))
    print(validator.validate("volume", 0.1, symbol=symbol))
    print(validator.validate("price", tick.ask, symbol=symbol))

    print("\nStop levels")
    print("-" * 40)
    entry = tick.ask
    sl = entry - (50 * symbol_info.point)
    tp = entry + (100 * symbol_info.point)
    print(
        validator.validate(
            "stop_loss",
            sl,
            entry_price=entry,
            order_type=mt5.ORDER_TYPE_BUY,
            symbol=symbol,
        )
    )
    print(
        validator.validate(
            "take_profit",
            tp,
            entry_price=entry,
            order_type=mt5.ORDER_TYPE_BUY,
            symbol=symbol,
        )
    )
    print(
        validator.validate(
            "freeze_level",
            entry,
            stop_price=sl,
            order_type=mt5.ORDER_TYPE_BUY,
            symbol=symbol,
        )
    )

    print("\nLot size")
    print("-" * 40)
    print(validator.validate("volume", 0.1, symbol=symbol))

    print("\nAccount limits")
    print("-" * 40)
    account_info = client.get_account_info()
    if account_info:
        print(validator.validate("margin", 10.0))
        print(
            validator.validate(
                "max_orders",
                account_info.get("orders_total", 0),
                account_limit=account_info.get("limit_orders"),
            )
        )
    else:
        print("Account info not available")

    print("\nSymbol limits")
    print("-" * 40)
    print(
        validator.validate(
            "symbol_volume",
            symbol_info.volume,
            volume_limit=symbol_info.volume_limit,
            symbol=symbol,
        )
    )

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)

    client.shutdown()


if __name__ == "__main__":
    main()
