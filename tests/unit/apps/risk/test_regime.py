
import pytest
import pandas as pd
import numpy as np
from apps.risk import regime

@pytest.fixture
def detector():
    return regime.RiskRegimeDetector(
        vol_spike_mult=1.5,
        corr_spike_level=0.5,
        dd_trigger_frac=0.1,
        lookback=10,
        vol_med_window=5
    )

def test_regime_state_defaults():
    state = regime.RegimeState(name="NORMAL")
    assert state.name == "NORMAL"

def test_detect_normal(detector):
    # Create benign data
    # Low volatility, low correlation, no drawdown
    dates = pd.date_range("2023-01-01", periods=20)
    returns = pd.DataFrame({
        "A": np.random.normal(0, 0.01, 20),
        "B": np.random.normal(0, 0.01, 20)
    }, index=dates)
    
    # Ensure no flags triggered
    # 1. Vol: stddev is small (approx 0.01)
    # 2. Corr: random ~0
    # 3. DD: None provided
    
    state = detector.detect(returns)
    assert state.name == "NORMAL"

def test_detect_vol_spike(detector):
    # Trigger vol spike: last returns huge
    dates = pd.date_range("2023-01-01", periods=20)
    data = np.random.normal(0, 0.01, (20, 2))
    # Make last few periods crazy volatile
    data[-3:, :] = np.random.normal(0, 0.10, (3, 2)) 
    
    returns = pd.DataFrame(data, columns=["A", "B"], index=dates)
    
    # This should trigger flag 1.
    # Flags = 1 -> NORMAL (need >= 2 for STRESS)
    state = detector.detect(returns)
    assert state.name == "NORMAL" 
    
    # To get STRESS we need 2 flags. Let's add correlation.
    
def test_detect_stress_combined(detector):
    # 1. High Vol
    dates = pd.date_range("2023-01-01", periods=20)
    # Perfectly correlated high vol
    # Vol spike: 5x normal
    # Corr spike: 1.0
    
    ret_a = np.concatenate([np.random.normal(0, 0.01, 15), np.random.normal(0, 0.1, 5)])
    ret_b = ret_a # Perfect correlation
    
    returns = pd.DataFrame({"A": ret_a, "B": ret_b}, index=dates)
    
    state = detector.detect(returns)
    assert state.name == "STRESS"

def test_detect_drawdown(detector):
    # Need 2 flags.
    # 1. Drawdown > 0.1
    # 2. Let's force Correlation or Vol to be high too.
    
    dates = pd.date_range("2023-01-01", periods=20)
    equity = pd.Series(np.linspace(100, 80, 20), index=dates) # 20% drop
    
    # Create high correlation returns to trigger 2nd flag
    ret_a = np.random.normal(0, 0.01, 20)
    ret_b = ret_a
    returns = pd.DataFrame({"A": ret_a, "B": ret_b}, index=dates)
    
    state = detector.detect(returns, equity_curve=equity)
    assert state.name == "STRESS"

def test_insufficient_data(detector):
    short_ret = pd.DataFrame({"A": [0.01]}, index=[pd.Timestamp("2023-01-01")])
    state = detector.detect(short_ret)
    assert state.name == "NORMAL"
