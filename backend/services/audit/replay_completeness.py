"""Replay completeness validation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from backend.contracts.replay_bundle.model import ReplayBundle
from backend.db import ResearchAuditRepository


@dataclass(frozen=True)
class ReplayCompletenessReport:
    """Completeness report for stored replay bundles."""

    complete: bool
    missing_refs: tuple[str, ...]
    available_refs: tuple[str, ...]


class ReplayCompletenessChecker:
    """Check whether a stored replay bundle still has all referenced artifacts available."""

    def __init__(self, repository: ResearchAuditRepository) -> None:
        self._repository = repository

    def check(self, bundle: ReplayBundle) -> ReplayCompletenessReport:
        workflow_id = bundle.payload.workflow_id
        available_refs = tuple(
            [item.evidence_bundle_id for item in self._repository.list_evidence_bundles_for_workflow(workflow_id)]
            + [item.log_id for item in self._repository.list_trajectory_logs_for_workflow(workflow_id)]
        )
        missing_refs = tuple(ref for ref in bundle.payload.included_refs if ref not in available_refs)
        return ReplayCompletenessReport(
            complete=not missing_refs,
            missing_refs=missing_refs,
            available_refs=available_refs,
        )
