"""
Example usage of HistoryOrderInfo with different providers.

This example demonstrates two ways to use HistoryOrderInfo:
1. MT5HistoryOrderProvider - Live trading with MT5 connection
2. BacktestHistoryOrderProvider - Backtest with simulated historical orders

Simply uncomment the provider you want to use.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger
from apps.trading import (
    HistoryOrderInfo,
    MT5HistoryOrderProvider,
    BacktestHistoryOrderProvider,
    OrderType,
    OrderState,
    OrderTypeFilling,
    OrderTypeTime,
)


def get_mt5_credentials():
    """Get MT5 credentials from database."""
    user_manager = UserManager()
    user_manager.db_path = "data/database/haruquant.db"

    username = "haruperi"  # Change this to your username
    user = user_manager.get_user(username=username)
    if not user:
        logger.error(f"User {username} not found")
        sys.exit(1)

    creds = user_manager.get_mt5_credentials(user["id"])
    if not creds:
        logger.error(f"No default broker credentials found for {username}")
        sys.exit(1)

    logger.info(f"Using credentials for account: {creds['login']} on {creds['server']}")
    return creds


def main():
    print("=" * 70)
    print("HistoryOrderInfo Example")
    print("=" * 70)
    print()

    # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client (needed for Option 1)
    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    print("Connecting to MT5...")
    if not client.is_connected():
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    try:
        print(f"Connected successfully!")
        print()

        # ============================================================
        # CHOOSE YOUR PROVIDER (uncomment one option)
        # ============================================================

        # Option 1: Live Trading with MT5 (last 30 days)
        now = datetime.now()
        start = now - timedelta(days=30)
        provider = MT5HistoryOrderProvider(client, date_from=start, date_to=now)
        print("Using: MT5HistoryOrderProvider (Live Trading - Last 30 Days)")

        # Option 2: Backtesting with Simulated Historical Orders
        # provider = BacktestHistoryOrderProvider()
        # provider.add_order(
        #     ticket=4001,
        #     time_setup=datetime.now() - timedelta(hours=2),
        #     time_done=datetime.now() - timedelta(hours=1),
        #     order_type=OrderType.BUY,
        #     state=OrderState.FILLED,
        #     symbol="EURUSD",
        #     volume_initial=0.1,
        #     volume_current=0.0,  # Fully filled
        #     price_open=1.1000,
        #     stop_loss=1.0950,
        #     take_profit=1.1050,
        #     price_current=1.1000,
        #     type_filling=OrderTypeFilling.FOK,
        #     type_time=OrderTypeTime.GTC,
        #     magic=12345,
        #     position_id=1001,
        #     comment="Filled buy history_order"
        # )
        # provider.add_order(
        #     ticket=4002,
        #     time_setup=datetime.now() - timedelta(hours=3),
        #     time_done=datetime.now() - timedelta(hours=2),
        #     order_type=OrderType.SELL_LIMIT,
        #     state=OrderState.CANCELED,
        #     symbol="GBPUSD",
        #     volume_initial=0.2,
        #     volume_current=0.2,  # Not filled
        #     price_open=1.2600,
        #     stop_loss=1.2650,
        #     take_profit=1.2550,
        #     price_current=1.2580,
        #     type_filling=OrderTypeFilling.FOK,
        #     type_time=OrderTypeTime.GTC,
        #     magic=12345,
        #     comment="Canceled sell limit"
        # )
        # print("Using: BacktestHistoryOrderProvider (Simulated Historical Orders)")

        print()

        # Create HistoryOrderInfo instance
        history_order = HistoryOrderInfo(provider)

        # Example 1: Iterate through all historical orders
        print("\n" + "=" * 70)
        print("Example 1: All Historical Orders")
        print("=" * 70)

        # Using total_orders()
        total = history_order.total_orders()
        print(f"Total orders: {total}\n")

        for i in range(total):
            if history_order.select_by_index(i):
                print(f"{i + 1}. {history_order.format_order()}")
                print(f"   State: {history_order.state_description()}")
                print(f"   Setup: {history_order.time_setup()}")
                print(f"   Done: {history_order.time_done()}")
                print(f"   Type: {history_order.type_description()}")
                print(f"   Symbol: {history_order.symbol()}")
                print(f"   Volume: {history_order.volume_current()}/{history_order.volume_initial()}")
                print(f"   Price: {history_order.price_open()}")
                print(f"   SL: {history_order.stop_loss()}, TP: {history_order.take_profit()}")
                print(f"   Magic: {history_order.magic()}")
                print(f"   Position ID: {history_order.position_id()}")
                print(f"   Position By ID: {history_order.position_by_id()}")
                print(f"   External ID: {history_order.external_id()}")

                # Volumes and Prices
                print(f"   Vol Initial: {history_order.volume_initial()}")
                print(f"   Vol Current: {history_order.volume_current()}")
                print(f"   Price Open: {history_order.price_open()}")
                print(f"   Price Current: {history_order.price_current()}")
                print(f"   Stop Limit: {history_order.price_stoplimit()}")
                print(f"   SL: {history_order.stop_loss()}")
                print(f"   TP: {history_order.take_profit()}")

                # Comment
                print(f"   Comment: {history_order.comment()}")

                # Test static formatters
                print(
                    f"   Format Type: {HistoryOrderInfo.format_type(history_order.order_type())}"
                )
                print(
                    f"   Format Status: {HistoryOrderInfo.format_status(history_order.state())}"
                )
                print(
                    f"   Format Filling: {HistoryOrderInfo.format_type_filling(history_order.type_filling())}"
                )
                print(
                    f"   Format Time: {HistoryOrderInfo.format_type_time(history_order.type_time())}"
                )
                if history_order.price_stoplimit() > 0:
                    print(
                        f"   Format Price: {HistoryOrderInfo.format_price(history_order.price_open(), history_order.price_stoplimit(), 5)}"
                    )

        # Example 2: Statistics
        print("\n" + "=" * 70)
        print("Example 2: history_order Statistics")
        print("=" * 70)

        filled_count = 0
        canceled_count = 0
        total_vol = 0.0

        for i in range(total):
            if history_order.select_by_index(i):
                total_vol += history_order.volume_initial()
                if history_order.state() == OrderState.FILLED:
                    filled_count += 1
                elif history_order.state() == OrderState.CANCELED:
                    canceled_count += 1

        print(f"Filled: {filled_count}")
        print(f"Canceled: {canceled_count}")
        print(f"Total Volume Ordered: {total_vol:.2f}")

        # Example 3: String Representation
        print("\n" + "=" * 70)
        print("Example 3: String Representation")
        print("=" * 70)

        if total > 0 and history_order.select_by_index(0):
            print(f"repr(): {repr(history_order)}")

        print("\n" + "=" * 70)
        print("Example Complete")
        print("=" * 70)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Shutdown MT5 connection
        print("\nShutting down MT5 connection...")
        client.shutdown()
        print("Disconnected.")


if __name__ == "__main__":
    main()
