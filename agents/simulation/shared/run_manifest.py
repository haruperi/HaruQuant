"""Run manifest builders."""

from __future__ import annotations

from datetime import datetime, timezone

from agents._shared.persistence import stable_id

from .artifact_paths import artifact_root
from .constants import ANALYTICS_VERSION, ENGINE_VERSION
from .contracts import BacktestRunManifest, SimulationRequestPayload
from .reproducibility import stable_hash


def create_run_id(strategy_id: str, symbol: str) -> str:
    return stable_id("sim", f"{strategy_id}-{symbol}-{datetime.now(timezone.utc).isoformat()}")


def build_manifest(payload: SimulationRequestPayload, *, run_id: str, status: str) -> BacktestRunManifest:
    return BacktestRunManifest(
        run_id=run_id,
        strategy_id=payload.strategy_id,
        strategy_version=payload.strategy_version,
        strategy_code_hash=payload.strategy_code_hash,
        strategy_spec_id=payload.strategy_spec_id,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        data_start=payload.data_start,
        data_end=payload.data_end,
        data_hash=stable_hash(payload.historical_data or payload.symbol),
        config_hash=stable_hash(payload.model_dump(mode="json", exclude={"historical_data", "returns"})),
        engine_version=ENGINE_VERSION,
        analytics_version=ANALYTICS_VERSION,
        created_at=datetime.now(timezone.utc).isoformat(),
        artifact_root=artifact_root(run_id),
        status=status,
    )
