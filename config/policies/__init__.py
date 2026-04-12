"""Policy configuration loader and resolver."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError


class FailureBehavior(str, Enum):
    """Policy failure behavior options."""
    REJECT_AND_ESCALATE = "reject_and_escalate"
    REJECT_AND_LOG = "reject_and_log"
    BLOCK_AND_NOTIFY = "block_and_notify"
    FALLBACK_TO_SAFE_MODEL = "fallback_to_safe_model"
    ESCALATE_TO_ONCALL = "escalate_to_oncall"
    DENY_AND_ESCALATE = "deny_and_escalate"
    RETAIN_UNTIL_REVIEW = "retain_until_review"


class LoggingRequirement(str, Enum):
    """Policy logging requirement options."""
    AUDIT_LOG_REQUIRED = "audit_log_required"
    STANDARD_LOG = "standard_log"
    NO_LOGGING = "no_logging"


class EnforcementLayer(str, Enum):
    """Policy enforcement layer options."""
    API_GATEWAY = "api_gateway"
    ROUTING = "routing"
    ORCHESTRATOR = "orchestrator"
    AGENT = "agent"
    MCP_SERVER = "mcp_server"
    EXECUTION_MCP = "execution_mcp"
    RISK_ENGINE = "risk_engine"
    APPROVAL_SERVICE = "approval_service"
    MONITORING = "monitoring"
    OBSERVABILITY = "observability"
    STORAGE = "storage"


class PolicyConfig(BaseModel):
    """Policy configuration schema."""
    policy_name: str = Field(..., description="Unique policy name")
    scope: str = Field(..., description="Workflow scope this policy applies to")
    owner: str = Field(..., description="Team or person owning this policy")
    enforcement_layers: List[EnforcementLayer] = Field(
        default_factory=list,
        description="Layers where this policy is enforced",
    )
    failure_behavior: FailureBehavior = Field(
        ...,
        description="Behavior when policy check fails",
    )
    logging_requirement: LoggingRequirement = Field(
        ...,
        description="Logging requirement level",
    )
    exception_process: str = Field(
        ...,
        description="Process for requesting policy exception",
    )
    review_cadence: str = Field(
        ...,
        description="How often this policy is reviewed",
    )


class PolicyResolver:
    """Load, validate, and resolve policies by scope."""

    def __init__(self, policy_dir: Optional[Path] = None) -> None:
        if policy_dir is None:
            policy_dir = Path(__file__).resolve().parent.parent.parent / "config" / "policies"
        self._policy_dir = policy_dir
        self._policies: Dict[str, PolicyConfig] = {}
        self._scope_index: Dict[str, List[str]] = {}
        self.load_all()

    @property
    def policies(self) -> Dict[str, PolicyConfig]:
        return dict(self._policies)

    def load_all(self) -> None:
        """Load all YAML policy files from the policy directory."""
        if not self._policy_dir.is_dir():
            return
        for path in sorted(self._policy_dir.glob("*.yaml")):
            self._load_single(path)
        self._build_scope_index()

    def _load_single(self, path: Path) -> None:
        """Load and validate a single policy file."""
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return
            config = PolicyConfig(**data)
            self._policies[config.policy_name] = config
        except (ValidationError, yaml.YAMLError) as exc:
            from backend.common.logger import logger
            logger.error(f"Failed to load policy {path}: {exc}")

    def _build_scope_index(self) -> None:
        """Build index mapping scope -> list of policy names."""
        self._scope_index = {}
        for name, policy in self._policies.items():
            self._scope_index.setdefault(policy.scope, []).append(name)

    def resolve_for_scope(self, scope: str) -> List[PolicyConfig]:
        """Return all policies that apply to the given scope."""
        names = self._scope_index.get(scope, [])
        return [self._policies[n] for n in names if n in self._policies]

    def get_by_name(self, name: str) -> Optional[PolicyConfig]:
        """Return a single policy by name."""
        return self._policies.get(name)

    def should_enforce(self, scope: str, layer: EnforcementLayer) -> List[PolicyConfig]:
        """Return policies that apply to scope AND enforcement layer."""
        return [
            p for p in self.resolve_for_scope(scope)
            if layer in p.enforcement_layers
        ]

    def on_failure(self, scope: str) -> Optional[FailureBehavior]:
        """Return the failure behavior for the first matching policy."""
        policies = self.resolve_for_scope(scope)
        if policies:
            return policies[0].failure_behavior
        return None

    def reload(self) -> None:
        """Reload all policies (useful for hot-reload scenarios)."""
        self._policies.clear()
        self._scope_index.clear()
        self.load_all()
