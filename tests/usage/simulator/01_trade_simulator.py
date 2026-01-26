"""
TradeSimulator usage example.

Demonstrates positions, pending orders, account monitoring, and realtime steps.
"""

import time
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5
from apps.ctrade import CSymbolInfo
from apps.logger import logger
from apps.ctrade import CTrade
from apps.simulator import TradeGateway, TradeSimulator
from apps.sqlite import SQLiteDatabase

magic_number = 123456
slippage = 10
symbol = "EURUSD"
sl_pips = 20
tp_pips = 40
pending_gap_pips = 5

def main() -> None:
    db = SQLiteDatabase()
    db.initialize_database()
    sim = TradeSimulator(
        simulator_name="Demo Simulator",
        deposit=1000.0,
        leverage="1:100",
        db=db,
    )

    if not mt5.initialize():
        logger.error(f"Failed to initialize MT5. Error: {mt5.last_error()}")
        return

    sim.set_magic_number(magic_number) # Set the simulator magic number
    sim.set_deviation_in_points(slippage) # Set the allowable slippage in points
    gateway = TradeGateway(sim)
    trade = gateway.get_trade(is_tester=True)
    trade.SetExpertMagicNumber(magic_number)
    trade.SetDeviationInPoints(slippage)

    def is_position_exists(position_type: str) -> bool:
        for pos in sim.get_positions():
            if (
                pos["magic"] == magic_number
                and pos["symbol"] == symbol
                and pos["type"] == position_type
            ):
                return True
        return False

    def close_positions(position_type: str) -> None:
        for pos in sim.get_positions():
            if (
                pos["magic"] == magic_number
                and pos["symbol"] == symbol
                and pos["type"] == position_type
            ):
                trade.PositionClose(pos["id"])

    m_symbol = CSymbolInfo(symbol)
    m_symbol.Name(symbol) # sets the symbol name for the class CSymbolInfo
    m_symbol.Refresh() # refreshes the symbol data
    m_symbol.RefreshRates() # refreshes the symbol rates
    pip = m_symbol.PipSize()

    if not m_symbol.IsSynchronized():
        logger.error("Failed to synchronize symbol data.")
        mt5.shutdown()
        return

    print("Starting simulator...")
    loop_count = 0

    def log_position(position: dict) -> None:
        time_value = position.get("time")
        if hasattr(time_value, "strftime"):
            formatted_time = time_value.strftime("%Y-%m-%d %H:%M:%S")
        else:
            formatted_time = str(time_value)
        logger.info(
            "Sim -> Ticket : {} | Symbol : {} | Time : {} | Type : {} | Volume : {} | SL : {} | TP : {} | Profit : {}".format(
                position["id"],
                position["symbol"],
                formatted_time,
                position["type"],
                position["volume"],
                position["sl"],
                position["tp"],
                position.get("profit", 0.0),
            )
        )

    while True:
        loop_count += 1
        sim.monitor_pending_orders()
        sim.monitor_positions(verbose=False)
        sim.monitor_account(verbose=False)
        
        # sim.run_toolbox_gui()  # Run the simulator toolbox GUI
        
        if m_symbol.RefreshRates() is None: # Get recent ticks data from MetaTrader5
            logger.error("failed to get recent ticks data")
            continue

        current_bid = m_symbol.Bid()
        current_ask = m_symbol.Ask()

        print(f"{symbol} Feed: {current_bid} / {current_ask}")
            
        if not is_position_exists("buy"): # open a buy trade in a simulator if it doesn't exist
            buy_ok = trade.Buy(
                volume=0.1,
                symbol=symbol,
                price=current_ask,
                sl=current_ask - sl_pips * pip,
                tp=current_ask + tp_pips * pip,
                comment="Demo buy",
            )
            if not buy_ok:
                logger.error(f"Buy failed: {sim.last_error}")
                return
            log_position(sim.get_positions()[-1])
        else:
            logger.info("Buy position already exists")
        
        close_positions("buy") # close all buy positions
        
        if not is_position_exists("sell"): # open a sell trade in a simulator if it doesn't exist
            sell_ok = trade.Sell(
                volume=0.1,
                symbol=symbol,
                price=current_bid,
                sl=current_bid + sl_pips * pip,
                tp=current_bid - tp_pips * pip,
                comment="Demo sell",
            )
            if not sell_ok:
                logger.error(f"Sell failed: {sim.last_error}")
                return
            log_position(sim.get_positions()[-1])
        else:
            logger.info("Sell position already exists")
        
        print(f"Loop count: {loop_count}")
        time.sleep(1) # sleep for one second    

    """    
    # Market Orders

    sim.buy(volume=0.1, symbol=symbol, price=m_symbol.Ask())
    sim.sell(volume=0.1, symbol=symbol, price=m_symbol.Bid())

    m_trade.buy(volume=0.1, symbol=symbol, price=m_symbol.Ask())
    m_trade.sell(volume=0.1, symbol=symbol, price=m_symbol.Bid())


    # Pending Orders

    expiry = datetime.now(tz=pytz.UTC) + timedelta(days=1)
    price_gap = 0.0005

    # Buy Stop: place above current ask
    sim.buy_stop(volume=0.1, symbol=symbol, price=m_symbol.Ask() + price_gap, sl=0.0, tp=0.0,
                comment="Buy Stop Example", expiry_date=expiry, expiration_mode="daily")

    m_trade.buy_stop(volume=0.1, symbol=symbol, price=m_symbol.Ask() + price_gap)

    # Buy Limit: place below current bid
    sim.buy_limit(volume=0.1, symbol=symbol, price=m_symbol.Bid() - price_gap, sl=0.0, tp=0.0,
                comment="Buy Limit Example", expiry_date=expiry, expiration_mode="daily_excluding_stops")

    m_trade.buy_limit(volume=0.1, symbol=symbol, price=m_symbol.Bid() - price_gap)

    # Sell Stop: place below current bid

    sim.sell_stop(volume=0.1, symbol=symbol, price=m_symbol.Bid() - price_gap, sl=0.0, tp=0.0,
                comment="Sell Stop Example", expiry_date=expiry, expiration_mode="gtc")

    m_trade.sell_stop(volume=0.1, symbol=symbol, price=m_symbol.Ask() - price_gap)

    # Sell Limit: place above current ask
    sim.sell_limit(volume=0.1, symbol=symbol, price=m_symbol.Ask() + price_gap, sl=0.0, tp=0.0,
                comment="Sell Limit Example", expiry_date=expiry, expiration_mode="gtc")

    m_trade.sell_limit(volume=0.1, symbol=symbol, price=m_symbol.Bid() + price_gap)

    while True: # constantly monitor trades and account metrics
        
        sim.monitor_pending_orders()
        sim.monitor_positions(verbose=False)
        sim.monitor_account(verbose=False)
        
        # sim.run_toolbox_gui()  # Run the simulator toolbox GUI
        
        time.sleep(1) # sleep for one second
    """



if __name__ == "__main__":
    main()
