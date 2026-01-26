"""
Order calc margin usage example.
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

    sim = TradeSimulator(
        simulator_name="MarginCalcDemo",
        deposit=1000,
        leverage="1:50",
        db=db,
    )

    info = CSymbolInfo(symbol)
    info.Name(symbol)
    info.Refresh()
    info.RefreshRates()
    if not info.IsSynchronized():
        logger.error("Failed to synchronize symbol data.")
        mt5.shutdown()
        return

    price = info.Ask()

    positions = mt5.positions_get()
    if not positions:
        logger.warning("No open MT5 positions to calculate margin from.")
        mt5.shutdown()
        return

    gateway = TradeGateway(sim)
    trade = gateway.get_trade(is_tester=True)
    sim.positions_container.clear()
    for pos in positions:
        symbol = pos.symbol
        info = CSymbolInfo(symbol)
        info.Name(symbol)
        info.Refresh()
        info.RefreshRates()
        if not info.IsSynchronized():
            logger.error("Failed to synchronize symbol data for %s.", symbol)
            continue
        sim.symbol_info(symbol)
        sim.update_tick(symbol, {"bid": info.Bid(), "ask": info.Ask()})
        opened = trade.PositionOpen(
            symbol=symbol,
            order_type=mt5.ORDER_TYPE_BUY
            if pos.type == mt5.POSITION_TYPE_BUY
            else mt5.ORDER_TYPE_SELL,
            volume=float(pos.volume),
            price=float(pos.price_open),
            comment="demo mirror",
        )
        if not opened:
            logger.warning("Simulator failed to mirror position for %s.", symbol)
    sim.monitor_positions(verbose=False)
    #print("Simulator positions:\n", sim.positions_get())
    print("Simulator margin caclulate: ", round(sim.positions_margin_total(), 2))
    sim.monitor_account(verbose=False)
    sim_account = sim.account_info()
    print("Simulator free margin: ", round(sim_account.margin_free, 2))
    print("Simulator margin level: ", round(sim_account.margin_level, 2))

    trade = gateway.get_trade(is_tester=False)
    print("MT5 margin caclulate: ", round(sim.positions_margin_total(), 2))
    mt5_account = sim.account_info()
    print("MT5 free margin: ", round(mt5_account.margin_free, 2))
    print("MT5 margin level: ", round(mt5_account.margin_level, 2))

    mt5.shutdown()


if __name__ == "__main__":
    main()
