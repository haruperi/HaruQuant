from services.risk.governor import RiskGovernor


def test_invalid_config_hash_fail_closed():
    governor = RiskGovernor(thresholds={"config_hash": ""})
    decision = governor.evaluate_trade(proposal={"proposal_id": "bad", "requested_volume": 0.01}, portfolio_snapshot={}, market_snapshot={})
    assert decision.decision == "error_fail_closed"


def test_kill_switch_blocks():
    decision = RiskGovernor().evaluate_trade(proposal={"proposal_id": "p1", "strategy_id": "s1", "strategy_code_hash": "hash", "symbol": "EURUSD", "side": "buy", "requested_volume": 0.01, "expected_risk": {"amount": 50}}, portfolio_snapshot={"equity": 100000, "kill_switch_active": True}, market_snapshot={"spread": 1.0})
    assert decision.decision == "blocked"
    assert "kill_switch_active" in decision.reasons

