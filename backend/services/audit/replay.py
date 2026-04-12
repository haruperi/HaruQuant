"""Replay bundle assembly helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib

from backend.common.ids import generate_id
from backend.contracts.common import Originator
from backend.contracts.replay_bundle.model import IntegrityManifest, ReplayBundle, ReplayBundlePayload
from backend.contracts.serialization import canonical_json_dumps
from backend.data.database import ReplayBundleRecord, ResearchAuditRepository


@dataclass(frozen=True)
class ReplayBundleAssemblyResult:
    bundle: ReplayBundle
    record: ReplayBundleRecord


class ReplayBundleAssembler:
    """Assemble replay bundles from workflow-scoped audit artifacts."""

    def __init__(self, repository: ResearchAuditRepository) -> None:
        self._repository = repository

    def assemble(
        self,
        *,
        workflow_id: str,
        export_profile: str,
    ) -> ReplayBundleAssemblyResult:
        evidence = self._repository.list_evidence_bundles_for_workflow(workflow_id)
        trajectory_logs = self._repository.list_trajectory_logs_for_workflow(workflow_id)
        included_refs = [item.evidence_bundle_id for item in evidence] + [item.log_id for item in trajectory_logs]
        manifest_hash = hashlib.sha256(
            canonical_json_dumps({"workflow_id": workflow_id, "included_refs": included_refs}).encode("utf-8")
        ).hexdigest()
        replay_bundle_id = generate_id("replay_bundle")
        generated_at = datetime.now(timezone.utc)

        bundle = ReplayBundle(
            workflow_id=workflow_id,
            correlation_id=f"corr_{workflow_id}",
            causation_id=f"evt_{replay_bundle_id}",
            timestamp_utc=generated_at,
            originator=Originator(type="service", id="replay_assembler"),
            environment="paper",
            operating_mode="MODE-002",
            payload=ReplayBundlePayload(
                replay_bundle_id=replay_bundle_id,
                workflow_id=workflow_id,
                completeness_status="complete" if included_refs else "partial",
                included_refs=included_refs,
                integrity_manifest=IntegrityManifest(
                    manifest_hash=manifest_hash,
                    manifest_algorithm="sha256",
                ),
                export_profile=export_profile,
                generated_at=generated_at,
            ),
        )
        record = self._repository.create_replay_bundle(
            replay_bundle_id=replay_bundle_id,
            workflow_id=workflow_id,
            bundle_hash=manifest_hash,
            object_store_uri=f"memory://replay/{replay_bundle_id}",
            completeness_status=bundle.payload.completeness_status,
            export_profile=export_profile,
            integrity_manifest_ref=manifest_hash,
        )
        return ReplayBundleAssemblyResult(bundle=bundle, record=record)
