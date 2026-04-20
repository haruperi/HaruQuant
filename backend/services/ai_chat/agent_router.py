"""Lightweight routing for chat response mode and model tier selection."""

from __future__ import annotations

from dataclasses import dataclass

from backend.services.ai_chat.domain_intelligence import resolve_domain_prompt_spec
from backend.services.ai_chat.policy import ChatResponseMode


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
        if (
            (
                "backtest" in normalized
                and any(keyword in normalized for keyword in ("launch", "run", "start"))
            )
            or (
                any(keyword in normalized for keyword in ("optimization", "optimisation", "optimize"))
                and any(keyword in normalized for keyword in ("launch", "run", "start"))
            )
            or "export" in normalized
            or "simulate" in normalized
            or "simulation" in normalized
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
