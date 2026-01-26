"""
Positions get usage example.

Checks open positions in simulator (tester) and in MetaTrader 5 (live).
"""

import MetaTrader5 as mt5
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
        simulator_name="PositionsGetDemo",
        deposit=1000.0,
        leverage="1:100",
        db=db,
    )

    gateway = TradeGateway(sim)
    trade = gateway.get_trade(is_tester=True)
    print("positions total in the Simulator: ", sim.positions_total())
    print("positions in the Simulator:\n", sim.positions_get())

    trade = gateway.get_trade(is_tester=False)
    print("positions total in MetaTrader5: ", sim.positions_total())
    print("positions in MetaTraer5:\n", sim.positions_get())

    mt5.shutdown()


if __name__ == "__main__":
    main()
