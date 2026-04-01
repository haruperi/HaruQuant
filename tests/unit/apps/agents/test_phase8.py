from __future__ import annotations

from apps.agents.core.agent_models import AgentTask
from apps.agents.core.audit import AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.policies import load_agent_settings
from apps.agents.core.verifier import AgentVerifier
from apps.agents.specialists.live_ops import LiveOpsAgent
from apps.agents.tools.live_tools import LiveTools
from apps.agents.workflows.live_ops_summary import run_live_ops_summary


class _StubLiveManager:
    def get_live_session(self, session_id: int):
        return {
            "session_id": session_id,
            "session_name": "Desk",
            "status": "running",
            "total_signals_detected": 10,
            "total_signals_executed": 7,
            "total_signals_rejected": 3,
            "error_message": "",
        }


def test_planner_routes_live_ops_summary():
    planner = AgentPlanner()
    plan = planner.plan(
        AgentTask(
            "live-ops-plan",
            "live_ops_summary",
            1,
            "ops",
            "live",
            "live_ops_summary",
            {"session_id": 7},
        )
    )
    assert plan.workflow_name == "live_ops_summary"
    assert plan.required_inputs == ["session_id"]


def test_live_ops_summary_workflow_runs(tmp_path):
    result = run_live_ops_summary(
        AgentTask(
            "live-ops",
            "live_ops_summary",
            1,
            "ops",
            "live",
            "live_ops_summary",
            {"session_id": 7},
            "corr-live-ops",
            "run-live-ops",
        ),
        planner=AgentPlanner(),
        verifier=AgentVerifier(),
        audit_logger=AgentAuditLogger(tmp_path / "live_ops.jsonl"),
        settings=load_agent_settings("config/agent_settings.json"),
        specialist=LiveOpsAgent(LiveTools(manager=_StubLiveManager(), active_sessions={})),
    )

    assert result.status == "ok"
    assert result.metadata["workflow"] == "live_ops_summary"
    assert result.metadata["state"] == "running"
