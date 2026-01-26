"""
History orders total usage example.
"""

from datetime import datetime, timedelta, timezone

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
        simulator_name="HistoryOrdersDemo",
        deposit=1000.0,
        leverage="1:100",
        db=db,
    )

    date_to = datetime.now(timezone.utc)
    date_from = date_to - timedelta(days=1)

    gateway = TradeGateway(sim)
    trade = gateway.get_trade(is_tester=True)
    print(sim.history_orders_total(date_from=date_from, date_to=date_to))

    trade = gateway.get_trade(is_tester=False)
    print(sim.history_orders_total(date_from=date_from, date_to=date_to))

    mt5.shutdown()


if __name__ == "__main__":
    main()
