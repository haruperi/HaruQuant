from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from backend.services.strategy import (
    BaseStrategy,
    SignalRouter,
    StrategyAdapter,
    StrategyStorage,
    attach_stability_metadata,
    build_run_manifest,
    compute_config_hash,
    validate_manifest_payload,
)


class DemoStrategy(BaseStrategy):
    def on_init(self) -> None:
        self.state["initialized"] = True

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        out = data.copy()
        out["entry_signal"] = [0, 1]
        out["exit_signal"] = [0, 0]
        out["price"] = out["close"]
        return out


def test_base_strategy_helpers_and_signal_adapter() -> None:
    strategy = DemoStrategy({"symbol": "EURUSD", "strategy_id": "demo-1"})
    adapter = StrategyAdapter(strategy, default_qty=0.25)
    routed: list[dict[str, Any]] = []
    router = SignalRouter(handler=lambda intent: routed.append(dict(intent)))
    data = pd.DataFrame({"close": [1.1, 1.2]}, index=pd.date_range("2026-01-01", periods=2))

    enriched = adapter.on_bar(data)
    intent = adapter.build_signal_intent(enriched, 1, features={"close": 1.2})

    assert intent is not None
    assert intent["action"] == "BUY"
    assert intent["qty"] == 0.25
    assert intent["strategy_id"] == "demo-1"
    assert intent["symbol"] == "EURUSD"
    router.route(intent)
    assert routed[0]["action"] == "BUY"
    with pytest.raises(ValueError):
        router.route({**intent, "action": "INVALID"})  # type: ignore[typeddict-item]


def test_strategy_storage_roundtrip_loads_strategy_class(tmp_path: Path) -> None:
    storage = StrategyStorage(base_dir=str(tmp_path / "strategies"))
    code = """
from backend.services.strategy import BaseStrategy


class StoredDemoStrategy(BaseStrategy):
    def on_init(self):
        pass

    def on_bar(self, data):
        return data
"""

    saved = storage.save_strategy(
        user_id=1,
        strategy_id=7,
        version="1.0.0",
        code=code,
        parameters={"symbol": "EURUSD"},
        metadata={"source": "unit"},
        username="Test User",
        strategy_name="Stored Demo",
    )

    assert Path(saved).exists()
    assert storage.list_versions(username="Test User", strategy_name="Stored Demo") == ["1.0.0"]
    assert storage.load_strategy_code(1, 7, "1.0.0", "Test User", "Stored Demo") == code
    assert storage.load_strategy_metadata(1, 7, "1.0.0", "Test User", "Stored Demo")["source"] == "unit"
    assert storage.load_strategy_class(1, 7, "1.0.0", "Test User", "Stored Demo").__name__ == "StoredDemoStrategy"


def test_strategy_storage_export_import_roundtrip(tmp_path: Path) -> None:
    storage = StrategyStorage(base_dir=str(tmp_path / "src"))
    code = """
from backend.services.strategy import BaseStrategy


class ExportedStrategy(BaseStrategy):
    def on_init(self):
        pass

    def on_bar(self, data):
        return data
"""
    storage.save_strategy(1, 1, "1.0.0", code, username="User", strategy_name="Alpha")
    archive = storage.export_strategy(
        1,
        1,
        "1.0.0",
        str(tmp_path / "exports" / "alpha.zip"),
        username="User",
        strategy_name="Alpha",
    )
    assert zipfile.is_zipfile(archive)

    imported = StrategyStorage(base_dir=str(tmp_path / "dst"))
    imported_path = imported.import_strategy(
        1,
        2,
        "1.0.0",
        archive,
        username="User",
        strategy_name="Alpha Imported",
    )
    assert Path(imported_path).exists()


def test_reproducible_strategy_manifest_helpers() -> None:
    config_hash = compute_config_hash({"symbol": "EURUSD", "params": {"fast": 20}})
    manifest = build_run_manifest(
        strategy_id="trend-1",
        strategy_version="1.0.0",
        config_hash=config_hash,
        artifacts={"equity": "equity.csv"},
    )
    ok, reason = validate_manifest_payload(manifest)
    enriched = attach_stability_metadata(
        manifest,
        stability={"stability_score": 0.91},
        sensitivity={"fast": "low"},
    )

    assert config_hash == compute_config_hash({"params": {"fast": 20}, "symbol": "EURUSD"})
    assert ok is True, reason
    assert enriched["metadata"]["stability"]["stability_score"] == 0.91
    assert enriched["metadata"]["sensitivity"]["fast"] == "low"
    assert "stability" not in manifest["metadata"]


def test_manifest_validation_rejects_missing_fields() -> None:
    ok, reason = validate_manifest_payload({"strategy_id": "x"})

    assert ok is False
    assert "missing required manifest fields" in reason
