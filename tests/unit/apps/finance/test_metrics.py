import pandas as pd
import pytest
from apps.finance.metrics import (
    longest_flat_period_duration,
    time_in_market_duration,
    _merge_intervals,
    avg_win,
    avg_loss,
    win_rate,
)

@pytest.fixture
def sample_trades():
    return pd.DataFrame({
        "open_time": pd.to_datetime([
            "2023-01-01 10:00",
            "2023-01-01 11:00",
            "2023-01-01 12:30",  # Overlaps with previous
            "2023-01-01 14:00"
        ]),
        "close_time": pd.to_datetime([
            "2023-01-01 10:30",
            "2023-01-01 13:00",
            "2023-01-01 13:30",
            "2023-01-01 14:30"
        ]),
        "profit_loss": [100.0, -50.0, 20.0, 10.0],
        "type": ["buy", "sell", "buy", "sell"],
        "size": [1.0, 1.0, 1.0, 1.0],
    })

def test_merge_intervals(sample_trades):
    # Expected intervals:
    # 1. 10:00 - 10:30 (30 min)
    # 2. 11:00 - 13:30 (150 min) - Merged 11:00-13:00 and 12:30-13:30
    # 3. 14:00 - 14:30 (30 min)
    
    intervals = _merge_intervals(sample_trades)
    assert len(intervals) == 3
    assert intervals[0] == (pd.Timestamp("2023-01-01 10:00"), pd.Timestamp("2023-01-01 10:30"))
    assert intervals[1] == (pd.Timestamp("2023-01-01 11:00"), pd.Timestamp("2023-01-01 13:30"))
    assert intervals[2] == (pd.Timestamp("2023-01-01 14:00"), pd.Timestamp("2023-01-01 14:30"))

def test_time_in_market_duration(sample_trades):
    # Total duration = 30 + 150 + 30 = 210 mins = 3h 30m
    duration = time_in_market_duration(sample_trades)
    assert duration == pd.Timedelta(minutes=210)

def test_longest_flat_period_duration(sample_trades):
    # Gaps:
    # Start -> 10:00 (0 if start time matches)
    # 10:30 -> 11:00 (30 min)
    # 13:30 -> 14:00 (30 min)
    # 14:30 -> End (0 if end time matches)
    
    # Let's specify start/end to create outer gaps
    start = pd.Timestamp("2023-01-01 09:00") # 1h gap at start
    end = pd.Timestamp("2023-01-01 16:00")   # 1.5h gap at end
    
    flat_duration = longest_flat_period_duration(sample_trades, start_time=start, end_time=end)
    
    # Start gap: 10:00 - 09:00 = 60 min
    # Gap 1: 11:00 - 10:30 = 30 min
    # Gap 2: 14:00 - 13:30 = 30 min
    # End gap: 16:00 - 14:30 = 90 min
    
    # Max gap should be 90 min
    assert flat_duration == pd.Timedelta(minutes=90)

def test_longest_flat_period_no_outer_bounds(sample_trades):
    # Without explicit start/end, should only look at internal gaps
    flat_duration = longest_flat_period_duration(sample_trades)
    # Gap 1: 30 min, Gap 2: 30 min
    assert flat_duration == pd.Timedelta(minutes=30)

def test_basic_metrics(sample_trades):
    assert win_rate(sample_trades) == 75.0 # 3 wins (100, 20, 10), 1 loss (-50) ? No, >1 is win
    # 100 > 1 (Win)
    # -50 < -1 (Loss)
    # 20 > 1 (Win)
    # 10 > 1 (Win)
    
    assert avg_win(sample_trades) == (100 + 20 + 10) / 3 # 43.333
    assert avg_loss(sample_trades) == -50.0
