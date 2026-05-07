from __future__ import annotations

import asyncio

from agents._shared.base_contracts import AgentContext, AgentRequest, AgentStatus, EvidenceItem, RiskLevel
from agents.research.research_orchestrator_agent.agent import build_agent
from agents.research.research_orchestrator_agent.contracts import ResearchOrchestratorAgentPayload
from agents.research.research_orchestrator_agent.deterministic_policy import make_final_decision
from agents.research.research_orchestrator_agent.evaluator import evaluate_response
from agents.research.research_orchestrator_agent.service import ResearchOrchestratorAgentService


def _request(**payload):
    data = {"symbol": "EURUSD", "timeframe": "H1"}
    data.update(payload)
    return AgentRequest(request_id="test-request", agent_name="research_orchestrator_agent", task="Run research test.", payload=data)


def test_payload_serializes_to_json():
    payload = ResearchOrchestratorAgentPayload(symbol="EURUSD", timeframe="H1")
    assert payload.model_dump_json()


def test_missing_symbol_is_allowed_at_schema_boundary():
    payload = ResearchOrchestratorAgentPayload(research_question="What changed?")
    assert payload.symbol is None
