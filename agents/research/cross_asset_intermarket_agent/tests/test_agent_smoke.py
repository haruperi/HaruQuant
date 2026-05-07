from __future__ import annotations

import asyncio

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentStatus, EvidenceItem, RiskLevel
from agents.research.cross_asset_intermarket_agent.agent import build_agent
from agents.research.cross_asset_intermarket_agent.contracts import CrossAssetIntermarketAgentPayload
from agents.research.cross_asset_intermarket_agent.deterministic_policy import make_final_decision
from agents.research.cross_asset_intermarket_agent.evaluator import evaluate_response
from agents.research.cross_asset_intermarket_agent.service import CrossAssetIntermarketAgentService


def _request(**payload):
    data = {"symbol": "EURUSD", "timeframe": "H1"}
    data.update(payload)
    return AgentRequest(request_id="test-request", agent_name="cross_asset_intermarket_agent", task="Run research test.", payload=data)


def test_build_agent_smoke():
    runtime_agent = build_agent()
    assert runtime_agent.name == "cross_asset_intermarket_agent"
    assert runtime_agent.instructions
