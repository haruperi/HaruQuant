from __future__ import annotations

import asyncio

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentStatus
from agents.strategy_development.strategy_template_selector_agent.agent import build_agent
from agents.strategy_development.strategy_template_selector_agent.contracts import StrategyTemplateSelectorAgentPayload
from agents.strategy_development.strategy_template_selector_agent.deterministic_policy import make_final_decision
from agents.strategy_development.strategy_template_selector_agent.evaluator import evaluate_response
from agents.strategy_development.strategy_template_selector_agent.service import StrategyTemplateSelectorAgentService


def _request(**payload):
    data = {"user_prompt": "create a EURUSD H1 mean-reversion strategy", "symbol": "EURUSD", "timeframe": "H1", "evidence_refs": ["ev-1"]}
    data.update(payload)
    return AgentRequest(request_id="test-request", agent_name="strategy_template_selector_agent", task=data["user_prompt"], payload=data)


def test_service_returns_agent_response():
    response = asyncio.run(StrategyTemplateSelectorAgentService().run(_request(), AgentContext(session_id="ctx-test")))
    assert response.agent_name == "strategy_template_selector_agent"
    assert response.audit["department"] == "Strategy Creation Department"
    assert "strategy_spec" in response.artifacts
    assert evaluate_response(response)["passed"]
