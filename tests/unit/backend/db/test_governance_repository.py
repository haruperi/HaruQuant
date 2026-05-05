from __future__ import annotations

from pathlib import Path
import sqlite3

from data.database import GovernanceRepository, apply_pending_migrations, default_migrations_dir


def test_governance_repository_enforces_approval_vote_distinctness(tmp_path) -> None:
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
    approval = repository.create_approval(
        approval_id="appr_001",
        action_type="live_execution",
        target_ref_type="workflow",
        target_ref_id="wf_001",
        required_count=2,
        state="PENDING",
        created_by_actor_type="user",
        created_by_actor_id="operator_001",
        compliance_profile_id="comp_001",
    )
    assert approval.approval_id == "appr_001"

    vote = repository.add_vote(
        approval_id="appr_001",
        approver_role="RISK_MANAGER",
        approver_id="risk_mgr_001",
        decision="APPROVE",
        rationale="Looks acceptable",
    )
    assert vote.vote_id > 0

    duplicate_failed = False
    try:
        repository.add_vote(
            approval_id="appr_001",
            approver_role="RISK_MANAGER",
            approver_id="risk_mgr_001",
            decision="REJECT",
            rationale="duplicate",
        )
    except sqlite3.IntegrityError:
        duplicate_failed = True

    policy = repository.create_policy(
        policy_version_id="policy_001",
        policy_type="risk",
        version="1.0.0",
        content_hash="hash_001",
        effective_from="2026-04-08T00:00:00Z",
        status="ACTIVE",
        created_by="risk_mgr_001",
    )
    strategy = repository.create_strategy(
        strategy_id="strat_001",
        strategy_name="FX Momentum",
        strategy_family="fx_momentum",
        current_lifecycle_state="PAPER_APPROVED",
        code_hash="code_hash_001",
        parameter_hash="param_hash_001",
    )

    assert duplicate_failed is True
    assert policy.policy_version_id == "policy_001"
    assert strategy.strategy_id == "strat_001"
