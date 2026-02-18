# Vectorized Backtest Runner (IP-38)

## Scope

IP-38 adds a C++ `VectorizedBacktestEngine` for batch-style bar processing with deterministic outputs.

## Core API (`hqt_engine.sim`)

- `VectorizedBacktestEngine(client)`
- `run(symbol, volume, bars)`
- `processed_bars()`
- `total_trades()`
- `account_snapshot()`

## Example

```python
from hqt_engine import sim

client = sim.TradeSimulator()
info = sim.SymbolInfoData()
info.symbol = "EURUSD"
client.set_symbol_info(info)

bars = []
for i in range(5):
    b = sim.BacktestBarStep()
    b.time_msc = (i + 1) * 1000
    b.close = 1.1000 + i * 0.0001
    if i == 0:
        b.entry_signal = 1
    if i == 2:
        b.exit_signal = 1
    bars.append(b)

engine = sim.VectorizedBacktestEngine(client)
engine.run("EURUSD", 0.1, bars)
print(engine.processed_bars(), engine.total_trades(), engine.account_snapshot().balance)
```

## Evidence

- `cpp/tests/test_backtest_vectorized.cpp`
- `tests/parity/test_event_vs_vectorized_parity.py`


