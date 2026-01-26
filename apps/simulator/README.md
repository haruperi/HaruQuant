# Trade Simulator

MT5-aligned local trade simulator built on `apps/ctrade` conventions. It models
positions, calculates P/L, validates trade parameters, modifies stops, and
monitors positions without sending real orders.

## What It Covers
- Trading Simulator 101: positions, orders, deals containers
- Calculating P/L by position (MT5 `order_calc_profit` when available)
- Simulating a position (open buy/sell)
- Trade validations (volume, step, SL/TP distance and direction)
- Modifying positions (SL/TP)
- Monitoring positions (update price, auto-close on SL/TP)
- Market pending orders (buy/sell stop/limit)
- Deleting and modifying pending orders
- Monitoring pending orders (trigger or expire)
- Monitoring the account (equity, margin, free margin)
- Realtime simulation step helper
- Optional GUI/toolbox callback hook
- Tester-mode MT5 overloads (ticks, bars, orders/positions history)
- Market data storage for bars/ticks (monthly parquet)
- MT5-like order_send handling with request/check/result tracking
- MT5-like tester runner with modelling modes (real ticks, simulated ticks, new bar, 1-minute OHLC)

## Core Class
`TradeSimulator` lives in `apps/simulator/engine.py`.
Market data storage lives in `apps/simulator/market_data.py`.
CTrade wrapper lives in `apps/ctrade/ctrade.py` and can be used with the simulator API.
Use `TradeGateway` to obtain a single entry point for live vs simulator trading.
Tester runner lives in `apps/simulator/tester.py`.

## Usage Example
```python
import MetaTrader5 as mt5

from apps.simulator import TradeSimulator

from apps.sqlite import SQLiteDatabase

db = SQLiteDatabase()
db.initialize_database()

sim = TradeSimulator(
    name="Demo",
    deposit=1000.0,
    leverage="1:100",
    db=db,
)

sim.set_magic_number(123456)
sim.set_deviation_in_points(10)

position = sim.open_position(
    action="buy",
    symbol="EURUSD",
    volume=0.1,
    price=1.1000,
    sl=1.0980,
    tp=1.1020,
    comment="demo",
)

price_feed = {"EURUSD": {"bid": 1.1010, "ask": 1.1012}}
sim.monitor_positions(price_feed=price_feed)

sim.modify_position(position_id=position["id"], sl=1.0990, tp=1.1025)

pending = sim.buy_stop(
    volume=0.1,
    symbol="EURUSD",
    open_price=1.1030,
    sl=1.1010,
    tp=1.1050,
    expiration_mode="daily",
)

sim.monitor_pending_orders(price_feed=price_feed)
sim.monitor_account(verbose=True)
sim.realtime_step(price_feed=price_feed)

if pending:
    sim.modify_order(pending["id"], open_price=1.1028, sl=1.1012, tp=1.1052)
    sim.delete_order(pending["id"])
```

## Tester Mode (Bars/Ticks)
```python
from datetime import datetime, timedelta, timezone

from apps.simulator import TradeSimulator
from apps.simulator.market_data import MarketDataStore

store = MarketDataStore()
start = datetime.now(timezone.utc) - timedelta(hours=1)
end = datetime.now(timezone.utc)

store.fetch_bars_range("EURUSD", mt5.TIMEFRAME_M1, start, end)
store.fetch_ticks_range("EURUSD", start, end, mt5.COPY_TICKS_ALL)

sim = TradeSimulator(simulator_name="Tester", data_store=store)
sim.start(is_tester=True)
sim.symbol_info("EURUSD")

ticks = store.read_ticks_range("EURUSD", start, end)
for tick in ticks[:10]:
    sim.update_tick("EURUSD", tick)
    bars = sim.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_M1, 0, 5)
    print(len(bars))
```

## Notes
- If MT5 is available, the simulator uses `order_calc_profit` and
  `order_calc_margin` for more accurate calculations.
- If MT5 is not available, it falls back to tick value or contract size math
  using the symbol snapshot.
- Deals can be stored in the shared SQLite database by passing `db=SQLiteDatabase()`.
- Provide `toolbox_callback` to integrate a UI or external monitor.
