# Strategy Adapter Latency (IP-23)

Date: 2026-02-18
Environment: local Python runtime

## Benchmark snippet

```python
import timeit
import pandas as pd
from apps.strategy.adapter import StrategyAdapter
from my_strategy import MyStrategy

strategy = MyStrategy({"symbol": "EURUSD", "strategy_id": "bench-1"})
adapter = StrategyAdapter(strategy)
df = pd.DataFrame([{"close": 1.1}, {"close": 1.2}])
df = adapter.on_bar(df)

n = 100_000
lat_us = timeit.timeit(
    "adapter.build_signal_intent(df, len(df)-1)",
    number=n,
    globals=globals(),
) / n * 1e6
print(lat_us)
```

## Notes

- This benchmark targets adapter normalization overhead only.
- Router overhead is validation + function dispatch and is expected to be small relative to strategy execution.
