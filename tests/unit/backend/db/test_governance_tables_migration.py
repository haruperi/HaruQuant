from __future__ import annotations

from pathlib import Path
import sqlite3

from backend.data.database import apply_pending_migrations, default_migrations_dir


def test_governance_tables_migration_enforces_vote_uniqueness_and_policy_versioning(tmp_path) -> None:
    migrations_dir = default_migrations_dir()
    database_path = tmp_path / "agentic.db"

    apply_pending_migrations(database_path, migrations_dir)

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("INSERT INTO core_workflows (workflow_id, workflow_type, environment, operating_mode, state, objective, scope_json, initiator_type, initiator_id, timeout_policy_json, stop_conditions_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("wf_001", "trade_review", "paper", "MODE-002", "CREATED", "Review setup", "{}", "user", "operator_001", "{}", "[]"))
        connection.execute("INSERT INTO gov_compliance_profiles (compliance_profile_id, name, version, profile_json, active_flag) VALUES (?, ?, ?, ?, ?)", ("comp_001", "default", "1.0.0", '{"rules":["baseline"]}', 1))
        connection.execute("INSERT INTO gov_approvals (approval_id, action_type, target_ref_type, target_ref_id, required_count, state, compliance_profile_id, expires_at, created_by_actor_type, created_by_actor_id, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("appr_001", "live_execution", "workflow", "wf_001", 2, "PENDING", "comp_001", "2026-04-08T13:00:00Z", "user", "operator_001", '{"route":"dual_auth"}'))
        connection.execute("INSERT INTO gov_approval_votes (approval_id, approver_role, approver_id, decision, reason_code, rationale) VALUES (?, ?, ?, ?, ?, ?)", ("appr_001", "RISK_MANAGER", "risk_mgr_001", "APPROVE", None, "Looks acceptable"))
        connection.execute("INSERT INTO gov_policies (policy_version_id, policy_type, version, content_hash, content_ref, effective_from, effective_to, status, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", ("policy_001", "risk", "1.0.0", "hash_001", "artifact_001", "2026-04-08T00:00:00Z", None, "ACTIVE", "risk_mgr_001"))
        connection.execute("INSERT INTO gov_strategy_registry (strategy_id, strategy_name, strategy_family, current_lifecycle_state, code_hash, parameter_hash, owner_id) VALUES (?, ?, ?, ?, ?, ?, ?)", ("strat_001", "FX Momentum", "fx_momentum", "PAPER_VERIFIED", "code_hash_001", "param_hash_001", "owner_001"))
        connection.execute("INSERT INTO gov_strategy_promotions (promotion_id, strategy_id, from_state, to_state, evidence_bundle_id, approver_1_id, approver_2_id, effective_at, rationale) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", ("promo_001", "strat_001", "PAPER_VERIFIED", "LIVE_LIMITED", "evidence_001", "risk_mgr_001", "comp_officer_001", "2026-04-08T14:00:00Z", "ready"))
        connection.commit()

        vote_failed = False
        try:
            connection.execute("INSERT INTO gov_approval_votes (approval_id, approver_role, approver_id, decision, reason_code, rationale) VALUES (?, ?, ?, ?, ?, ?)", ("appr_001", "RISK_MANAGER", "risk_mgr_001", "REJECT", "duplicate", "duplicate"))
            connection.commit()
        except sqlite3.IntegrityError:
            vote_failed = True
            connection.rollback()

        policy_failed = False
        try:
            connection.execute("INSERT INTO gov_policies (policy_version_id, policy_type, version, content_hash, content_ref, effective_from, effective_to, status, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", ("policy_002", "risk", "1.0.0", "hash_002", "artifact_002", "2026-04-09T00:00:00Z", None, "ACTIVE", "risk_mgr_001"))
            connection.commit()
        except sqlite3.IntegrityError:
            policy_failed = True
            connection.rollback()

        promotion = connection.execute("SELECT strategy_id, to_state FROM gov_strategy_promotions").fetchone()
    finally:
        connection.close()

    assert vote_failed is True
    assert policy_failed is True
    assert promotion == ("strat_001", "LIVE_LIMITED")
