"""General trading advisor specialist for broader strategy and market questions."""

from __future__ import annotations

from typing import Any

from backend.agents.chat.ai_chat.models import SpecialistAgentArtifact
from backend.agents.chat.ai_chat.tool_executor import ToolExecutionResult

from .agent_base import SpecialistAgentBase


class TradingAdvisorAgent(SpecialistAgentBase):
    """LLM-backed general trading advisor.
    
    Handles qualitative strategy questions, market regime context, and 
    synthesis of research plans.
    """

    agent_name = "trading_advisor_agent"

    SYSTEM_PROMPT = """You are HaruQuant's Senior Trading Advisor.
Analyze the user request and available context to produce a high-quality trading perspective.

Output schema (JSON only):
{
  "summary": "<one sentence overview of the advice>",
  "findings": [
    "FACT: <neutral observation from current context>",
    "INTERPRETATION: <strategic implication of this fact>",
    "RISK: <downside or limitation of this perspective>"
  ],
  "evidence": ["source=value", ...],
  "recommendation": "<one concrete next action, e.g. 'run a walk-forward optimization', 'check correlation with SPX'>",
  "confidence": <integer 0-100>,
  "missing_data": ["<field name>", ...]
}

Rules:
- findings MUST follow the FACT/INTERPRETATION/RISK prefix pattern.
- focus on strategy robustness, market fit, and risk management.
- distinguish between 'observed behavior' and 'expected behavior'.
- if instrument or timeframe is unknown, list them in missing_data.
- do not suggest specific entry/exit prices or live trades.
- maximum 6 findings (2 sets of Fact/Interpretation/Risk).
"""

    def analyze(
        self,
        *,
        task_class: str,
        tool_results: list[ToolExecutionResult],
        page_context: Any,
        tool_context: dict[str, object],
    ) -> SpecialistAgentArtifact | None:
        # This agent can consume any relevant tool results
        stats = self._get_result(tool_results, "symbol_stats")
        knowledge = self._get_result(tool_results, "internal_knowledge")

        deterministic = self._deterministic_artifact(
            task_class=task_class,
            stats=stats,
            knowledge=knowledge,
            page_context=page_context,
        )

        user_payload = self._build_user_payload(
            stats=stats,
            knowledge=knowledge,
            task_class=task_class,
            page_context=page_context,
        )
        raw = self._call_llm_plan(user_payload=user_payload)
        return self._validated_artifact(raw=raw, task_class=task_class, fallback=deterministic)

    @staticmethod
    def _build_user_payload(
        *,
        stats: ToolExecutionResult | None,
        knowledge: ToolExecutionResult | None,
        task_class: str,
        page_context: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "task_class": task_class,
            "page_type": page_context.payload.page_type,
            "page_title": page_context.payload.page_title,
        }

        if stats is not None:
            payload["symbol_stats"] = stats.payload
        
        if knowledge is not None:
            # Knowledge results can be large, just send summaries/snippets
            k = knowledge.payload
            payload["relevant_knowledge"] = [
                {"title": item.get("title"), "snippet": item.get("snippet")}
                for item in (k.get("items") or [])[:3]
            ]

        return payload

    def _deterministic_artifact(
        self,
        *,
        task_class: str,
        stats: ToolExecutionResult | None,
        knowledge: ToolExecutionResult | None,
        page_context: Any,
    ) -> SpecialistAgentArtifact | None:
        evidence: list[str] = []
        findings: list[str] = []

        if stats is not None:
            s = stats.payload
            evidence.append(f"symbol={s.get('symbol')} vol={s.get('volatility_24h')}")
            findings.append(f"Market context for {s.get('symbol')} is available.")
        
        if knowledge is not None:
            findings.append("Internal HaruQuant documentation context is available.")

        return SpecialistAgentArtifact(
            agent_name=self.agent_name,
            task_class=task_class,
            summary="Strategic advisor context is available to ground the trading perspective.",
            findings=findings or ["General trading advice based on current page context."],
            evidence=evidence or [page_context.payload.summary.headline],
            recommendation="Review strategy robustness and market regime alignment.",
            confidence=65,
        )
