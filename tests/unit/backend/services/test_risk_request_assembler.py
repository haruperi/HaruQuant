from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend_retiring.contracts.common import Originator
from backend_retiring.contracts.trade_proposal.model import TradeProposal
from haruquant.risk import (
    ApprovalPolicy,
    ComplianceProfile,
    PolicyBundle,
    PolicyScope,
    PolicyVersion,
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


def _proposal(*, readiness_state: str = "ready_for_risk", symbol: str = "EURUSD") -> TradeProposal:
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
                "symbol": symbol,
                "direction": "buy",
                "candidate_price_logic": {"entry": "market"},
                "proposed_size": {"units": 1000},
                "operating_envelope": {"strategy_id": "strat_001"},
                "session_restrictions": {},
                "expiry_at": "2026-04-09T10:05:00Z",
                "transformation_version": "proposal_v1",
                "readiness_state": readiness_state,
            },
        }
    )


def _context() -> RiskRequestAssemblyContext:
    return RiskRequestAssemblyContext(
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
            policies=(
                PolicyVersion(
                    policy_version_id="risk_policy_001",
                    policy_type="risk",
                    version="1.0.0",
                    status="active",
                    effective_from="2026-04-09T00:00:00Z",
                ),
            ),
            bundle_version="risk_bundle_v1",
            metadata={"formula_version": "formula_v1"},
        ),
        strategy_lifecycle_state="paper",
        current_kill_switch_state="inactive",
        tenant_id="tenant_001",
        account_scope_id="acct_001",
        strategy_scope_id="strat_001",
    )


def _account_snapshot(observed_at: datetime) -> AccountSnapshot:
    return AccountSnapshot.from_policy(
        snapshot_id="acct_snap_001",
        account_id="acct_001",
        observed_at=observed_at,
        balance=10000.0,
        equity=9950.0,
        free_margin=8000.0,
        margin_used=1950.0,
        currency="USD",
    )


def _portfolio_snapshot(observed_at: datetime) -> PortfolioSnapshot:
    return PortfolioSnapshot.from_policy(
        snapshot_id="port_snap_001",
        portfolio_id="portfolio_001",
        observed_at=observed_at,
        open_position_count=2,
        gross_exposure=5000.0,
        net_exposure=1000.0,
        symbols=("EURUSD", "GBPUSD"),
    )


def _market_snapshot(observed_at: datetime, *, symbol: str = "EURUSD") -> MarketSnapshot:
    return MarketSnapshot.from_policy(
        snapshot_id="mkt_snap_001",
        symbol=symbol,
        snapshot_type="best_bid_ask_tick",
        observed_at=observed_at,
        best_bid=1.1,
        best_ask=1.1002,
        spread_points=2.0,
        tradable=True,
    )


def test_risk_request_assembler_builds_complete_contract():
    observed_at = datetime(2026, 4, 9, 10, 0, tzinfo=UTC)

    contract = assemble_risk_assessment_request(
        proposal=_proposal(),
        account_snapshot=_account_snapshot(observed_at),
        portfolio_snapshot=_portfolio_snapshot(observed_at),
        market_snapshot=_market_snapshot(observed_at),
        context=_context(),
        risk_request_id="risk_req_001",
    )

    assert contract.workflow_id == "wf_001"
    assert contract.payload.risk_request_id == "risk_req_001"
    assert contract.payload.proposal_id == "prop_001"
    assert contract.payload.action_type == "new_entry"
    assert contract.payload.account_snapshot_ref == "acct_snap_001"
    assert contract.payload.portfolio_snapshot_ref == "port_snap_001"
    assert contract.payload.market_snapshot_ref == "mkt_snap_001"
    assert contract.payload.requested_freshness_classes.account_snapshot == "HOT"
    assert contract.payload.requested_freshness_classes.portfolio_snapshot == "HOT"
    assert contract.payload.requested_freshness_classes.market_snapshot == "HOT"
    assert contract.payload.active_policy_bundle.policy_version == "risk_bundle_v1"
    assert contract.payload.active_policy_bundle.formula_version == "formula_v1"
    assert contract.payload.compliance_profile_id == "comp_internal"
    assert contract.payload.current_kill_switch_state == "inactive"


def test_risk_request_assembler_rejects_non_ready_proposal():
    observed_at = datetime(2026, 4, 9, 10, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="ready_for_risk"):
        assemble_risk_assessment_request(
            proposal=_proposal(readiness_state="validated"),
            account_snapshot=_account_snapshot(observed_at),
            portfolio_snapshot=_portfolio_snapshot(observed_at),
            market_snapshot=_market_snapshot(observed_at),
            context=_context(),
        )


def test_risk_request_assembler_rejects_symbol_mismatch():
    observed_at = datetime(2026, 4, 9, 10, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="symbol must match"):
        assemble_risk_assessment_request(
            proposal=_proposal(symbol="EURUSD"),
            account_snapshot=_account_snapshot(observed_at),
            portfolio_snapshot=_portfolio_snapshot(observed_at),
            market_snapshot=_market_snapshot(observed_at, symbol="USDJPY"),
            context=_context(),
        )


def test_risk_request_assembler_rejects_missing_formula_version():
    observed_at = datetime(2026, 4, 9, 10, 0, tzinfo=UTC)
    context = _context()
    context = RiskRequestAssemblyContext(
        **{
            **context.__dict__,
            "policy_bundle": PolicyBundle(
                scope=context.policy_bundle.scope,
                policies=context.policy_bundle.policies,
                bundle_version=context.policy_bundle.bundle_version,
                metadata={},
            ),
        }
    )

    with pytest.raises(ValueError, match="formula_version"):
        assemble_risk_assessment_request(
            proposal=_proposal(),
            account_snapshot=_account_snapshot(observed_at + timedelta(seconds=1)),
            portfolio_snapshot=_portfolio_snapshot(observed_at + timedelta(seconds=1)),
            market_snapshot=_market_snapshot(observed_at + timedelta(seconds=1)),
            context=context,
        )
