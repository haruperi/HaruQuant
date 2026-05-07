from services.risk.margin import margin_failures, margin_impact
from services.risk.thresholds import load_risk_thresholds


def test_low_free_margin_rejection():
    impact = margin_impact({"required_margin": 80000}, {"equity": 100000, "used_margin": 10000, "free_margin": 90000})
    failures = margin_failures(impact, load_risk_thresholds())
    assert "max_total_margin_usage" in failures or "min_free_margin" in failures

