"""Lightweight routing for chat response mode and model tier selection."""

from __future__ import annotations

from dataclasses import dataclass
import re

from backend.agents.chat.ai_chat.domain_intelligence import resolve_domain_prompt_spec
from backend.agents.chat.ai_chat.policy import ChatResponseMode


@dataclass(frozen=True)
class ChatRouteDecision:
    response_mode: ChatResponseMode
    task_class: str
    model_tier: str
    rationale: str
    response_style: str
    domain_focus: str
    allowed_tools: tuple[str, ...] = ()


class ChatAgentRouter:
    """Classify chat requests into a response mode and routing tier."""

    def route(self, prompt: str) -> ChatRouteDecision:
        normalized = prompt.lower()
        if self._looks_like_knowledge_dialogue(normalized):
            spec = resolve_domain_prompt_spec("knowledge_dialogue")
            return ChatRouteDecision(
                response_mode=ChatResponseMode.ANSWER,
                task_class="knowledge_dialogue",
                model_tier="standard",
                rationale="Prompt requests internal documentation or workflow knowledge.",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
            )
        if any(keyword in normalized for keyword in ("compare", "versus", "vs", "better than")):
            spec = resolve_domain_prompt_spec("comparison")
            return ChatRouteDecision(
                response_mode=ChatResponseMode.ANSWER,
                task_class="comparison",
                model_tier="premium",
                rationale="Prompt requests comparative reasoning.",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
            )
        if (
            self._contains_action_phrase(normalized, noun="backtest")
            or self._contains_action_phrase(normalized, noun="optimization")
            or self._contains_action_phrase(normalized, noun="optimisation")
            or "optimize this" in normalized
            or "optimise this" in normalized
            or "export this" in normalized
            or "export the" in normalized
            or self._contains_action_phrase(normalized, noun="simulation")
            or "draft order" in normalized
            or "create order" in normalized
            or "place order" in normalized
        ):
            spec = resolve_domain_prompt_spec("action_draft")
            return ChatRouteDecision(
                response_mode=ChatResponseMode.ACTION_DRAFT,
                task_class="action_draft",
                model_tier="standard",
                rationale="Prompt requests a supervised operational draft.",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
            )
        if any(keyword in normalized for keyword in ("buy", "sell", "signal", "entry", "setup")):
            spec = resolve_domain_prompt_spec("signal_proposal")
            return ChatRouteDecision(
                response_mode=ChatResponseMode.SIGNAL_PROPOSAL,
                task_class="signal_proposal",
                model_tier="standard",
                rationale="Prompt looks like signal or trade analysis.",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
            )
        if any(keyword in normalized for keyword in ("diagnose", "why", "drawdown", "underperform", "flat", "stalled")):
            spec = resolve_domain_prompt_spec("diagnostic")
            return ChatRouteDecision(
                response_mode=ChatResponseMode.ANSWER,
                task_class="diagnostic",
                model_tier="premium",
                rationale="Prompt requests diagnostic reasoning.",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
            )
        if any(keyword in normalized for keyword in ("risk", "exposure", "var", "draw risk", "danger")):
            spec = resolve_domain_prompt_spec("risk_explanation")
            return ChatRouteDecision(
                response_mode=ChatResponseMode.ANSWER,
                task_class="risk_explanation",
                model_tier="premium",
                rationale="Prompt requests risk explanation.",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
            )
        if any(keyword in normalized for keyword in ("recommend", "next step", "should i", "what next")):
            spec = resolve_domain_prompt_spec("recommendation")
            return ChatRouteDecision(
                response_mode=ChatResponseMode.ANSWER,
                task_class="recommendation",
                model_tier="standard",
                rationale="Prompt requests a research recommendation.",
                response_style=spec.response_style,
                domain_focus=spec.domain_focus,
            )
        spec = resolve_domain_prompt_spec("performance_summary")
        return ChatRouteDecision(
            response_mode=ChatResponseMode.ANSWER,
            task_class="performance_summary",
            model_tier="fast",
            rationale="Default performance summary path.",
            response_style=spec.response_style,
            domain_focus=spec.domain_focus,
        )

    @staticmethod
    def _contains_action_phrase(normalized_prompt: str, *, noun: str) -> bool:
        pattern = rf"\b(?:launch|run|start)\s+(?:an?\s+|the\s+|this\s+)?{re.escape(noun)}\b"
        return re.search(pattern, normalized_prompt) is not None

    @staticmethod
    def _looks_like_knowledge_dialogue(normalized_prompt: str) -> bool:
        knowledge_keywords = (
            "docs",
            "documentation",
            "runbook",
            "runbooks",
            "playbook",
            "policy",
            "policies",
            "architecture",
            "implementation plan",
            "rollout",
            "rbac",
            "support sop",
            "knowledge base",
            "what does haruquant",
            "how does haruquant",
        )
        return any(keyword in normalized_prompt for keyword in knowledge_keywords)
