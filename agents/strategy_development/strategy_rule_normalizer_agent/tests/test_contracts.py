from __future__ import annotations

import asyncio

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentStatus
from agents.strategy_development.strategy_rule_normalizer_agent.agent import build_agent
from agents.strategy_development.strategy_rule_normalizer_agent.contracts import StrategyRuleNormalizerAgentPayload
from agents.strategy_development.strategy_rule_normalizer_agent.deterministic_policy import make_final_decision
from agents.strategy_development.strategy_rule_normalizer_agent.evaluator import evaluate_response
from agents.strategy_development.strategy_rule_normalizer_agent.service import StrategyRuleNormalizerAgentService


def _request(**payload):
    data = {"user_prompt": "create a EURUSD H1 mean-reversion strategy", "symbol": "EURUSD", "timeframe": "H1", "evidence_refs": ["ev-1"]}
    data.update(payload)
    return AgentRequest(request_id="test-request", agent_name="strategy_rule_normalizer_agent", task=data["user_prompt"], payload=data)


def test_payload_serializes():
    assert StrategyRuleNormalizerAgentPayload(symbol="EURUSD", timeframe="H1").model_dump_json()
