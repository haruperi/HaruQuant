# Exception Mapping (IP-20)

This note shows how C++ bridge errors map into typed Python exceptions.

## Typed exceptions exported by `haruquant`

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
import haruquant

try:
    haruquant.raise_exception_for_retcode(10013, "invalid request")
except haruquant.OrderStateError as exc:
    print(type(exc).__name__, exc)
```

## Example: map by category

```python
import haruquant

try:
    haruquant.raise_exception_for_category("risk", "max exposure breached")
except haruquant.RiskViolationError as exc:
    print(type(exc).__name__, exc)
```

## Python adapter behavior

`apps/simulation/backend.py` preserves typed `haruquant.*Error` exceptions and only falls back to retcode-based translation when needed.
