# Nanobind Module Layout (IP-18)

## Scope

Bridge module:
- `hqt_engine` (nanobind extension)

Skeleton submodules:
- `hqt_engine._event`
- `hqt_engine._data`
- `hqt_engine._risk`
- `hqt_engine._oms`
- `hqt_engine._execution`
- `hqt_engine._backtest`
- `hqt_engine._metrics`

Lifecycle hooks:
- `hqt_engine.initialize()`
- `hqt_engine.teardown()`
- `hqt_engine.health_check()`

## Quick Check

```python
import hqt_engine

assert hqt_engine.initialize() is True
print(hqt_engine.health_check())

for name in ["_event", "_data", "_risk", "_oms", "_execution", "_backtest", "_metrics"]:
    sub = getattr(hqt_engine, name)
    print(name, sub.health_check())

assert hqt_engine.teardown() is True
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
