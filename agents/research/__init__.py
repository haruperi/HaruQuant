"""Research Department agents."""

from __future__ import annotations

import asyncio
from typing import Any

from agents._shared import AgentRunContext, AgentRunResult
from agents._shared.base_contracts import AgentContext, AgentRequest

from .cross_asset_intermarket_agent import CrossAssetIntermarketAgentService
from .evidence_curator_agent import EvidenceCuratorAgentService
from .macro_fundamental_context_agent import MacroFundamentalContextAgentService
from .market_intelligence_agent import MarketIntelligenceAgentService
from .news_sentiment_agent import NewsSentimentAgentService
from .research_orchestrator_agent import ResearchOrchestratorAgentService
from .research_validation_agent import ResearchValidationAgentService
from .seasonality_calendar_agent import SeasonalityCalendarAgentService
from .strategy_hypothesis_agent import StrategyHypothesisAgentService
from .strategy_scout_agent import StrategyScoutAgentService
from .technical_analyst_agent import TechnicalAnalystAgentService


class _LegacyResearchRunAdapter:
    agent_name = "research_agent"
    service_class: type | None = None

    def run(
        self,
        *,
        context: AgentRunContext,
        task_input: dict[str, Any],
    ) -> AgentRunResult:
        if self.service_class is not None:
            payload = self._normalize_payload(context=context, task_input=task_input)
            response = asyncio.run(
                self.service_class().run(
                    AgentRequest(
                        request_id=context.task_id,
                        user_id=context.actor_id,
                        agent_name=self.agent_name,
                        task=context.user_request,
                        payload=payload,
                    ),
                    AgentContext(session_id=context.workflow_id),
                )
            )
            return AgentRunResult(
                agent_name=self.agent_name,
                status=response.status.value,
                output={
                    "decision": response.decision.model_dump(mode="json"),
                    "artifacts": response.artifacts,
                    "audit": response.audit,
                },
                observations=[
                    {
                        "task_id": context.task_id,
                        "agent_name": self.agent_name,
                        "summary": response.llm_analysis.summary
                        if response.llm_analysis
                        else response.decision.decision,
                    }
                ],
                decisions=[
                    {
                        "task_id": context.task_id,
                        "agent_name": self.agent_name,
                        "decision": response.decision.decision,
                        "rationale": "; ".join(response.decision.reasons),
                    }
                ],
                evidence_refs=response.audit.get("evidence_refs", []),
            )
        return AgentRunResult(
            agent_name=self.agent_name,
            status="completed",
            output={
                "task_id": context.task_id,
                "department": "Research Department",
                "task_input": task_input,
            },
            observations=[
                {
                    "task_id": context.task_id,
                    "agent_name": self.agent_name,
                    "summary": f"{self.agent_name} completed deterministic research review.",
                }
            ],
            decisions=[
                {
                    "task_id": context.task_id,
                    "agent_name": self.agent_name,
                    "decision": "completed",
                    "rationale": "Compatibility adapter for existing operating-cycle callers.",
                }
            ],
        )

    def _normalize_payload(
        self,
        *,
        context: AgentRunContext,
        task_input: dict[str, Any],
    ) -> dict[str, Any]:
        payload = dict(task_input)
        payload.setdefault("research_question", context.user_request)
        payload.setdefault("symbol", self._infer_symbol(context.user_request))
        payload.setdefault("timeframe", self._infer_timeframe(context.user_request))
        payload.setdefault("data_window", "90d")
        if "spreads" in payload and "spread_pips" not in payload:
            spreads = payload.get("spreads") or []
            if spreads:
                payload["spread_pips"] = max(spreads)
        if "ohlcv" in payload and "sample_size" not in payload:
            payload["sample_size"] = len(payload.get("ohlcv") or [])
        return payload

    @staticmethod
    def _infer_symbol(text: str) -> str:
        for token in text.replace(".", " ").replace(",", " ").split():
            if token.isalpha() and token.isupper() and len(token) >= 5:
                return token
        return "EURUSD"

    @staticmethod
    def _infer_timeframe(text: str) -> str:
        for token in text.replace(".", " ").replace(",", " ").split():
            if token.upper() in {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"}:
                return token.upper()
        return "H1"


class MarketIntelligenceAgent(_LegacyResearchRunAdapter):
    agent_name = "market_intelligence_agent"
    service_class = MarketIntelligenceAgentService


class StrategyScoutAgent(_LegacyResearchRunAdapter):
    agent_name = "strategy_scout_agent"
    service_class = StrategyScoutAgentService


class TechnicalAnalystAgent(_LegacyResearchRunAdapter):
    agent_name = "technical_analyst_agent"
    service_class = TechnicalAnalystAgentService

__all__ = [
    "CrossAssetIntermarketAgentService",
    "EvidenceCuratorAgentService",
    "MacroFundamentalContextAgentService",
    "MarketIntelligenceAgent",
    "MarketIntelligenceAgentService",
    "NewsSentimentAgentService",
    "ResearchOrchestratorAgentService",
    "ResearchValidationAgentService",
    "SeasonalityCalendarAgentService",
    "StrategyScoutAgent",
    "StrategyHypothesisAgentService",
    "StrategyScoutAgentService",
    "TechnicalAnalystAgent",
    "TechnicalAnalystAgentService",
]
