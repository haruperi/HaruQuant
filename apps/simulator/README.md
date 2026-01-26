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

## Core Class
`TradeSimulator` lives in `apps/simulator/engine.py`.

## Usage Example
```python
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

## Notes
- If MT5 is available, the simulator uses `order_calc_profit` and
  `order_calc_margin` for more accurate calculations.
- If MT5 is not available, it falls back to tick value or contract size math
  using the symbol snapshot.
- Deals can be stored in the shared SQLite database by passing `db=SQLiteDatabase()`.
- Provide `toolbox_callback` to integrate a UI or external monitor.
