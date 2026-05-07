from __future__ import annotations

import asyncio

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentStatus
from agents.strategy_development.strategy_reviewer_agent.agent import build_agent
from agents.strategy_development.strategy_reviewer_agent.contracts import StrategyReviewerAgentPayload
from agents.strategy_development.strategy_reviewer_agent.deterministic_policy import make_final_decision
from agents.strategy_development.strategy_reviewer_agent.evaluator import evaluate_response
from agents.strategy_development.strategy_reviewer_agent.service import StrategyReviewerAgentService


def _request(**payload):
    data = {"user_prompt": "create a EURUSD H1 mean-reversion strategy", "symbol": "EURUSD", "timeframe": "H1", "evidence_refs": ["ev-1"]}
    data.update(payload)
    return AgentRequest(request_id="test-request", agent_name="strategy_reviewer_agent", task=data["user_prompt"], payload=data)


def test_payload_serializes():
    assert StrategyReviewerAgentPayload(symbol="EURUSD", timeframe="H1").model_dump_json()
