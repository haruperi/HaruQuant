"""Strategy reproducibility helpers for manifest/version binding (IP-24)."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, TypedDict

from apps.contracts.schema_registry import RunManifestSchema, create_default_schema_registry


class StabilityMetadata(TypedDict, total=False):
    """Stability and sensitivity summary payload."""

    stability_score: float
    sensitivity: Dict[str, float]
    notes: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_config_hash(config: Mapping[str, Any]) -> str:
    """Compute deterministic config hash from key-sorted JSON-like repr."""
    # Keep implementation minimal and dependency-free.
    items = sorted((str(k), repr(v)) for k, v in config.items())
    raw = "|".join(f"{k}={v}" for k, v in items).encode("utf-8")
    return sha256(raw).hexdigest()


def build_run_manifest(
    *,
    run_id: str,
    strategy_name: str,
    strategy_version: str,
    environment: str,
    symbols: Iterable[str],
    timeframe: str,
    config_hash: str,
    code_version: Optional[str] = None,
    seed: Optional[int] = None,
    strategy_artifacts: Optional[Mapping[str, Any]] = None,
    model_artifacts: Optional[Mapping[str, Any]] = None,
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build run manifest payload and validate against canonical schema."""
    payload: Dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "strategy_name": strategy_name,
        "strategy_version": strategy_version,
        "started_at": started_at or _utc_now_iso(),
        "ended_at": ended_at,
        "environment": environment,
        "symbols": list(symbols),
        "timeframe": timeframe,
        "config_hash": config_hash,
        "code_version": code_version,
        "seed": seed,
        "strategy_artifacts": dict(strategy_artifacts or {}),
        "model_artifacts": dict(model_artifacts or {}),
    }
    # Canonical schema validation (extra fields allowed by schema).
    RunManifestSchema.model_validate(payload)
    return payload


def attach_stability_metadata(
    manifest: MutableMapping[str, Any],
    stability: StabilityMetadata,
) -> Dict[str, Any]:
    """Attach stability/sensitivity metadata to an existing manifest."""
    out = dict(manifest)
    out["stability"] = dict(stability)
    return out


def validate_manifest_payload(payload: Mapping[str, Any]) -> tuple[bool, str]:
    """Validate payload through registered run manifest schema."""
    registry = create_default_schema_registry()
    return registry.validate(
        name="storage.run_manifest",
        version="1.0",
        payload=dict(payload),
    )

