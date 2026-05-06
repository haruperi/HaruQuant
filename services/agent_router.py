"""Lightweight route selection for AI Chat requests."""

from __future__ import annotations

from services.schemas.chat import ChatRouteDecision, ChatTurnRequest, PageContext


class AgentRouter:
    """Classifies chat turns before model routing.

    The router is deliberately read-only. It decides how to answer, but it does
    not execute tools or commit side effects. That keeps regeneration safe.
    """

    def classify(
        self,
        *,
        request: ChatTurnRequest,
        page_context: PageContext,
    ) -> ChatRouteDecision:
        prompt = " ".join(request.prompt.lower().strip().split())
        attached_tools = [tool for tool in request.attached_tools if tool]
        page_type = str(page_context.page_type or "generic")

        if _is_page_identity_question(prompt):
            return ChatRouteDecision(
                intent="page_identity",
                task_class="context_lookup",
                response_mode="page_aware_summary",
                response_style="summary",
                domain_focus=page_type,
                route_mode="plain_answer",
                requires_tools=False,
                model_policy_key="fast",
                structured_schema="page_context_answer",
            )

        if attached_tools:
            return ChatRouteDecision(
                intent="tool_assisted_answer",
                task_class="tool_assisted",
                response_mode="tool_assisted",
                response_style="structured",
                domain_focus=page_type,
                route_mode="tool_assisted",
                requires_tools=True,
                model_policy_key="strong",
                structured_schema="tool_disclosure_answer",
            )

        if _contains_any(prompt, ("risk", "drawdown", "exposure", "var", "kill switch", "governor")):
            return ChatRouteDecision(
                intent="risk_review",
                task_class="risk_review",
                response_mode="risk_memo",
                response_style="warning",
                domain_focus="portfolio_risk",
                route_mode="plain_answer",
                model_policy_key="strong",
                structured_schema="risk_memo",
            )

        if _contains_any(prompt, ("strategy", "alpha", "signal", "indicator", "entry", "exit")):
            return ChatRouteDecision(
                intent="strategy_work",
                task_class="strategy",
                response_mode="strategy_spec_draft",
                response_style="recommendation",
                domain_focus="strategy",
                route_mode="plain_answer",
                model_policy_key="strong",
                structured_schema="strategy_memo",
            )

        if _contains_any(prompt, ("backtest", "optimization", "optimize", "walk forward", "simulation")):
            return ChatRouteDecision(
                intent="analysis_workflow",
                task_class="analysis",
                response_mode="evidence_grounded_explanation",
                response_style="diagnostic",
                domain_focus=page_type,
                route_mode="plain_answer",
                model_policy_key="analysis",
                structured_schema="analysis_answer",
            )

        return ChatRouteDecision(
            intent="general_answer",
            task_class="plain_answer",
            response_mode="direct_answer",
            response_style="summary",
            domain_focus=page_type,
            route_mode="plain_answer",
            model_policy_key="fast",
            structured_schema="plain_answer",
        )


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _is_page_identity_question(prompt: str) -> bool:
    page_terms = (
        "what page am i on",
        "which page am i on",
        "where am i",
        "what screen am i on",
        "which screen am i on",
        "what route am i on",
        "current page",
        "current screen",
    )
    return any(term in prompt for term in page_terms)


__all__ = ["AgentRouter"]
