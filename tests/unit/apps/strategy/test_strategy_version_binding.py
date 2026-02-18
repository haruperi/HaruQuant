from __future__ import annotations

from apps.strategy.repro import (
    attach_stability_metadata,
    build_run_manifest,
    compute_config_hash,
    validate_manifest_payload,
)


def test_compute_config_hash_is_deterministic() -> None:
    cfg_a = {"alpha": 1, "beta": 2}
    cfg_b = {"beta": 2, "alpha": 1}
    assert compute_config_hash(cfg_a) == compute_config_hash(cfg_b)


def test_build_run_manifest_binds_strategy_and_artifacts() -> None:
    payload = build_run_manifest(
        run_id="run-001",
        strategy_name="TrendFollowing",
        strategy_version="1.2.0",
        environment="backtest",
        symbols=["EURUSD"],
        timeframe="M15",
        config_hash="abc123",
        code_version="git:deadbeef",
        seed=42,
        strategy_artifacts={"path": "data/strategies/user/trend/v1.2.0/strategy.py"},
        model_artifacts={"model_version": "m1", "path": "models/m1.pkl"},
        started_at="2026-02-18T00:00:00Z",
    )
    assert payload["strategy_version"] == "1.2.0"
    assert payload["strategy_artifacts"]["path"].endswith("strategy.py")
    assert payload["model_artifacts"]["model_version"] == "m1"

    ok, msg = validate_manifest_payload(payload)
    assert ok is True
    assert msg == "ok"


def test_attach_stability_metadata() -> None:
    payload = build_run_manifest(
        run_id="run-002",
        strategy_name="MeanReversion",
        strategy_version="2.0.0",
        environment="research",
        symbols=["GBPUSD"],
        timeframe="H1",
        config_hash="def456",
        started_at="2026-02-18T00:00:00Z",
    )
    enriched = attach_stability_metadata(
        payload,
        {
            "stability_score": 0.87,
            "sensitivity": {"lookback": 0.12, "threshold": 0.08},
            "notes": "stable in tested window",
        },
    )
    assert enriched["stability"]["stability_score"] == 0.87
    assert enriched["stability"]["sensitivity"]["lookback"] == 0.12


def test_manifest_validation_fails_when_required_field_missing() -> None:
    bad = {
        "schema_version": "1.0",
        "run_id": "run-003",
        "strategy_name": "X",
        # missing strategy_version
        "started_at": "2026-02-18T00:00:00Z",
        "environment": "backtest",
        "symbols": ["EURUSD"],
        "timeframe": "M1",
        "config_hash": "zzz",
    }
    ok, msg = validate_manifest_payload(bad)
    assert ok is False
    assert "strategy_version" in msg
