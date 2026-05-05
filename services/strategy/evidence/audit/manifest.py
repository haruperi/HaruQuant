"""Integrity manifest generation helpers."""

from __future__ import annotations

import hashlib

from backend_retiring.contracts.serialization import canonical_json_dumps


def generate_integrity_manifest(artifacts: dict[str, str]) -> dict[str, object]:
    """Generate a stable manifest from artifact-name to hash mappings."""

    manifest_entries = {
        name: artifact_hash
        for name, artifact_hash in sorted(artifacts.items())
    }
    manifest_hash = hashlib.sha256(
        canonical_json_dumps(manifest_entries).encode("utf-8")
    ).hexdigest()
    return {
        "algorithm": "sha256",
        "entries": manifest_entries,
        "manifest_hash": manifest_hash,
    }
