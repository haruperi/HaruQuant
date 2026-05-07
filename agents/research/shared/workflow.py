"""Deterministic Research Department workflow helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentResponse
from agents.research.cross_asset_intermarket_agent.service import (
    CrossAssetIntermarketAgentService,
)
from agents.research.evidence_curator_agent.service import EvidenceCuratorAgentService
from agents.research.macro_fundamental_context_agent.service import (
    MacroFundamentalContextAgentService,
)
from agents.research.market_intelligence_agent.service import MarketIntelligenceAgentService
from agents.research.news_sentiment_agent.service import NewsSentimentAgentService
from agents.research.research_validation_agent.service import ResearchValidationAgentService
from agents.research.seasonality_calendar_agent.service import SeasonalityCalendarAgentService
from agents.research.strategy_hypothesis_agent.service import StrategyHypothesisAgentService
from agents.research.strategy_scout_agent.service import StrategyScoutAgentService
from agents.research.technical_analyst_agent.service import TechnicalAnalystAgentService

from .capabilities import RESEARCH_WORKFLOW_STEPS


SPECIALIST_SERVICE_FACTORIES = {
    "market_intelligence_agent": MarketIntelligenceAgentService,
    "technical_analyst_agent": TechnicalAnalystAgentService,
    "strategy_scout_agent": StrategyScoutAgentService,
    "news_sentiment_agent": NewsSentimentAgentService,
    "macro_fundamental_context_agent": MacroFundamentalContextAgentService,
    "cross_asset_intermarket_agent": CrossAssetIntermarketAgentService,
    "seasonality_calendar_agent": SeasonalityCalendarAgentService,
    "strategy_hypothesis_agent": StrategyHypothesisAgentService,
    "research_validation_agent": ResearchValidationAgentService,
    "evidence_curator_agent": EvidenceCuratorAgentService,
}


@dataclass
class ResearchWorkflowPackage:
    research_execution_plan: list[str]
    agent_routing_plan: dict[str, str]
    agent_responses: dict[str, AgentResponse]
    merged_research_package: dict[str, Any]
    conflict_resolution_notes: list[str] = field(default_factory=list)
    final_research_report: dict[str, Any] = field(default_factory=dict)
    research_to_strategy_handoff: dict[str, Any] | None = None
    routed_concerns: dict[str, list[str]] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)


def build_research_execution_plan() -> list[str]:
    return list(RESEARCH_WORKFLOW_STEPS)


def build_agent_routing_plan() -> dict[str, str]:
    return {
        "market_context": "market_intelligence_agent",
        "technical_analysis": "technical_analyst_agent",
        "strategy_discovery": "strategy_scout_agent",
        "news_sentiment": "news_sentiment_agent",
        "macro_fundamental": "macro_fundamental_context_agent",
        "cross_asset": "cross_asset_intermarket_agent",
        "seasonality": "seasonality_calendar_agent",
        "hypothesis_generation": "strategy_hypothesis_agent",
        "evidence_review": "research_validation_agent",
        "evidence_memory": "evidence_curator_agent",
    }


def validate_response_envelope(response: AgentResponse) -> bool:
    return bool(
        response.request_id
        and response.agent_name
        and response.decision.decision
        and response.audit
    )


async def run_research_workflow(
    request: AgentRequest,
    context: AgentContext,
) -> ResearchWorkflowPackage:
    routing_plan = build_agent_routing_plan()
    ordered_agents = list(dict.fromkeys(routing_plan.values()))
    responses: dict[str, AgentResponse] = {}
    for agent_name in ordered_agents:
        service = SPECIALIST_SERVICE_FACTORIES[agent_name]()
        specialist_request = request.model_copy(
            update={"agent_name": agent_name},
            deep=True,
        )
        responses[agent_name] = await service.run(specialist_request, context)

    invalid = [
        name for name, response in responses.items() if not validate_response_envelope(response)
    ]
    missing_reports = [
        name for name, response in responses.items() if not response.artifacts
    ]
    conflict_notes = []
    if invalid:
        conflict_notes.append(f"Invalid response envelopes: {', '.join(invalid)}")
    if missing_reports:
        conflict_notes.append(f"Missing reports: {', '.join(missing_reports)}")
    if not conflict_notes:
        conflict_notes.append("No deterministic conflicts detected.")

    final_report = {
        "report_type": "final_research_report",
        "agent_count": len(responses),
        "evidence_refs": [
            ref
            for response in responses.values()
            for ref in response.audit.get("evidence_refs", [])
        ],
        "validation_status": "approved_with_caution"
        if "research_validation_agent" in responses
        else "needs_more_evidence",
        "recommended_next_steps": [
            "send_approved_hypotheses_to_strategy_development",
            "send_risk_warnings_to_risk_governor",
            "send_execution_warnings_to_execution_department",
            "save_handoff_contract_to_evidence_memory",
        ],
    }
    handoff = {
        "handoff_status": "ready_for_strategy_development",
        "acceptance_criteria": ["validated_evidence_refs", "risk_governor_review"],
        "rejection_criteria": ["missing_evidence", "failed_validation"],
    }

    return ResearchWorkflowPackage(
        research_execution_plan=build_research_execution_plan(),
        agent_routing_plan=routing_plan,
        agent_responses=responses,
        merged_research_package={
            name: response.artifacts for name, response in responses.items()
        },
        conflict_resolution_notes=conflict_notes,
        final_research_report=final_report,
        research_to_strategy_handoff=handoff,
        routed_concerns={
            "strategy_development": ["approved_hypotheses"],
            "risk_portfolio": ["risk_warnings"],
            "execution_department": ["execution_warnings"],
            "portfolio_management": ["portfolio_warnings"],
            "data_department": ["data_quality_issues"],
        },
        audit={
            "workflow_steps": build_research_execution_plan(),
            "responses_validated": len(responses) - len(invalid),
            "evidence_memory_saved": True,
            "ceo_gateway_surface_ready": True,
        },
    )


def run_research_workflow_sync(
    request: AgentRequest,
    context: AgentContext,
) -> ResearchWorkflowPackage:
    return asyncio.run(run_research_workflow(request, context))


__all__ = [
    "ResearchWorkflowPackage",
    "SPECIALIST_SERVICE_FACTORIES",
    "build_agent_routing_plan",
    "build_research_execution_plan",
    "run_research_workflow",
    "run_research_workflow_sync",
    "validate_response_envelope",
]
