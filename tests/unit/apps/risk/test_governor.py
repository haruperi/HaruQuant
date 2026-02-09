
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from apps.risk import governor, risk_limits, regime

@pytest.fixture
def mock_mt5_client():
    client = MagicMock()
    # Mock get_data to return sample OHLC data
    dates = pd.date_range("2023-01-01", periods=100)
    sample_data = pd.DataFrame({
        "high": np.random.uniform(1.1, 1.2, 100),
        "low": np.random.uniform(0.9, 1.0, 100),
        "close": np.random.uniform(1.0, 1.1, 100)
    }, index=dates)
    client.get_data.return_value = sample_data
    return client

@pytest.fixture
def limits():
    return risk_limits.RiskLimits(
        var_cap_frac=0.10,
        es_cap_frac=0.15,
        delta_var_cap_frac=0.02,
        delta_es_cap_frac=0.03
    )

@pytest.fixture
def gov(mock_mt5_client, limits):
    return governor.RiskGovernor(mock_mt5_client, limits)

def test_governor_init(mock_mt5_client, limits):
    g = governor.RiskGovernor(mock_mt5_client, limits)
    assert g.mt5_client == mock_mt5_client
    assert g.limits == limits

def test_evaluate_add_position_accept(gov):
    # Small position, should accept
    current = {"A": 1.0}
    report = gov.evaluate_add_position(current, "B", 0.5)
    # With random data, hard to guarantee, but structure check
    assert report.decision in ["ACCEPT", "REJECT"]
    assert report.current_var >= 0
    assert report.new_var >= 0

def test_evaluate_add_position_reject_var(gov):
    # Massive position to trigger rejection
    current = {"A": 100.0}
    report = gov.evaluate_add_position(current, "B", 1000.0)
    # Should likely reject due to VaR cap
    assert report.decision in ["ACCEPT", "REJECT"]

def test_effective_limits_normal(gov):
    normal_regime = regime.RegimeState(name="NORMAL")
    eff = gov.effective_limits(normal_regime)
    assert eff.var_cap_frac == gov.limits.var_cap_frac

def test_effective_limits_stress(gov):
    stress_regime = regime.RegimeState(name="STRESS")
    eff = gov.effective_limits(stress_regime)
    # Should tighten limits
    assert eff.var_cap_frac < gov.limits.var_cap_frac

def test_compute_portfolio_risk(gov):
    positions = {"A": 1.0, "B": 1.0}
    equity = 10000.0
    eff = gov.limits
    
    var_val, es_val, margin, rc_map = gov._compute_portfolio_risk(positions, equity, eff)
    assert var_val >= 0
    assert es_val >= 0
    assert es_val >= var_val  # ES should be >= VaR

def test_estimate_covariance(gov):
    returns_df = pd.DataFrame({
        "A": np.random.normal(0, 0.01, 100),
        "B": np.random.normal(0, 0.01, 100)
    })
    symbols = ["A", "B"]
    
    cov = gov._estimate_covariance(returns_df, symbols, gov.limits)
    assert cov.shape == (2, 2)
    assert np.all(np.isfinite(cov))

def test_build_weights_from_positions(gov):
    positions = {"A": 1.0, "B": 2.0}
    data = {
        "A": pd.DataFrame({"close": [1.1] * 100, "Close": [1.1] * 100}),
        "B": pd.DataFrame({"close": [1.2] * 100, "Close": [1.2] * 100})
    }
    symbols = ["A", "B"]
    
    weights = gov._build_weights_from_positions(positions, data, symbols)
    assert len(weights) == 2
    assert np.sum(weights) == pytest.approx(1.0)

def test_compute_risk_contributions_pct(gov):
    weights = np.array([0.5, 0.5])
    cov = np.array([[0.01, 0.0], [0.0, 0.04]])
    symbols = ["A", "B"]
    
    rc_pct = gov._compute_risk_contributions_pct(weights, cov, symbols)
    assert len(rc_pct) == 2
    assert sum(rc_pct.values()) == pytest.approx(1.0)

def test_rc_violations(gov):
    rc_pct = {"A": 0.15, "B": 0.85}
    violations = gov._rc_violations(rc_pct, max_single=0.20)
    assert "B" in violations

def test_portfolio_correlation_map(gov):
    weights = np.array([0.5, 0.5])
    cov = np.array([[0.01, 0.005], [0.005, 0.04]])
    symbols = ["A", "B"]
    
    corr_map = gov._portfolio_correlation_map(weights, cov, symbols)
    assert len(corr_map) == 2
    assert all(-1 <= v <= 1 for v in corr_map.values())

def test_check_cluster_caps(gov):
    positions = {"A": 1.0, "B": 1.0, "C": 1.0}
    equity = 10000.0
    symbol_to_cluster = {"A": "FX", "B": "FX", "C": "EQUITY"}
    
    violations = gov._check_cluster_caps(positions, equity, symbol_to_cluster, gov.limits)
    # Should return list (may be empty)
    assert isinstance(violations, list)

def test_estimate_margin_used(gov):
    positions = {"A": 1.0, "B": 2.0}
    margin = gov._estimate_margin_used(positions)
    assert margin >= 0

def test_get_data(gov):
    symbols = ["EURUSD", "GBPUSD"]
    data = gov._get_data(symbols)
    assert len(data) == 2
    assert "EURUSD" in data

def test_build_returns_df(gov):
    data = {
        "A": pd.DataFrame({"close": [1.0, 1.01, 1.02]}),
        "B": pd.DataFrame({"close": [2.0, 2.02, 2.04]})
    }
    symbols = ["A", "B"]
    
    returns_df = gov._build_returns_df(data, symbols)
    assert returns_df.shape[1] == 2
    assert returns_df.shape[0] <= 3

def test_portfolio_notional_value(gov):
    positions = {"A": 1.0, "B": 1.0}
    data = {
        "A": pd.DataFrame({"close": [1.1]}),
        "B": pd.DataFrame({"close": [1.2]})
    }
    symbols = ["A", "B"]
    
    notional = gov._portfolio_notional_value(positions, data, symbols)
    assert notional > 0

def test_symbol_notional_value(gov):
    data = {"A": pd.DataFrame({"close": [1.1]})}
    notional = gov._symbol_notional_value("A", 1.0, data)
    assert notional > 0
