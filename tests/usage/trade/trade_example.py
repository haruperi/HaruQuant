"""
Example usage of Trade class with different providers.
"""

import sys
import os
from datetime import datetime

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5 import MT5Client
from apps.sqlite.users import UserManager
from apps.utils.logger import logger
from apps.trade import Trade
from apps.simulation.data import TradeSimulator, SymbolTickSimulator, PositionInfoSimulator

# For MQL5 constants (need to import mt5 to access constants if they are used in main)
# Trade class uses them internally, but we might need them for arguments.
from apps.mt5 import get_mt5_api
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
    print("Trade Example (CTrade Refactored)")
    print("=" * 70)
    print()

    # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client (needed for Option 1)
    client = MT5Client()
    connected = client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    if not connected:
        print("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return

    print(f"Connected successfully!")
    print()

    # ============================================================
    # CHOOSE YOUR OPTION
    # ============================================================

    # Option 1: Live Trading with MT5 (Default)
    use_simulator = False
    simulator = None

    trade = Trade()
    print("Using: MT5 Live Connection")

    # Option 2: Simulator (Uncomment to use)
    # use_simulator = True
    # sim_ticks = {
    #     "EURUSD": SymbolTickSimulator(bid=1.19645, ask=1.19645, last=1.19645),
    #     "GBPUSD": SymbolTickSimulator(bid=1.37736, ask=1.37738, last=1.37737),
    # }
    # sim_positions = {
    #     3001: PositionInfoSimulator(
    #         ticket=3001,
    #         symbol="EURUSD",
    #         type=getattr(mt5, "POSITION_TYPE_BUY", 0),
    #         volume=0.1,
    #         price_open=1.19645,
    #     ),
    # }
    # simulator = TradeSimulator(ticks_data=sim_ticks, positions_data=sim_positions)
    # trade = Trade(api=simulator)
    # print("Using: Simulator (Simulated Trade)")
    # print()

    # Configure trade settings
    trade.SetExpertMagicNumber(12345)
    trade.SetDeviationInPoints(10)

    # Detect and set the best filling mode for the symbol
    if trade.SetTypeFillingBySymbol("EURUSD"):
        print("Set filling mode for EURUSD from symbol settings")
    else:
        print("Using default filling mode for EURUSD")
    print()
    
    print("=" * 70)
    print("Example 1: Open Position")
    print("=" * 70)
    print()

    # Get current market prices
    if use_simulator and simulator:
        sim_symbol = simulator.symbol_info("EURUSD")
        symbol_info = sim_symbol if sim_symbol else None
    else:
        symbol_info = mt5.symbol_info("EURUSD")
    if not symbol_info:
        print("✗ Failed to get symbol info for EURUSD")
        return

    bid = symbol_info.bid
    ask = symbol_info.ask
    point = symbol_info.point

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
    if trade.PositionOpen(
        symbol="EURUSD",
        order_type=mt5.ORDER_TYPE_BUY,
        volume=0.1,
        price=buy_price,
        sl=sl_buy,
        tp=tp_buy,
        comment="Example buy order"
    ):
        print(f"✓ Position opened successfully!")
        print(f"  Order: #{trade.ResultOrder()}")
        print(f"  Deal: #{trade.ResultDeal()}")
        print(f"  Volume: {trade.ResultVolume()}")
        print(f"  Price: {trade.ResultPrice()}")
        print(f"  Comment: {trade.ResultComment()}")
    else:
        print(f"✗ Failed to open position")
        print(f"  Retcode: {trade.ResultRetcodeDescription()}")
        print(f"  Comment: {trade.ResultComment()}")
    
    print()
    print("=" * 70)
    print("Example 2: Modify Position")
    print("=" * 70)
    print()

    # Get updated prices
    if use_simulator and simulator:
        sim_symbol = simulator.symbol_info("EURUSD")
        symbol_info = sim_symbol if sim_symbol else None
    else:
        symbol_info = mt5.symbol_info("EURUSD")
    if symbol_info:
        current_bid = symbol_info.bid
        current_ask = symbol_info.ask

        # Adjust SL/TP: Move SL closer (30 points), extend TP (150 points)
        new_sl = current_ask - (30 * point)
        new_tp = current_ask + (150 * point)

        print(f"Modifying position with new SL/TP:")
        print(f"  New SL: {new_sl:.5f}")
        print(f"  New TP: {new_tp:.5f}")
        print()
    else:
        new_sl = 0.0
        new_tp = 0.0

    # Modify SL/TP
    if trade.PositionModify(
        symbol="EURUSD",
        sl=new_sl,
        tp=new_tp
    ):
        print(f"✓ Position modified successfully!")
        print(f"  New SL: {new_sl:.5f}")
        print(f"  New TP: {new_tp:.5f}")
    else:
        print(f"✗ Failed to modify position")
        print(f"  Retcode: {trade.ResultRetcodeDescription()}")
    
    print()
    print("=" * 70)
    print("Example 3: Close Position")
    print("=" * 70)
    print()
    
    # Close position
    if trade.PositionClose(symbol="EURUSD"):
        print(f"✓ Position closed successfully!")
        print(f"  Deal: #{trade.ResultDeal()}")
        print(f"  Volume: {trade.ResultVolume()}")
        print(f"  Price: {trade.ResultPrice()}")
    else:
        print(f"✗ Failed to close position")
        print(f"  Retcode: {trade.ResultRetcodeDescription()}")
    
    print()
    print("=" * 70)
    print("Example 4: Pending Order")
    print("=" * 70)
    print()

    # Get current GBPUSD prices for pending order
    if use_simulator and simulator:
        sim_symbol = simulator.symbol_info("GBPUSD")
        gbp_info = sim_symbol if sim_symbol else None
    else:
        gbp_info = mt5.symbol_info("GBPUSD")
    if not gbp_info:
        print("✗ Failed to get symbol info for GBPUSD")
    else:
        # Set filling mode for GBPUSD
        if trade.SetTypeFillingBySymbol("GBPUSD"):
            print("Set filling mode for GBPUSD from symbol settings")
        else:
            print("Using default filling mode for GBPUSD")

        gbp_bid = gbp_info.bid
        gbp_ask = gbp_info.ask
        gbp_point = gbp_info.point

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
    if gbp_info and trade.OrderOpen(
        symbol="GBPUSD",
        order_type=mt5.ORDER_TYPE_BUY_LIMIT,
        volume=0.05,
        price=limit_price,
        sl=sl_limit,
        tp=tp_limit,
        comment="Pending buy limit"
    ):
        print(f"✓ Pending order placed successfully!")
        print(f"  Order: #{trade.ResultOrder()}")
        print(f"  Price: {trade.RequestPrice()}")
        print(f"  Volume: {trade.RequestVolume()}")
    else:
        print(f"✗ Failed to place pending order")
        print(f"  Retcode: {trade.ResultRetcodeDescription()}")

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)

    # Shutdown MT5 connection
    print("\nShutting down MT5 connection...")
    client.shutdown()
    print("Disconnected.")


if __name__ == "__main__":
    main()


