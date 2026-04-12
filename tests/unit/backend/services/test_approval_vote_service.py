from __future__ import annotations

from pathlib import Path

from backend.common import ValidationError
from backend.db import GovernanceRepository, apply_pending_migrations
from backend.services.approval import (
    ApprovalCreateRequest,
    ApprovalCreationService,
    ApprovalVoteRequest,
    ApprovalVoteService,
)


def test_approval_vote_service_rejects_duplicate_voter(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    migrations_dir = repo_root / "backend" / "db" / "migrations"
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    repository = GovernanceRepository(database_path)
    repository.create_compliance_profile(
        compliance_profile_id="comp_001",
        name="default",
        version="1.0.0",
        profile_json='{"rules":["baseline"]}',
        active_flag=1,
    )
    approval = ApprovalCreationService(repository).create(
        ApprovalCreateRequest(
            action_type="live_execution",
            target_ref_type="workflow",
            target_ref_id="wf_001",
            required_count=2,
            created_by_actor_type="user",
            created_by_actor_id="operator_001",
            compliance_profile_id="comp_001",
            expires_at="2026-04-09T12:00:00Z",
        )
    )
    service = ApprovalVoteService(repository)

    first = service.vote(
        ApprovalVoteRequest(
            approval_id=approval.approval_id,
            approver_role="RISK_MANAGER",
            approver_id="risk_mgr_001",
            decision="APPROVE",
            rationale="Looks acceptable",
        )
    )
    assert first.vote_id > 0

    duplicate_failed = False
    try:
        service.vote(
            ApprovalVoteRequest(
                approval_id=approval.approval_id,
                approver_role="RISK_MANAGER",
                approver_id="risk_mgr_001",
                decision="REJECT",
                rationale="duplicate",
            )
        )
    except ValidationError as exc:
        duplicate_failed = exc.code == "approval_duplicate_voter"

    assert duplicate_failed is True
