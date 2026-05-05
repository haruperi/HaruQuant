from __future__ import annotations

from pathlib import Path

from data.database import ResearchAuditRepository, apply_pending_migrations, default_migrations_dir
from haruquant.strategy import LegalHoldAwareReplayService


def test_legal_hold_aware_replay_service_blocks_protected_exports(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ResearchAuditRepository(database_path)

    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review setup", "{}", "user", "operator_001", "{}", "[]"),
        )

    repository.create_replay_bundle(
        replay_bundle_id="rpb_001",
        workflow_id="wf_001",
        bundle_hash="hash_001",
        object_store_uri="s3://bucket/replay_001",
        completeness_status="complete",
        export_profile="audit_export",
        integrity_manifest_ref="manifest_001",
    )
    repository.place_legal_hold(
        target_type="replay_bundle",
        target_ref_id="rpb_001",
        hold_reason="regulatory_review",
        placed_by_actor_id="audit_001",
    )

    result = LegalHoldAwareReplayService(repository).get_replay_bundle("rpb_001")

    assert result.blocked is True
    assert result.replay_bundle is not None
    assert result.active_holds[0].target_ref_id == "rpb_001"
