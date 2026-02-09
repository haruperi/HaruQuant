
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from apps.finance.metrics import (
    total_trades, winning_trades, losing_trades, breakeven_trades,
    long_trades, short_trades, win_rate, loss_rate,
    avg_win, avg_loss,
    max_consecutive_wins, max_consecutive_losses,
    sqn, trade_efficiency,
    trading_period_duration, time_in_market_duration, percent_time_in_market
)

@pytest.fixture
def sample_trades():
    return pd.DataFrame({
        "profit_loss": [100.0, -50.0, 200.0, -20.0, 0.5, 150.0],
        "type": ["buy", "sell", "buy", "sell", "buy", "buy"],
        "exit_reason": ["TP", "SL", "TP", "SL", "TIME", "TP"],
        "slippage": [0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        "commission": [2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
        "swap": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        "size": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        "r_multiple": [2.0, -1.0, 4.0, -0.5, 0.1, 3.0],
        "mfe_pips": [20, 5, 40, 2, 1, 30],
        "mae_pips": [5, 10, 10, 4, 1, 5],
        "time_in_trade": [1.0, 0.5, 2.0, 0.2, 0.1, 1.5],
        "open_time": [
            pd.Timestamp("2023-01-01 10:00"),
            pd.Timestamp("2023-01-01 11:00"),
            pd.Timestamp("2023-01-01 12:00"),
            pd.Timestamp("2023-01-01 13:00"),
            pd.Timestamp("2023-01-01 14:00"),
            pd.Timestamp("2023-01-01 15:00")
        ],
        "close_time": [
            pd.Timestamp("2023-01-01 11:00"),
            pd.Timestamp("2023-01-01 11:30"),
            pd.Timestamp("2023-01-01 14:00"),
            pd.Timestamp("2023-01-01 13:12"),
            pd.Timestamp("2023-01-01 14:06"),
            pd.Timestamp("2023-01-01 16:30")
        ]
    })

def test_trade_counts(sample_trades):
    # Total: 6
    assert total_trades(sample_trades) == 6
    # Winners (>1): 100, 200, 150 -> 3
    assert winning_trades(sample_trades) == 3
    # Losers (<-1): -50, -20 -> 2
    assert losing_trades(sample_trades) == 2
    # Breakeven (>= -1 and <= 1): 0.5 -> 1
    assert breakeven_trades(sample_trades) == 1
    
    assert long_trades(sample_trades) == 4
    assert short_trades(sample_trades) == 2

def test_win_loss_rates(sample_trades):
    # 3/6 = 50%
    assert win_rate(sample_trades) == 50.0
    # 2/6 = 33.33...%
    assert abs(loss_rate(sample_trades) - 33.333) < 0.01

def test_averages(sample_trades):
    # Winners: 100, 200, 150 -> mean 150
    assert avg_win(sample_trades) == 150.0
    # Losers: -50, -20 -> mean -35
    assert avg_loss(sample_trades) == -35.0

def test_streaks(sample_trades):
    # PnL: 100(W), -50(L), 200(W), -20(L), 0.5(BE/L?), 150(W)
    # logic in metrics.py use >1 for win, <-1 for loss.
    # 100 (W), -50 (L), 200 (W), -20 (L), 0.5 (Not W, Not L), 150 (W)
    # Consecutive wins: W, L, W, L, N, W -> max 1
    # Let's verify logic for neutral trades interrupting streaks
    
    # Create explicit streak data
    streak_df = pd.DataFrame({
        "profit_loss": [10.0, 10.0, -10.0, 10.0, -10.0, -10.0, -10.0, 10.0]
    })
    # W, W, L, W, L, L, L, W
    # Max W: 2
    # Max L: 3
    assert max_consecutive_wins(streak_df) == 2
    assert max_consecutive_losses(streak_df) == 3

def test_sqn(sample_trades):
    # R: 2, -1, 4, -0.5, 0.1, 3
    # Mean: 1.266
    # Std: 2.05
    # N: 6
    # SQN = sqrt(6) * (1.266 / 2.05) ~= 2.449 * 0.617 ~= 1.51
    s = sqn(sample_trades)
    assert s > 1.0
    assert s < 2.0

def test_trade_efficiency(sample_trades):
    # eff = mfe / mae
    # 20/5=4, 5/10=0.5, 40/10=4, 2/4=0.5, 1/1=1, 30/5=6
    # mean: (4+0.5+4+0.5+1+6)/6 = 16/6 = 2.66...
    eff = trade_efficiency(sample_trades)
    assert abs(eff - 2.666) < 0.01

def test_time_metrics(sample_trades):
    # Period: 10:00 to 16:30 -> 6.5 hours
    period = trading_period_duration(sample_trades)
    assert period.total_seconds() == 6.5 * 3600
    
    # Time in market:
    # 1. 10:00-11:00
    # 2. 11:00-11:30 (overlaps/adj) -> 10:00-11:30
    # 3. 12:00-14:00
    # 4. 13:00-13:12 (inside 3)
    # 5. 14:00-14:06 (overlaps/adj to 3) -> 12:00-14:06
    # 6. 15:00-16:30
    # Total: 1.5h + 2.1h + 1.5h = 5.1h
    
    # merge logic verification
    market_time = time_in_market_duration(sample_trades)
    # 10:00-11:30 (1.5h) + 12:00-14:06 (2.1h) + 15:00-16:30 (1.5h) = 5.1h
    expected_seconds = (1.5 + 2.1 + 1.5) * 3600
    # Allow small float error
    assert abs(market_time.total_seconds() - expected_seconds) < 60 # within 1 min
    
    pct = percent_time_in_market(sample_trades)
    # 5.1 / 6.5 * 100 ~= 78.46%
    assert pct > 70
    assert pct < 80
