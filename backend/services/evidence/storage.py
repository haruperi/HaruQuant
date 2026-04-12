"""Evidence bundle hashing and persistence."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from backend.common import generate_id
from backend.contracts.serialization import canonical_json_dumps
from backend.db import EvidenceBundleRecord, ResearchAuditRepository

from .assembler import LifecycleEvidenceBundle


@dataclass(frozen=True)
class StoredEvidenceBundle:
    content_hash: str
    content_ref: str
    record: EvidenceBundleRecord


class EvidenceBundleStorageService:
    """Hash and persist lifecycle evidence bundles."""

    def __init__(self, repository: ResearchAuditRepository) -> None:
        self._repository = repository

    def store(
        self,
        bundle: LifecycleEvidenceBundle,
        *,
        workflow_id: str | None = None,
    ) -> StoredEvidenceBundle:
        manifest_json = canonical_json_dumps(bundle.manifest)
        content_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
        evidence_bundle_id = generate_id("evidence_bundle")
        content_ref = f"memory://evidence/{evidence_bundle_id}"
        record = self._repository.create_evidence_bundle(
            evidence_bundle_id=evidence_bundle_id,
            workflow_id=workflow_id,
            bundle_type=str(bundle.manifest["bundle_type"]),
            summary=f"{bundle.lifecycle_state.value} evidence bundle",
            content_ref=content_ref,
            content_hash=content_hash,
            freshness_status="fresh",
        )
        return StoredEvidenceBundle(
            content_hash=content_hash,
            content_ref=content_ref,
            record=record,
        )
