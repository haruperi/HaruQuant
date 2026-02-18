# Risk Override Policy (IP-30)

This runbook defines role-bound risk overrides for live operations.

## Scope

`Config.apply_risk_override(...)` provides:
- restricted key allowlist (risk/safety only)
- mandatory reason
- live-profile authorization gate (superuser token)
- immutable audit event append (`risk_override`)

## Allowed Keys

- `safety.max_positions`
- `safety.max_daily_trades`
- `safety.min_balance`
- `safety.min_margin_level`

## API

```python
from apps.live.config import Config

cfg = Config("settings/live_config.json", profile="live")
cfg.apply_risk_override(
    "safety.max_positions",
    3,
    authorization_token="Bearer <session-token>",
    reason="Temporary risk reduction during abnormal volatility",
)
```

## Authorization Rules

In `live` profile:
- token must be valid
- actor must have superuser role

## Audit Trail

Each override writes a JSONL record with:
- `timestamp`
- `event` = `risk_override`
- `profile`
- `key`
- `reason`
- `user_id`
- `actor`
- `before`
- `after`

Default path:
- `artifacts/logs/security/secret_access_audit.json`

## Evidence

- `tests/security/test_risk_override_audit.py`
