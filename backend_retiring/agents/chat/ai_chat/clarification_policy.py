"""Clarification heuristics for conversational AI chat turns."""

from __future__ import annotations

from dataclasses import dataclass

from backend_retiring.contracts.page_context_packet.model import PageContextPacket
from backend_retiring.agents.chat.ai_chat.agent_router import ChatRouteDecision
from backend_retiring.agents.chat.ai_chat.models import ConversationState, ConversationThreadRecord


@dataclass(frozen=True)
class ClarificationDecision:
    needs_clarification: bool
    question: str | None = None
    rationale: str | None = None


class ClarificationPolicy:
    """Decide when the chatbot should ask a clarifying question."""

    _REFERENCE_PHRASES = (
        "this run",
        "previous run",
        "previous one",
        "that run",
        "same strategy",
        "same one",
        "that drawdown",
        "why again",
        "compare this",
        "compare that",
    )

    _PAGE_QUESTION_PHRASES = (
        "what does this page do",
        "what is this page",
        "summaries current page",
        "summarize current page",
        "summary current page",
        "summarise current page",
        "summarize this page",
        "summarise this page",
        "describe this page",
    )

    _KNOWLEDGE_BROAD_PHRASES = (
        "docs",
        "documentation",
        "show docs",
        "show me the docs",
        "explain the docs",
        "runbooks",
        "policies",
        "architecture docs",
    )

    _KNOWLEDGE_SPECIFICITY_MARKERS = (
        "chatbot",
        "rollout",
        "runbook",
        "policy",
        "architecture",
        "rbac",
        "support",
        "implementation plan",
        "execution safety",
        "strategy",
        "agent",
        "workflow",
        "backtest",
        "optimization",
        "risk",
    )

    _LIVE_CHART_PHRASES = (
        "last candle",
        "latest candle",
        "current candle",
        "bullish",
        "bearish",
        "ohlc",
        "candlestick",
    )

    def evaluate(
        self,
        *,
        prompt: str,
        thread: ConversationThreadRecord,
        page_context: PageContextPacket,
        conversation_state: ConversationState | None,
        tool_context: dict[str, object],
        route_decision: ChatRouteDecision,
    ) -> ClarificationDecision:
        normalized = " ".join(prompt.lower().split())
        if not normalized:
            return ClarificationDecision(
                needs_clarification=True,
                question="What do you want me to help with on this page?",
                rationale="Empty prompt requires clarification.",
            )

        if any(phrase in normalized for phrase in self._PAGE_QUESTION_PHRASES):
            return ClarificationDecision(needs_clarification=False)

        if self._needs_live_chart_clarification(
            normalized=normalized,
            page_context=page_context,
            tool_context=tool_context,
        ):
            return ClarificationDecision(
                needs_clarification=True,
                question="Which live session and chart should I inspect? Select a session on the page or tell me the symbol and timeframe.",
                rationale="Prompt asks for chart-specific live data, but the current live context is missing a session, symbol, or timeframe anchor.",
            )

        if self._needs_reference_clarification(
            normalized=normalized,
            thread=thread,
            page_context=page_context,
            conversation_state=conversation_state,
            tool_context=tool_context,
            route_decision=route_decision,
        ):
            return ClarificationDecision(
                needs_clarification=True,
                question=self._build_reference_question(route_decision=route_decision),
                rationale="Prompt relies on unresolved references and current context does not identify the target entity.",
            )

        if self._needs_knowledge_clarification(normalized=normalized, route_decision=route_decision):
            return ClarificationDecision(
                needs_clarification=True,
                question="Which document area do you want: architecture, rollout, runbooks, governance, or strategy workflows?",
                rationale="Prompt asks for internal documentation, but the requested document area is too broad.",
            )

        return ClarificationDecision(needs_clarification=False)

    def _needs_live_chart_clarification(
        self,
        *,
        normalized: str,
        page_context: PageContextPacket,
        tool_context: dict[str, object],
    ) -> bool:
        if page_context.payload.page_type != "live_trading":
            return False
        if not any(phrase in normalized for phrase in self._LIVE_CHART_PHRASES):
            return False
        required_keys = ("session_id", "symbol", "timeframe")
        return not all(tool_context.get(key) for key in required_keys)

    def _needs_reference_clarification(
        self,
        *,
        normalized: str,
        thread: ConversationThreadRecord,
        page_context: PageContextPacket,
        conversation_state: ConversationState | None,
        tool_context: dict[str, object],
        route_decision: ChatRouteDecision,
    ) -> bool:
        if not any(phrase in normalized for phrase in self._REFERENCE_PHRASES):
            return False
        if self._has_anchor(
            page_context=page_context,
            conversation_state=conversation_state,
            tool_context=tool_context,
            normalized=normalized,
        ):
            return False
        if self._recent_messages_contain_anchor(thread):
            return False
        return route_decision.task_class in {
            "comparison",
            "diagnostic",
            "recommendation",
            "performance_summary",
            "risk_explanation",
        }

    @staticmethod
    def _has_anchor(
        *,
        page_context: PageContextPacket,
        conversation_state: ConversationState | None,
        tool_context: dict[str, object],
        normalized: str,
    ) -> bool:
        if any(
            tool_context.get(key)
            for key in ("strategy_id", "backtest_id", "optimization_id", "session_id", "symbol")
        ):
            return True
        if conversation_state is not None:
            resolved = conversation_state.resolved_references
            if any(
                phrase in normalized
                for phrase in ("previous run", "previous one")
            ):
                if any(key in resolved for key in ("previous_backtest_id", "previous_optimization_id")):
                    return True
            if any(
                key in resolved
                for key in ("strategy_id", "backtest_id", "optimization_id", "session_id", "symbol")
            ):
                return True
        if page_context.payload.page_type != "generic":
            return True
        return bool(page_context.payload.entity_refs)

    @staticmethod
    def _recent_messages_contain_anchor(thread: ConversationThreadRecord) -> bool:
        recent = " ".join(message.content.lower() for message in thread.messages[-4:])
        anchor_terms = (
            "strategy",
            "backtest",
            "optimization",
            "optimisation",
            "session",
            "portfolio",
            "dashboard",
            "eurusd",
            "usdjpy",
            "spy",
            "qqq",
        )
        return any(term in recent for term in anchor_terms)

    @staticmethod
    def _build_reference_question(*, route_decision: ChatRouteDecision) -> str:
        if route_decision.task_class == "comparison":
            return "Which two runs or strategies do you want me to compare?"
        if route_decision.task_class == "diagnostic":
            return "Which run, strategy, or page state do you want me to diagnose?"
        if route_decision.task_class == "risk_explanation":
            return "Which portfolio, strategy, or live session should I explain the risk for?"
        return "Which strategy, run, or page state are you referring to?"

    def _needs_knowledge_clarification(self, *, normalized: str, route_decision: ChatRouteDecision) -> bool:
        if route_decision.task_class != "knowledge_dialogue":
            return False
        if any(marker in normalized for marker in self._KNOWLEDGE_SPECIFICITY_MARKERS):
            return False
        return normalized in self._KNOWLEDGE_BROAD_PHRASES or any(
            normalized.startswith(phrase)
            for phrase in ("show me the docs", "explain the docs", "documentation for", "docs for")
        )
