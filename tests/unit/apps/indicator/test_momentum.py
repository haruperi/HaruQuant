
import pytest
import pandas as pd
import numpy as np
from apps.indicator.momentum.rsi import rsi

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "close": [10, 11, 12, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 10, 11, 12, 13],
        "open":  [10] * 20 # Dummy
    })

def test_rsi_calculation(sample_data):
    period = 14
    result = rsi(sample_data, period)
    
    assert f"rsi_{period}" in result.columns
    # Check that values are within 0-100 range (except NaNs)
    rsi_vals = result[f"rsi_{period}"].dropna()
    assert ((rsi_vals >= 0) & (rsi_vals <= 100)).all()
    
    # First (period-1) should be 50.0 (fillna) or NaN depending on implementation
    # Implementation says: rsi_values = rsi_values.fillna(50.0)
    # So initial values should be 50.0
    assert result[f"rsi_{period}"].iloc[0] == 50.0

def test_rsi_invalid_period(sample_data):
    with pytest.raises(ValueError, match="Period must be positive"):
        rsi(sample_data, 0)

def test_rsi_missing_column(sample_data):
    with pytest.raises(ValueError, match="Price column 'volume' is required"):
        rsi(sample_data, 14, price_col="volume")

def test_rsi_all_gains(sample_data):
    # If price always goes up, RSI should approach 100
    up_data = pd.DataFrame({"close": range(100)})
    result = rsi(up_data, 14)
    # The last value should be very high, close to 100
    assert result["rsi_14"].iloc[-1] > 90

def test_rsi_all_losses(sample_data):
    # If price always goes down, RSI should approach 0
    down_data = pd.DataFrame({"close": range(100, 0, -1)})
    result = rsi(down_data, 14)
    # The last value should be very low, close to 0
    assert result["rsi_14"].iloc[-1] < 10
