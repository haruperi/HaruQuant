"""Risk governor adapter over deterministic risk services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.contracts.risk_assessment_decision.model import RiskAssessmentDecision


class DeterministicRiskService(Protocol):
    """Deterministic risk service contract used by the adapter."""

    def evaluate(self, risk_request_id: str) -> RiskAssessmentDecision: ...


@dataclass(frozen=True)
class RiskGovernorAgentAdapter:
    """Controlled adapter that only forwards deterministic risk decisions."""

    risk_service: DeterministicRiskService
    agent_name: str = "risk_governor_agent"

    def evaluate(self, *, risk_request_id: str) -> RiskAssessmentDecision:
        decision = self.risk_service.evaluate(risk_request_id)
        if decision.contract_type != "RiskAssessmentDecision":
            raise ValueError("RiskGovernorAgent must return RiskAssessmentDecision")
        return decision
