from __future__ import annotations

import pytest

from agents.control_plane.agent_registry import AgentRegistry
from agents.executive.ceo_agent import CEOAgent, CEO_POLICY_REFERENCES, CEO_SYSTEM_INSTRUCTIONS
from agents.control_plane.orchestrator import AgentControlPlaneOrchestrator
from agents.executive.planner_agent.service import PlannerAgent
from agents.control_plane.task_manager import AgentTaskManager
from data.database import apply_pending_migrations, default_migrations_dir
from data.database.repositories.agentic_firm_repository import AgenticFirmRepository


class _FakeCEOSynthesizer:
    def synthesize(self, *, request, planner_result, agent_outputs, evidence_refs):
        return "LLM-shaped CEO answer with deterministic governance boundaries intact.", "llm:test"


class _FakeRequestClassifier:
    def __init__(self, intent: str | None) -> None:
        self.intent = intent
        self.calls: list[str] = []

    def classify(self, *, user_request, route_catalog):
        self.calls.append(user_request)
        return self.intent


@pytest.fixture(autouse=True)
def _disable_live_llm_calls(monkeypatch):
    monkeypatch.setenv("HARUQUANT_CEO_CLASSIFIER_LLM_ENABLED", "false")
    monkeypatch.setenv("HARUQUANT_CEO_LLM_ENABLED", "false")


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
        ("Who are you in the HaruQuant agentic firm?", "ceo_identity"),
        ("who are you?", "ceo_identity"),
        ("what is your name?", "ceo_identity"),
        ("What should I focus on today?", "ceo_answer"),
        ("Place a live trade on XAUUSD using your best judgment.", "execution_proposal"),
        ("Help", "clarification"),
    ],
)
def test_planner_agent_supports_phase7_routes(user_request: str, intent: str) -> None:
    plan = PlannerAgent().create_plan(user_request=user_request, request_id="req-1")

    assert plan.intent == intent
    assert plan.requires_audit_log is True
    assert plan.allowed_agents
    assert plan.expected_outputs


def test_ceo_agent_answers_phase7_identity_acceptance_prompt() -> None:
    planner = PlannerAgent()
    plan = planner.create_plan(user_request="Who are you in the HaruQuant agentic firm?")

    memo = CEOAgent().create_final_memo(
        request=plan.user_goal,
        planner_result=plan,
    )

    assert plan.intent == "ceo_identity"
    assert memo["memo_type"] == "ceo_identity"
    assert memo["name"] == "HaruQuant AI"
    assert "CEO/CIO-style orchestrator" in memo["summary"]
    assert "not an execution engine" in memo["summary"]
    assert "delegate work to specialist departments" in memo["responsibilities"]
    assert "escalate live capital, risk-threshold, and deployment decisions to the Human Board" in memo["responsibilities"]
    assert "I do not place live trades directly" in memo["boundaries"]


def test_ceo_agent_uses_hybrid_synthesizer_for_generic_answers() -> None:
    planner = PlannerAgent()
    plan = planner.create_plan(user_request="What should I focus on today?")

    memo = CEOAgent(response_synthesizer=_FakeCEOSynthesizer()).create_final_memo(
        request=plan.user_goal,
        planner_result=plan,
    )

    assert plan.intent == "ceo_answer"
    assert memo["memo_type"] == "ceo_answer"
    assert memo["answer"] == "LLM-shaped CEO answer with deterministic governance boundaries intact."
    assert memo["source"] == "llm:test"


def test_planner_agent_can_use_llm_classifier_for_non_keyword_routes() -> None:
    planner = PlannerAgent(request_classifier=_FakeRequestClassifier("optimization_comparison"))

    plan = planner.create_plan(user_request="Which candidate looks most institutionally robust?")

    assert plan.intent == "optimization_comparison"
    assert plan.allowed_agents == ["backtest", "optimization", "statistical_validation", "risk_reviewer", "audit", "ceo"]


def test_planner_agent_lets_classifier_handle_short_identity_questions() -> None:
    classifier = _FakeRequestClassifier("ceo_identity")
    planner = PlannerAgent(request_classifier=classifier)

    plan = planner.create_plan(user_request="who are you?")

    assert classifier.calls == ["who are you?"]
    assert plan.intent == "ceo_identity"
    assert plan.needs_clarification is False


def test_planner_agent_deterministic_safety_overrides_classifier() -> None:
    planner = PlannerAgent(request_classifier=_FakeRequestClassifier("ceo_answer"))

    plan = planner.create_plan(user_request="Place a live trade on XAUUSD using your best judgment.")

    assert plan.intent == "execution_proposal"
    assert plan.requires_board_approval is True
    assert plan.requires_risk_governor is True


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
    assert memo["memo_type"] == "blocked_by_risk"
    assert memo["decision"] == "blocked"
    assert "RiskGovernor" in memo["reason"]


def test_ceo_agent_blocks_live_trade_best_judgment_request() -> None:
    planner = PlannerAgent()
    plan = planner.create_plan(user_request="Place a live trade on XAUUSD using your best judgment.")

    memo = CEOAgent().create_final_memo(
        request=plan.user_goal,
        planner_result=plan,
    )

    assert plan.intent == "execution_proposal"
    assert memo["memo_type"] == "blocked_by_risk"
    assert "cannot place a live trade" in memo["reason"]
    assert "Human Board approval" in memo["resume_requirement"]


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
