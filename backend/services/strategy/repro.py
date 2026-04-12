"""Deterministic strategy run manifest helpers."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping


REQUIRED_MANIFEST_FIELDS = {
    "strategy_id",
    "strategy_version",
    "config_hash",
    "created_at",
    "artifacts",
}


def compute_config_hash(config: Mapping[str, Any]) -> str:
    """Compute a deterministic sha256 hash for a strategy run configuration."""
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"


def build_run_manifest(
    *,
    strategy_id: str,
    strategy_version: str,
    config_hash: str,
    artifacts: Mapping[str, Any] | None = None,
    created_at: datetime | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a replayable strategy run manifest payload."""
    timestamp = created_at or datetime.now(timezone.utc)
    return {
        "schema": "strategy.run_manifest",
        "schema_version": "1.0",
        "strategy_id": str(strategy_id),
        "strategy_version": str(strategy_version),
        "config_hash": str(config_hash),
        "created_at": timestamp.isoformat(),
        "artifacts": dict(artifacts or {}),
        "metadata": dict(metadata or {}),
    }


def validate_manifest_payload(manifest: Mapping[str, Any]) -> tuple[bool, str]:
    """Validate the minimal replay fields expected on a strategy run manifest."""
    missing = sorted(field for field in REQUIRED_MANIFEST_FIELDS if field not in manifest)
    if missing:
        return False, f"missing required manifest fields: {', '.join(missing)}"
    if manifest.get("schema") not in {None, "strategy.run_manifest"}:
        return False, "unsupported manifest schema"
    if not str(manifest.get("config_hash", "")).startswith("sha256:"):
        return False, "config_hash must use sha256:<hex> format"
    if not isinstance(manifest.get("artifacts"), Mapping):
        return False, "artifacts must be a mapping"
    return True, "manifest is valid"


def attach_stability_metadata(
    manifest: Mapping[str, Any],
    *,
    stability: Mapping[str, Any],
    sensitivity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach stability/sensitivity evidence without mutating the source manifest."""
    updated = deepcopy(dict(manifest))
    metadata = dict(updated.get("metadata") or {})
    metadata["stability"] = dict(stability)
    if sensitivity is not None:
        metadata["sensitivity"] = dict(sensitivity)
    updated["metadata"] = metadata
    return updated
