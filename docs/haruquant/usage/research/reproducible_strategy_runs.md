# Reproducible Strategy Runs (IP-24)

Use strategy reproducibility helpers to build and validate a run manifest.

## Build manifest with version + artifact binding

```python
from apps.strategy import build_run_manifest, compute_config_hash, validate_manifest_payload

config = {"ema_fast": 20, "ema_slow": 50, "risk_per_trade": 0.01}
cfg_hash = compute_config_hash(config)

manifest = build_run_manifest(
    run_id="run-20260218-001",
    strategy_name="TrendFollowing",
    strategy_version="1.3.0",
    environment="backtest",
    symbols=["EURUSD", "GBPUSD"],
    timeframe="M15",
    config_hash=cfg_hash,
    code_version="git:abcdef1",
    seed=42,
    strategy_artifacts={"path": "backend/data/strategies/alice/trend_following/v1.3.0/strategy.py"},
    model_artifacts={"model_version": "none"},
)

ok, msg = validate_manifest_payload(manifest)
print(ok, msg)
```

## Attach stability/sensitivity metadata

```python
from apps.strategy import attach_stability_metadata

manifest = attach_stability_metadata(
    manifest,
    {
        "stability_score": 0.88,
        "sensitivity": {"ema_fast": 0.11, "ema_slow": 0.06},
        "notes": "stable under tested perturbations",
    },
)
```
