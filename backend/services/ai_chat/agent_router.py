"""Lightweight routing for chat response mode and model tier selection."""

from __future__ import annotations

from dataclasses import dataclass

from backend.services.ai_chat.policy import ChatResponseMode


@dataclass(frozen=True)
class ChatRouteDecision:
    response_mode: ChatResponseMode
    task_class: str
    model_tier: str
    rationale: str
    allowed_tools: tuple[str, ...] = ()


class ChatAgentRouter:
    """Classify chat requests into a response mode and routing tier."""

    def route(self, prompt: str) -> ChatRouteDecision:
        normalized = prompt.lower()
        if any(keyword in normalized for keyword in ("buy", "sell", "signal", "entry", "setup")):
            return ChatRouteDecision(
                response_mode=ChatResponseMode.SIGNAL_PROPOSAL,
                task_class="signal_analysis",
                model_tier="standard",
                rationale="Prompt looks like signal or trade analysis.",
            )
        if any(keyword in normalized for keyword in ("compare", "diagnose", "why", "drawdown", "underperform")):
            return ChatRouteDecision(
                response_mode=ChatResponseMode.ANSWER,
                task_class="diagnostic",
                model_tier="premium",
                rationale="Prompt requests comparative or diagnostic reasoning.",
            )
        return ChatRouteDecision(
            response_mode=ChatResponseMode.ANSWER,
            task_class="general_research",
            model_tier="fast",
            rationale="Default read-only answer path.",
        )
