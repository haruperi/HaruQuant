from __future__ import annotations

import asyncio

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentStatus, EvidenceItem, RiskLevel
from agents.research.technical_analyst_agent.agent import build_agent
from agents.research.technical_analyst_agent.contracts import TechnicalAnalystAgentPayload
from agents.research.technical_analyst_agent.deterministic_policy import make_final_decision
from agents.research.technical_analyst_agent.evaluator import evaluate_response
from agents.research.technical_analyst_agent.service import TechnicalAnalystAgentService


def _request(**payload):
    data = {"symbol": "EURUSD", "timeframe": "H1"}
    data.update(payload)
    return AgentRequest(request_id="test-request", agent_name="technical_analyst_agent", task="Run research test.", payload=data)


def test_normal_policy_allows_research_actions():
    decision = make_final_decision([EvidenceItem(source="technical_context", description="ok", value={"data_quality_score": 0.9, "sample_size": 250})], None)
    assert decision.status == AgentStatus.SUCCESS
    assert decision.allowed_actions


def test_extreme_volatility_blocks_execution():
    decision = make_final_decision([EvidenceItem(source="technical_context", description="risk", value={"volatility_state": "extreme"})], None)
    assert decision.risk_level == RiskLevel.CRITICAL
    assert "trade_execution" in decision.blocked_actions


def test_llm_cannot_override_rejected_validation():
    decision = make_final_decision([EvidenceItem(source="technical_context", description="reject", value={"validation_status": "rejected"})], None)
    assert "handoff_approved_hypothesis" not in decision.allowed_actions
