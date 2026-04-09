"""Legal-hold aware replay retrieval helpers."""

from __future__ import annotations

from dataclasses import dataclass

from backend.db import LegalHoldRecord, ReplayBundleRecord, ResearchAuditRepository


@dataclass(frozen=True)
class LegalHoldAwareReplayResult:
    replay_bundle: ReplayBundleRecord | None
    blocked: bool
    active_holds: tuple[LegalHoldRecord, ...]


class LegalHoldAwareReplayService:
    """Protect replay retrieval when active legal holds exist."""

    def __init__(self, repository: ResearchAuditRepository) -> None:
        self._repository = repository

    def get_replay_bundle(self, replay_bundle_id: str) -> LegalHoldAwareReplayResult:
        holds = tuple(
            self._repository.list_active_legal_holds(
                target_type="replay_bundle",
                target_ref_id=replay_bundle_id,
            )
        )
        replay_bundle = self._repository.get_replay_bundle(replay_bundle_id)
        return LegalHoldAwareReplayResult(
            replay_bundle=replay_bundle,
            blocked=bool(holds),
            active_holds=holds,
        )
