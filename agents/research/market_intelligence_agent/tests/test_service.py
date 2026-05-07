from __future__ import annotations

import asyncio

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentStatus, EvidenceItem, RiskLevel
from agents.research.market_intelligence_agent.agent import build_agent
from agents.research.market_intelligence_agent.contracts import MarketIntelligenceAgentPayload
from agents.research.market_intelligence_agent.deterministic_policy import make_final_decision
from agents.research.market_intelligence_agent.evaluator import evaluate_response
from agents.research.market_intelligence_agent.service import MarketIntelligenceAgentService


def _request(**payload):
    data = {"symbol": "EURUSD", "timeframe": "H1"}
    data.update(payload)
    return AgentRequest(request_id="test-request", agent_name="market_intelligence_agent", task="Run research test.", payload=data)


def test_service_returns_agent_response():
    service = MarketIntelligenceAgentService()
    response = asyncio.run(service.run(_request(), AgentContext(session_id="ctx-test")))
    assert response.agent_name == "market_intelligence_agent"
    assert response.audit["permission_profile"] == "research_read_only_v1"
    assert response.evidence
    assert response.decision.decision
    assert evaluate_response(response)["passed"]


def test_service_handles_missing_symbol_safely():
    service = MarketIntelligenceAgentService()
    response = asyncio.run(service.run(_request(symbol=None), AgentContext()))
    assert response.status == AgentStatus.NEEDS_MORE_CONTEXT
