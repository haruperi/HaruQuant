from __future__ import annotations

from pathlib import Path

from haruquant.utils import ValidationError
from backend.data.database import GovernanceRepository, apply_pending_migrations, default_migrations_dir
from haruquant.execution import ApprovalCreateRequest, ApprovalCreationService


def test_approval_creation_service_requires_positive_count_and_expiry(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)
    service = ApprovalCreationService(GovernanceRepository(database_path))

    invalid_count = False
    try:
        service.create(
            ApprovalCreateRequest(
                action_type="live_execution",
                target_ref_type="workflow",
                target_ref_id="wf_001",
                required_count=0,
                created_by_actor_type="user",
                created_by_actor_id="operator_001",
                expires_at="2026-04-09T12:00:00Z",
            )
        )
    except ValidationError as exc:
        invalid_count = exc.code == "approval_required_count_invalid"

    missing_expiry = False
    try:
        service.create(
            ApprovalCreateRequest(
                action_type="live_execution",
                target_ref_type="workflow",
                target_ref_id="wf_001",
                required_count=2,
                created_by_actor_type="user",
                created_by_actor_id="operator_001",
                expires_at=None,
            )
        )
    except ValidationError as exc:
        missing_expiry = exc.code == "approval_expiry_required"

    assert invalid_count is True
    assert missing_expiry is True


def test_approval_creation_service_persists_pending_request(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
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
    service = ApprovalCreationService(repository)

    record = service.create(
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

    assert record.approval_id.startswith("appr_")
    assert record.state == "PENDING"
