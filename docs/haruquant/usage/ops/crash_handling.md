# Crash Handling (FR-UTIL-009)

This runbook covers crash-time log flushing and state persistence.

## Install once at process startup

```python
from apps.utils.crash_handler import install_crash_handler

def state_provider() -> dict:
    return {"run_id": "live-2026-02-17", "mode": "LIVE"}

install_crash_handler(state_provider=state_provider)
```

## What happens on crash paths

- Captures uncaught exceptions via `sys.excepthook`.
- Enables `faulthandler` output to `artifacts/logs/crash/faulthandler.log`.
- Handles `SIGTERM`, `SIGINT`, `SIGABRT` (best-effort).
- Flushes Python logger sinks via `apps.utils.logger.logger.flush()`.
- Flushes C++ async logger via `haruquant.flush_logs()` when bridge is present.
- Appends crash payload to `artifacts/logs/crash/crash_state.json`.
