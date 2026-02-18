# Execution Router Retry and Failure Policies (IP-35)

## Scope

IP-35 adds a C++ execution router with:

- final pre-send risk checks
- bounded retry policy for retryable failures
- order spam prevention rate limiting

## Core API (`hqt_engine.sim`)

- `ExecutionPolicy`
  - `max_retries`
  - `max_orders_per_window`
  - `rate_limit_window_ms`
  - `escalation_after_failures`
- `ExecutionRouter(broker, policy=ExecutionPolicy())`
  - `connect()`
  - `set_risk_account_state(equity, peak_equity, gross_exposure, net_exposure)`
  - `submit(request, candidate_gross_add=..., candidate_net_delta=..., margin_required=..., free_margin=..., live_mode=True)`
  - `cancel(order_id)`
  - `consecutive_failures()`
- `ExecutionRouteResult`
  - `result`, `attempts`, `retried`
  - `risk_blocked`, `rate_limited`
  - `escalated`, `escalation_reason`
  - `policy_code`, `reason`

## Example

```python
from hqt_engine import sim

client = sim.SimulatorClient()
broker = sim.MockBroker(client)

policy = sim.ExecutionPolicy()
policy.max_retries = 2
policy.max_orders_per_window = 5
policy.rate_limit_window_ms = 1000
policy.escalation_after_failures = 3

router = sim.ExecutionRouter(broker, policy)
router.connect()
router.set_risk_account_state(10000.0, 10000.0, 0.0, 0.0)

req = sim.TradeRequest()
req.action = 1
req.type = 0
req.symbol = "EURUSD"
req.volume = 0.1

out = router.submit(req)
print(out.policy_code, out.reason, out.result.retcode)
```

## Evidence

- `cpp/tests/test_execution_retry.cpp`
- `tests/integration/test_execution_escalation.py`

