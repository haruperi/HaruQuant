"""Deterministic Phase 6 planner."""

from __future__ import annotations

from agents.schemas import AgentPlan


class PlannerAgent:
    agent_name = "planner"

    def create_plan(self, *, user_request: str, request_id: str | None = None) -> AgentPlan:
        lowered = user_request.lower()
        intent = "research"
        allowed_agents = ["research", "audit", "ceo"]
        expected_outputs = ["ResearchReport"]

        if "backtest" in lowered or "strategy" in lowered:
            intent = "strategy_creation"
            allowed_agents = [
                "research",
                "strategy_creator",
                "strategy_reviewer",
                "backtest",
                "risk_reviewer",
                "audit",
                "ceo",
            ]
            expected_outputs = [
                "ResearchReport",
                "StrategySpec",
                "StrategyReview",
                "BacktestResultSummary",
                "RiskReview",
            ]
        elif "risk" in lowered:
            intent = "risk_review"
            allowed_agents = ["risk_reviewer", "audit", "ceo"]
            expected_outputs = ["RiskReview"]

        return AgentPlan(
            conversation_plan_id=request_id or "phase6-plan",
            user_goal=user_request,
            response_mode="governed_artifact",
            task_class=intent,
            model_tier="deterministic",
            response_style="structured",
            domain_focus="trading",
            rationale="Phase 6 deterministic planner routed the request.",
            intent=intent,
            backend_tools_to_run=[],
            artifact_expected=True,
            risk_level="medium" if intent == "strategy_creation" else "low",
            requires_board_approval=False,
            requires_risk_governor=intent in {"strategy_creation", "risk_review"},
            requires_audit_log=True,
            allowed_agents=allowed_agents,
            blocked_agents=["live_execution"],
            expected_outputs=expected_outputs,
            evidence_requirements=["task_trace", "agent_outputs", "audit_log"],
            failure_policy={"on_agent_failure": "record_failure_and_continue"},
        )
