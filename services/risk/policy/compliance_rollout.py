"""Compliance rollout helpers and profile seeds."""

from __future__ import annotations

from services.utils import ErrorDescriptor, ValidationError
from .compliance import ApprovalPolicy, ComplianceProfile, RetentionPolicy


_LIVE_WORKFLOW_COMPLIANCE_PROFILE_REQUIRED = ErrorDescriptor(
    code=4030,
    name="LIVE_WORKFLOW_COMPLIANCE_PROFILE_REQUIRED",
    message="Live execution workflows require an attached compliance profile.",
    domain="compliance",
)


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


def seed_uae_enterprise_profile() -> ComplianceProfile:
    """Seed the UAE enterprise profile as the initial production baseline."""

    return ComplianceProfile(
        compliance_profile_id="comp_uae_enterprise",
        name="UAE Enterprise",
        version="1.0.0",
        active=True,
        jurisdictions=("UAE",),
        retention=RetentionPolicy(90, 2555, 2555),
        approvals=ApprovalPolicy(
            dual_auth_live_override=True,
            hard_kill_recovery_dual_auth=True,
            policy_change_dual_auth=True,
            required_roles=("risk_manager", "compliance"),
        ),
        metadata={"regulatory_tier": "enterprise", "board_baseline": True},
    )


def require_live_execution_profile(*, compliance_profile_id: str | None, operating_mode: str) -> str:
    """Attach and validate the active compliance profile for live-capable workflows."""

    if operating_mode in {"MODE-003", "MODE-004"} and not compliance_profile_id:
        raise ValidationError(
            _LIVE_WORKFLOW_COMPLIANCE_PROFILE_REQUIRED,
        )
    return compliance_profile_id or ""


def build_compliance_profile_labels(*, export_profile: str, compliance_profile_id: str) -> tuple[str, ...]:
    """Build stable export labels from the active compliance profile."""

    return (export_profile, f"profile:{compliance_profile_id}")
