"""Workflow runner for the consolidated daily desk pack."""

from __future__ import annotations

from typing import List

from apps.agents.core.agent_models import AgentResult, AgentTask
from apps.agents.core.audit import AgentAuditEvent, AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.policies import AgentSettings
from apps.agents.core.reporter import AgentReporter
from apps.agents.core.tool_registry import ToolRegistry
from apps.agents.core.verifier import AgentVerifier
from apps.agents.specialists.incident_investigator import IncidentInvestigatorAgent
from apps.agents.specialists.live_ops import LiveOpsAgent
from apps.agents.specialists.research_orchestrator import ResearchOrchestratorAgent
from apps.agents.specialists.risk_supervisor import RiskSupervisorAgent
from apps.agents.specialists.strategy_qa import StrategyQAAgent
from apps.agents.tools.edge_tools import EdgeTools
from apps.agents.tools.live_tools import LiveTools
from apps.agents.tools.risk_tools import RiskTools
from apps.agents.workflows.daily_market_brief import run_daily_market_brief
from apps.agents.workflows.incident_review import run_incident_review
from apps.agents.workflows.live_ops_summary import run_live_ops_summary
from apps.agents.workflows.live_risk_watch import run_live_risk_watch
from apps.agents.workflows.strategy_promotion_review import run_strategy_promotion_review


def run_daily_desk_pack(
    task: AgentTask,
    *,
    planner: AgentPlanner,
    verifier: AgentVerifier,
    audit_logger: AgentAuditLogger,
    settings: AgentSettings,
    reporter: AgentReporter,
    tool_registry: ToolRegistry,
    edge_tools: EdgeTools,
    risk_tools: RiskTools,
    live_tools: LiveTools,
) -> AgentResult:
    """Run the consolidated desk-pack workflow over existing workflow outputs."""
    plan = planner.plan(task)
    sub_results: List[tuple[str, AgentResult]] = []

    brief_task = _subtask(task, "daily_market_brief", {"symbol", "timeframe"})
    brief_result = run_daily_market_brief(
        brief_task,
        planner=planner,
        verifier=verifier,
        audit_logger=audit_logger,
        settings=settings,
        specialist=ResearchOrchestratorAgent(edge_tools),
    )
    sub_results.append(("daily_market_brief", brief_result))

    risk_task = _subtask(task, "live_risk_watch", {"snapshot_id"})
    risk_result = run_live_risk_watch(
        risk_task,
        planner=planner,
        verifier=verifier,
        audit_logger=audit_logger,
        settings=settings,
        specialist=RiskSupervisorAgent(risk_tools),
    )
    sub_results.append(("live_risk_watch", risk_result))

    if task.input_payload.get("session_id") not in (None, "", 0):
        live_ops_task = _subtask(task, "live_ops_summary", {"session_id"})
        live_ops_result = run_live_ops_summary(
            live_ops_task,
            planner=planner,
            verifier=verifier,
            audit_logger=audit_logger,
            settings=settings,
            specialist=LiveOpsAgent(live_tools),
        )
        sub_results.append(("live_ops_summary", live_ops_result))

    if _has_keys(task, "backtest_id", "optimization_id", "strategy_version_id"):
        strategy_task = _subtask(
            task,
            "strategy_promotion_review",
            {"backtest_id", "optimization_id", "strategy_version_id", "monte_carlo_id"},
        )
        strategy_result = run_strategy_promotion_review(
            strategy_task,
            planner=planner,
            verifier=verifier,
            audit_logger=audit_logger,
            settings=settings,
            specialist=StrategyQAAgent(tool_registry),
        )
        sub_results.append(("strategy_promotion_review", strategy_result))

    if task.input_payload.get("incident_run_id") not in (None, "", 0):
        incident_task = _subtask(task, "incident_review", {"incident_run_id"}, aliases={"incident_run_id": "run_id"})
        incident_result = run_incident_review(
            incident_task,
            planner=planner,
            verifier=verifier,
            audit_logger=audit_logger,
            settings=settings,
            specialist=IncidentInvestigatorAgent(risk_tools),
        )
        sub_results.append(("incident_review", incident_result))

    sections = [reporter.section_from_result(name, result) for name, result in sub_results]
    summary = _build_summary(sub_results)
    packet = reporter.build_packet(
        report_name=f"daily_desk_pack_{task.task_id}",
        title="Daily Desk Pack",
        summary=summary,
        sections=sections,
        metadata={"workflow": "daily_desk_pack"},
    )
    artifact_bundle = reporter.write_packet(packet)
    result = AgentResult(
        status="ok",
        summary=summary,
        evidence=[
            {"type": "desk_pack_section", "workflow": name, "status": child.status}
            for name, child in sub_results
        ],
        recommendations=[],
        required_actions=[],
        warnings=[warning for _, child in sub_results for warning in child.warnings],
        confidence=0.8,
        metadata={
            "workflow": "daily_desk_pack",
            "artifact_refs": artifact_bundle["artifact_refs"],
            "section_count": len(sections),
        },
    )
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
            metadata={"task_type": task.task_type, "artifact_refs": artifact_bundle["artifact_refs"]},
        )
    )
    return result


def _subtask(
    task: AgentTask,
    task_type: str,
    allowed_keys: set[str],
    *,
    aliases: dict[str, str] | None = None,
) -> AgentTask:
    payload = {}
    alias_map = aliases or {}
    for key in allowed_keys:
        if key in task.input_payload:
            payload[alias_map.get(key, key)] = task.input_payload[key]
    return AgentTask(
        task_id=f"{task.task_id}:{task_type}",
        task_type=task_type,
        actor_user_id=task.actor_user_id,
        actor_role=task.actor_role,
        scope=task.scope,
        intent=task_type,
        input_payload=payload,
        correlation_id=task.correlation_id,
        run_id=task.run_id,
        approval_mode=task.approval_mode,
    )


def _has_keys(task: AgentTask, *keys: str) -> bool:
    return all(task.input_payload.get(key) not in (None, "", []) for key in keys)


def _build_summary(sub_results: List[tuple[str, AgentResult]]) -> str:
    states = [f"{name}={result.status}" for name, result in sub_results]
    return f"Daily desk pack compiled from {len(sub_results)} workflow(s): " + ", ".join(states) + "."
