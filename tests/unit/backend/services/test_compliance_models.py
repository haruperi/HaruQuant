from backend.services.policy.compliance import (
    ApprovalPolicy,
    ComplianceProfile,
    RetentionPolicy,
)


def test_compliance_profile_models_capture_retention_and_approval_rules() -> None:
    profile = ComplianceProfile(
        compliance_profile_id="comp_001",
        name="default",
        version="1.0.0",
        active=True,
        jurisdictions=("UAE", "EU"),
        retention=RetentionPolicy(
            hot_days=30,
            archive_days=365,
            replay_retention_days=730,
            legal_hold_blocks_purge=True,
        ),
        approvals=ApprovalPolicy(
            dual_auth_live_override=True,
            hard_kill_recovery_dual_auth=True,
            policy_change_dual_auth=True,
            required_roles=("RISK_MANAGER", "COMPLIANCE_OFFICER"),
        ),
        metadata={"export_profile": "regulated"},
    )

    assert profile.active is True
    assert profile.retention.replay_retention_days == 730
    assert profile.approvals.required_roles == ("RISK_MANAGER", "COMPLIANCE_OFFICER")
