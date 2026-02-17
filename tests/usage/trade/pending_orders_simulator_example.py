"""
Example usage of pending orders in the Trade simulator.
"""

import os
import sys
from datetime import datetime, timedelta

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator, SymbolTickSimulator
from apps.utils.logger import logger
from apps.mt5 import MT5Client, get_mt5_api
from apps.sqlite.users import UserManager

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
    print("Pending Orders Simulator Example")
    print("=" * 70)
    print()

    # Get credentials and connect to MT5
    creds = get_mt5_credentials()
    client = MT5Client()

    if not client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    ):
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    print(f"Connected to MT5 successfully!")
    print()

    # Adding symbol info (default real mt5 symbol info)
    symbol = "EURUSD"
    symbol_info = SymbolInfoSimulator.from_mt5_symbol(symbol)
    symbol_info.trade_stops_level = 10

    # Add synthetic tick data
    tick = SymbolTickSimulator(bid=1.10000, ask=1.10010, last=1.10005)

    account_info = AccountInfoSimulator()
    simulator = TradeSimulator(
        simulator_name="PendingOrdersExample",
        mt5_client=client,
        account_info=account_info,
        symbols={symbol: symbol_info},
    )
    simulator._ticks_data[symbol] = tick

    print("Submitting pending orders...")
    print("-" * 70)

    # (a) Invalid order type
    ok = simulator._place_pending_order(
        order_type="buy",
        volume=0.1,
        symbol=symbol,
        open_price=1.09900,
        sl=0.0,
        tp=0.0,
        comment="Invalid type for pending order",
        expiry_date=None,
        expiration_mode="gtc",
    )
    print(f"Invalid type accepted? {ok}")

    # (b) Too close to market (buy-related)
    ok = simulator.buy_limit(
        volume=0.1,
        symbol=symbol,
        open_price=1.10001,
        comment="Too close to bid",
    )
    print(f"Too close buy limit accepted? {ok}")

    # (c) Expiration in the past
    past = datetime.now() - timedelta(minutes=1)
    ok = simulator.sell_limit(
        volume=0.1,
        symbol=symbol,
        open_price=1.10150,
        expiry_date=past,
        expiration_mode="daily",
        comment="Past expiration",
    )
    print(f"Past expiration accepted? {ok}")

    # Valid pending orders
    future = datetime.now() + timedelta(minutes=10)
    ok = simulator.buy_stop(
        volume=0.1,
        symbol=symbol,
        open_price=1.10100,
        expiry_date=future,
        expiration_mode="daily",
        comment="Valid Buy Stop",
    )
    print(f"Valid buy stop accepted? {ok}")

    ok = simulator.sell_limit(
        volume=0.1,
        symbol=symbol,
        open_price=1.10200,
        expiry_date=future,
        expiration_mode="daily",
        comment="Valid Sell Limit",
    )
    print(f"Valid sell limit accepted? {ok}")

    print("\nPending orders stored:")
    total = len(simulator._simulator._orders_data)
    print(f"Total pending orders: {total}")
    for order in simulator._simulator._orders_data.values():
        print(
            f"#{order.ticket} {order.type} {order.symbol} "
            f"{order.volume_current} at {order.open_price}"
        )

    # Loop with synthetic ticks to trigger pending orders
    print("\nSimulating ticks...")
    for i in range(6):
        tick.bid = 1.10000 + (i * 0.00040)
        tick.ask = tick.bid + 0.00020
        logger.info(f"Tick {i}: bid={tick.bid:.5f} ask={tick.ask:.5f}")
        simulator.monitor_pending_orders()

    print("\nPositions after triggers:")
    from apps.trade import PositionInfo
    pos_info = PositionInfo(api=simulator._simulator)
    total_positions = simulator._simulator.positions_get()
    if total_positions:
        for idx in range(len(total_positions)):
            if pos_info.SelectByIndex(idx):
                print(
                    f"Position #{pos_info.Identifier()} {pos_info.TypeDescription()} "
                    f"{pos_info.Symbol()} {pos_info.Volume()} at {pos_info.PriceOpen()}"
                )
    else:
        print("No positions opened.")

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()

