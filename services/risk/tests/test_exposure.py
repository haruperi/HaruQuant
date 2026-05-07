from services.risk.calculations.exposure import exposure_snapshot, proposed_exposure_impact, concentration_failures
from services.risk.config.thresholds import load_risk_thresholds


def test_symbol_exposure_breach():
    impact = proposed_exposure_impact({"requested_volume": 1.0, "requested_price": 1.0}, {"equity": 100000, "symbol_exposure": 0.1})
    assert "max_symbol_concentration" in concentration_failures(impact, load_risk_thresholds())


def test_exposure_snapshot():
    snap = exposure_snapshot([{"symbol": "EURUSD", "strategy_id": "s1", "volume": 0.1, "price": 1.0}], equity=100000)
    assert snap["gross_exposure"] > 0

