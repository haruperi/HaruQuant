from __future__ import annotations

from datetime import datetime, timezone

from backend_retiring.agents import RiskGovernorAgentAdapter
from backend_retiring.contracts.common import Originator
from backend_retiring.contracts.risk_assessment_decision.model import (
    ProvenanceBundleRef,
    RiskAssessmentDecision,
    RiskAssessmentDecisionPayload,
)


UTC = timezone.utc


class FakeDeterministicRiskService:
    def __init__(self) -> None:
        self.seen_request_id = None

    def evaluate(self, risk_request_id: str) -> RiskAssessmentDecision:
        self.seen_request_id = risk_request_id
        return RiskAssessmentDecision(
            workflow_id="wf_001",
            correlation_id="corr_001",
            causation_id="evt_001",
            originator=Originator(type="service", id="risk_service"),
            environment="paper",
            operating_mode="MODE-002",
            payload=RiskAssessmentDecisionPayload(
                risk_decision_id="risk_001",
                proposal_id="prop_001",
                decision="APPROVE",
                reasons=["all_checks_passed"],
                limit_constraints=[],
                risk_metrics_snapshot={"margin_utilization": 0.2},
                freshness_expiry=datetime(2026, 4, 9, 10, 5, tzinfo=UTC),
                policy_version="risk_policy_v1",
                formula_version="formula_v1",
                provenance_bundle_ref=ProvenanceBundleRef(
                    bundle_id="bundle_001",
                    account_snapshot_ref="acct_001",
                    market_snapshot_ref="mkt_001",
                ),
            ),
        )


def test_risk_governor_adapter_cannot_bypass_deterministic_decision_source() -> None:
    service = FakeDeterministicRiskService()
    adapter = RiskGovernorAgentAdapter(risk_service=service)

    result = adapter.evaluate(risk_request_id="risk_req_001")

    assert service.seen_request_id == "risk_req_001"
    assert result.contract_type == "RiskAssessmentDecision"
