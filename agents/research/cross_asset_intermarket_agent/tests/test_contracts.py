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


def test_payload_serializes_to_json():
    payload = CrossAssetIntermarketAgentPayload(symbol="EURUSD", timeframe="H1")
    assert payload.model_dump_json()


def test_missing_symbol_is_allowed_at_schema_boundary():
    payload = CrossAssetIntermarketAgentPayload(research_question="What changed?")
    assert payload.symbol is None
