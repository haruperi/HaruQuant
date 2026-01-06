"""
Example usage of OrderInfo with different providers.

This example demonstrates two ways to use OrderInfo:
1. MT5OrderProvider - Live trading with MT5 connection
2. BacktestOrderProvider - Backtest with simulated active orders

Simply uncomment the provider you want to use.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger
from apps.trading import (
    OrderInfo,
    MT5OrderProvider,
    BacktestOrderProvider,
    OrderType,
    OrderState,
    OrderTypeFilling,
    OrderTypeTime,
)
from datetime import datetime


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
    print("OrderInfo Example")
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

        # Option 1: Live Trading with MT5
        provider = MT5OrderProvider(client)
        print("Using: MT5OrderProvider (Live Trading)")

        # Option 2: Backtesting with Simulated Active Orders
        # provider = BacktestOrderProvider()
        # provider.add_order(
        #     ticket=3001,
        #     time_setup=datetime.now(),
        #     order_type=OrderType.BUY_LIMIT,
        #     state=OrderState.PLACED,
        #     symbol="EURUSD",
        #     volume_initial=0.1,
        #     volume_current=0.1,
        #     price_open=1.0950,
        #     stop_loss=1.0900,
        #     take_profit=1.1000,
        #     price_current=1.0960,
        #     type_filling=OrderTypeFilling.FOK,
        #     type_time=OrderTypeTime.GTC,
        #     magic=12345,
        #     comment="Pending buy limit"
        # )
        # provider.add_order(
        #     ticket=3002,
        #     time_setup=datetime.now(),
        #     order_type=OrderType.SELL_STOP,
        #     state=OrderState.PLACED,
        #     symbol="GBPUSD",
        #     volume_initial=0.2,
        #     volume_current=0.2,
        #     price_open=1.2450,
        #     stop_loss=1.2500,
        #     take_profit=1.2400,
        #     price_current=1.2480,
        #     type_filling=OrderTypeFilling.FOK,
        #     type_time=OrderTypeTime.GTC,
        #     magic=12345,
        #     comment="Pending sell stop"
        # )
        # print("Using: BacktestOrderProvider (Simulated Orders)")

        print()

        # Create OrderInfo instance
        order = OrderInfo(provider)

        # Example 1: Iterate through orders
        print("\n" + "=" * 60)

        total = order.total_orders()
        print(f"Total orders: {total}")

        for i in range(total):
            if order.select_by_index(i):
                print(f"\n{i + 1}. Order #{order.ticket()}")
                print(f"   Symbol: {order.symbol()}")
                print(f"   Type: {order.type_description()}")
                print(f"   State: {order.state_description()}")
                print(f"   Volume: {order.volume_current():.2f}")
                print(f"   Price: {order.price_open()}")
                print(f"   Formatted: {order.format_order()}")

                # Detailed Properties
                print(f"   Ticket: {order.ticket()}")
                print(f"   Magic: {order.magic()}")
                print(f"   Position ID: {order.position_id()}")
                print(f"   Position By ID: {order.position_by_id()}")
                print(f"   External ID: {order.external_id()}")

                print(f"   Type: {order.type_description()} ({order.order_type()})")
                print(f"   State: {order.state_description()} ({order.state()})")
                print(
                    f"   Filling: {order.type_filling_description()} ({order.type_filling()})"
                )
                print(
                    f"   Time Type: {order.type_time_description()} ({order.type_time()})"
                )

                print(
                    f"   Time Setup: {order.time_setup()} (MSC: {order.time_setup_msc()})"
                )
                print(f"   Expiration: {order.time_expiration()}")

                print(f"   Vol Initial: {order.volume_initial()}")
                print(f"   Vol Current: {order.volume_current()}")
                print(f"   Price Open: {order.price_open()}")
                print(f"   Price Current: {order.price_current()}")
                print(f"   Stop Limit: {order.price_stoplimit()}")
                print(f"   SL: {order.stop_loss()}")
                print(f"   TP: {order.take_profit()}")

                print(f"   Comment: {order.comment()}")

        print("\n" + "=" * 60)
        print("Example 2: Select Order by Ticket")
        print("=" * 60)

        if total > 0:
            # Select first order to get its ticket
            if order.select_by_index(0):
                ticket_to_select = order.ticket()
                if order.select(ticket_to_select):
                    print(f"Selected order #{ticket_to_select}:")
                    print(f"  Symbol: {order.symbol()}")
                    print(f"  Comment: {order.comment()}")
                    print(f"  Filling: {order.type_filling_description()}")
                    print(f"  Time Type: {order.type_time_description()}")
                else:
                    print(f"Order #{ticket_to_select} not found")
        else:
            print("No orders to select.")

        # Example 3: State management
        print("\n" + "=" * 60)
        print("Example 3: State Management")
        print("=" * 60)
        if total > 0:
            # Select first order
            if order.select_by_index(0):
                ticket_to_select = order.ticket()
                print(f"Storing state for order #{ticket_to_select}...")
                order.store_state()

                print("Checking if changed... ", end="")
                if order.check_state():
                    print("Changed!")
                else:
                    print("Unchanged.")
        else:
            print("No orders to test state management.")

        # Example 4: Iterate all
        print("\n" + "=" * 60)
        print("Iterating all orders:")

        total = order.total_orders()
        print(f"Total orders: {total}")

        for i in range(total):
            if order.select_by_index(i):
                print(f"#{i+1}: {order.format_order()}")
                print(f"    State: {order.state_description()}")

        print("\n" + "=" * 60)
        print("Example completed successfully!")
        print("=" * 60)

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
