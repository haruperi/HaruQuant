"""Planner Agent for firm-level request routing."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from backend.agents.base import AgentRunContext, AgentRunResult, BaseAgent
from backend.agents.intent_router import IntentRouterAgent, IntentRouterError, intent_router_agent
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
        if self._needs_clarification(normalized):
            return PlannerRoute(
                intent="clarification",
                task_class="clarification",
                response_style="clarification",
                domain_focus="request_scoping",
                artifact_expected=None,
                allowed_agents=("ceo",),
                backend_tools=(),
                expected_outputs=("clarifying_question",),
                evidence_requirements=("user_clarification",),
                answer_mode="clarification",
            )
        if self._is_page_action(normalized):
            return PlannerRoute(
                intent="page_action",
                task_class="page_action",
                response_style="operator_instruction",
                domain_focus="ui_operation",
                artifact_expected="page_action_plan",
                allowed_agents=("ceo", "audit"),
                backend_tools=(),
                expected_outputs=("page_action_plan", "audit_trace"),
                evidence_requirements=("planner_result", "operator_confirmation"),
                risk_level="page_action_plan",
            )
        if self._is_execution_proposal(normalized):
            return PlannerRoute(
                intent="execution_proposal",
                task_class="execution_proposal",
                response_style="board_escalation",
                domain_focus="execution_governance",
                artifact_expected="action_draft",
                allowed_agents=("research", "risk_reviewer", "execution", "audit", "ceo"),
                backend_tools=("get_symbol_data", "get_latest_ohlcv", "get_risk_snapshot"),
                expected_outputs=("market_snapshot", "risk_review", "trade_proposal_draft", "audit_trace", "ceo_board_request"),
                evidence_requirements=("market_data", "risk_snapshot", "risk_governor_decision", "human_board_approval"),
                risk_level="critical",
                requires_board_approval=True,
                requires_risk_governor=True,
            )
        if self._is_governed_action_draft(normalized):
            return PlannerRoute(
                intent="governed_action_draft",
                task_class="governed_action_draft",
                response_style="approval_draft",
                domain_focus="governed_operations",
                artifact_expected="action_draft",
                allowed_agents=("planner", "audit", "ceo"),
                backend_tools=("create_report",),
                expected_outputs=("action_draft", "audit_trace", "ceo_summary"),
                evidence_requirements=("planner_result", "operator_confirmation"),
                risk_level="supervised_drafts",
                requires_board_approval=True,
            )
        if self._is_optimization_comparison(normalized):
            return PlannerRoute(
                intent="optimization_comparison",
                task_class="optimization_comparison",
                response_style="comparison_memo",
                domain_focus="optimization_selection",
                artifact_expected="optimization_comparison",
                allowed_agents=("backtest", "optimization", "statistical_validation", "risk_reviewer", "audit", "ceo"),
                backend_tools=("get_backtest_result", "get_analytics_summary", "run_optimization", "create_report"),
                expected_outputs=("optimization_summary", "statistical_review", "risk_review", "audit_trace", "ceo_recommendation"),
                evidence_requirements=("optimization_runs", "backtest_metrics", "risk_review", "audit_trace"),
            )
        if self._is_backtest_diagnosis(normalized):
            return PlannerRoute(
                intent="backtest_diagnosis",
                task_class="backtest_diagnosis",
                response_style="diagnostic_memo",
                domain_focus="backtest_quality",
                artifact_expected="backtest_report",
                allowed_agents=("backtest", "strategy_reviewer", "risk_reviewer", "audit", "ceo"),
                backend_tools=("get_strategy", "get_backtest_result", "get_analytics_summary", "create_report"),
                expected_outputs=("backtest_diagnosis", "strategy_review", "risk_review", "audit_trace", "ceo_recommendation"),
                evidence_requirements=("backtest_result", "strategy_spec", "risk_review", "audit_trace"),
            )
        if self._is_risk_review(normalized):
            return PlannerRoute(
                intent="risk_review",
                task_class="risk_review",
                response_style="risk_memo",
                domain_focus="portfolio_risk",
                artifact_expected="risk_memo",
                allowed_agents=("research", "risk_reviewer", "portfolio_manager", "audit", "ceo"),
                backend_tools=("get_open_positions", "get_account_snapshot", "get_risk_snapshot", "create_risk_review", "create_report"),
                expected_outputs=("market_snapshot", "risk_review", "portfolio_view", "audit_trace", "ceo_risk_memo"),
                evidence_requirements=("portfolio_snapshot", "risk_snapshot", "risk_review", "audit_trace"),
                requires_risk_governor=True,
            )
        if self._is_reporting(normalized):
            return PlannerRoute(
                intent="reporting",
                task_class="reporting",
                response_style="board_report",
                domain_focus="firm_reporting",
                artifact_expected="firm_report",
                allowed_agents=("performance_reporter", "risk_reviewer", "audit", "ceo"),
                backend_tools=("get_analytics_summary", "get_risk_snapshot", "create_report"),
                expected_outputs=("performance_report", "risk_summary", "audit_trace", "ceo_board_summary"),
                evidence_requirements=("performance_snapshot", "risk_snapshot", "audit_trace"),
            )
        if self._is_research(normalized):
            return PlannerRoute(
                intent="research",
                task_class="research",
                response_style="research_memo",
                domain_focus="market_research",
                artifact_expected="research_report",
                allowed_agents=("research", "audit", "ceo"),
                backend_tools=("get_symbol_data", "get_latest_ohlcv", "get_analytics_summary", "create_report"),
                expected_outputs=("research_report", "audit_trace", "ceo_summary"),
                evidence_requirements=("market_data", "research_observations", "audit_trace"),
            )
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
        return PlannerRoute(
            intent="strategy_creation",
            task_class="strategy_creation",
            response_style="strategy_proposal",
            domain_focus="strategy_creation",
            artifact_expected="strategy_artifact",
            allowed_agents=("research", "strategy_creator", "strategy_reviewer", "audit", "ceo"),
            backend_tools=("get_symbol_data", "get_latest_ohlcv", "create_strategy_spec"),
            expected_outputs=("research_summary", "strategy_spec", "strategy_review", "audit_trace", "ceo_strategy_memo"),
            evidence_requirements=("market_data", "strategy_spec", "strategy_review", "audit_trace"),
            risk_level="supervised_drafts",
        )

    @staticmethod
    def _needs_clarification(normalized: str) -> bool:
        return len(normalized.split()) < 4 or normalized in {"help", "do it", "make it better", "proceed"}

    @staticmethod
    def _clarification_question() -> str:
        return "What market, timeframe, and desired outcome should the CEO Agent plan for?"

    @staticmethod
    def _is_page_action(normalized: str) -> bool:
        return any(token in normalized for token in ("click", "navigate", "open tab", "select row", "change filter"))

    @staticmethod
    def _is_execution_proposal(normalized: str) -> bool:
        return any(token in normalized for token in ("place order", "live order", "execute trade", "trade proposal", "buy ", "sell "))

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


__all__ = [
    "PLANNER_AGENT_DEPARTMENT",
    "ConversationPlanner",
    "IntentRouterAgent",
    "IntentRouterError",
    "PlannerAgent",
    "PlannerRoute",
    "intent_router_agent",
]
