"""Compliance rollout helpers and profile seeds."""

from __future__ import annotations

from backend.services.policy import ApprovalPolicy, ComplianceProfile, RetentionPolicy


def seed_internal_non_regulated_profile() -> ComplianceProfile:
    """Seed the default internal non-regulated compliance profile."""

    return ComplianceProfile(
        compliance_profile_id="comp_internal_non_regulated",
        name="Internal / Non-Regulated",
        version="1.0.0",
        active=True,
        jurisdictions=("internal",),
        retention=RetentionPolicy(30, 180, 180),
        approvals=ApprovalPolicy(
            dual_auth_live_override=False,
            hard_kill_recovery_dual_auth=True,
            policy_change_dual_auth=True,
            required_roles=("operator",),
        ),
        metadata={"regulatory_tier": "internal"},
    )
