from __future__ import annotations

from pathlib import Path

from backend.db import ResearchAuditRepository, apply_pending_migrations
from backend.services.audit.legal_hold import LegalHoldAwareReplayService


def test_legal_hold_aware_purge_blocker_rejects_protected_targets(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ResearchAuditRepository(database_path)

    repository.place_legal_hold(
        target_type="replay_bundle",
        target_ref_id="rpb_001",
        hold_reason="regulatory_review",
        placed_by_actor_id="audit_001",
    )

    decision = LegalHoldAwareReplayService(repository).check_purge_allowed(
        target_type="replay_bundle",
        target_ref_id="rpb_001",
    )

    assert decision.blocked is True
    assert decision.active_holds[0].target_ref_id == "rpb_001"


def test_legal_hold_aware_purge_blocker_allows_unprotected_targets(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ResearchAuditRepository(database_path)

    decision = LegalHoldAwareReplayService(repository).check_purge_allowed(
        target_type="replay_bundle",
        target_ref_id="rpb_002",
    )

    assert decision.blocked is False
    assert decision.active_holds == ()
