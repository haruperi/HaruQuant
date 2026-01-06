"""
Trade Example

Demonstrates the use of Trade class with both MT5 and Backtest providers.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.trading import (
    Trade,
    MT5TradeProvider,
    BacktestTradeProvider,
    OrderType,
    OrderTypeFilling,
)
from apps.logger import logger


def get_supported_filling_mode(client, symbol):
    """
    Determine the best filling mode for a symbol.

    MT5 has three filling modes:
    - RETURN: Can be partially filled, remaining is kept as pending
    - IOC: Immediate or Cancel - Fill what you can, cancel the rest
    - FOK: Fill or Kill - All or nothing

    For Forex, RETURN is most commonly supported.
    """
    symbol_info = client.get_symbol_info(symbol)
    if not symbol_info:
        logger.warning(f"Could not get symbol info for {symbol}, defaulting to RETURN")
        return OrderTypeFilling.RETURN

    # Check filling_mode flags (bitwise)
    filling_mode = symbol_info.get('filling_mode', 0)

    # Bit flags: 1=RETURN, 2=IOC, 4=FOK
    # Try RETURN first (most compatible for Forex)
    if filling_mode & 1:  # RETURN supported
        logger.info(f"{symbol} supports RETURN filling mode")
        return OrderTypeFilling.RETURN
    elif filling_mode & 2:  # IOC supported
        logger.info(f"{symbol} supports IOC filling mode")
        return OrderTypeFilling.IOC
    elif filling_mode & 4:  # FOK supported
        logger.info(f"{symbol} supports FOK filling mode")
        return OrderTypeFilling.FOK
    else:
        logger.warning(f"No standard filling mode detected for {symbol}, defaulting to RETURN")
        return OrderTypeFilling.RETURN


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
    """Main example function."""
    client = None
    
    try:
        print("=" * 70)
        print("Trade Example")
        print("=" * 70)
        print()

        # Get credentials from database
        creds = get_mt5_credentials()

        # Initialize MT5 Client
        print("Connecting to MT5...")
        client = MT5Client(
            login=creds["login"],
            password=creds["password"],
            server=creds["server"],
            path=creds["path"]
        )
        if not client.is_connected():
            print("Failed to connect to MT5")
            return
        print("Connected successfully!")
        print()

        # ============================================================
        # Provider Selection
        # ============================================================

        # Option 1: Live Trading with MT5
        provider = MT5TradeProvider(client)
        print("Using: MT5TradeProvider (Live Trading)")

        # Option 2: Backtesting with Simulated Trades
        # provider = BacktestTradeProvider(initial_balance=10000.0)
        # # Set current prices for simulation
        # provider.set_symbol_price("EURUSD", bid=1.0950, ask=1.0952)
        # provider.set_symbol_price("GBPUSD", bid=1.2600, ask=1.2602)
        # print("Using: BacktestTradeProvider (Simulated Trading)")

        print()

        # Create Trade instance
        trade = Trade(provider)

        # Configure trade settings
        trade.set_expert_magic_number(12345)
        trade.set_deviation_in_points(10)

        # Detect and set the best filling mode for the symbol
        filling_mode = get_supported_filling_mode(client, "EURUSD")
        trade.set_type_filling(filling_mode)
        print(f"Set filling mode to: {filling_mode.name}")
        print()
        
        print("=" * 70)
        print("Example 1: Open Position")
        print("=" * 70)
        print()

        # Get current market prices
        symbol_info = client.get_symbol_info("EURUSD")
        if not symbol_info:
            print("✗ Failed to get symbol info for EURUSD")
            return

        bid = symbol_info.get('bid', 0)
        ask = symbol_info.get('ask', 0)
        point = symbol_info.get('point', 0.00001)

        print(f"Current EURUSD prices:")
        print(f"  Bid: {bid:.5f}")
        print(f"  Ask: {ask:.5f}")
        print()

        # For BUY orders, use ask price
        # Set SL 50 points below, TP 100 points above
        buy_price = ask
        sl_buy = buy_price - (50 * point)
        tp_buy = buy_price + (100 * point)

        # Open a buy position
        if trade.position_open(
            symbol="EURUSD",
            order_type=OrderType.BUY,
            volume=0.1,
            price=buy_price,
            sl=sl_buy,
            tp=tp_buy,
            comment="Example buy order"
        ):
            print(f"✓ Position opened successfully!")
            print(f"  Order: #{trade.result_order()}")
            print(f"  Deal: #{trade.result_deal()}")
            print(f"  Volume: {trade.result_volume()}")
            print(f"  Price: {trade.result_price()}")
            print(f"  Comment: {trade.result_comment()}")
        else:
            print(f"✗ Failed to open position")
            print(f"  Retcode: {trade.result_retcode_description()}")
            print(f"  Comment: {trade.result_comment()}")
        
        print()
        print("=" * 70)
        print("Example 2: Modify Position")
        print("=" * 70)
        print()

        # Get updated prices
        symbol_info = client.get_symbol_info("EURUSD")
        if symbol_info:
            current_bid = symbol_info.get('bid', 0)
            current_ask = symbol_info.get('ask', 0)

            # Adjust SL/TP: Move SL closer (30 points), extend TP (150 points)
            new_sl = current_ask - (30 * point)
            new_tp = current_ask + (150 * point)

            print(f"Modifying position with new SL/TP:")
            print(f"  New SL: {new_sl:.5f}")
            print(f"  New TP: {new_tp:.5f}")
            print()

        # Modify SL/TP
        if trade.position_modify(
            symbol="EURUSD",
            sl=new_sl,
            tp=new_tp
        ):
            print(f"✓ Position modified successfully!")
            print(f"  New SL: {new_sl:.5f}")
            print(f"  New TP: {new_tp:.5f}")
        else:
            print(f"✗ Failed to modify position")
            print(f"  Retcode: {trade.result_retcode_description()}")
        
        print()
        print("=" * 70)
        print("Example 3: Close Position")
        print("=" * 70)
        print()
        
        # Close position
        if trade.position_close(symbol="EURUSD"):
            print(f"✓ Position closed successfully!")
            print(f"  Deal: #{trade.result_deal()}")
            print(f"  Volume: {trade.result_volume()}")
            print(f"  Price: {trade.result_price()}")
        else:
            print(f"✗ Failed to close position")
            print(f"  Retcode: {trade.result_retcode_description()}")
        
        print()
        print("=" * 70)
        print("Example 4: Pending Order")
        print("=" * 70)
        print()

        # Get current GBPUSD prices for pending order
        gbp_info = client.get_symbol_info("GBPUSD")
        if not gbp_info:
            print("✗ Failed to get symbol info for GBPUSD")
        else:
            # Set filling mode for GBPUSD
            gbp_filling_mode = get_supported_filling_mode(client, "GBPUSD")
            trade.set_type_filling(gbp_filling_mode)
            print(f"Set filling mode for GBPUSD to: {gbp_filling_mode.name}")

            gbp_bid = gbp_info.get('bid', 0)
            gbp_ask = gbp_info.get('ask', 0)
            gbp_point = gbp_info.get('point', 0.00001)

            print(f"Current GBPUSD prices:")
            print(f"  Bid: {gbp_bid:.5f}")
            print(f"  Ask: {gbp_ask:.5f}")
            print()

            # BUY_LIMIT: Place order below current ask price
            # Set limit 50 points below ask, SL 100 points below limit, TP 150 points above limit
            limit_price = gbp_ask - (50 * gbp_point)
            sl_limit = limit_price - (100 * gbp_point)
            tp_limit = limit_price + (150 * gbp_point)

            print(f"Placing BUY LIMIT order:")
            print(f"  Limit Price: {limit_price:.5f}")
            print(f"  Stop Loss: {sl_limit:.5f}")
            print(f"  Take Profit: {tp_limit:.5f}")
            print()

        # Place a pending order
        if trade.order_open(
            symbol="GBPUSD",
            order_type=OrderType.BUY_LIMIT,
            volume=0.05,
            limit_price=0.0,
            price=limit_price,
            sl=sl_limit,
            tp=tp_limit,
            comment="Pending buy limit"
        ):
            print(f"✓ Pending order placed successfully!")
            print(f"  Order: #{trade.result_order()}")
            print(f"  Price: {trade.request_price()}")
            print(f"  Volume: {trade.request_volume()}")
        else:
            print(f"✗ Failed to place pending order")
            print(f"  Retcode: {trade.result_retcode_description()}")
        
        print()
        print("=" * 70)
        print("Example completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Shutdown MT5 connection
        if client is not None:
            print("\nShutting down MT5 connection...")
            client.shutdown()
            print("Disconnected.")


if __name__ == "__main__":
    main()
