"""Policy domain models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PolicyScope:
    """Policy applicability scope."""

    environment: str
    account_id: str | None = None
    strategy_id: str | None = None
    symbol: str | None = None
    workflow_type: str | None = None
    role: str | None = None


@dataclass(frozen=True)
class PolicyVersion:
    """Versioned policy reference."""

    policy_version_id: str
    policy_type: str
    version: str
    status: str
    effective_from: str
    effective_to: str | None = None
    content_hash: str = ""
    content_ref: str | None = None


@dataclass(frozen=True)
class PolicyBundle:
    """Resolved active policy bundle for an execution scope."""

    scope: PolicyScope
    policies: tuple[PolicyVersion, ...]
    bundle_version: str
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyEnforcementResult:
    """Deterministic result of applying policy to an action."""

    allowed: bool
    policy_bundle_version: str
    reason_codes: tuple[str, ...] = ()
    applied_policy_ids: tuple[str, ...] = ()
    constraints: dict[str, object] = field(default_factory=dict)
