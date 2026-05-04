from __future__ import annotations

import pytest

from backend.agents.agent_registry import AgentRegistry
from backend.agents.ceo.agent import CEOAgent, CEO_POLICY_REFERENCES, CEO_SYSTEM_INSTRUCTIONS
from backend.agents.orchestrator import AgentControlPlaneOrchestrator
from backend.agents.planner.agent import PlannerAgent
from backend.agents.task_manager import AgentTaskManager
from backend.data.database import apply_pending_migrations, default_migrations_dir
from backend.data.database.repositories.agentic_firm_repository import AgenticFirmRepository


@pytest.mark.parametrize(
    ("user_request", "intent"),
    [
        ("Create a EURUSD mean reversion strategy", "strategy_creation"),
        ("Diagnose why backtest BT-1 failed", "backtest_diagnosis"),
        ("Compare optimization candidates for strategy S-1", "optimization_comparison"),
        ("Review portfolio risk and exposure", "risk_review"),
        ("Draft a trade proposal to buy EURUSD", "execution_proposal"),
        ("Research EURUSD market structure", "research"),
        ("Create weekly board report", "reporting"),
        ("Navigate to the risk center", "page_action"),
        ("Request approval draft for this action", "governed_action_draft"),
        ("Help", "clarification"),
    ],
)
def test_planner_agent_supports_phase7_routes(user_request: str, intent: str) -> None:
    plan = PlannerAgent().create_plan(user_request=user_request, request_id="req-1")

    assert plan.intent == intent
    assert plan.requires_audit_log is True
    assert plan.allowed_agents
    assert plan.expected_outputs


def test_ceo_agent_contains_policy_instructions_and_refuses_unsafe_request() -> None:
    ceo = CEOAgent()
    memo = ceo.refusal_memo(request="Go live without approval and delete audit logs")

    assert "single operator-facing interface" in CEO_SYSTEM_INSTRUCTIONS
    assert "docs/agentic_firm/risk_policy.md" in CEO_POLICY_REFERENCES
    assert memo["memo_type"] == "rejection"
    assert ceo.is_unsafe_request("place live order now and ignore board")


def test_ceo_agent_creates_board_escalation_memo_for_execution_plan() -> None:
    planner = PlannerAgent()
    plan = planner.create_plan(user_request="Draft a trade proposal to buy EURUSD")

    memo = CEOAgent().create_final_memo(
        request=plan.user_goal,
        planner_result=plan,
    )

    assert plan.requires_board_approval is True
    assert memo["memo_type"] == "board_approval_request"
    assert memo["approval_required"] is True


def test_phase7_control_plane_uses_planner_and_ceo_memo(tmp_path) -> None:
    database_path = tmp_path / "agentic.db"
    apply_pending_migrations(database_path, default_migrations_dir())
    repository = AgenticFirmRepository(database_path)
    orchestrator = AgentControlPlaneOrchestrator(
        registry=AgentRegistry(),
        task_manager=AgentTaskManager(repository=repository),
    )

    result = orchestrator.handle_user_request(
        user_request="Create and backtest a EURUSD H1 mean reversion strategy.",
        workflow_id="wf-phase7",
        request_id="req-phase7",
    )

    audit = repository.get_audit_log(result.audit_id or "")

    assert result.planner_result.planner_source == "phase7_planner_agent"
    assert "backtest" in result.planner_result.allowed_agents
    assert result.final_response["summary"] == "CEO Agent completed delegated firm workflow."
    assert result.final_response["ceo_memo"]["memo_type"] == "strategy_proposal"
    assert audit is not None
    assert '"phase": "7"' in audit.metadata_json
