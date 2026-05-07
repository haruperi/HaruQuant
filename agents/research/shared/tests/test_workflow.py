from __future__ import annotations

from agents._shared.base_contracts import AgentContext, AgentRequest
from agents.executive.planner_agent.service import PlannerAgent
from agents.research.shared.workflow import run_research_workflow_sync


def test_research_workflow_runs_and_merges_department_package():
    package = run_research_workflow_sync(
        AgentRequest(
            request_id="research-workflow-test",
            agent_name="research_orchestrator_agent",
            task="Research EURUSD H1 context.",
            payload={"symbol": "EURUSD", "timeframe": "H1"},
        ),
        AgentContext(session_id="ctx-research-workflow-test"),
    )

    assert package.research_execution_plan
    assert package.agent_routing_plan["market_context"] == "market_intelligence_agent"
    assert len(package.agent_responses) == 10
    assert package.merged_research_package
    assert package.final_research_report["report_type"] == "final_research_report"
    assert package.research_to_strategy_handoff is not None
    assert package.audit["evidence_memory_saved"]


def test_planner_registers_full_research_department_route():
    plan = PlannerAgent().create_plan(user_request="Research EURUSD market structure")

    assert plan.intent == "research"
    assert "research_orchestrator_agent" in plan.allowed_agents
    assert "evidence_curator_agent" in plan.allowed_agents
    assert "ResearchToStrategyHandoff" in plan.expected_outputs
