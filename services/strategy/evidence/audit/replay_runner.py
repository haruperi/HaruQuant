"""Stored replay-bundle validation runner."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from backend_retiring.contracts.replay_bundle.model import ReplayBundle
from backend_retiring.contracts.serialization import canonical_json_dumps
from data.database import ResearchAuditRepository


@dataclass(frozen=True)
class ReplayRunResult:
    """Deterministic replay run result built from stored bundle references."""

    workflow_id: str
    replay_bundle_id: str
    included_refs: tuple[str, ...]
    reconstructed_hash: str


class StoredReplayRunner:
    """Reconstruct a replay view from stored bundle references."""

    def __init__(self, repository: ResearchAuditRepository) -> None:
        self._repository = repository

    def run(self, bundle: ReplayBundle) -> ReplayRunResult:
        workflow_id = bundle.payload.workflow_id
        evidence_refs = [item.evidence_bundle_id for item in self._repository.list_evidence_bundles_for_workflow(workflow_id)]
        trajectory_refs = [item.log_id for item in self._repository.list_trajectory_logs_for_workflow(workflow_id)]
        available_refs = tuple(evidence_refs + trajectory_refs)
        replay_refs = tuple(ref for ref in bundle.payload.included_refs if ref in available_refs)
        reconstructed_hash = hashlib.sha256(
            canonical_json_dumps({"workflow_id": workflow_id, "included_refs": replay_refs}).encode("utf-8")
        ).hexdigest()
        return ReplayRunResult(
            workflow_id=workflow_id,
            replay_bundle_id=bundle.payload.replay_bundle_id,
            included_refs=replay_refs,
            reconstructed_hash=reconstructed_hash,
        )
