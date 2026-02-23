# Nanobind Module Layout (IP-18)

## Scope

Bridge module:
- `haruquant` (nanobind extension)

Skeleton submodules:
- `haruquant._event`
- `haruquant._data`
- `haruquant._risk`
- `haruquant._oms`
- `haruquant._execution`
- `haruquant._backtest`
- `haruquant._metrics`

Lifecycle hooks:
- `haruquant.initialize()`
- `haruquant.teardown()`
- `haruquant.health_check()`

## Quick Check

```python
import haruquant

assert haruquant.initialize() is True
print(haruquant.health_check())

for name in ["_event", "_data", "_risk", "_oms", "_execution", "_backtest", "_metrics"]:
    sub = getattr(haruquant, name)
    print(name, sub.health_check())

assert haruquant.teardown() is True
```

Expected:
- module imports successfully
- lifecycle hooks return valid payloads
- all required skeleton submodules exist and report `ok=True`

## ASan Leak Check

CI leak verification runs:
- workflow: `.github/workflows/asan_leak_check.yml`
- stress script: `tests/contracts/asan_bridge_lifecycle_check.py`

The script repeatedly executes bridge lifecycle:
- `initialize()`
- `health_check()`
- `teardown()`

When run under ASan with leak detection enabled, any leak on shutdown fails the CI job.
