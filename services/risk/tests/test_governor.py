from services.risk.governor import RiskGovernor


def test_normal_approval_case():
    decision = RiskGovernor().evaluate_trade(proposal={"proposal_id": "p1", "strategy_id": "s1", "strategy_code_hash": "hash", "symbol": "EURUSD", "side": "buy", "requested_volume": 0.01, "expected_risk": {"amount": 50}}, portfolio_snapshot={"equity": 100000}, market_snapshot={"spread": 1.0})
    assert decision.decision == "approved"
    assert decision.approval_token


def test_size_reduction_case():
    decision = RiskGovernor().evaluate_trade(proposal={"proposal_id": "p2", "strategy_id": "s1", "strategy_code_hash": "hash", "symbol": "EURUSD", "side": "buy", "requested_volume": 0.01, "expected_risk": {"amount": 750}}, portfolio_snapshot={"equity": 100000}, market_snapshot={"spread": 1.0})
    assert decision.decision == "approved_with_reduced_size"
    assert decision.approved_volume < decision.requested_volume


def test_max_risk_rejection():
    decision = RiskGovernor().evaluate_trade(proposal={"proposal_id": "p3", "strategy_id": "s1", "strategy_code_hash": "hash", "symbol": "EURUSD", "side": "buy", "requested_volume": 1.0, "expected_risk": {"amount": 5000}}, portfolio_snapshot={"equity": 100000}, market_snapshot={"spread": 1.0})
    assert decision.decision == "rejected"
    assert "max_risk_per_trade" in decision.reasons

