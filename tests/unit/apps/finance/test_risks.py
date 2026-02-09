
import pytest
import pandas as pd
import numpy as np
from apps.finance import risks

@pytest.fixture
def sample_returns():
    # Mean 0.0, Std 0.01414...
    return pd.Series([0.01, -0.01, 0.02, -0.02, 0.0])

@pytest.fixture
def sample_trades():
    return pd.DataFrame({
        "profit_loss": [100.0, -50.0, -50.0, 100.0],
        "size": [1.0, 1.0, 1.0, 1.0],
        "time_in_trade": [1.0, 1.0, 1.0, 1.0],
        "open_time": pd.date_range("2023-01-01", periods=4),
        "close_time": pd.date_range("2023-01-01 01:00", periods=4)
    })

def test_volatility(sample_returns):
    vol = risks.volatility(sample_returns)
    assert vol > 0.0

def test_annualized_volatility(sample_returns):
    ann_vol = risks.annualized_volatility(sample_returns)
    assert ann_vol > risks.volatility(sample_returns)

def test_downside_volatility(sample_returns):
    # Neg returns: -0.01, -0.02.
    down_vol = risks.downside_volatility(sample_returns)
    assert down_vol > 0.0

def test_value_at_risk(sample_returns):
    # Historical
    var_hist = risks.value_at_risk(sample_returns, method="historical")
    assert var_hist >= 0.0
    
    # Parametric
    var_param = risks.value_at_risk(sample_returns, method="parametric")
    assert var_param > 0.0

    # Cornish-Fisher
    var_cf = risks.value_at_risk(sample_returns, method="cornish_fisher")
    assert var_cf > 0.0

def test_conditional_var(sample_returns):
    cvar = risks.conditional_var(sample_returns)
    assert cvar >= 0.0

def test_risk_of_ruin(sample_trades):
    # Small sample, high risk simulation
    prob = risks.risk_of_ruin(sample_trades, risk_per_trade=0.1, num_simulations=100)
    assert 0.0 <= prob <= 1.0

def test_max_loss_probability(sample_trades):
    # Losses: -50, -50.
    # Threshold -40. Both exceed. Prob 1.0
    prob = risks.max_loss_probability(sample_trades, loss_threshold=-40.0)
    assert prob == 1.0
    
    # Threshold -60. None exceed. Prob 0.0
    prob2 = risks.max_loss_probability(sample_trades, loss_threshold=-60.0)
    assert prob2 == 0.0

def test_drawdown_probability():
    equity = pd.Series([100, 90, 80, 70, 80, 90, 100])
    # Drawdowns: 0, -10%, -20%, -30%, ...
    # Threshold 15%. Exceeded at 80 (20%) and 70 (30%).
    # Total points 7. Exceeded 2?
    # Wait, rolling/expanding max.
    # 100 -> 90 (-10%), 80 (-20%), 70 (-30%), 80 (max 100 -> -20%), 90 (-10%), 100 (0%).
    # DDs: 0, -10, -20, -30, -20, -10, 0.
    # Exceeding 15% (i.e. < -15%): -20, -30, -20. (3 points).
    # Prob = 3/7
    prob = risks.drawdown_probability(equity, threshold=15.0)
    assert pytest.approx(prob) == 3/7

def test_max_exposure(sample_trades):
    # Size 1.0 -> 100,000
    assert risks.max_exposure(sample_trades) == 100000.0

def test_avg_exposure(sample_trades):
    assert risks.avg_exposure(sample_trades) == 100000.0

def test_exposure_time_ratio(sample_trades):
    # Total trade time: 4.0 hours
    # Total time: 0 to 3+1hr = ~4 hours?
    # Open times: 0, 1, 2, 3 days? No, freq D default in date_range.
    # 2023-01-01 to 2023-01-04.
    # Total range ~3 days = 72 hours.
    # Ratio small.
    ratio = risks.exposure_time_ratio(sample_trades)
    assert 0.0 < ratio < 1.0
