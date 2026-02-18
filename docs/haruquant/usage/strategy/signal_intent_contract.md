# Signal Intent Contract (IP-23)

This usage note shows `StrategyAdapter` + `SignalRouter` with canonical `SignalIntent`.

```python
import pandas as pd

from apps.strategy import StrategyAdapter, SignalRouter
from my_strategy import MyStrategy

strategy = MyStrategy({"symbol": "EURUSD", "strategy_id": "trend-1"})
adapter = StrategyAdapter(strategy)
router = SignalRouter(handler=lambda intent: print("ROUTED", intent))

data = pd.DataFrame([...])  # OHLCV with datetime index
data = adapter.on_bar(data)
intent = adapter.build_signal_intent(data, len(data) - 1)
if intent:
    router.route(intent)
```

## Canonical `SignalIntent` fields

- `action`: `BUY | SELL | EXIT | REDUCE | HOLD`
- `qty`: position size
- `order_type`: `MARKET | LIMIT | STOP | STOP_LIMIT`
- `price`: optional limit/stop price
- `time_in_force`: `GTC | IOC | FOK | DAY`
- `strategy_id`, `symbol`
- explainability: `reason`, `features`, `confidence`, `tags`, `metadata`
