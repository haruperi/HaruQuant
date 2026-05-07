from agents.portfolio.shared.contracts import LiveOrderRequest


def test_live_order_request_serializes():
    request = LiveOrderRequest(symbol="EURUSD", side="buy", requested_volume=0.01)
    assert request.symbol == "EURUSD"
