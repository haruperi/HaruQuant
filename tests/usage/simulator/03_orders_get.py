"""
Orders get usage example.

Checks pending orders in simulator (tester) and in MetaTrader 5 (live).
"""

from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5
from apps.ctrade import CSymbolInfo
from apps.logger import logger
from apps.simulator import TradeGateway, TradeSimulator
from apps.sqlite import SQLiteDatabase


def main() -> None:
    if not mt5.initialize():
        logger.error("Failed to initialize MT5: %s", mt5.last_error())
        return

    db = SQLiteDatabase()
    db.initialize_database()
    sim = TradeSimulator(
        simulator_name="OrdersGetDemo",
        deposit=1000.0,
        leverage="1:100",
        db=db,
    )

    symbol_a = "GBPUSD"
    symbol_b = "EURUSD"
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=1)

    sym_a = CSymbolInfo(symbol_a)
    sym_a.Name(symbol_a)
    sym_a.Refresh()
    sym_a.RefreshRates()
    sym_b = CSymbolInfo(symbol_b)
    sym_b.Name(symbol_b)
    sym_b.Refresh()
    sym_b.RefreshRates()

    if not (sym_a.IsSynchronized() and sym_b.IsSynchronized()):
        logger.error("Failed to synchronize symbol data.")
        mt5.shutdown()
        return

    gateway = TradeGateway(sim)
    trade = gateway.get_trade(is_tester=True)
    trade.OrderOpen(
        symbol=symbol_a,
        order_type=mt5.ORDER_TYPE_BUY_LIMIT,
        volume=0.01,
        price=sym_a.Bid() - 10 * sym_a.PipSize(),
        sl=sym_a.Bid() - 20 * sym_a.PipSize(),
        tp=sym_a.Bid() + 20 * sym_a.PipSize(),
        expiration=expiry,
        comment="sim buy limit",
    )
    trade.OrderOpen(
        symbol=symbol_b,
        order_type=mt5.ORDER_TYPE_SELL_LIMIT,
        volume=0.01,
        price=sym_b.Ask() + 10 * sym_b.PipSize(),
        sl=sym_b.Ask() + 20 * sym_b.PipSize(),
        tp=sym_b.Ask() - 20 * sym_b.PipSize(),
        expiration=expiry,
        comment="sim sell limit",
    )

    print("Orders in the simulator:\n", sim.orders_get())

    trade = gateway.get_trade(is_tester=False)
    print("Orders in MetaTrader 5:\n", sim.orders_get())

    mt5.shutdown()


if __name__ == "__main__":
    main()
