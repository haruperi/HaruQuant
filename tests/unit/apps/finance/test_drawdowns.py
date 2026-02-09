
import pytest
import pandas as pd
import numpy as np
from apps.finance import drawdowns

@pytest.fixture
def sample_equity():
    # 100 -> 110 -> 100 -> 90 -> 120 -> 110
    return pd.Series([100.0, 110.0, 100.0, 90.0, 120.0, 110.0])

@pytest.fixture
def sample_trades():
    return pd.DataFrame({
        "profit_loss": [10.0, -10.0, -20.0, 40.0, -10.0],
        "close_time": pd.date_range("2023-01-01", periods=5),
        "mfe_usd": [15.0, 5.0, 5.0, 50.0, 5.0],
        "mae_usd": [5.0, 15.0, 25.0, 10.0, 15.0]
    })

def test_drawdown_series(sample_equity):
    # Peaks: 100, 110, 110, 110, 120, 120
    # DD: 0, 0, -10, -20, 0, -10
    dd = drawdowns.drawdown_series(sample_equity)
    expected = pd.Series([0.0, 0.0, -10.0, -20.0, 0.0, -10.0])
    pd.testing.assert_series_equal(dd, expected)
    
    assert drawdowns.drawdown_series(pd.Series(dtype=float)).empty

def test_max_strategy_drawdown(sample_equity):
    # Max DD is 20 (from 110 down to 90)
    assert drawdowns.max_strategy_drawdown(sample_equity) == 20.0
    assert drawdowns.max_strategy_drawdown(pd.Series(dtype=float)) == 0.0

def test_max_strategy_drawdown_percent(sample_equity):
    # 90 / 110 - 1 = -0.1818...
    mdd_pct = drawdowns.max_strategy_drawdown_percent(sample_equity)
    assert pytest.approx(mdd_pct) == (20/110) * 100

def test_avg_drawdown(sample_equity):
    # DD values: -10, -20, -10
    # Mean: -13.333
    assert pytest.approx(drawdowns.avg_drawdown(sample_equity)) == 13.333333

def test_drawdown_distribution(sample_equity):
    dist = drawdowns.drawdown_distribution(sample_equity)
    assert dist["max"] == 20.0
    assert pytest.approx(dist["avg"]) == 13.333333

def test_drawdown_duration_series(sample_equity):
    # Peaks: 100, 110, 110, 110, 120, 120
    # High?  Y,   Y,   N,   N,   Y,   N
    # Dur:   0,   0,   1,   2,   0,   1
    dur = drawdowns.drawdown_duration_series(sample_equity)
    expected = pd.Series([0, 0, 1, 2, 0, 1])
    pd.testing.assert_series_equal(dur, expected)

def test_max_drawdown_duration(sample_equity):
    assert drawdowns.max_drawdown_duration(sample_equity) == 2

def test_avg_drawdown_duration(sample_equity):
    # Durations > 0: 1, 2, 1 -> mean 1.333
    assert pytest.approx(drawdowns.avg_drawdown_duration(sample_equity)) == 1.333333

def test_time_to_recovery(sample_equity):
    # DD 1: len 2 (recovered at index 4)
    # DD 2: len 1 (not recovered yet? logic says append when high)
    # The loop finishes. Last point is not high. So last DD not recovered.
    # Only 1 recovered DD of length 2.
    recoveries = drawdowns.time_to_recovery(sample_equity)
    assert recoveries == [2]

def test_ulcer_index(sample_equity):
    # PCT DD: 0, 0, -10/110, -20/110, 0, -10/120
    # Square, mean, sqrt
    val = drawdowns.ulcer_index(sample_equity)
    assert val > 0

def test_pain_index(sample_equity):
    val = drawdowns.pain_index(sample_equity)
    assert val > 0

def test_pain_ratio(sample_equity):
    returns = sample_equity.pct_change().dropna()
    pr = drawdowns.pain_ratio(sample_equity, returns)
    assert pr != 0

def test_recovery_factor(sample_equity):
    # Net profit: 110 - 100 = 10
    # Max DD: 20
    # RF = 0.5
    assert drawdowns.recovery_factor(sample_equity) == 0.5

def test_trade_level_drawdowns(sample_trades):
    # PnL: 10, -10, -20, 40, -10
    # Cum: 10, 0, -20, 20, 10
    # Max: 10, 10, 10, 20, 20
    # DD:  0, -10, -30, 0, -10
    dd = drawdowns.trade_level_drawdowns(sample_trades)
    expected = pd.Series([0.0, -10.0, -30.0, 0.0, -10.0], index=sample_trades.index)
    # Note: function uses sort_values('close_time'), but our sample is already sorted
    # Result index aligns with sorted trades
    pd.testing.assert_series_equal(dd, expected)

def test_max_close_to_close_drawdown(sample_trades):
    # Uses MFE/MAE
    # 1. Start 0. Trade 1: MFE 15, MAE 5, PL 10. Peak 15. Close 10. RunMax 15. DD_Valley (15- -5) = 20? No valley is equity - mae.
    # Logic: trade_valley = current_equity - trade["mae_usd"]
    # 1. Eq 0. Pk 15, Val -5. Close 10. MaxEq 15. DD_V: 15-(-5)=20. DD_C: 15-10=5. MaxDD 20. Eq 10.
    # 2. Eq 10. Pk 10+5=15. Val 10-15=-5. Close 10-10=0. MaxEq 15. DD_V: 15-(-5)=20. DD_C: 15-0=15. MaxDD 20. Eq 0.
    # 3. Eq 0. Pk 5. Val -25. Close -20. MaxEq 15. DD_V: 15-(-25)=40. DD_C: 15-(-20)=35. MaxDD 40. Eq -20.
    # 4. Eq -20. Pk -20+50=30. Val -20-10=-30. Close -20+40=20. MaxEq 30. DD_V: 30-(-30)=60. DD_C: 30-20=10. MaxDD 60. Eq 20.
    # 5. Eq 20. Pk 25. Val 5. Close 10. MaxEq 30. DD_V: 30-5=25. DD_C: 30-10=20. MaxDD 60.
    
    mdd = drawdowns.max_close_to_close_drawdown(sample_trades)
    assert mdd == 60.0

def test_account_size_required(sample_trades):
    assert drawdowns.account_size_required(sample_trades) == 60.0

def test_avg_yearly_max_drawdown():
    dates = pd.date_range("2023-01-01", periods=500, freq="D")
    equity = pd.Series(np.random.normal(0, 1, 500).cumsum() + 100, index=dates)
    # Should cover 2023 and 2024
    avg_mdd = drawdowns.avg_yearly_max_drawdown(equity)
    assert avg_mdd >= 0.0

def test_max_strategy_drawdown_date(sample_equity):
    # Equity: 100, 110, 100, 90, 120, 110
    # DD: 0, 0, -10, -20, 0, -10
    # Min is -20 at index 3
    dates = pd.date_range("2023-01-01", periods=6)
    sample_equity.index = dates
    
    date = drawdowns.max_strategy_drawdown_date(sample_equity)
    assert date == dates[3]
