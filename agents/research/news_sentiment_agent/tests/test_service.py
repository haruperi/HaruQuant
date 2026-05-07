from __future__ import annotations

import asyncio

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentStatus, EvidenceItem, RiskLevel
from agents.research.news_sentiment_agent.agent import build_agent
from agents.research.news_sentiment_agent.contracts import NewsSentimentAgentPayload
from agents.research.news_sentiment_agent.deterministic_policy import make_final_decision
from agents.research.news_sentiment_agent.evaluator import evaluate_response
from agents.research.news_sentiment_agent.service import NewsSentimentAgentService


def _request(**payload):
    data = {"symbol": "EURUSD", "timeframe": "H1"}
    data.update(payload)
    return AgentRequest(request_id="test-request", agent_name="news_sentiment_agent", task="Run research test.", payload=data)


def test_service_returns_agent_response():
    service = NewsSentimentAgentService()
    response = asyncio.run(service.run(_request(), AgentContext(session_id="ctx-test")))
    assert response.agent_name == "news_sentiment_agent"
    assert response.audit["permission_profile"] == "research_read_only_v1"
    assert response.evidence
    assert response.decision.decision
    assert evaluate_response(response)["passed"]


def test_service_handles_missing_symbol_safely():
    service = NewsSentimentAgentService()
    response = asyncio.run(service.run(_request(symbol=None), AgentContext()))
    assert response.status == AgentStatus.NEEDS_MORE_CONTEXT
