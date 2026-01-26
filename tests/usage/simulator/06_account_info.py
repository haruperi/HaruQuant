"""
Account info usage example.
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
        simulator_name="AccountInfoDemo",
        deposit=1078.3,
        leverage="1:200",
        db=db,
    )

    gateway = TradeGateway(sim)
    trade = gateway.get_trade(is_tester=True)
    print("simulator's account info: ", sim.account_info())

    trade = gateway.get_trade(is_tester=False)
    print("MetaTrader5's account info: ", sim.account_info())

    mt5.shutdown()


if __name__ == "__main__":
    main()
