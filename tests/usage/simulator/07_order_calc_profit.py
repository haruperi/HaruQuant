"""
Order calc profit usage example.
"""

import MetaTrader5 as mt5
from apps.ctrade import CSymbolInfo
from apps.logger import logger
from apps.simulator import TradeGateway, TradeSimulator
from apps.sqlite import SQLiteDatabase


def main() -> None:
    symbol = "EURUSD"

    if not mt5.initialize():
        logger.error("Failed to initialize MT5: %s", mt5.last_error())
        return

    db = SQLiteDatabase()
    db.initialize_database()
    sim = TradeSimulator(
        simulator_name="ProfitCalcDemo",
        deposit=1000.0,
        leverage="1:100",
        db=db,
    )

    positions = mt5.positions_get()
    if not positions:
        logger.warning("No open MT5 positions to calculate profit from.")
        mt5.shutdown()
        return

    first_pos = positions[0]
    symbol = first_pos.symbol
    action = first_pos.type
    volume = float(first_pos.volume)
    price_open = float(first_pos.price_open)

    info = CSymbolInfo(symbol)
    info.Name(symbol)
    info.Refresh()
    info.RefreshRates()
    if not info.IsSynchronized():
        logger.error("Failed to synchronize symbol data.")
        mt5.shutdown()
        return

    current_tick = {
        "bid": info.Bid(),
        "ask": info.Ask(),
    }

    gateway = TradeGateway(sim)
    trade = gateway.get_trade(is_tester=True)
    sim.symbol_info(symbol)
    sim.update_tick(symbol, current_tick)
    sim.positions_container.clear()
    trade.PositionOpen(
        symbol=symbol,
        order_type=mt5.ORDER_TYPE_BUY
        if action == mt5.POSITION_TYPE_BUY
        else mt5.ORDER_TYPE_SELL,
        volume=volume,
        price=price_open,
        comment="demo mirror",
    )
    sim.monitor_positions(verbose=False)
    print("Simulator profit caclulate: ", round(sim.positions_profit_total(), 2))

    trade = gateway.get_trade(is_tester=False)
    print("MT5 profit caclulate: ", round(sim.positions_profit_total(), 2))

    mt5.shutdown()


if __name__ == "__main__":
    main()
