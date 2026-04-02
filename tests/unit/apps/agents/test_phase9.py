from __future__ import annotations

from apps.agents.core.agent_models import AgentTask
from apps.agents.core.audit import AgentAuditLogger
from apps.agents.core.planner import AgentPlanner
from apps.agents.core.policies import load_agent_settings
from apps.agents.core.verifier import AgentVerifier
from apps.agents.specialists.trade_review_assistant import TradeReviewAssistantAgent
from apps.agents.tools.edge_tools import EdgeTools
from apps.agents.tools.simulator_tools import SimulatorTools
from apps.agents.workflows.trade_review_assistant import run_trade_review_assistant


class _StubSimulatorTools:
    def sim_preview_trade(self, *, session_id: int, trade_request):
        return {
            "governance": {"decision": "accept"},
            "rows": [
                {"item": "Portfolio VaR", "acceptable": True},
                {"item": "Margin Used", "acceptable": True},
            ],
        }

    def sim_run_what_if(self, *, session_id: int, actions, leverage_override=None):
        return {
            "summary": {
                "projected_compliance_state": "compliant",
                "projected_governance_decision": "accept",
            }
        }


class _StubEdgeManager:
    def get_profile_snapshot(self, snapshot_id: int):
        return {
            "snapshot_id": snapshot_id,
            "strategy_fit": [{"archetype": "trend_following", "fit_score": 80.0}],
        }


def test_planner_routes_trade_review_assistant():
    planner = AgentPlanner()
    plan = planner.plan(
        AgentTask(
            "trade-review-plan",
            "trade_review_assistant",
            1,
            "owner",
            "simulation",
            "trade_review_assistant",
            {"session_id": 7, "trade_request": {"side": "buy", "volume": 0.1}},
        )
    )
    assert plan.workflow_name == "trade_review_assistant"
    assert plan.required_inputs == ["session_id", "trade_request"]


def test_trade_review_assistant_workflow_runs(tmp_path):
    result = run_trade_review_assistant(
        AgentTask(
            "trade-review-1",
            "trade_review_assistant",
            1,
            "owner",
            "simulation",
            "trade_review_assistant",
            {
                "session_id": 7,
                "trade_request": {"symbol": "EURUSD", "side": "buy", "volume": 0.1},
                "what_if_actions": [{"action_type": "reduce", "symbol": "EURUSD", "delta_lots": 0.05}],
                "edge_snapshot_id": 21,
            },
            "corr-trade",
            "run-trade",
        ),
        planner=AgentPlanner(),
        verifier=AgentVerifier(),
        audit_logger=AgentAuditLogger(tmp_path / "trade_review.jsonl"),
        settings=load_agent_settings("config/agent_settings.json"),
        specialist=TradeReviewAssistantAgent(
            _StubSimulatorTools(),
            EdgeTools(manager=_StubEdgeManager()),
        ),
    )

    assert result.status == "ok"
    assert result.metadata["workflow"] == "trade_review_assistant"
    assert result.metadata["state"] == "accept"
