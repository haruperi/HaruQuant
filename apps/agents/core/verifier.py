"""Verification layer for workflow evidence and policy boundary checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.core.planner import WorkflowPlan
from apps.agents.core.policies import AgentSettings


@dataclass(frozen=True)
class VerificationResult:
    """Result of lightweight workflow verification."""

    status: str
    warnings: List[str] = field(default_factory=list)


class AgentVerifier:
    """Verifier with workflow-specific completeness and policy checks."""

    def verify(
        self,
        task: AgentTask,
        result: AgentResult,
        *,
        plan: WorkflowPlan,
        settings: AgentSettings | None = None,
    ) -> VerificationResult:
        """Ensure the workflow result is complete enough for reporting."""
        warnings: List[str] = []
        if not task.correlation_id:
            warnings.append("task_missing_correlation_id")
        if plan.workflow_name == "unmapped_task":
            return VerificationResult(status="policy_blocked", warnings=["unmapped_task"])
        if settings is not None and not settings.allows_permission(plan.permission_tier):
            return VerificationResult(
                status="policy_blocked",
                warnings=warnings + [f"permission_not_allowed:{plan.permission_tier}"],
            )
        for input_name in plan.required_inputs:
            if task.input_payload.get(input_name) in (None, "", []):
                warnings.append(f"missing_required_input:{input_name}")
        if warnings and any(item.startswith("missing_required_input:") for item in warnings):
            return VerificationResult(status="incomplete_evidence", warnings=warnings)
        if not result.summary.strip():
            return VerificationResult(status="incomplete_evidence", warnings=warnings)
        if not result.evidence:
            return VerificationResult(
                status="incomplete_evidence",
                warnings=warnings + ["missing_evidence_refs"],
            )
        return VerificationResult(status="ok", warnings=warnings)
