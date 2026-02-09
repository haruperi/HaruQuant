
import pytest
import pandas as pd
import numpy as np
from apps.finance import ratios

@pytest.fixture
def sample_returns():
    return pd.Series([0.01, 0.02, -0.01, 0.03, -0.02])

@pytest.fixture
def sample_trades():
    return pd.DataFrame({
        "profit_loss": [100.0, 200.0, -100.0],
        "size": [1.0, 2.0, 1.0],
        "mae_usd": [10.0, 20.0, 60.0],
        "mfe_usd": [120.0, 250.0, 10.0],
        "r_multiple": [1.0, 2.0, -1.0],
        "initial_risk_usd": [100.0, 100.0, 100.0],
        "close_time": pd.date_range("2023-01-01", periods=3)
    })

def test_sharpe_ratio(sample_returns):
    # Mean: 0.006
    # Std: 0.020736...
    sr = ratios.sharpe_ratio(sample_returns, annualize=False)
    assert sr > 0.0
    
    sr_ann = ratios.sharpe_ratio(sample_returns, annualize=True)
    assert sr_ann > sr

def test_sortino_ratio(sample_returns):
    # Downside: -0.01, -0.02
    # Target 0
    sortino = ratios.sortino_ratio(sample_returns, annualize=False)
    assert sortino > 0.0

def test_fouse_ratio(sample_returns):
    # rc (approx mean): 0.006
    # dd > 0
    fouse = ratios.fouse_ratio(sample_returns, risk_tolerance=1.0)
    assert isinstance(fouse, float)

def test_upside_potential_ratio(sample_returns):
    upr = ratios.upside_potential_ratio(sample_returns)
    assert upr > 0.0

def test_calmar_ratio():
    assert ratios.calmar_ratio(20.0, 10.0) == 2.0
    assert ratios.calmar_ratio(10.0, 0.0) == float("inf")

def test_information_ratio(sample_returns):
    bench = pd.Series([0.005, 0.01, -0.005, 0.015, -0.01])
    ir = ratios.information_ratio(sample_returns, bench, annualize=False)
    assert ir > 0.0

def test_omega_ratio(sample_returns):
    # Gains: 0.01, 0.02, 0.03 -> 0.06
    # Losses: 0.01, 0.02 -> 0.03
    # Ratio: 2.0
    omega = ratios.omega_ratio(sample_returns)
    assert pytest.approx(omega) == 2.0

def test_gain_to_pain_ratio(sample_returns):
    # Sum: 0.03
    # Abs Neg: 0.03
    # Ratio: 1.0
    gtp = ratios.gain_to_pain_ratio(sample_returns)
    assert pytest.approx(gtp) == 1.0

def test_kappa_ratio(sample_returns):
    k = ratios.kappa_ratio(sample_returns)
    assert k > 0.0

def test_profit_to_mae_ratio(sample_trades):
    # 100/10=10, 200/20=10, -100/60=-1.66
    # Mean: (10+10-1.66)/3 = 6.11
    val = ratios.profit_to_mae_ratio(sample_trades)
    assert val > 0.0

def test_mfe_to_mae_ratio(sample_trades):
    # 120/10=12, 250/20=12.5, 10/60=0.166
    val = ratios.mfe_to_mae_ratio(sample_trades)
    assert val > 8.0

def test_return_over_drawdown(sample_trades):
    # Total PL: 200
    # Max DD: Needs calculation but let's assume > 0
    # Trades: +100 (Eq 100), +200 (Eq 300), -100 (Eq 200). Peak 300. DD 100.
    rod = ratios.return_over_drawdown(sample_trades)
    assert rod > 0.0

def test_net_profit_percent_largest_loss(sample_trades):
    # Net: 200
    # Largest Loss: 100
    # Ratio: 200%
    assert ratios.net_profit_as_percent_of_largest_loss(sample_trades) == 200.0

def test_net_profit_percent_max_trade_dd(sample_trades):
    val = ratios.net_profit_as_percent_of_max_trade_drawdown(sample_trades)
    assert val > 0.0

def test_net_profit_percent_max_strategy_dd():
    assert ratios.net_profit_as_percent_of_max_strategy_drawdown(100.0, 50.0) == 200.0

def test_expectancy(sample_trades):
    # Win%: 66.66% (2/3)
    # Loss%: 33.33% (1/3)
    # Avg Win: 150
    # Avg Loss: -100
    # Exp: (0.666 * 150) + (0.333 * -100) = 100 - 33.33 = 66.66
    # Total PL 200 / 3 = 66.66
    expected = 200.0 / 3.0
    assert pytest.approx(ratios.expectancy(sample_trades)) == expected

def test_expectancy_r(sample_trades):
    # R: 1, 2, -1
    # Mean: 0.666
    assert pytest.approx(ratios.expectancy_r(sample_trades)) == 2.0/3.0

def test_payoff_ratio(sample_trades):
    # Avg Win: 150
    # Avg Loss: 100 (abs)
    # Ratio: 1.5
    assert ratios.payoff_ratio(sample_trades) == 1.5

def test_profit_factor(sample_trades):
    # Gross P: 300
    # Gross L: 100
    # PF: 3.0
    assert ratios.profit_factor(sample_trades) == 3.0

def test_sterling_ratio():
    # CAGR 20, AvgDD 10
    # Sterling = 20 / (10 + 10) = 1.0
    assert ratios.sterling_ratio(20.0, 10.0) == 1.0
