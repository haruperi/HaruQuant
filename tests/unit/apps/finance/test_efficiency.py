
import pytest
import pandas as pd
import numpy as np
from apps.finance import efficiency

@pytest.fixture
def sample_trades():
    return pd.DataFrame({
        "profit_loss": [100.0, 200.0, -50.0],
        "size": [1.0, 2.0, 1.0],
        "mae_usd": [10.0, 20.0, 60.0],
        "mfe_usd": [120.0, 250.0, 10.0],
        "time_in_trade": [1.0, 2.0, 0.5],
        "initial_risk_usd": [50.0, 50.0, 50.0],
        "open_time": [
            pd.Timestamp("2023-01-01 10:00"),
            pd.Timestamp("2023-01-01 12:00"),
            pd.Timestamp("2023-01-02 10:00")
        ],
        "close_time": [
            pd.Timestamp("2023-01-01 11:00"),
            pd.Timestamp("2023-01-01 14:00"),
            pd.Timestamp("2023-01-02 10:30")
        ]
    })

def test_capital_efficiency(sample_trades):
    # Total PL: 250
    # Avg size: 1.333
    # Position value: 1.333 * 100000 = 133333.33
    # Eff: 250 / 133333.33 ~= 0.001875
    eff = efficiency.capital_efficiency(sample_trades)
    assert eff > 0.0
    
    assert efficiency.capital_efficiency(pd.DataFrame()) == 0.0

def test_return_per_unit_risk(sample_trades):
    # Total PL: 250
    # Total MAE: 90
    # Ratio: 250/90 = 2.777...
    assert pytest.approx(efficiency.return_per_unit_risk(sample_trades)) == 2.777777

def test_time_efficiency(sample_trades):
    # Total PL: 250
    # Total time: 3.5
    # Ratio: 250 / 3.5 = 71.428...
    assert pytest.approx(efficiency.time_efficiency(sample_trades)) == 71.428571

def test_return_per_trade(sample_trades):
    # Mean PL: 250 / 3 = 83.333
    assert pytest.approx(efficiency.return_per_trade(sample_trades)) == 83.333333

def test_return_per_unit_time(sample_trades):
    # First open: Jan 1 10:00
    # Last close: Jan 2 10:30
    # Diff: 24.5 hours
    # Ratio: 250 / 24.5 = 10.204...
    assert pytest.approx(efficiency.return_per_unit_time(sample_trades)) == 10.204081

    # Empty
    assert efficiency.return_per_unit_time(pd.DataFrame()) == 0.0

def test_mfe_efficiency(sample_trades):
    # Winners: 1 (100/120=0.833), 2 (200/250=0.8)
    # Mean: 0.81666...
    assert pytest.approx(efficiency.mfe_efficiency(sample_trades)) == 0.816666

def test_mae_efficiency(sample_trades):
    # Losers: 3 (-50, MAE 60) -> abs(-50)/60 = 0.8333
    assert pytest.approx(efficiency.mae_efficiency(sample_trades)) == 0.833333

def test_exit_efficiency(sample_trades):
    # MFE eff: 0.81666
    # MAE eff: 0.83333 -> inverted limits at 1.0 - 0.8333 = 0.1666
    # Avg: (0.81666 + 0.1666) / 2 = 0.4916...
    assert efficiency.exit_efficiency(sample_trades) > 0.0

def test_position_size_efficiency(sample_trades):
    # Size: 1, 2, 1
    # PL: 100, 200, -50
    # Corr should be high (positive)
    corr = efficiency.position_size_efficiency(sample_trades)
    assert corr > 0.0

def test_risk_adjusted_efficiency(sample_trades):
    # Total PL: 250
    # Total Risk: 150
    # Ratio: 1.666
    assert pytest.approx(efficiency.risk_adjusted_efficiency(sample_trades)) == 1.666666

def test_trades_per_day(sample_trades):
    # Days: 24.5 hours / 24 = 1.0208 days
    # Trades: 3
    # Ratio: 3 / 1.0208 = 2.93...
    tpd = efficiency.trades_per_day(sample_trades)
    assert tpd > 2.0
    assert tpd < 3.0

def test_return_per_trade_opportunity(sample_trades):
    # Total PL: 250
    # Days: 1.0208
    # Ratio: 250 / 1.0208 = 244.9...
    val = efficiency.return_per_trade_opportunity(sample_trades)
    assert val > 200.0

def test_win_efficiency(sample_trades):
    # Winners PL: 300
    # Winners MFE: 370
    # Ratio: (300/370)*100 = 81.08...
    assert pytest.approx(efficiency.win_efficiency(sample_trades)) == 81.081081

def test_loss_containment_efficiency(sample_trades):
    # Losers PL: -50 (abs 50)
    # Losers MAE: 60
    # Ratio: 50/60 = 0.8333
    # Containment: (1 - 0.8333) * 100 = 16.666...
    assert pytest.approx(efficiency.loss_containment_efficiency(sample_trades)) == 16.666666
