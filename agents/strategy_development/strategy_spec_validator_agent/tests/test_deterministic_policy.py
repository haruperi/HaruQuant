from __future__ import annotations

import asyncio

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentStatus
from agents.strategy_development.strategy_spec_validator_agent.agent import build_agent
from agents.strategy_development.strategy_spec_validator_agent.contracts import StrategySpecValidatorAgentPayload
from agents.strategy_development.strategy_spec_validator_agent.deterministic_policy import make_final_decision
from agents.strategy_development.strategy_spec_validator_agent.evaluator import evaluate_response
from agents.strategy_development.strategy_spec_validator_agent.service import StrategySpecValidatorAgentService


def _request(**payload):
    data = {"user_prompt": "create a EURUSD H1 mean-reversion strategy", "symbol": "EURUSD", "timeframe": "H1", "evidence_refs": ["ev-1"]}
    data.update(payload)
    return AgentRequest(request_id="test-request", agent_name="strategy_spec_validator_agent", task=data["user_prompt"], payload=data)


def test_policy_accepts_valid_request():
    decision = make_final_decision(_request())
    assert decision.status == AgentStatus.SUCCESS
    assert "execute_trade" in decision.blocked_actions


def test_policy_needs_context_for_missing_symbol():
    decision = make_final_decision(_request(symbol=None, user_prompt="create strategy"))
    assert decision.status == AgentStatus.NEEDS_MORE_CONTEXT


def test_policy_rejects_rejected_research():
    decision = make_final_decision(_request(research_validation_status="rejected"))
    assert decision.status == AgentStatus.REJECTED
