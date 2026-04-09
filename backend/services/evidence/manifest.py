"""Evidence bundle content manifest helpers."""

from __future__ import annotations

from dataclasses import dataclass

from backend.contracts.serialization import canonical_json_dumps


@dataclass(frozen=True)
class EvidenceArtifact:
    artifact_type: str
    artifact_ref: str
    artifact_hash: str


def build_evidence_bundle_manifest(
    *,
    bundle_type: str,
    strategy_id: str,
    lifecycle_state: str,
    artifacts: tuple[EvidenceArtifact, ...],
) -> dict[str, object]:
    """Build a stable manifest for one evidence bundle."""

    manifest_artifacts = [
        {
            "artifact_type": artifact.artifact_type,
            "artifact_ref": artifact.artifact_ref,
            "artifact_hash": artifact.artifact_hash,
        }
        for artifact in sorted(artifacts, key=lambda item: (item.artifact_type, item.artifact_ref))
    ]
    return {
        "bundle_type": bundle_type,
        "strategy_id": strategy_id,
        "lifecycle_state": lifecycle_state,
        "artifact_count": len(manifest_artifacts),
        "artifacts": manifest_artifacts,
        "content_hash_basis": canonical_json_dumps(manifest_artifacts),
    }


__all__ = [
    "EvidenceArtifact",
    "build_evidence_bundle_manifest",
]
