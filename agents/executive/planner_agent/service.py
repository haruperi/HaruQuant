"""Phase 7 CEO planner for governed HaruQuant workflows."""

from __future__ import annotations

import os

from agents.executive.planner_agent.contracts import RequestClassifier, RouteDefinition
from agents._shared.schemas import AgentPlan


ROUTE_CATALOG: dict[str, RouteDefinition] = {
    "strategy_creation": RouteDefinition(
        intent="strategy_creation",
        allowed_agents=[
            "research_orchestrator_agent",
            "strategy_creation_orchestrator_agent",
            "strategy_creator_agent",
            "strategy_spec_validator_agent",
            "strategy_rule_normalizer_agent",
            "strategy_template_selector_agent",
            "strategy_risk_assumption_agent",
            "strategy_cost_execution_agent",
            "strategy_test_plan_agent",
            "strategy_codegen_agent",
            "strategy_reviewer_agent",
            "strategy_spec_storage_agent",
            "strategy_code_storage_agent",
            "strategy_handoff_agent",
            "backtest_agent",
            "risk_reviewer_agent",
            "audit",
            "ceo",
        ],
        expected_outputs=[
            "ResearchToStrategyHandoff",
            "StrategySpec",
            "StrategyImplementationBrief",
            "StrategySpecValidationReport",
            "StrategyCodePackage",
            "StrategyReviewReport",
            "StrategySpecStorageReceipt",
            "StrategyCodeStorageReceipt",
            "StrategyValidationHandoffPackage",
            "BacktestResultSummary",
            "RiskReview",
        ],
        risk_level="medium",
        requires_risk_governor=True,
        evidence_requirements=[
            "approved_research_report",
            "validated_strategy_hypothesis",
            "evidence_refs",
            "strategy_spec",
            "generated_code_package",
            "review_report",
            "validation_handoff",
            "audit_trace",
        ],
    ),
    "backtest_diagnosis": RouteDefinition(
        intent="backtest_diagnosis",
        allowed_agents=[
            "simulation_orchestrator_agent",
            "backtest_agent",
            "backtest_analyst_agent",
            "simulation_evidence_curator_agent",
            "strategy_reviewer_agent",
            "risk_reviewer_agent",
            "audit",
            "ceo",
        ],
        expected_outputs=["BacktestResultPackage", "BacktestDiagnosisReport", "SimulationEvidenceIndex", "RiskReview"],
        risk_level="medium",
        requires_risk_governor=True,
        evidence_requirements=["backtest_run_ref", "diagnostics", "audit_trace"],
    ),
    "optimization_comparison": RouteDefinition(
        intent="optimization_comparison",
        allowed_agents=[
            "simulation_orchestrator_agent",
            "backtest_agent",
            "optimization_agent",
            "optimization_comparator_agent",
            "robustness_agent",
            "statistical_validation_agent",
            "simulation_evidence_curator_agent",
            "risk_reviewer_agent",
            "audit",
            "ceo",
        ],
        expected_outputs=["OptimizationPackage", "OptimizationComparison", "RobustnessReport", "StatisticalValidationReport", "RiskReview"],
        risk_level="medium",
        requires_risk_governor=True,
        evidence_requirements=["candidate_runs", "robustness_metrics", "risk_review", "audit_trace"],
    ),
    "simulation": RouteDefinition(
        intent="simulation",
        allowed_agents=[
            "simulation_orchestrator_agent",
            "backtest_agent",
            "backtest_analyst_agent",
            "optimization_agent",
            "optimization_comparator_agent",
            "robustness_agent",
            "statistical_validation_agent",
            "simulation_evidence_curator_agent",
            "risk_reviewer_agent",
            "audit",
            "ceo",
        ],
        expected_outputs=[
            "SimulationPlan",
            "BacktestResultPackage",
            "BacktestDiagnosisReport",
            "OptimizationPackage",
            "OptimizationComparison",
            "RobustnessReport",
            "StatisticalValidationReport",
            "SimulationEvidenceIndex",
            "SimulationDecisionArtifact",
            "SimulationToRiskHandoff",
        ],
        risk_level="medium",
        requires_risk_governor=True,
        evidence_requirements=[
            "validated_strategy_spec",
            "strategy_code_hash",
            "strategy_review_report",
            "market_data_manifest",
            "cost_model",
            "simulation_artifacts",
            "audit_trace",
        ],
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
        allowed_agents=[
            "research_orchestrator_agent",
            "market_intelligence_agent",
            "technical_analyst_agent",
            "strategy_scout_agent",
            "news_sentiment_agent",
            "macro_fundamental_context_agent",
            "cross_asset_intermarket_agent",
            "seasonality_calendar_agent",
            "strategy_hypothesis_agent",
            "research_validation_agent",
            "evidence_curator_agent",
            "audit",
            "ceo",
        ],
        expected_outputs=[
            "ResearchExecutionPlan",
            "AgentRoutingPlan",
            "MarketIntelligenceReport",
            "TechnicalAnalysisReport",
            "StrategyScoutReport",
            "NewsSentimentReport",
            "MacroFundamentalReport",
            "CrossAssetIntermarketReport",
            "SeasonalityCalendarReport",
            "StrategyHypothesisReport",
            "ResearchValidationReport",
            "EvidenceMemoryIndex",
            "FinalResearchReport",
            "ResearchToStrategyHandoff",
        ],
        evidence_requirements=[
            "research_request",
            "market_context",
            "technical_context",
            "strategy_memory",
            "approved_news_sources",
            "macro_context",
            "cross_asset_context",
            "seasonality_context",
            "evidence_refs",
            "audit_trace",
        ],
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

    def plan_read_only_tools(self, *, user_request: str, plan: AgentPlan, attached_tools: list[str] | None = None) -> list[str]:
        lowered = " ".join(user_request.lower().split())
        tool_names: list[str] = []
        allowed_attached = {
            "portfolio_summary",
            "open_positions",
            "backtest_summary",
            "strategy_parameters",
            "optimization_results",
            "risk_snapshot",
            "alert_history",
            "symbol_stats",
        }
        tool_names.extend(tool for tool in attached_tools or [] if tool in allowed_attached)
        if any(term in lowered for term in ("portfolio", "balance", "equity", "account")):
            tool_names.append("portfolio_summary")
        if any(term in lowered for term in ("position", "positions", "open trades")):
            tool_names.append("open_positions")
        if "backtest" in lowered:
            tool_names.append("backtest_summary")
        if "optimization" in lowered or "optimisation" in lowered:
            tool_names.append("optimization_results")
        if any(term in lowered for term in ("strategy parameter", "parameters", "strategy settings")) or plan.intent == "strategy_creation":
            tool_names.append("strategy_parameters")
        if any(term in lowered for term in ("risk", "drawdown", "exposure", "var")) or plan.intent == "risk_review":
            tool_names.append("risk_snapshot")
        if any(term in lowered for term in ("alert", "incident", "kill switch", "history")):
            tool_names.append("alert_history")
        if any(term in lowered for term in ("symbol", "spread", "tick", "price", "stats")):
            tool_names.append("symbol_stats")
        return list(dict.fromkeys(tool_names))

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
        if "simulation" in lowered or "simulate" in lowered or "historical test" in lowered:
            return "simulation"
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
