"""Planner Agent for firm-level request routing."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from backend.agents.base import AgentRunContext, AgentRunResult, BaseAgent
from backend.agents.intent_router import IntentRouterAgent, IntentRouterError, intent_router_agent
from backend.agents.permissions import AgentToolPermissionService
from backend.services.ai_chat.conversation_planner import ConversationPlanner
from backend.services.ai_chat.models import ConversationPlan

PLANNER_AGENT_DEPARTMENT = "planner"


@dataclass(frozen=True)
class PlannerRoute:
    """One deterministic route supported by the firm Planner Agent."""

    intent: str
    task_class: str
    response_style: str
    domain_focus: str
    artifact_expected: str | None
    allowed_agents: tuple[str, ...]
    backend_tools: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    risk_level: str = "read_only"
    requires_board_approval: bool = False
    requires_risk_governor: bool = False
    answer_mode: str = "governed_artifact"


@dataclass(frozen=True)
class RouteCatalogEntry:
    intent: str
    description: str
    examples: tuple[str, ...]


ROUTE_CATALOG: tuple[RouteCatalogEntry, ...] = (
    RouteCatalogEntry("strategy_creation", "Create or draft a strategy idea, strategy spec, or strategy artifact.", ("Create a EURUSD H1 mean reversion strategy.",)),
    RouteCatalogEntry("backtest_diagnosis", "Diagnose, analyze, or review existing backtest behavior and metrics.", ("Why did backtest BT-42 fail?",)),
    RouteCatalogEntry("optimization_comparison", "Compare, rank, or select optimization candidates or parameter runs.", ("Which optimization candidate is strongest?",)),
    RouteCatalogEntry("risk_review", "Review portfolio risk, exposure, drawdown, loss limits, or RiskGovernor context.", ("Review current portfolio exposure.",)),
    RouteCatalogEntry("execution_proposal", "Any live order, live trade, buy/sell request, execution proposal, or capital-affecting action.", ("Place a live trade on XAUUSD.",)),
    RouteCatalogEntry("research", "Research markets, regimes, market structure, strategy themes, or opportunities.", ("Research EURUSD market structure.",)),
    RouteCatalogEntry("reporting", "Create or summarize daily, weekly, Board, performance, risk, or audit reports.", ("Create weekly Board report.",)),
    RouteCatalogEntry("page_action", "Operate or navigate the UI, click, filter, open, or select dashboard elements.", ("Navigate to the risk center.",)),
    RouteCatalogEntry("governed_action_draft", "Draft an approval request or governed action without executing it.", ("Draft an approval request for this change.",)),
    RouteCatalogEntry("ceo_identity", "Ask the CEO's name, identity, role, or how the firm interface works.", ("Who are you in the HaruQuant agentic firm?", "What is your name?")),
    RouteCatalogEntry("ceo_answer", "General CEO conversation, explanations, advice, and questions that do not require a specialist workflow.", ("What should I focus on today?",)),
    RouteCatalogEntry("clarification", "Too vague to classify; requires a clarifying question before planning.", ("Help.",)),
)


class FirmRequestClassifier(Protocol):
    def classify(self, *, user_request: str, route_catalog: tuple[RouteCatalogEntry, ...]) -> str | None: ...


class PlannerAgent(BaseAgent):
    """Structured Planner Agent used by the firm control plane."""

    agent_name = "planner"
    role = "Planner Agent"
    allowed_tools = (
        "get_symbol_data",
        "get_latest_ohlcv",
        "get_strategy",
        "list_strategies",
        "get_backtest_result",
        "get_analytics_summary",
        "get_open_positions",
        "get_account_snapshot",
        "get_risk_snapshot",
        "create_strategy_spec",
        "create_report",
        "create_trade_proposal",
        "request_risk_approval",
    )

    def __init__(
        self,
        *,
        permission_service: AgentToolPermissionService | None = None,
        request_classifier: FirmRequestClassifier | None = None,
    ) -> None:
        super().__init__(permission_service=permission_service)
        self.request_classifier = request_classifier or DefaultFirmRequestClassifier()

    def create_plan(self, *, user_request: str, request_id: str | None = None) -> ConversationPlan:
        route = self._select_route(user_request)
        return ConversationPlan(
            conversation_plan_id=f"plan-{uuid4().hex}",
            user_goal=user_request,
            answer_mode=route.answer_mode,
            response_mode="answer",
            task_class=route.task_class,
            model_tier="premium" if route.requires_risk_governor else "standard",
            response_style=route.response_style,
            domain_focus=route.domain_focus,
            rationale=f"Planner Agent selected {route.intent} from governed request analysis.",
            needs_clarification=route.intent == "clarification",
            clarification_question=self._clarification_question() if route.intent == "clarification" else None,
            intent=route.intent,
            backend_tools_to_run=list(route.backend_tools),
            tools_to_run=list(route.backend_tools),
            agents_to_consult=list(route.allowed_agents),
            allowed_agents=list(route.allowed_agents),
            artifact_expected=route.artifact_expected,
            risk_level=route.risk_level,
            requires_board_approval=route.requires_board_approval,
            requires_risk_governor=route.requires_risk_governor,
            requires_audit_log=True,
            expected_outputs=list(route.expected_outputs),
            evidence_requirements=list(route.evidence_requirements),
            failure_policy={
                "default": "fail_parent_if_required_child_fails",
                "blocked": "return_ceo_blocked_memo",
            },
            planner_source="phase7_planner_agent",
            planner_confidence=0.9 if route.intent != "clarification" else 0.62,
        )

    def run(self, *, context: AgentRunContext, task_input: dict[str, object]) -> AgentRunResult:
        user_request = str(
            task_input.get("user_request")
            or context.user_request
            or task_input.get("description")
            or ""
        )
        plan = self.create_plan(user_request=user_request, request_id=context.request_id)
        return AgentRunResult(
            agent_name=self.agent_name,
            task_id=context.task_id,
            status="completed",
            output=plan.model_dump(mode="json"),
            observations=(
                {
                    "observation_type": "planner_route",
                    "summary": f"Planner selected {plan.intent}.",
                    "confidence": plan.planner_confidence,
                },
            ),
            decisions=(
                {
                    "decision_type": "report",
                    "decision": plan.intent,
                    "rationale": plan.rationale,
                },
            ),
        )

    def _select_route(self, user_request: str) -> PlannerRoute:
        normalized = user_request.lower().strip()
        if self._is_execution_proposal(normalized):
            return self._route_for_intent("execution_proposal")
        classified_intent = self.request_classifier.classify(
            user_request=user_request,
            route_catalog=ROUTE_CATALOG,
        )
        if classified_intent:
            return self._route_for_intent(classified_intent)
        if self._is_ceo_identity(normalized):
            return self._route_for_intent("ceo_identity")
        if self._is_page_action(normalized):
            return self._route_for_intent("page_action")
        if self._is_governed_action_draft(normalized):
            return self._route_for_intent("governed_action_draft")
        if self._is_optimization_comparison(normalized):
            return self._route_for_intent("optimization_comparison")
        if self._is_backtest_diagnosis(normalized):
            return self._route_for_intent("backtest_diagnosis")
        if self._is_risk_review(normalized):
            return self._route_for_intent("risk_review")
        if self._is_reporting(normalized):
            return self._route_for_intent("reporting")
        if self._is_research(normalized):
            return self._route_for_intent("research")
        if "backtest" in normalized:
            return PlannerRoute(
                intent="strategy_creation",
                task_class="strategy_creation",
                response_style="strategy_proposal",
                domain_focus="strategy_creation",
                artifact_expected="strategy_artifact",
                allowed_agents=("research", "strategy_creator", "strategy_reviewer", "backtest", "audit", "ceo"),
                backend_tools=("get_symbol_data", "get_latest_ohlcv", "create_strategy_spec", "run_backtest"),
                expected_outputs=("research_summary", "strategy_spec", "strategy_review", "backtest_summary", "audit_trace", "ceo_strategy_memo"),
                evidence_requirements=("market_data", "strategy_spec", "strategy_review", "backtest_result", "audit_trace"),
                risk_level="supervised_drafts",
            )
        if self._is_strategy_creation(normalized):
            return self._route_for_intent("strategy_creation")
        if self._needs_clarification(normalized):
            return self._route_for_intent("clarification")
        return self._route_for_intent("ceo_answer")

    @staticmethod
    def _route_for_intent(intent: str) -> PlannerRoute:
        if intent == "clarification":
            return PlannerRoute("clarification", "clarification", "clarification", "request_scoping", None, ("ceo",), (), ("clarifying_question",), ("user_clarification",), answer_mode="clarification")
        if intent == "ceo_identity":
            return PlannerRoute("ceo_identity", "firm_identity", "identity_memo", "firm_governance", None, ("ceo",), (), ("ceo_identity_statement",), ("constitution", "agent_permissions", "strategy_lifecycle"), answer_mode="direct_answer")
        if intent == "page_action":
            return PlannerRoute("page_action", "page_action", "operator_instruction", "ui_operation", "page_action_plan", ("ceo", "audit"), (), ("page_action_plan", "audit_trace"), ("planner_result", "operator_confirmation"), risk_level="page_action_plan")
        if intent == "execution_proposal":
            return PlannerRoute("execution_proposal", "execution_proposal", "board_escalation", "execution_governance", "action_draft", ("research", "risk_reviewer", "execution", "audit", "ceo"), ("get_symbol_data", "get_latest_ohlcv", "get_risk_snapshot"), ("market_snapshot", "risk_review", "trade_proposal_draft", "audit_trace", "ceo_board_request"), ("market_data", "risk_snapshot", "risk_governor_decision", "human_board_approval"), risk_level="critical", requires_board_approval=True, requires_risk_governor=True)
        if intent == "governed_action_draft":
            return PlannerRoute("governed_action_draft", "governed_action_draft", "approval_draft", "governed_operations", "action_draft", ("planner", "audit", "ceo"), ("create_report",), ("action_draft", "audit_trace", "ceo_summary"), ("planner_result", "operator_confirmation"), risk_level="supervised_drafts", requires_board_approval=True)
        if intent == "optimization_comparison":
            return PlannerRoute("optimization_comparison", "optimization_comparison", "comparison_memo", "optimization_selection", "optimization_comparison", ("backtest", "optimization", "statistical_validation", "risk_reviewer", "audit", "ceo"), ("get_backtest_result", "get_analytics_summary", "run_optimization", "create_report"), ("optimization_summary", "statistical_review", "risk_review", "audit_trace", "ceo_recommendation"), ("optimization_runs", "backtest_metrics", "risk_review", "audit_trace"))
        if intent == "backtest_diagnosis":
            return PlannerRoute("backtest_diagnosis", "backtest_diagnosis", "diagnostic_memo", "backtest_quality", "backtest_report", ("backtest", "strategy_reviewer", "risk_reviewer", "audit", "ceo"), ("get_strategy", "get_backtest_result", "get_analytics_summary", "create_report"), ("backtest_diagnosis", "strategy_review", "risk_review", "audit_trace", "ceo_recommendation"), ("backtest_result", "strategy_spec", "risk_review", "audit_trace"))
        if intent == "risk_review":
            return PlannerRoute("risk_review", "risk_review", "risk_memo", "portfolio_risk", "risk_memo", ("research", "risk_reviewer", "portfolio_manager", "audit", "ceo"), ("get_open_positions", "get_account_snapshot", "get_risk_snapshot", "create_risk_review", "create_report"), ("market_snapshot", "risk_review", "portfolio_view", "audit_trace", "ceo_risk_memo"), ("portfolio_snapshot", "risk_snapshot", "risk_review", "audit_trace"), requires_risk_governor=True)
        if intent == "reporting":
            return PlannerRoute("reporting", "reporting", "board_report", "firm_reporting", "firm_report", ("performance_reporter", "risk_reviewer", "audit", "ceo"), ("get_analytics_summary", "get_risk_snapshot", "create_report"), ("performance_report", "risk_summary", "audit_trace", "ceo_board_summary"), ("performance_snapshot", "risk_snapshot", "audit_trace"))
        if intent == "research":
            return PlannerRoute("research", "research", "research_memo", "market_research", "research_report", ("market_intelligence", "technical_analyst", "strategy_scout", "audit", "ceo"), ("get_symbol_data", "get_latest_ohlcv", "get_analytics_summary", "create_report"), ("market_intelligence_report", "technical_analysis_report", "strategy_ideas", "audit_trace", "ceo_summary"), ("market_data", "research_observations", "audit_trace"))
        if intent == "strategy_creation":
            return PlannerRoute("strategy_creation", "strategy_creation", "strategy_proposal", "strategy_creation", "strategy_artifact", ("research", "strategy_creator", "strategy_reviewer", "audit", "ceo"), ("get_symbol_data", "get_latest_ohlcv", "create_strategy_spec"), ("research_summary", "strategy_spec", "strategy_review", "audit_trace", "ceo_strategy_memo"), ("market_data", "strategy_spec", "strategy_review", "audit_trace"), risk_level="supervised_drafts")
        return PlannerRoute("ceo_answer", "firm_answer", "ceo_answer", "firm_operations", None, ("ceo",), (), ("ceo_answer",), ("planner_result", "governance_boundaries"), answer_mode="direct_answer")

    @staticmethod
    def _needs_clarification(normalized: str) -> bool:
        return len(normalized.split()) < 4 or normalized in {"help", "do it", "make it better", "proceed"}

    @staticmethod
    def _clarification_question() -> str:
        return "What market, timeframe, and desired outcome should the CEO Agent plan for?"

    @staticmethod
    def _is_ceo_identity(normalized: str) -> bool:
        identity_markers = (
            "who are you",
            "what are you",
            "what is your name",
            "what's your name",
            "your name",
            "who am i talking to",
            "tell me about yourself",
            "introduce yourself",
            "your role",
            "what is your role",
            "who do i speak to",
            "ceo agent",
            "cio",
        )
        firm_markers = ("haruquant", "agentic firm", "firm", "ceo", "cio")
        has_identity_marker = any(marker in normalized for marker in identity_markers)
        has_firm_marker = any(marker in normalized for marker in firm_markers)
        direct_identity_questions = {
            "who are you",
            "what are you",
            "what is your name",
            "what's your name",
            "who am i talking to",
        }
        return has_identity_marker and (
            has_firm_marker or normalized.rstrip("?.!") in direct_identity_questions
        )

    @staticmethod
    def _is_page_action(normalized: str) -> bool:
        return any(token in normalized for token in ("click", "navigate", "open tab", "select row", "change filter"))

    @staticmethod
    def _is_execution_proposal(normalized: str) -> bool:
        return any(
            token in normalized
            for token in (
                "place order",
                "place a trade",
                "place trade",
                "live order",
                "live trade",
                "execute trade",
                "execute this signal",
                "trade proposal",
                "using your best judgment",
                "buy ",
                "sell ",
            )
        )

    @staticmethod
    def _is_governed_action_draft(normalized: str) -> bool:
        return any(token in normalized for token in ("approval draft", "request approval", "draft action", "launch backtest", "run backtest"))

    @staticmethod
    def _is_optimization_comparison(normalized: str) -> bool:
        return any(token in normalized for token in ("optimization", "optimisation", "compare candidates", "rank candidates"))

    @staticmethod
    def _is_backtest_diagnosis(normalized: str) -> bool:
        return "backtest" in normalized and any(token in normalized for token in ("diagnose", "why", "analyze", "analyse", "review"))

    @staticmethod
    def _is_risk_review(normalized: str) -> bool:
        return any(token in normalized for token in ("risk", "drawdown", "exposure", "var", "portfolio danger"))

    @staticmethod
    def _is_reporting(normalized: str) -> bool:
        return any(token in normalized for token in ("report", "memo", "board summary", "weekly", "daily"))

    @staticmethod
    def _is_research(normalized: str) -> bool:
        return any(token in normalized for token in ("research", "market regime", "market structure", "investigate", "scan market"))

    @staticmethod
    def _is_strategy_creation(normalized: str) -> bool:
        return any(
            token in normalized
            for token in (
                "create strategy",
                "create a strategy",
                "make strategy",
                "make a strategy",
                "strategy idea",
                "strategy spec",
                "mean reversion strategy",
                "breakout strategy",
                "scalping strategy",
            )
        )


class DefaultFirmRequestClassifier:
    """LLM-capable route selector for the CEO planning engine.

    The model can only select from ROUTE_CATALOG. It does not create plans,
    grant permissions, or override deterministic safety checks.
    """

    SYSTEM_PROMPT = """You classify HaruQuant CEO requests into exactly one approved route.
Return compact JSON with exactly: {"intent": "...", "confidence": 0.0}.
Choose only from the provided route catalog. If unclear, choose ceo_answer or clarification.
Never choose a route outside the catalog."""

    def classify(self, *, user_request: str, route_catalog: tuple[RouteCatalogEntry, ...]) -> str | None:
        if not self._llm_enabled():
            return None
        valid_intents = {entry.intent for entry in route_catalog}
        try:
            from backend.agents.runtime import create_llm_runtime
            from backend.config.agent_model import get_model_for_tier

            runtime = create_llm_runtime(
                model=get_model_for_tier("fast"),
                json_mode=True,
                temperature=0.0,
                max_output_tokens=300,
                timeout_seconds=15,
            )
            payload = {
                "user_request": user_request,
                "routes": [
                    {
                        "intent": entry.intent,
                        "description": entry.description,
                        "examples": list(entry.examples),
                    }
                    for entry in route_catalog
                ],
            }
            result = runtime._call_llm(
                self.SYSTEM_PROMPT,
                json.dumps(payload, ensure_ascii=False, default=str),
            )
            parsed = json.loads(str(result.get("content") or "{}"))
            intent = str(parsed.get("intent") or "").strip()
            if intent in valid_intents:
                return intent
        except (json.JSONDecodeError, Exception):
            return None
        return None

    @staticmethod
    def _llm_enabled() -> bool:
        value = os.environ.get("HARUQUANT_CEO_CLASSIFIER_LLM_ENABLED", "true")
        return value.strip().lower() not in {"0", "false", "no", "off"}


__all__ = [
    "DefaultFirmRequestClassifier",
    "FirmRequestClassifier",
    "PLANNER_AGENT_DEPARTMENT",
    "ROUTE_CATALOG",
    "RouteCatalogEntry",
    "ConversationPlanner",
    "IntentRouterAgent",
    "IntentRouterError",
    "PlannerAgent",
    "PlannerRoute",
    "intent_router_agent",
]
