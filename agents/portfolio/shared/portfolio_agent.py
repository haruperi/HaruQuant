"""Reusable deterministic Portfolio Department agent implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agents._shared.base_contracts import AgentRunContext, AgentRunResult
from agents._shared.persistence import utc_stamp, write_json_artifact


@dataclass(frozen=True)
class PortfolioAgentConfig:
    agent_name: str
    display_name: str
    allowed_actions: list[str]
    blocked_actions: list[str]
    required_evidence: list[str] = field(default_factory=list)
    permission_profile: str = "portfolio_read_only_v1"


class GenericPortfolioAgent:
    def __init__(self, config: PortfolioAgentConfig) -> None:
        self.config = config
        self.agent_name = config.agent_name

    def gather_evidence(self, task_input: dict[str, Any]) -> dict[str, Any]:
        context = task_input.get("context", {}) if isinstance(task_input.get("context", {}), dict) else {}
        missing = [key for key in self.config.required_evidence if key not in task_input and key not in context]
        return {"context": context, "missing_evidence": missing, "evidence_refs": task_input.get("evidence_refs", [])}

    def deterministic_policy(self, task_input: dict[str, Any], evidence_state: dict[str, Any]) -> dict[str, Any]:
        reasons: list[str] = []
        if evidence_state.get("missing_evidence"):
            reasons.append("missing_required_evidence")
        if task_input.get("kill_switch_state") in {"triggered", "active"}:
            reasons.append("kill_switch_active")
        if task_input.get("audit_logging_available", True) is False:
            reasons.append("audit_logging_unavailable")
        if task_input.get("risk_governor_available", True) is False:
            reasons.append("risk_governor_unavailable")
        if task_input.get("request_type") in {"live_allocation_change", "increase_allocation", "promote_to_micro_live"} and not task_input.get("board_approval_id"):
            reasons.append("board_approval_required")
        return {
            "status": "blocked" if reasons else "completed",
            "decision": "blocked" if reasons else f"{self.agent_name}_review_complete",
            "reasons": reasons or ["Deterministic portfolio policy checks passed."],
            "allowed_actions": [] if reasons else self.config.allowed_actions,
            "blocked_actions": self.config.blocked_actions + reasons,
        }

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        evidence = self.gather_evidence(task_input)
        policy = self.deterministic_policy(task_input, evidence)
        output = {
            "request_id": task_input.get("request_id", context.task_id),
            "agent_name": self.agent_name,
            "permission_profile": self.config.permission_profile,
            "policy_version": "portfolio_deterministic_policy_v1",
            "prompt_version": f"{self.agent_name}_prompt_v1",
            "tools_called": [],
            "llm_used": False,
            "model_provider": "none",
            "model_name": "deterministic",
            "fallback_used": False,
            "evidence": evidence,
            "policy": policy,
        }
        audit_ref = write_json_artifact("reports/logs/portfolio", f"{self.agent_name}-{utc_stamp()}.json", output)
        output["audit_ref"] = audit_ref
        return AgentRunResult(
            agent_name=self.agent_name,
            status=policy["status"],
            output=output,
            evidence_refs=[audit_ref, *task_input.get("evidence_refs", [])],
            failure_reason=";".join(policy["reasons"]) if policy["status"] == "blocked" else None,
        )
