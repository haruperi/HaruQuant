from __future__ import annotations

from pathlib import Path

from agents.portfolio.portfolio_manager_agent.activation import LiveActivationRequest, LiveActivationWorkflow
from agents.audit import AuditAgent, IncidentAgent
from agents._shared import AgentRunContext
from agents.operations_audit.cost_optimizer_agent.service import CostOptimizerAgent
from agents.operations_audit.audit_compliance_agent.debate import DebateTranscript
from agents.control_plane.evaluation import AgentEvaluationFramework
from agents.portfolio.live_execution_agent import LiveExecutionAgent
from agents.portfolio.synthesis_trader_agent import SynthesisTraderAgent
from agents.control_plane.operating_cycle import OperatingCycleRunner
from agents.research.bear_researcher_agent import BearResearcherAgent
from agents.research.bull_researcher_agent import BullResearcherAgent
from execution.ctrader_bridge import CTraderBridge
from execution.mt5_bridge import MT5Bridge
from execution.order_router import OrderRouter
from services.risk.safety.kill_switch import KillSwitchService


ROOT = Path(__file__).resolve().parents[4]


def test_phase22_dashboard_routes_exist() -> None:
    for route in ("ai-ceo", "agents", "strategy-lab", "backtests", "risk-center", "board-room"):
        assert (ROOT / "ui" / "src" / "app" / "(dashboard)" / route / "page.tsx").exists()


def test_phase23_live_bridges_and_router_fail_closed() -> None:
    mt5 = MT5Bridge(live_enabled=False)
    ctrader = CTraderBridge(live_enabled=False)
    router = OrderRouter()

    assert mt5.get_account_info()["live_enabled"] is False
    assert mt5.place_order({"symbol": "EURUSD"})["status"] == "blocked"
    assert ctrader.normalize_order_status("FILLED") == "filled"

    routed = router.route_order(
        order={"strategy_id": "s1", "symbol": "EURUSD", "side": "buy", "requested_size": 0.01},
        approval_token=None,
        live_config={"global_live_mode": False, "strategies": {}},
        broker_status={"heartbeat": "healthy"},
        kill_switch_status="healthy",
    )
    assert routed["status"] == "rejected"
    assert "missing_risk_approval_token" in routed["reasons"]


def test_phase24_kill_switch_and_incident_agent() -> None:
    incident = KillSwitchService().evaluate({"daily_loss": 0.05, "broker_connection": "disconnected"})
    memo = IncidentAgent().summarize({"severity": "critical", "trigger": "daily_loss", "affected_strategies": ["s1"]})

    assert incident["status"] == "triggered"
    assert incident["disable_new_orders"] is True
    assert memo["requires_human_approval_to_resume"] is True


def test_phase25_activation_workflow_and_config() -> None:
    request = LiveActivationRequest(
        strategy_id="s1",
        strategy_version="0.1.0",
        backtest_evidence=["bt"],
        robustness_evidence=["robust"],
        paper_trading_evidence=["paper"],
        risk_memo="risk",
        portfolio_memo="portfolio",
        requested_allocation=0.02,
        max_risk_per_trade=0.005,
        kill_switch_status="healthy",
        broker_readiness_status="ready",
    )
    decision = LiveActivationWorkflow().request_board_approval(request)

    assert decision.status == "pending_board"
    assert "approve_micro_live" in decision.evidence_pack["approval_options"]
    assert (ROOT / "config" / "live_trading.yaml").exists()


def test_phase26_live_execution_blocks_without_gates() -> None:
    result = LiveExecutionAgent().run(
        context=AgentRunContext(workflow_id="wf", task_id="task", user_request="live"),
        task_input={"live_mode_enabled": False, "strategy_state": "paper", "kill_switch_status": "healthy"},
    )
    assert result.status == "blocked"
    assert "live_mode_disabled" in result.output["blocked_reasons"]


def test_phase27_audit_agent_detects_critical_violations() -> None:
    report = AuditAgent().audit(records={"live_orders": [{"order_id": "o1", "proposal_id": "p1"}]})

    assert report["critical_audit_failure_disables_live_trading"] is True
    assert report["live_trading_allowed"] is False


def test_phase28_cost_optimizer_tracks_costs_and_routes_models() -> None:
    report = CostOptimizerAgent().summarize_costs(
        [
            {
                "model_provider": "openai",
                "model_name": "strong",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "cost": 1.25,
                "task_id": "t1",
                "agent_name": "ceo",
                "workflow_id": "wf",
                "strategy_id": "s1",
                "strategy_outcome": "accepted",
            }
        ]
    )

    assert report["daily_cost_report"]["total_cost"] == 1.25
    assert report["model_routes"]["order_placement"] == "no_llm"


def test_phase29_debate_layer_stores_evidence_bound_transcript() -> None:
    bull = BullResearcherAgent().argue(evidence_refs=["e1"], context={})
    bear = BearResearcherAgent().argue(evidence_refs=["e1"], context={})
    synthesis = SynthesisTraderAgent().synthesize(
        analyst_reports=[],
        bull_memo=bull,
        bear_memo=bear,
        risk_governor_output={"decision": "approved"},
    )
    transcript = DebateTranscript().store(
        strategy_id="s1",
        bull_memo=bull,
        bear_memo=bear,
        synthesis_memo=synthesis,
        portfolio_decision={"decision": "admit_to_paper"},
        evidence_refs=["e1"],
    )

    assert bull["uses_only_evidence_refs"] is True
    assert bear["uses_only_evidence_refs"] is True
    assert synthesis["never_place_order_directly"] is True
    assert transcript["evidence_refs"] == ["e1"]


def test_phase30_evaluation_framework_passes_core_checks() -> None:
    result = AgentEvaluationFramework().run_all()

    assert result["passed"] is True


def test_phase31_operating_cycle_runs_all_cadences() -> None:
    cycle = OperatingCycleRunner().run_full_cycle()

    assert set(cycle) == {"daily", "weekly", "monthly"}
    assert cycle["daily"]["strategy_signals_checked"] is True
    assert cycle["weekly"]["board_decisions"] == "pending_human_board"
    assert cycle["monthly"]["review_risk_policy"] is True




