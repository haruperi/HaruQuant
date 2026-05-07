from agents.portfolio.shared.contracts import PortfolioRequest

def test_portfolio_request_serializes():
    request = PortfolioRequest(request_type="portfolio_review")
    assert request.request_id
    assert request.model_dump() if hasattr(request, "model_dump") else request.dict()
