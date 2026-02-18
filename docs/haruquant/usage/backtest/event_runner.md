# Event-Driven Backtest Runner (IP-37)

## Scope

IP-37 uses the C++ `BacktestEngine` as the deterministic event runner with OMS path through `TradeSimulator`.

Lifecycle hooks now available:

- `on_bar`
- `on_tick`
- `on_trade`

## Core API (`hqt_engine.sim`)

- `BacktestEngine.run_trading_timeframe(symbol, volume, bars)`
- `BacktestEngine.run_trading_timeframe_with_ticks(symbol, volume, bars, ticks)`
- `BacktestEngine.set_on_bar_processed(callback)`
- `BacktestEngine.set_on_tick_processed(callback)`
- `BacktestEngine.set_on_trade_event(callback)`

## Example

```python
from hqt_engine import sim

client = sim.TradeSimulator()
info = sim.SymbolInfo()
info.symbol = "EURUSD"
client.set_symbol_info(info)

engine = sim.BacktestEngine(client)
engine.set_on_bar_processed(lambda i, b, s: print("bar", i, b.time_msc))
engine.set_on_tick_processed(lambda t, s: print("tick", t.time_msc))
engine.set_on_trade_event(lambda e, s: print("trade", e.event_type, e.trade.ticket))

bars = []
for i in range(3):
    b = sim.BacktestBarStep()
    b.time_msc = (i + 1) * 1000
    b.close = 1.1000 + i * 0.0001
    if i == 0:
        b.entry_signal = 1
    if i == 2:
        b.exit_signal = 1
    bars.append(b)

engine.run_trading_timeframe("EURUSD", 0.1, bars)
```

## Evidence

- `cpp/tests/test_backtest_event_runner.cpp`
- `tests/e2e/test_backtest_event_path.py`



