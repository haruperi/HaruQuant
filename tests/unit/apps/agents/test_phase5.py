from __future__ import annotations

import json

from apps.agents.core.agent_models import AgentTask
from apps.agents.core.audit import AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.policies import load_agent_settings
from apps.agents.core.verifier import AgentVerifier
from apps.agents.specialists.edge_intelligence import EdgeIntelligenceAgent
from apps.agents.specialists.execution_oversight import ExecutionOversightAgent
from apps.agents.specialists.portfolio_allocator import PortfolioAllocationAgent
from apps.agents.tools.edge_tools import EdgeTools
from apps.agents.tools.live_tools import LiveTools
from apps.agents.tools.risk_tools import RiskTools
from apps.agents.workflows.execution_quality_watch import run_execution_quality_watch
from apps.agents.workflows.portfolio_allocation_review import run_portfolio_allocation_review
from apps.agents.workflows.snapshot_drift_watch import run_snapshot_drift_watch


class _StubEdgeManager:
    def get_profile_snapshots(self, symbol: str, timeframe: str, limit: int = 5):
        return [
            {"snapshot_id": 21, "symbol": symbol, "timeframe": timeframe},
            {"snapshot_id": 20, "symbol": symbol, "timeframe": timeframe},
        ]

    def get_profile_snapshot(self, snapshot_id: int):
        return {
            "snapshot_id": snapshot_id,
            "symbol": "EURUSD",
            "timeframe": "H1",
            "strategy_fit": [
                {
                    "archetype": "trend_following" if snapshot_id == 21 else "mean_reversion",
                    "fit_score": 81.0 if snapshot_id == 21 else 74.0,
                }
            ],
        }

    def compare_profile_snapshots(self, left_snapshot_id: int, right_snapshot_id: int):
        return {
            "left_snapshot": {
                "snapshot_id": left_snapshot_id,
                "primary_strategy_fit": {"archetype": "mean_reversion", "fit_score": 74.0},
            },
            "right_snapshot": {
                "snapshot_id": right_snapshot_id,
                "primary_strategy_fit": {"archetype": "trend_following", "fit_score": 81.0},
            },
            "metric_diffs": [{"key": "score.a", "left_value": 1, "right_value": 2}],
            "score_diffs": [{"score_key": "final_score", "left_score": 70.0, "right_score": 78.0}],
        }


class _StubLiveManager:
    def get_live_session(self, session_id: int):
        return {
            "session_id": session_id,
            "session_name": "Desk",
            "status": "running",
            "total_signals_detected": 10,
            "total_signals_executed": 6,
            "total_signals_rejected": 4,
            "error_message": "",
        }


class _StubRiskManager:
    def get_risk_snapshot_bundle(self, snapshot_id: int):
        return {
            "snapshot": {"snapshot_id": snapshot_id, "run_id": 42},
            "recommendations": [
                {"action_type": "reduce", "symbol": "EURUSD", "delta_lots": -0.1},
                {"action_type": "rebalance", "symbol": "GBPUSD", "delta_lots": 0.05},
            ],
        }


def test_planner_routes_phase5_workflows():
    planner = AgentPlanner()
    assert planner.plan(
        AgentTask("a", "snapshot_drift_watch", 1, "owner", "edge", "snapshot_drift_watch", {})
    ).workflow_name == "snapshot_drift_watch"
    assert planner.plan(
        AgentTask("b", "execution_quality_watch", 1, "owner", "live", "execution_quality_watch", {"session_id": 1})
    ).workflow_name == "execution_quality_watch"
    assert planner.plan(
        AgentTask("c", "portfolio_allocation_review", 1, "owner", "risk", "portfolio_allocation_review", {"snapshot_id": 1})
    ).workflow_name == "portfolio_allocation_review"


def test_snapshot_drift_watch_workflow_runs(tmp_path):
    result = run_snapshot_drift_watch(
        AgentTask(
            "edge-drift",
            "snapshot_drift_watch",
            1,
            "research",
            "edge",
            "snapshot_drift_watch",
            {"symbol": "EURUSD", "timeframe": "H1"},
            "corr-edge",
            "run-edge",
        ),
        planner=AgentPlanner(),
        verifier=AgentVerifier(),
        audit_logger=AgentAuditLogger(tmp_path / "edge_drift.jsonl"),
        settings=load_agent_settings("config/agent_settings.json"),
        specialist=EdgeIntelligenceAgent(EdgeTools(manager=_StubEdgeManager())),
    )
    assert result.status == "ok"
    assert "Primary fit changed" in result.summary


def test_execution_quality_watch_workflow_runs(tmp_path):
    result = run_execution_quality_watch(
        AgentTask(
            "exec-watch",
            "execution_quality_watch",
            1,
            "ops",
            "live",
            "execution_quality_watch",
            {"session_id": 7},
            "corr-exec",
            "run-exec",
        ),
        planner=AgentPlanner(),
        verifier=AgentVerifier(),
        audit_logger=AgentAuditLogger(tmp_path / "exec_watch.jsonl"),
        settings=load_agent_settings("config/agent_settings.json"),
        specialist=ExecutionOversightAgent(LiveTools(manager=_StubLiveManager(), active_sessions={})),
    )
    assert result.status == "ok"
    assert result.metadata["state"] == "normal"


def test_portfolio_allocation_review_workflow_runs(tmp_path):
    audit_path = tmp_path / "allocation.jsonl"
    result = run_portfolio_allocation_review(
        AgentTask(
            "alloc",
            "portfolio_allocation_review",
            1,
            "pm",
            "risk",
            "portfolio_allocation_review",
            {"snapshot_id": 8, "edge_snapshot_id": 21},
            "corr-alloc",
            "run-alloc",
        ),
        planner=AgentPlanner(),
        verifier=AgentVerifier(),
        audit_logger=AgentAuditLogger(audit_path),
        settings=load_agent_settings("config/agent_settings.json"),
        specialist=PortfolioAllocationAgent(
            RiskTools(manager=_StubRiskManager(), what_if_engine=type("W", (), {})(), what_if_serializer=lambda x: x),
            EdgeTools(manager=_StubEdgeManager()),
        ),
    )
    assert result.status == "ok"
    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert entries[0]["workflow_name"] == "portfolio_allocation_review"
