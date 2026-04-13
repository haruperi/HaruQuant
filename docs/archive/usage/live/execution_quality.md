# Execution Quality (IP-36)

## Scope

IP-36 adds:

- TWAP and VWAP execution schedules
- partial-fill modeling and tracking
- latency/slippage/spread quality metrics (including p99 latency)

## Core API (`haruquant.sim`)

- `ExecutionAlgoTWAP.build_schedule(total_volume, start_time_ms, end_time_ms, slices)`
- `ExecutionAlgoVWAP.build_schedule(total_volume, start_time_ms, end_time_ms, market_volume_profile)`
- `ExecutionRouter.submit(...)` returning `ExecutionRouteResult`
- `ExecutionRouter.quality_summary()` returning:
  - `samples`
  - `partial_fill_count`, `partial_fill_rate`
  - `avg_slippage`, `avg_spread`
  - `avg_latency_ms`, `p99_latency_ms`

## Example

```python
from haruquant import sim

twap = sim.ExecutionAlgoTWAP.build_schedule(1.0, 0, 3000, 4)
vwap = sim.ExecutionAlgoVWAP.build_schedule(1.0, 0, 3000, [1, 2, 3, 4])

client = sim.TradeSimulator()
broker = sim.MockBroker(client)
broker.set_partial_fill_ratio(0.5)

router = sim.ExecutionRouter(broker)
router.connect()
router.set_risk_account_state(10000.0, 10000.0, 0.0, 0.0)

req = sim.TradeRequest()
req.action = 1
req.type = 0
req.symbol = "EURUSD"
req.volume = 1.0
out = router.submit(req)

summary = router.quality_summary()
print(out.result.retcode, summary.partial_fill_rate, summary.p99_latency_ms)
```

## Evidence

- `cpp/tests/test_twap_vwap.cpp`
- `tests/integration/test_partial_fills.py`


