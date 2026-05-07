import pytest
from services.risk.governance.approval_tokens import USED_APPROVAL_SIGNATURES, validate_approval_token
from services.risk.domain.exceptions import RiskTokenError
from services.risk.governance.governor import RiskGovernor


def test_token_validation_and_replay():
    USED_APPROVAL_SIGNATURES.clear()
    decision = RiskGovernor().evaluate_trade(proposal={"proposal_id": "p1", "strategy_id": "s1", "strategy_code_hash": "hash", "symbol": "EURUSD", "side": "buy", "order_type": "market", "requested_volume": 0.01, "expected_risk": {"amount": 50}}, portfolio_snapshot={"equity": 100000}, market_snapshot={"spread": 1.0})
    token = decision.approval_token
    assert token is not None
    assert validate_approval_token(token, proposal={"proposal_id": "p1", "symbol": "EURUSD", "side": "buy", "order_type": "market", "requested_volume": 0.01}) is True
    with pytest.raises(RiskTokenError):
        validate_approval_token(token, proposal={"proposal_id": "p1", "symbol": "EURUSD", "side": "buy", "order_type": "market", "requested_volume": 0.01})

