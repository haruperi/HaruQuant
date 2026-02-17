# Exception Mapping (IP-20)

This note shows how C++ bridge errors map into typed Python exceptions.

## Typed exceptions exported by `hqt_engine`

- `BridgeError`
- `ConfigurationError`
- `ValidationError`
- `RiskViolationError`
- `OrderStateError`
- `ExecutionError`
- `TransientConnectivityError`
- `FatalEngineError`

## Example: map by retcode

```python
import hqt_engine

try:
    hqt_engine.raise_exception_for_retcode(10013, "invalid request")
except hqt_engine.OrderStateError as exc:
    print(type(exc).__name__, exc)
```

## Example: map by category

```python
import hqt_engine

try:
    hqt_engine.raise_exception_for_category("risk", "max exposure breached")
except hqt_engine.RiskViolationError as exc:
    print(type(exc).__name__, exc)
```

## Python adapter behavior

`apps/simulation/backend.py` preserves typed `hqt_engine.*Error` exceptions and only falls back to retcode-based translation when needed.
