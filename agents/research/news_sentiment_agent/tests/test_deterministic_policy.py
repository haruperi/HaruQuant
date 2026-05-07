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


def test_normal_policy_allows_research_actions():
    decision = make_final_decision([EvidenceItem(source="news_sentiment_snapshot", description="ok", value={"data_quality_score": 0.9, "sample_size": 250})], None)
    assert decision.status == AgentStatus.SUCCESS
    assert decision.allowed_actions


def test_extreme_volatility_blocks_execution():
    decision = make_final_decision([EvidenceItem(source="news_sentiment_snapshot", description="risk", value={"volatility_state": "extreme"})], None)
    assert decision.risk_level == RiskLevel.CRITICAL
    assert "trade_execution" in decision.blocked_actions


def test_llm_cannot_override_rejected_validation():
    decision = make_final_decision([EvidenceItem(source="news_sentiment_snapshot", description="reject", value={"validation_status": "rejected"})], None)
    assert "handoff_approved_hypothesis" not in decision.allowed_actions
