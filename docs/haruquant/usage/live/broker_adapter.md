# Broker Adapter and Mock Broker (IP-34)

## Scope

IP-34 introduces a standardized broker abstraction in C++ and a deterministic mock implementation:

- `BrokerAdapter` interface (`connect`, `submit`, `cancel`, `fetch_state`)
- `MockBroker` deterministic adapter for test/backtest execution flows
- `PaperTradingEngine` wrapper that routes orders through a broker adapter

## Core API (`hqt_engine.sim`)

- `MockBroker(client: SimulatorClient)`
- `MockBroker.connect()`
- `MockBroker.submit(request)`
- `MockBroker.cancel(order_id)`
- `MockBroker.fetch_state()`
- `MockBroker.set_partial_fill_ratio(ratio)`
- `MockBroker.set_deterministic_price(price)`
- `PaperTradingEngine(broker: MockBroker)`
- `PaperTradingEngine.connect()`
- `PaperTradingEngine.submit_order(request)`
- `PaperTradingEngine.cancel_order(order_id)`
- `PaperTradingEngine.snapshot_state()`

## Determinism Controls

- `set_partial_fill_ratio(ratio)`:
  - scales submitted volume by fixed ratio in `[0, 1]`
- `set_deterministic_price(price)`:
  - overrides request price with fixed deterministic price

## Example

```python
from hqt_engine import sim

client = sim.SimulatorClient()
broker = sim.MockBroker(client)
broker.connect()
broker.set_partial_fill_ratio(0.5)
broker.set_deterministic_price(1.2000)

engine = sim.PaperTradingEngine(broker)
engine.connect()

req = sim.TradeRequest()
req.action = 1
req.type = 0
req.symbol = "EURUSD"
req.volume = 1.0
result = engine.submit_order(req)
state = engine.snapshot_state()
```

## Evidence

- `cpp/tests/test_broker_adapter_interface.cpp`
- `tests/integration/test_mock_broker.py`

