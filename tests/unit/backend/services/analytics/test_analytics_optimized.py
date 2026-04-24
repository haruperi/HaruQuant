import numpy as np
import pandas as pd
import pytest
from backend.services.analytics import metrics, drawdowns, risks, statistical_tests

def test_consecutive_wins_losses_optimized():
    # Test with standard list/array
    data = [1, 2, -1, -2, -3, 1, 1, 1, -1]
    max_wins, max_losses = metrics.consecutive_wins_losses(data)
    assert max_wins == 3
    assert max_losses == 3
    
    # Test with Series
    s = pd.Series([1, 1, -1, 1, 1, 1, 1, -1, -1])
    max_wins, max_losses = metrics.consecutive_wins_losses(s)
    assert max_wins == 4
    assert max_losses == 2

def test_drawdown_duration_optimized():
    equity = pd.Series([100, 110, 90, 80, 120, 115, 130])
    # Dds: [0, 0, -20, -30, 0, -5, 0]
    # Durations: [0, 0, 1, 2, 0, 1, 0]
    durations = drawdowns.drawdown_duration_series(equity)
    assert durations.tolist() == [0, 0, 1, 2, 0, 1, 0]
    assert drawdowns.max_drawdown_duration(equity) == 2

def test_max_close_to_close_drawdown_optimized():
    trades = pd.DataFrame({
        "close_time": pd.date_range("2024-01-01", periods=3),
        "profit_loss": [100, -50, 200],
        "mfe_usd": [120, 10, 250],
        "mae_usd": [10, 60, 20]
    })
    # Initial Equity = 0
    # T1: Peak=120, Valley=-10, Close=100. MaxDD=130 (Peak 120 to Valley -10)
    # T2: Peak=100+10=110, Valley=100-60=40, Close=100-50=50. 
    #     RunningMax is 120. DD_valley = 120-40=80, DD_close=120-50=70.
    # T3: Peak=50+250=300, Valley=50-20=30, Close=50+200=250.
    #     RunningMax is 300. DD_valley = 300-30=270, DD_close=300-250=50.
    # MaxDD should be 270.
    
    mdd = drawdowns.max_close_to_close_drawdown(trades)
    assert mdd == 270.0

def test_risk_of_ruin_optimized():
    trades = pd.DataFrame({
        "profit_loss": [10, -5, 10, -5, 10],
        "r_multiple": [2.0, -1.0, 2.0, -1.0, 2.0]
    })
    # Just check it runs and returns a valid probability
    prob = risks.risk_of_ruin(trades, risk_per_trade=1.0, target_drawdown=10.0, num_simulations=100)
    assert 0.0 <= prob <= 1.0

def test_permutation_test_optimized():
    class FakeResult:
        def __init__(self, strategy_name):
            self.strategy_name = strategy_name
        def get_equity_df(self):
            return pd.DataFrame({
                "equity": [100, 101, 102, 103, 104]
            }, index=pd.date_range("2024-01-01", periods=5))
    
    result = FakeResult("TestStrategy")
    pt_result = statistical_tests.permutation_test(result, n_permutations=100)
    assert pt_result.metric_name == "Sharpe Ratio"
    assert pt_result.n_permutations == 100
