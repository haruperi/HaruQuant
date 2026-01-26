"""
Bars/Ticks tester-mode usage example.

Demonstrates storing MT5 data to disk and using tester-mode overloads.
"""

from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5
from apps.logger import logger
from apps.simulator import TradeGateway, TradeSimulator
from apps.simulator.market_data import MarketDataStore
from apps.sqlite import SQLiteDatabase


def main() -> None:
    symbol = "EURUSD"
    timeframe = mt5.TIMEFRAME_M1

    if not mt5.initialize():
        logger.error("Failed to initialize MT5: %s", mt5.last_error())
        return

    data_store = MarketDataStore()
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=60)

    logger.info("Fetching bars and ticks for storage (2 months)...")
    data_store.fetch_bars_range(symbol, timeframe, start_time, end_time)
    data_store.fetch_ticks_range(symbol, start_time, end_time, mt5.COPY_TICKS_ALL)

    db = SQLiteDatabase()
    db.initialize_database()
    sim = TradeSimulator(
        simulator_name="BarsTicksTester",
        deposit=1000.0,
        leverage="1:100",
        db=db,
        data_store=data_store,
    )
    gateway = TradeGateway(sim)
    trade = gateway.get_trade(is_tester=True)
    sim.symbol_info(symbol)

    tester_ticks = data_store.read_ticks_range(symbol, start_time, end_time)
    if not tester_ticks:
        logger.warning("No ticks available for tester run.")
        mt5.shutdown()
        return

    def format_tick_sample(rows: list[dict]) -> str:
        if len(rows) <= 6:
            return f"{rows}"
        head = rows[:3]
        tail = rows[-3:]
        return f"{head}\n ...\n {tail}"

    print("is_tester=true")
    print(format_tick_sample(tester_ticks))

    trade = gateway.get_trade(is_tester=False)
    live_ticks = sim.copy_ticks_range(
        symbol, start_time, end_time, mt5.COPY_TICKS_ALL
    )
    print("is_tester=false")
    print(format_tick_sample(live_ticks))

    mt5.shutdown()


if __name__ == "__main__":
    main()
