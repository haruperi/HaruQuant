"""Workflow runner for Edge snapshot drift watch."""

from __future__ import annotations

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.core.audit import AgentAuditEvent, AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.policies import AgentSettings
from apps.agents.core.verifier import AgentVerifier
from apps.agents.specialists.edge_intelligence import EdgeIntelligenceAgent


def run_snapshot_drift_watch(
    task: AgentTask,
    *,
    planner: AgentPlanner,
    verifier: AgentVerifier,
    audit_logger: AgentAuditLogger,
    settings: AgentSettings,
    specialist: EdgeIntelligenceAgent,
) -> AgentResult:
    """Run the saved-snapshot drift-watch workflow."""
    plan = planner.plan(task)
    result = specialist.run(task)
    verification = verifier.verify(task, result, plan=plan, settings=settings)
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
