from services.risk.correlation import correlation_failures, correlation_impact
from services.risk.thresholds import load_risk_thresholds


def test_cluster_breach():
    impact = correlation_impact({"symbol": "EURUSD", "cluster_exposure_impact": 0.1}, {"currency_cluster_exposure": 0.3})
    assert "max_currency_cluster_exposure" in correlation_failures(impact, load_risk_thresholds())

