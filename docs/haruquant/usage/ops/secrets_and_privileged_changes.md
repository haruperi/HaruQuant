# Secrets and Privileged Config Changes (IP-05)

## Scope

This runbook covers:
- OS keyring-backed secret references in live config (`FR-CONF-009`).
- Privileged live config mutation with authorization + audit (`FR-CONF-006`).
- C++ configurable connection pooling primitive (`FR-CONF-010`).

## 1) Keyring Secret References

Use `keyring://<service>/<account>` for secret fields in config files.

Example:

```json
{
  "mt5": {
    "login": 123456,
    "password": "keyring://hqt/mt5_live_password",
    "server": "MetaQuotes-Demo"
  }
}
```

At load time, `apps/live/config.py` resolves this using `apps/live/secrets.py`.

## 2) Privileged Live Mutation

Use `Config.apply_privileged_mutation(...)` for runtime updates in `LIVE` profile.

```python
from apps.live.config import Config

cfg = Config("settings/live_config.json", profile="live")
cfg.apply_privileged_mutation(
    "logging.level",
    "ERROR",
    authorization_token="Bearer <session-token>",
    reason="Incident mitigation",
)
```

Rules:
- Allowed keys are a restricted allowlist of non-critical runtime knobs.
- For `live` profile:
  - token must be valid
  - actor must be superuser
- Every mutation appends an audit event JSON line to:
  - `artifacts/logs/security/secret_access_audit.json`

## 3) C++ Connection Pool Primitive

The C++ core includes a configurable pool-concurrency primitive:

- Header: `cpp/include/util/connection_pool.hpp`
- Impl: `cpp/src/engine/connection_pool.cpp`

Config fields:
- `pool_size`
- `max_overflow`
- `acquire_timeout`

Behavior:
- Acquires up to `pool_size + max_overflow`.
- Waits up to `acquire_timeout`.
- Uses RAII lease release on scope exit.

