from __future__ import annotations

from pathlib import Path

from backend.data.database import ResearchAuditRepository, apply_pending_migrations
from backend.services import (
    EvidenceArtifact,
    EvidenceBundleStorageService,
    StrategyLifecycleState,
    assemble_lifecycle_evidence_bundle,
)


def test_evidence_bundle_storage_service_hashes_and_persists_bundle(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = ResearchAuditRepository(database_path)
    with repository._connect() as connection:  # noqa: SLF001
        connection.execute(
            "INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Evidence flow", "{}", "user", "operator_001", "{}", "[]"),
        )

    bundle = assemble_lifecycle_evidence_bundle(
        strategy_id="strat_001",
        lifecycle_state=StrategyLifecycleState.PAPER_APPROVED,
        artifacts=(
            EvidenceArtifact(
                artifact_type="paper_report",
                artifact_ref="memory://paper",
                artifact_hash="hash_paper",
            ),
        ),
    )

    stored = EvidenceBundleStorageService(repository).store(bundle, workflow_id="wf_001")

    assert stored.record.workflow_id == "wf_001"
    assert stored.record.bundle_type == "paper_report"
    assert stored.record.content_ref == stored.content_ref
    assert stored.record.content_hash == stored.content_hash
