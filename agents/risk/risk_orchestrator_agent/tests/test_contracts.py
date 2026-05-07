from services.risk.domain.contracts import RiskProposal


def test_risk_proposal_contract():
    proposal = RiskProposal(proposal_id="p1", strategy_id="s1", strategy_code_hash="hash", symbol="EURUSD", requested_volume=0.01)
    assert proposal.proposal_id == "p1"

