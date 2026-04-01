from __future__ import annotations

import json

from apps.agents.core.agent_models import AgentTask
from apps.agents.core.audit import AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.policies import load_agent_settings
from apps.agents.core.verifier import AgentVerifier
from apps.agents.specialists.incident_investigator import IncidentInvestigatorAgent
from apps.agents.specialists.research_orchestrator import ResearchOrchestratorAgent
from apps.agents.specialists.risk_supervisor import RiskSupervisorAgent
from apps.agents.tools.edge_tools import EdgeTools
from apps.agents.tools.risk_tools import RiskTools
from apps.agents.workflows.daily_market_brief import run_daily_market_brief
from apps.agents.workflows.incident_review import run_incident_review
from apps.agents.workflows.live_risk_watch import run_live_risk_watch


class _StubEdgeManager:
    def get_profile_snapshots(self, symbol: str, timeframe: str, limit: int = 5):
        return [
            {"snapshot_id": 11, "symbol": symbol, "timeframe": timeframe},
            {"snapshot_id": 10, "symbol": symbol, "timeframe": timeframe},
        ]

    def get_profile_snapshot(self, snapshot_id: int):
        score = 78.0 if snapshot_id == 11 else 74.0
        return {
            "snapshot_id": snapshot_id,
            "symbol": "EURUSD",
            "timeframe": "H1",
            "scorecard_summary": {
                "final_score": score,
                "readiness_label": "research_ready",
            },
            "strategy_fit": [
                {
                    "archetype": "trend_following",
                    "fit_score": 81.0,
                    "rationale": "Persistent directional structure.",
                }
            ],
        }


class _StubRiskManager:
    def get_risk_snapshot_bundle(self, snapshot_id: int):
        return {
            "snapshot": {"snapshot_id": snapshot_id, "run_id": 42, "as_of": "2026-04-01T09:00:00"},
            "metric_rows": [],
            "score_rows": [],
            "policy_events": [],
            "recommendations": [
                {"action_type": "reduce", "symbol": "EURUSD", "delta_lots": -0.1, "usefulness_score": 8.0}
            ],
            "scenarios": [
                {"scenario_name": "stress", "loss": -1200.0, "stressed_var": 900.0, "stressed_es": 1100.0}
            ],
        }

    def get_risk_run(self, run_id: int):
        return {"run_id": run_id, "label": "demo"}

    def get_risk_replay_frames(self, run_id: int):
        return [
            {
                "frame_timestamp": "2026-04-01T08:00:00",
                "score_summary_json": {"overall_risk_quality_score": 65.0},
                "cockpit_payload_json": {"governance": {"status": "warning"}, "regime": {"name": "stress"}},
                "what_if_summary_json": None,
            },
            {
                "frame_timestamp": "2026-04-01T09:00:00",
                "score_summary_json": {"overall_risk_quality_score": 55.0},
                "cockpit_payload_json": {"governance": {"status": "breach"}, "regime": {"name": "crisis"}},
                "what_if_summary_json": {"delta": -10},
            },
        ]


def test_planner_routes_phase2_workflows():
    planner = AgentPlanner()

    assert planner.plan(
        AgentTask(
            task_id="1",
            task_type="daily_market_brief",
            actor_user_id=1,
            actor_role="owner",
            scope="edge",
            intent="daily_market_brief",
            input_payload={"symbol": "EURUSD", "timeframe": "H1"},
        )
    ).workflow_name == "daily_market_brief"
    assert planner.plan(
        AgentTask(
            task_id="2",
            task_type="live_risk_watch",
            actor_user_id=1,
            actor_role="owner",
            scope="risk",
            intent="live_risk_watch",
            input_payload={"snapshot_id": 7},
        )
    ).workflow_name == "live_risk_watch"
    assert planner.plan(
        AgentTask(
            task_id="3",
            task_type="incident_review",
            actor_user_id=1,
            actor_role="owner",
            scope="risk",
            intent="incident_review",
            input_payload={"run_id": 42},
        )
    ).workflow_name == "incident_review"


def test_verifier_requires_workflow_inputs():
    verifier = AgentVerifier()
    settings = load_agent_settings("config/agent_settings.json")
    plan = AgentPlanner().plan(
        AgentTask(
            task_id="4",
            task_type="live_risk_watch",
            actor_user_id=1,
            actor_role="owner",
            scope="risk",
            intent="live_risk_watch",
            input_payload={},
        )
    )
    result = RiskSupervisorAgent(RiskTools(manager=_StubRiskManager())).run(
        AgentTask(
            task_id="4",
            task_type="live_risk_watch",
            actor_user_id=1,
            actor_role="owner",
            scope="risk",
            intent="live_risk_watch",
            input_payload={"snapshot_id": 1},
            correlation_id="corr-4",
        )
    )

    verification = verifier.verify(
        AgentTask(
            task_id="4",
            task_type="live_risk_watch",
            actor_user_id=1,
            actor_role="owner",
            scope="risk",
            intent="live_risk_watch",
            input_payload={},
            correlation_id="corr-4",
        ),
        result,
        plan=plan,
        settings=settings,
    )

    assert verification.status == "incomplete_evidence"
    assert "missing_required_input:snapshot_id" in verification.warnings


def test_daily_market_brief_workflow_runs_with_stub_edge_manager(tmp_path):
    task = AgentTask(
        task_id="task-edge",
        task_type="daily_market_brief",
        actor_user_id=5,
        actor_role="research",
        scope="edge",
        intent="daily_market_brief",
        input_payload={"symbol": "EURUSD", "timeframe": "H1"},
        correlation_id="corr-edge",
        run_id="run-edge",
    )
    result = run_daily_market_brief(
        task,
        planner=AgentPlanner(),
        verifier=AgentVerifier(),
        audit_logger=AgentAuditLogger(tmp_path / "edge_audit.jsonl"),
        settings=load_agent_settings("config/agent_settings.json"),
        specialist=ResearchOrchestratorAgent(EdgeTools(manager=_StubEdgeManager())),
    )

    assert result.status == "ok"
    assert "Latest Edge snapshot" in result.summary
    assert result.evidence[0]["snapshot_id"] == 11


def test_live_risk_watch_workflow_runs_with_stub_risk_manager(tmp_path):
    task = AgentTask(
        task_id="task-risk",
        task_type="live_risk_watch",
        actor_user_id=5,
        actor_role="risk_manager",
        scope="risk",
        intent="live_risk_watch",
        input_payload={"snapshot_id": 7},
        correlation_id="corr-risk",
        run_id="run-risk",
    )
    result = run_live_risk_watch(
        task,
        planner=AgentPlanner(),
        verifier=AgentVerifier(),
        audit_logger=AgentAuditLogger(tmp_path / "risk_audit.jsonl"),
        settings=load_agent_settings("config/agent_settings.json"),
        specialist=RiskSupervisorAgent(RiskTools(manager=_StubRiskManager())),
    )

    assert result.status == "ok"
    assert result.metadata["state"] == "unknown"
    assert result.evidence[0]["snapshot_id"] == 7


def test_incident_review_workflow_runs_with_stub_risk_manager(tmp_path):
    audit_path = tmp_path / "incident_audit.jsonl"
    task = AgentTask(
        task_id="task-incident",
        task_type="incident_review",
        actor_user_id=5,
        actor_role="ops",
        scope="risk",
        intent="incident_review",
        input_payload={"run_id": 42},
        correlation_id="corr-incident",
        run_id="run-incident",
    )
    result = run_incident_review(
        task,
        planner=AgentPlanner(),
        verifier=AgentVerifier(),
        audit_logger=AgentAuditLogger(audit_path),
        settings=load_agent_settings("config/agent_settings.json"),
        specialist=IncidentInvestigatorAgent(RiskTools(manager=_StubRiskManager())),
    )

    assert result.status == "ok"
    assert result.evidence[0]["frame_count"] == 2
    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert entries[0]["workflow_name"] == "incident_review"
