"""Minimal verification layer for evidence and policy boundary checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from apps.agents.core.agent_models import AgentResult, AgentTask


@dataclass(frozen=True)
class VerificationResult:
    """Result of lightweight workflow verification."""

    status: str
    warnings: List[str] = field(default_factory=list)


class AgentVerifier:
    """Phase 0 verifier with simple completeness checks."""

    def verify(self, task: AgentTask, result: AgentResult) -> VerificationResult:
        """Ensure the scaffold returns a minimally valid structured result."""
        warnings: List[str] = []
        if not task.correlation_id:
            warnings.append("task_missing_correlation_id")
        if not result.summary.strip():
            return VerificationResult(status="incomplete_evidence", warnings=warnings)
        return VerificationResult(status="ok", warnings=warnings)
