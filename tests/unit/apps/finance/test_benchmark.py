
import pytest
import pandas as pd
import numpy as np
from apps.finance import benchmark

@pytest.fixture
def sample_data():
    """Create sample strategy and benchmark data."""
    dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
    strategy_returns = pd.Series(
        [0.01, 0.02, -0.01, 0.03, 0.01, -0.02, 0.01, 0.0, 0.02, -0.01], index=dates
    )
    benchmark_returns = pd.Series(
        [0.005, 0.01, -0.005, 0.02, 0.005, -0.01, 0.005, 0.0, 0.01, -0.005], index=dates
    )
    
    # Create equity curves starting at 100
    strategy_equity = (1 + strategy_returns).cumprod() * 100
    benchmark_equity = (1 + benchmark_returns).cumprod() * 100
    
    return {
        "strategy_returns": strategy_returns,
        "benchmark_returns": benchmark_returns,
        "strategy_equity": strategy_equity,
        "benchmark_equity": benchmark_equity
    }

def test_benchmark_returns():
    # Test typical case
    equity = pd.Series([100, 101, 102.01, 99.0], index=[1, 2, 3, 4])
    returns = benchmark.benchmark_returns(equity)
    expected = pd.Series([0.01, 0.01, -0.029506], index=[2, 3, 4])
    # Values: 101/100-1=0.01, 102.01/101-1=0.01, 99/102.01-1=-0.0295069...
    # We'll use approx to avoid precision issues
    assert returns.iloc[0] == pytest.approx(0.01)
    assert returns.iloc[1] == pytest.approx(0.01)
    assert returns.iloc[2] == pytest.approx(-0.0295069)

    
    # Test insufficient data
    empty_returns = benchmark.benchmark_returns(pd.Series([100]))
    assert empty_returns.empty

def test_excess_returns(sample_data):
    s_ret = sample_data["strategy_returns"]
    b_ret = sample_data["benchmark_returns"]
    excess = benchmark.excess_returns(s_ret, b_ret)
    
    # Manual check first few
    # 0.01 - 0.005 = 0.005
    # 0.02 - 0.01 = 0.01
    assert excess.iloc[0] == 0.005
    assert excess.iloc[1] == 0.01
    
    # Test mismatch length
    excess_mismatch = benchmark.excess_returns(s_ret.iloc[1:], b_ret)
    assert len(excess_mismatch) == 9

def test_beta(sample_data):
    s_ret = pd.Series([0.02, 0.02, -0.02, -0.02])
    b_ret = pd.Series([0.01, 0.01, -0.01, -0.01])
    # Strategy moves 2x benchmark -> Beta should be 2.0
    b = benchmark.beta(s_ret, b_ret)
    assert b == 2.0
    
    # Test zero variance benchmark
    flat_bench = pd.Series([0.01, 0.01, 0.01, 0.01])
    assert benchmark.beta(s_ret, flat_bench) == 0.0

def test_alpha(sample_data):
    s_ret = pd.Series([0.02, 0.02, 0.02, 0.02]) # 2% per day -> huge annualized
    b_ret = pd.Series([0.01, 0.01, 0.01, 0.01]) # 1% per day
    # Beta undefined (variance 0), function returns 0.0 if aligned < 2, 
    # but here variance is 0, so beta is 0. 
    # alpha = avg_strat - (rf + beta * (avg_bench - rf))
    # alpha = 0.02 - (0 + 0) = 0.02 daily -> 5.04 annualized
    
    a = benchmark.alpha(s_ret, b_ret, risk_free_rate=0.0)
    a = benchmark.alpha(s_ret, b_ret, risk_free_rate=0.0)
    # Alpha = AvgStrat - (Rf + Beta * (AvgBench - Rf))
    # Alpha = 0.02 - (0 + 2.0 * (0.01 - 0)) ??? No, Beta is 0.0 because variance is 0.
    # So Alpha = 0.02 - 0 = 0.02
    # Annualized = 0.02 * 252 = 5.04
    assert pytest.approx(a, rel=1e-5) == 0.02 * 252

def test_r_squared(sample_data):
    s_ret = pd.Series([0.01, 0.02, 0.03])
    b_ret = pd.Series([0.01, 0.02, 0.03])
    # Perfect correlation
    assert benchmark.r_squared(s_ret, b_ret) == pytest.approx(1.0)
    
    s_ret_opp = pd.Series([0.01, 0.02, 0.03])
    b_ret_opp = pd.Series([-0.01, -0.02, -0.03])
    # Perfect negative correlation -> R2 is correlation squared -> (-1)^2 = 1
    assert benchmark.r_squared(s_ret_opp, b_ret_opp) == pytest.approx(1.0)

def test_tracking_error(sample_data):
    s_ret = pd.Series([0.02, 0.02])
    b_ret = pd.Series([0.01, 0.01])
    # Excess: 0.01, 0.01 -> std is 0
    assert benchmark.tracking_error(s_ret, b_ret) == 0.0

def test_relative_drawdown(sample_data):
    # Strategy: 100 -> 110 -> 100 (DD starts)
    # Benchmark: 100 -> 100 -> 100 (Flat)
    # Relative: 1.0 -> 1.1 -> 1.0
    # Peak relative: 1.1
    # Current relative: 1.0
    # DD: 1.0 - 1.1 = -0.1
    
    s_eq = pd.Series([100, 110, 100])
    b_eq = pd.Series([100, 100, 100])
    
    dd = benchmark.relative_drawdown(s_eq, b_eq)
    assert pytest.approx(dd.iloc[2]) == -0.1

def test_batting_average(sample_data):
    s_ret = pd.Series([0.02, 0.00, 0.02])
    b_ret = pd.Series([0.01, 0.01, 0.01])
    # 0.02 > 0.01 (Win)
    # 0.00 < 0.01 (Loss)
    # 0.02 > 0.01 (Win)
    # 2/3 = 66.66%
    assert pytest.approx(benchmark.batting_average(s_ret, b_ret)) == (2/3) * 100

def test_up_down_capture():
    # Benchmark UP: 2 periods
    # Benchmark DOWN: 2 periods
    b_ret = pd.Series([0.01, 0.02, -0.01, -0.02])
    
    # Strategy matches exactly
    s_ret = pd.Series([0.01, 0.02, -0.01, -0.02])
    
    up, down = benchmark.up_down_capture(s_ret, b_ret)
    assert up == 100.0
    assert down == 100.0
    
    # Strategy double gains, half losses
    s_ret_2 = pd.Series([0.02, 0.04, -0.005, -0.01])
    # Up mean bench: 0.015, strat: 0.03 -> 200%
    # Down mean bench: -0.015, strat: -0.0075 -> 50%
    up2, down2 = benchmark.up_down_capture(s_ret_2, b_ret)
    assert up2 == 200.0
    assert down2 == 50.0

