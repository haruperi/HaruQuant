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


def test_build_agent_smoke():
    runtime_agent = build_agent()
    assert runtime_agent.name == "news_sentiment_agent"
    assert runtime_agent.instructions
