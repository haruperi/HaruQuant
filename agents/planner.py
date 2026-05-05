"""Phase 7 CEO planner for governed HaruQuant workflows."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from agents.schemas import AgentPlan


class RequestClassifier(Protocol):
    def classify(self, *, user_request: str, route_catalog: dict[str, "RouteDefinition"]) -> str | None:
        ...


@dataclass(frozen=True)
class RouteDefinition:
    intent: str
    allowed_agents: list[str]
    expected_outputs: list[str]
    response_mode: str = "governed_artifact"
    task_class: str | None = None
    artifact_expected: bool = True
    risk_level: str = "low"
    requires_board_approval: bool = False
    requires_risk_governor: bool = False
    context_needed: list[str] | None = None
    backend_tools_to_run: list[str] | None = None
    attached_tools: list[str] | None = None
    page_actions_to_plan: list[str] | None = None
    evidence_requirements: list[str] | None = None
    blocked_agents: list[str] | None = None
    needs_clarification: bool = False


ROUTE_CATALOG: dict[str, RouteDefinition] = {
    "strategy_creation": RouteDefinition(
        intent="strategy_creation",
        allowed_agents=[
            "research",
            "strategy_creator",
            "strategy_reviewer",
            "backtest",
            "risk_reviewer",
            "audit",
            "ceo",
        ],
        expected_outputs=["ResearchReport", "StrategySpec", "StrategyReview", "BacktestResultSummary", "RiskReview"],
        risk_level="medium",
        requires_risk_governor=True,
        evidence_requirements=["market_context", "strategy_spec", "backtest_summary", "risk_review", "audit_trace"],
    ),
    "backtest_diagnosis": RouteDefinition(
        intent="backtest_diagnosis",
        allowed_agents=["backtest", "strategy_reviewer", "risk_reviewer", "audit", "ceo"],
        expected_outputs=["BacktestResultSummary", "StrategyReview", "RiskReview"],
        risk_level="medium",
        requires_risk_governor=True,
        evidence_requirements=["backtest_run_ref", "diagnostics", "audit_trace"],
    ),
    "optimization_comparison": RouteDefinition(
        intent="optimization_comparison",
        allowed_agents=["backtest", "optimization", "statistical_validation", "risk_reviewer", "audit", "ceo"],
        expected_outputs=["OptimizationComparison", "StatisticalValidation", "RiskReview"],
        risk_level="medium",
        requires_risk_governor=True,
        evidence_requirements=["candidate_runs", "robustness_metrics", "risk_review", "audit_trace"],
    ),
    "risk_review": RouteDefinition(
        intent="risk_review",
        allowed_agents=["risk_reviewer", "audit", "ceo"],
        expected_outputs=["RiskReview"],
        risk_level="high",
        requires_risk_governor=True,
        evidence_requirements=["portfolio_snapshot", "risk_policy", "audit_trace"],
    ),
    "execution_proposal": RouteDefinition(
        intent="execution_proposal",
        allowed_agents=["risk_reviewer", "portfolio_manager", "execution", "audit", "ceo"],
        expected_outputs=["TradeProposal", "RiskReview", "BoardApprovalRequest"],
        risk_level="critical",
        requires_board_approval=True,
        requires_risk_governor=True,
        evidence_requirements=["trade_proposal", "risk_governor_decision", "board_approval", "audit_trace"],
        blocked_agents=["live_execution"],
    ),
    "research": RouteDefinition(
        intent="research",
        allowed_agents=["market_intelligence", "technical_analyst", "strategy_scout", "audit", "ceo"],
        expected_outputs=["MarketIntelligenceReport", "TechnicalAnalysisReport", "StrategyScoutReport"],
        evidence_requirements=["research_sources", "audit_trace"],
    ),
    "reporting": RouteDefinition(
        intent="reporting",
        allowed_agents=["performance_reporter", "audit", "ceo"],
        expected_outputs=["PerformanceReport", "BoardReport"],
        evidence_requirements=["report_inputs", "audit_trace"],
    ),
    "page_action": RouteDefinition(
        intent="page_action",
        allowed_agents=["ceo", "audit"],
        expected_outputs=["PageActionPlan"],
        response_mode="ui_action_plan",
        page_actions_to_plan=["navigate"],
        artifact_expected=False,
        evidence_requirements=["operator_request", "audit_trace"],
    ),
    "clarification": RouteDefinition(
        intent="clarification",
        allowed_agents=["ceo"],
        expected_outputs=["ClarifyingQuestion"],
        response_mode="clarification",
        artifact_expected=False,
        needs_clarification=True,
        evidence_requirements=["operator_request"],
    ),
    "ceo_identity": RouteDefinition(
        intent="ceo_identity",
        allowed_agents=["ceo"],
        expected_outputs=["CEOIdentityMemo"],
        response_mode="direct_answer",
        artifact_expected=False,
        evidence_requirements=["firm_constitution", "risk_policy"],
    ),
    "ceo_answer": RouteDefinition(
        intent="ceo_answer",
        allowed_agents=["ceo", "audit"],
        expected_outputs=["CEOAnswer"],
        response_mode="direct_answer",
        artifact_expected=False,
        evidence_requirements=["firm_context", "audit_trace"],
    ),
    "governed_action_draft": RouteDefinition(
        intent="governed_action_draft",
        allowed_agents=["risk_reviewer", "audit", "ceo"],
        expected_outputs=["GovernedActionDraft", "BoardApprovalRequest"],
        risk_level="high",
        requires_board_approval=True,
        requires_risk_governor=True,
        evidence_requirements=["governance_context", "risk_policy", "audit_trace"],
    ),
}


class PlannerAgent:
    agent_name = "planner"
    planner_source = "phase7_planner_agent"

    def __init__(self, *, request_classifier: RequestClassifier | None = None) -> None:
        self.request_classifier = request_classifier

    def create_plan(self, *, user_request: str, request_id: str | None = None) -> AgentPlan:
        intent = self._classify(user_request)
        route = ROUTE_CATALOG[intent]
        return self._build_plan(user_request=user_request, request_id=request_id, route=route)

    def _classify(self, user_request: str) -> str:
        lowered = user_request.lower().strip()

        safety_intent = self._deterministic_safety_route(lowered)
        if safety_intent:
            return safety_intent

        if self.request_classifier is not None:
            classified = self.request_classifier.classify(user_request=user_request, route_catalog=ROUTE_CATALOG)
            if classified in ROUTE_CATALOG:
                return classified

        if os.getenv("HARUQUANT_CEO_CLASSIFIER_LLM_ENABLED", "false").lower() == "true":
            # The extension point is intentionally bounded to the route catalog. No free-form route is accepted.
            return "ceo_answer"

        return self._deterministic_fallback(lowered)

    def _deterministic_safety_route(self, lowered: str) -> str | None:
        live_terms = ("live trade", "live order", "place a trade", "place live", "buy ", "sell ")
        execution_terms = ("trade proposal", "order", "execute", "execution")
        if any(term in lowered for term in live_terms) or any(term in lowered for term in execution_terms):
            return "execution_proposal"
        if "navigate" in lowered or "open " in lowered or "go to " in lowered:
            return "page_action"
        if lowered in {"help", "?", "hi", "hello"}:
            return "clarification"
        return None

    def _deterministic_fallback(self, lowered: str) -> str:
        if lowered in {"who are you?", "what is your name?", "who are you"} or "who are you" in lowered:
            return "ceo_identity"
        if "approval" in lowered or "approve" in lowered:
            return "governed_action_draft"
        if "diagnose" in lowered or "failed" in lowered:
            return "backtest_diagnosis"
        if "optimization" in lowered or "candidate" in lowered or "robust" in lowered:
            return "optimization_comparison"
        if "risk" in lowered or "exposure" in lowered:
            return "risk_review"
        if "report" in lowered or "board report" in lowered:
            return "reporting"
        if "research" in lowered or "market structure" in lowered:
            return "research"
        if "strategy" in lowered or "backtest" in lowered:
            return "strategy_creation"
        if len(lowered.split()) <= 1:
            return "clarification"
        return "ceo_answer"

    def _build_plan(
        self,
        *,
        user_request: str,
        request_id: str | None,
        route: RouteDefinition,
    ) -> AgentPlan:
        return AgentPlan(
            conversation_plan_id=request_id or f"{self.planner_source}:{route.intent}",
            user_goal=user_request,
            response_mode=route.response_mode,
            task_class=route.task_class or route.intent,
            model_tier="hybrid_governed",
            response_style="structured",
            domain_focus="trading",
            rationale=f"Phase 7 planner selected the governed {route.intent} route.",
            intent=route.intent,
            missing_inputs=["clarify_goal"] if route.needs_clarification else [],
            context_needed=route.context_needed or [],
            backend_tools_to_run=route.backend_tools_to_run or [],
            attached_tools=route.attached_tools or [],
            page_actions_to_plan=route.page_actions_to_plan or [],
            artifact_expected=route.artifact_expected,
            risk_level=route.risk_level,  # type: ignore[arg-type]
            requires_board_approval=route.requires_board_approval,
            requires_risk_governor=route.requires_risk_governor,
            requires_audit_log=True,
            allowed_agents=route.allowed_agents,
            blocked_agents=route.blocked_agents or ["live_execution"],
            expected_outputs=route.expected_outputs,
            evidence_requirements=route.evidence_requirements or ["audit_trace"],
            failure_policy={
                "on_agent_failure": "record_failure_and_continue",
                "on_missing_evidence": "block_promotion_or_execution",
                "on_governance_violation": "escalate_to_board",
            },
            needs_clarification=route.needs_clarification,
            planner_source=self.planner_source,
        )


__all__ = ["PlannerAgent", "ROUTE_CATALOG", "RouteDefinition"]
