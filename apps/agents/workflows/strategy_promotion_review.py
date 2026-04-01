"""Workflow runner for deterministic strategy promotion review."""

from __future__ import annotations

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.core.audit import AgentAuditEvent, AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.policies import AgentSettings
from apps.agents.core.verifier import AgentVerifier
from apps.agents.specialists.strategy_qa import StrategyQAAgent


def run_strategy_promotion_review(
    task: AgentTask,
    *,
    planner: AgentPlanner,
    verifier: AgentVerifier,
    audit_logger: AgentAuditLogger,
    settings: AgentSettings,
    specialist: StrategyQAAgent,
) -> AgentResult:
    """Run the stored-artifact strategy QA workflow."""
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
