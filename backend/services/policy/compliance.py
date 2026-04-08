"""Compliance profile domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetentionPolicy:
    """Retention and export controls for a compliance profile."""

    hot_days: int
    archive_days: int
    replay_retention_days: int
    legal_hold_blocks_purge: bool = True


@dataclass(frozen=True)
class ApprovalPolicy:
    """Approval routing requirements under a compliance profile."""

    dual_auth_live_override: bool = False
    hard_kill_recovery_dual_auth: bool = True
    policy_change_dual_auth: bool = True
    required_roles: tuple[str, ...] = ()


@dataclass(frozen=True)
class ComplianceProfile:
    """Parsed compliance profile definition."""

    compliance_profile_id: str
    name: str
    version: str
    active: bool
    jurisdictions: tuple[str, ...] = ()
    retention: RetentionPolicy = field(default_factory=lambda: RetentionPolicy(30, 365, 365))
    approvals: ApprovalPolicy = field(default_factory=ApprovalPolicy)
    metadata: dict[str, object] = field(default_factory=dict)
