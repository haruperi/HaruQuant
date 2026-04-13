# Schema Registry (IP-12)

## Scope

Implemented in:
- `apps/contracts/schema_registry.py`

Includes:
- versioned in-memory schema registry
- backward compatibility checks for schema evolution
- canonical contracts for events/API/storage payloads
- run manifest and run report schema validation

## Built-In Contracts

- `event.tick:1.0`
- `event.bar:1.0`
- `api.order:1.0`
- `api.fill:1.0`
- `storage.position:1.0`
- `storage.run_manifest:1.0`
- `storage.run_report:1.0`

## Basic Usage

```python
from apps.contracts.schema_registry import create_default_schema_registry

registry = create_default_schema_registry()

ok, msg = registry.validate(
    name="event.tick",
    version="1.0",
    payload={
        "provider": "mt5_ea",
        "schema_version": "1.0",
        "symbol": "EURUSD",
        "timestamp": "2026-02-17T12:00:00Z",
        "bid": 1.1000,
        "ask": 1.1002,
        "volume": 100.0,
    },
)
print(ok, msg)  # True, "ok"
```

Runnable usage script:

```bash
python tests/usage/utils/usage_schema_registry.py
```

## Register New Version With Compatibility Guard

```python
from apps.contracts.schema_registry import SchemaRegistry, TickMessage

registry = SchemaRegistry()
registry.register(name="event.tick", version="1.0", model=TickMessage)

class TickV11(TickMessage):
    schema_version: str = "1.1"
    venue: str | None = None  # additive optional field

registry.register(
    name="event.tick",
    version="1.1",
    model=TickV11,
    enforce_backward_compat_with="1.0",
)
```

Compatibility rules (conservative):
- old fields cannot be removed
- optional old fields cannot become required
- field type changes are rejected
