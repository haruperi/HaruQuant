"""Permission tiers and baseline settings for the agent layer."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List


class PermissionTier:
    """Simple enum-like helper for tool permission modes."""

    READ_ONLY = "read_only"
    ADVISORY_WRITE = "advisory_write"
    PRIVILEGED = "privileged"

    @classmethod
    def values(cls) -> List[str]:
        """Return all supported permission tier values."""
        return [cls.READ_ONLY, cls.ADVISORY_WRITE, cls.PRIVILEGED]

    @classmethod
    def from_value(cls, value: str) -> str:
        """Validate one tier string and return it unchanged."""
        normalized = str(value).strip().lower()
        if normalized not in cls.values():
            raise ValueError(f"Unsupported permission tier: {value}")
        return normalized


class ApprovalMode:
    """Simple enum-like helper for task approval posture."""

    AUTO_READ_ONLY = "auto_read_only"
    REQUIRE_APPROVAL = "require_approval"
    DENY_PRIVILEGED = "deny_privileged"

    @classmethod
    def values(cls) -> List[str]:
        """Return all supported approval modes."""
        return [cls.AUTO_READ_ONLY, cls.REQUIRE_APPROVAL, cls.DENY_PRIVILEGED]

    @classmethod
    def from_value(cls, value: str) -> str:
        """Validate one mode string and return it unchanged."""
        normalized = str(value).strip().lower()
        if normalized not in cls.values():
            raise ValueError(f"Unsupported approval mode: {value}")
        return normalized


@dataclass(frozen=True)
class ProviderSettings:
    """LLM provider configuration loaded from baseline agent settings."""

    provider: str = "noop"
    model: str = "noop-model"
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class N8NSettings:
    """Outbound/inbound workflow integration settings."""

    webhook_url: str = ""
    shared_secret_env: str = "HQT_N8N_WEBHOOK_SECRET"
    outbox_dir: str = "artifacts/workflows/n8n_outbox"
    require_signature: bool = True


@dataclass(frozen=True)
class ApprovalSettings:
    """Approval artifact storage settings."""

    store_dir: str = "artifacts/approvals"


@dataclass(frozen=True)
class AgentSettings:
    """Minimal configuration required for the Phase 0 scaffold."""

    schema_version: str = "1.0.0"
    default_approval_mode: str = ApprovalMode.AUTO_READ_ONLY
    enabled_permission_tiers: List[str] = field(
        default_factory=lambda: [PermissionTier.READ_ONLY, PermissionTier.ADVISORY_WRITE]
    )
    audit_log_path: str = "artifacts/logs/agents/agent_runs.jsonl"
    provider: ProviderSettings = field(default_factory=ProviderSettings)
    n8n: N8NSettings = field(default_factory=N8NSettings)
    approvals: ApprovalSettings = field(default_factory=ApprovalSettings)
    workflow_defaults: Dict[str, Any] = field(
        default_factory=lambda: {"noop_workflow_enabled": True}
    )

    def allows_permission(self, tier: str) -> bool:
        """Return whether a permission tier is enabled in settings."""
        return PermissionTier.from_value(tier) in self.enabled_permission_tiers


def _coerce_settings(raw: Dict[str, Any]) -> AgentSettings:
    """Normalize JSON data into an AgentSettings instance."""
    provider_raw = dict(raw.get("provider") or {})
    n8n_raw = dict(raw.get("n8n") or {})
    approvals_raw = dict(raw.get("approvals") or {})
    enabled_tiers = [
        PermissionTier.from_value(value)
        for value in (raw.get("enabled_permission_tiers") or [PermissionTier.READ_ONLY])
    ]
    return AgentSettings(
        schema_version=str(raw.get("schema_version") or "1.0.0"),
        default_approval_mode=ApprovalMode.from_value(
            raw.get("default_approval_mode") or ApprovalMode.AUTO_READ_ONLY
        ),
        enabled_permission_tiers=enabled_tiers,
        audit_log_path=str(
            raw.get("audit_log_path") or "artifacts/logs/agents/agent_runs.jsonl"
        ),
        provider=ProviderSettings(
            provider=str(provider_raw.get("provider") or "noop"),
            model=str(provider_raw.get("model") or "noop-model"),
            timeout_seconds=float(provider_raw.get("timeout_seconds") or 5.0),
        ),
        n8n=N8NSettings(
            webhook_url=str(n8n_raw.get("webhook_url") or ""),
            shared_secret_env=str(n8n_raw.get("shared_secret_env") or "HQT_N8N_WEBHOOK_SECRET"),
            outbox_dir=str(n8n_raw.get("outbox_dir") or "artifacts/workflows/n8n_outbox"),
            require_signature=bool(n8n_raw.get("require_signature", True)),
        ),
        approvals=ApprovalSettings(
            store_dir=str(approvals_raw.get("store_dir") or "artifacts/approvals"),
        ),
        workflow_defaults=dict(raw.get("workflow_defaults") or {}),
    )


def load_agent_settings(path: str | Path) -> AgentSettings:
    """Load baseline agent settings from a JSON file."""
    settings_path = Path(path)
    with settings_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return _coerce_settings(raw)
