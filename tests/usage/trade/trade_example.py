"""
Example usage of Trade class with MT5 live execution.

This file intentionally uses the Python MT5 transport:
`apps.mt5.trade.Trade` for real order routing.
"""

import os
import sys

# Add repo root to path for local imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from apps.mt5 import MT5Client, get_mt5_api
from apps.sqlite.users import UserManager
from apps.utils.logger import logger
from apps.mt5 import Trade

mt5 = get_mt5_api()


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main():
    print("=" * 70)
    print("Trade Example (LIVE MT5 Execution via apps.mt5.Trade)")
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

    print("Connected successfully!")
    print()

    trade = Trade()
    trade.SetExpertMagicNumber(12345)
    trade.SetDeviationInPoints(10)

    if trade.SetTypeFillingBySymbol("EURUSD"):
        print("Set filling mode for EURUSD from symbol settings")
    else:
        print("Using default filling mode for EURUSD")
    print()

    print("=" * 70)
    print("Example 1: Open Position")
    print("=" * 70)
    print()

    symbol_info = mt5.symbol_info("EURUSD")
    if not symbol_info:
        print("[FAIL] Failed to get symbol info for EURUSD")
        return

    bid = symbol_info.bid
    ask = symbol_info.ask
    point = symbol_info.point

    print(f"Current EURUSD prices:")
    print(f"  Bid: {bid:.5f}")
    print(f"  Ask: {ask:.5f}")
    print()

    buy_price = ask
    sl_buy = buy_price - (50 * point)
    tp_buy = buy_price + (100 * point)

    if trade.PositionOpen(
        symbol="EURUSD",
        order_type=mt5.ORDER_TYPE_BUY,
        volume=0.1,
        price=buy_price,
        sl=sl_buy,
        tp=tp_buy,
        comment="Example buy order",
    ):
        print("[OK] Position opened successfully")
        print(f"  Order: #{trade.ResultOrder()}")
        print(f"  Deal: #{trade.ResultDeal()}")
        print(f"  Volume: {trade.ResultVolume()}")
        print(f"  Price: {trade.ResultPrice()}")
        print(f"  Comment: {trade.ResultComment()}")
    else:
        print("[FAIL] Failed to open position")
        print(f"  Retcode: {trade.ResultRetcodeDescription()}")
        print(f"  Comment: {trade.ResultComment()}")

    print()
    print("=" * 70)
    print("Example 2: Modify Position")
    print("=" * 70)
    print()

    symbol_info = mt5.symbol_info("EURUSD")
    if symbol_info:
        current_ask = symbol_info.ask
        new_sl = current_ask - (30 * point)
        new_tp = current_ask + (150 * point)
    else:
        new_sl = 0.0
        new_tp = 0.0

    print(f"Modifying position with new SL/TP:")
    print(f"  New SL: {new_sl:.5f}")
    print(f"  New TP: {new_tp:.5f}")
    print()

    if trade.PositionModify(symbol="EURUSD", sl=new_sl, tp=new_tp):
        print("[OK] Position modified successfully")
    else:
        print("[FAIL] Failed to modify position")
        print(f"  Retcode: {trade.ResultRetcodeDescription()}")

    print()
    print("=" * 70)
    print("Example 3: Close Position")
    print("=" * 70)
    print()

    if trade.PositionClose(symbol="EURUSD"):
        print("[OK] Position closed successfully")
        print(f"  Deal: #{trade.ResultDeal()}")
        print(f"  Volume: {trade.ResultVolume()}")
        print(f"  Price: {trade.ResultPrice()}")
    else:
        print("[FAIL] Failed to close position")
        print(f"  Retcode: {trade.ResultRetcodeDescription()}")

    print()
    print("=" * 70)
    print("Example 4: Pending Order")
    print("=" * 70)
    print()

    gbp_info = mt5.symbol_info("GBPUSD")
    if not gbp_info:
        print("[FAIL] Failed to get symbol info for GBPUSD")
    else:
        if trade.SetTypeFillingBySymbol("GBPUSD"):
            print("Set filling mode for GBPUSD from symbol settings")
        else:
            print("Using default filling mode for GBPUSD")

        gbp_ask = gbp_info.ask
        gbp_point = gbp_info.point
        limit_price = gbp_ask - (50 * gbp_point)
        sl_limit = limit_price - (100 * gbp_point)
        tp_limit = limit_price + (150 * gbp_point)

        print(f"Placing BUY LIMIT order:")
        print(f"  Limit Price: {limit_price:.5f}")
        print(f"  Stop Loss: {sl_limit:.5f}")
        print(f"  Take Profit: {tp_limit:.5f}")
        print()

        if trade.OrderOpen(
            symbol="GBPUSD",
            order_type=mt5.ORDER_TYPE_BUY_LIMIT,
            volume=0.05,
            price=limit_price,
            sl=sl_limit,
            tp=tp_limit,
            comment="Pending buy limit",
        ):
            print("[OK] Pending order placed successfully")
            print(f"  Order: #{trade.ResultOrder()}")
            print(f"  Price: {trade.RequestPrice()}")
            print(f"  Volume: {trade.RequestVolume()}")
        else:
            print("[FAIL] Failed to place pending order")
            print(f"  Retcode: {trade.ResultRetcodeDescription()}")

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)

    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()


