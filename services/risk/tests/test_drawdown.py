from services.risk.calculations.drawdown import drawdown_state
from services.risk.config.thresholds import load_risk_thresholds


def test_drawdown_breach():
    state = drawdown_state({"drawdown": 0.2}, load_risk_thresholds())
    assert "max_portfolio_drawdown" in state["failures"]
    assert state["critical"] is True

