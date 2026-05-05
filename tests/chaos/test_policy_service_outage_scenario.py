from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.contracts.common import Originator
from backend.contracts.trade_proposal.model import TradeProposal
from haruquant.risk import (
    ApprovalPolicy,
    ComplianceProfile,
    PolicyBundle,
    PolicyScope,
    RetentionPolicy,
)
from haruquant.risk import (
    AccountSnapshot,
    MarketSnapshot,
    PortfolioSnapshot,
    RiskRequestAssemblyContext,
    assemble_risk_assessment_request,
)


UTC = timezone.utc


def _proposal() -> TradeProposal:
    return TradeProposal.model_validate(
        {
            "workflow_id": "wf_001",
            "correlation_id": "corr_001",
            "causation_id": "evt_001",
            "timestamp_utc": "2026-04-09T10:00:00Z",
            "originator": {"type": "service", "id": "proposal-service"},
            "environment": "dev",
            "operating_mode": "MODE-002",
            "contract_type": "TradeProposal",
            "payload": {
                "proposal_id": "prop_001",
                "source_hypothesis_id": "hyp_001",
                "symbol": "EURUSD",
                "direction": "buy",
                "candidate_price_logic": {"entry": "market"},
                "proposed_size": {"units": 1000},
                "operating_envelope": {"strategy_id": "strat_001"},
                "session_restrictions": {},
                "expiry_at": "2026-04-09T10:05:00Z",
                "transformation_version": "proposal_v1",
                "readiness_state": "ready_for_risk",
            },
        }
    )


def test_policy_service_outage_chaos_scenario_fails_closed_on_missing_policy_bundle() -> None:
    observed_at = datetime(2026, 4, 9, 10, 0, tzinfo=UTC)
    context = RiskRequestAssemblyContext(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_prop_001",
        originator=Originator(type="service", id="risk-assembler"),
        environment="dev",
        operating_mode="MODE-002",
        compliance_profile=ComplianceProfile(
            compliance_profile_id="comp_internal",
            name="Internal",
            version="1.0.0",
            active=True,
            retention=RetentionPolicy(30, 365, 365),
            approvals=ApprovalPolicy(),
        ),
        policy_bundle=PolicyBundle(
            scope=PolicyScope(environment="dev"),
            policies=(),
            bundle_version="risk_bundle_v1",
            metadata={},
        ),
        strategy_lifecycle_state="paper",
        current_kill_switch_state="inactive",
    )

    with pytest.raises(ValueError, match="policy bundle must contain at least one policy version"):
        assemble_risk_assessment_request(
            proposal=_proposal(),
            account_snapshot=AccountSnapshot.from_policy(
                snapshot_id="acct_snap_001",
                account_id="acct_001",
                observed_at=observed_at,
                balance=10000.0,
                equity=9950.0,
                free_margin=8000.0,
                margin_used=1950.0,
                currency="USD",
            ),
            portfolio_snapshot=PortfolioSnapshot.from_policy(
                snapshot_id="port_snap_001",
                portfolio_id="portfolio_001",
                observed_at=observed_at,
                open_position_count=2,
                gross_exposure=5000.0,
                net_exposure=1000.0,
                symbols=("EURUSD",),
            ),
            market_snapshot=MarketSnapshot.from_policy(
                snapshot_id="mkt_snap_001",
                symbol="EURUSD",
                snapshot_type="best_bid_ask_tick",
                observed_at=observed_at,
                best_bid=1.1,
                best_ask=1.1002,
                spread_points=2.0,
                tradable=True,
            ),
            context=context,
        )
