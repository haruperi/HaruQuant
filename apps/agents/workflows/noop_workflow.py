"""Deterministic no-op workflow used to verify Phase 0 wiring."""

from __future__ import annotations

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.core.audit import AgentAuditEvent, AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.verifier import AgentVerifier
from apps.agents.integrations.llm_client import LLMClient


def run_noop_workflow(
    task: AgentTask,
    *,
    planner: AgentPlanner,
    verifier: AgentVerifier,
    audit_logger: AgentAuditLogger,
    llm_client: LLMClient,
) -> AgentResult:
    """Run a minimal end-to-end workflow without touching real engines."""
    plan = planner.plan(task)
    summary = llm_client.complete(
        prompt="foundation_check",
        metadata={"task_id": task.task_id, "intent": task.intent},
    )
    result = AgentResult(
        status="ok" if plan.workflow_name == "noop_workflow" else "unmapped_task",
        summary=summary,
        evidence=[
            {
                "type": "workflow_plan",
                "workflow_name": plan.workflow_name,
                "reason": plan.metadata.get("reason", ""),
            }
        ],
        recommendations=[],
        required_actions=[],
        warnings=[],
        confidence=1.0 if plan.workflow_name == "noop_workflow" else 0.0,
        metadata={"workflow_name": plan.workflow_name},
    )
    verification = verifier.verify(task, result)
    result.warnings.extend(verification.warnings)
    audit_logger.append(
        AgentAuditEvent(
            event_type="workflow_run",
            task_id=task.task_id,
            run_id=task.run_id,
            workflow_name=plan.workflow_name,
            correlation_id=task.correlation_id,
            status=verification.status,
            user_id=task.actor_user_id,
            actor_role=task.actor_role,
            evidence_refs=result.evidence,
            metadata={"task_type": task.task_type},
        )
    )
    return result
