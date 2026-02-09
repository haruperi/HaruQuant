
import pytest
from apps.risk import risk_limits

def test_risk_limits_defaults():
    limits = risk_limits.RiskLimits()
    assert limits.var_cap_frac == 0.10
    assert limits.es_cap_frac == 0.15
    assert limits.delta_var_cap_frac == 0.02
    assert limits.delta_es_cap_frac == 0.03
    assert limits.max_margin_used_frac == 0.50
    assert limits.min_pair_corr == 0.20
    assert limits.stressed_corr_floor == 0.50
    assert limits.use_stressed_corr is True
    assert limits.confidence_level == 0.95
    assert limits.time_horizon_days == 1
    assert limits.vol_lookback == 20
    assert limits.corr_lookback == 60
    assert limits.max_single_rc_frac == 0.20
    assert limits.rc_rebalance_tolerance == 0.05
    assert limits.cluster_var_caps is None
    assert limits.cluster_es_caps is None

def test_risk_limits_custom():
    limits = risk_limits.RiskLimits(var_cap_frac=0.05)
    assert limits.var_cap_frac == 0.05
    assert limits.es_cap_frac == 0.15  # Default remains

def test_correlation_preference_defaults():
    pref = risk_limits.CorrelationPreference()
    assert pref.target_corr == 0.50
    assert pref.penalty_strength == 2.0
    assert pref.min_budget_frac == 0.30

def test_correlation_preference_custom():
    pref = risk_limits.CorrelationPreference(target_corr=0.3)
    assert pref.target_corr == 0.3
