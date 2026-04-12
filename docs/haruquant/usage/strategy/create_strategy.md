# Create Strategy (IP-22)

Use `BaseStrategy` and implement `on_init()` + `on_bar()`.
Optional lifecycle hooks are available for runtime events.

```python
import pandas as pd
from backend.services.strategy import BaseStrategy


class SimpleStrategy(BaseStrategy):
    def on_init(self) -> None:
        self.state["initialized"] = True

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.copy()
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data.loc[data.index[-1], "entry_signal"] = 1
        data.loc[data.index[-1], "price"] = float(data.iloc[-1]["close"])
        return data

    def on_trade(self, event) -> None:
        self.state["last_trade_event"] = event["event_id"]
```

## Optional hooks

- `on_tick(data)`
- `on_trade(event)`
- `on_order_update(event)`
- `on_timer(event)`
- `on_shutdown(event=None)`

## Canonical event keys (`StrategyEvent`)

- `event_id`
- `event_type`
- `symbol`
- `strategy_id`
- `event_ts`
- `recv_ts`
- `payload`
- `run_id`
- `trace_id`
- `correlation_id`
