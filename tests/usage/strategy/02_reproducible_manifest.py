"""Usage example: strategy run manifest version binding + reproducibility metadata."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow direct execution from repository root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.strategy import (  # noqa: E402
    attach_stability_metadata,
    build_run_manifest,
    compute_config_hash,
    validate_manifest_payload,
)


def main() -> None:
    config = {"ema_fast": 20, "ema_slow": 50, "risk_per_trade": 0.01}
    cfg_hash = compute_config_hash(config)

    manifest = build_run_manifest(
        run_id="run-20260218-usage",
        strategy_name="TrendFollowing",
        strategy_version="1.3.0",
        environment="backtest",
        symbols=["EURUSD"],
        timeframe="M15",
        config_hash=cfg_hash,
        code_version="git:abcdef1",
        seed=42,
        strategy_artifacts={"path": "data/strategies/user/trend_following/v1.3.0/strategy.py"},
        model_artifacts={"model_version": "none"},
        started_at="2026-02-18T00:00:00Z",
    )
    manifest = attach_stability_metadata(
        manifest,
        {
            "stability_score": 0.89,
            "sensitivity": {"ema_fast": 0.10, "ema_slow": 0.07},
            "notes": "stable under sampled perturbations",
        },
    )

    ok, msg = validate_manifest_payload(manifest)
    print("schema validation:", ok, msg)
    print(json.dumps(manifest, indent=2, default=str))

    out = Path("artifacts/logs/repro/sample_manifest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    print(f"wrote: {out}")


if __name__ == "__main__":
    main()
