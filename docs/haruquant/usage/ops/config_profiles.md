# Configuration Profiles And Precedence

This guide describes profile loading, precedence, schema versioning, and runtime reload behavior.

## Supported Profiles

- `DEV`
- `BACKTEST`
- `PAPER`
- `LIVE`

Profile selection sources (highest to lowest priority):

1. Explicit `profile=` argument when calling loader/config class.
2. `HQT_PROFILE` environment variable.
3. Top-level `profile` key in config file.

## Precedence Rules

Effective config is built in this order:

1. Base file config (`.toml` preferred, `.json` supported)
2. Profile overlay from `profiles.<selected_profile>`
3. Environment overlay (`HQT_SECTION__KEY=value`)
4. Runtime overrides (dotted keys, for example `logging.level`)

## Schema Versioning

- Configs support `schema_version`.
- Current supported versions:
  - `1.0.0`
- Unsupported versions fail fast during config load.

If `schema_version` is missing, loader defaults it to `1.0.0` for compatibility.

## Self-Documenting Schema Metadata

Schema metadata is available through:

- `apps.live.config.get_schema_spec()`

Each documented key includes:

- `description`
- `safeguards`
- `units`

## Runtime Reloading (Non-Critical)

`Config.reload_non_critical()` reloads only non-critical parameters:

- `logging.level`
- safety/risk limits (`safety.*`)
- selected trading knobs (`trading.volume`, `trading.deviation`)

Use this to update operations controls without restarting runtime.

## Examples

### TOML profile overlays

```toml
schema_version = "1.0.0"
profile = "dev"

[logging]
dir = "backend/logs"
level = "INFO"

[profiles.dev.logging]
level = "DEBUG"

[profiles.live.logging]
level = "WARNING"
```

### Environment overlays

```bash
set HQT_PROFILE=LIVE
set HQT_LOGGING__LEVEL=ERROR
set HQT_TRADING__VOLUME=0.25
```

### Runtime overrides

```python
from apps.live.config import Config

cfg = Config("backend/config/live_trading_config.toml", profile="paper")
cfg.set_runtime_override("logging.level", "DEBUG")
cfg.set_runtime_override("safety.max_positions", 3)

changed = cfg.reload_non_critical()
print(changed)
```

