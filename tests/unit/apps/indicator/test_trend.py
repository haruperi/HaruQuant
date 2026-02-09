import pytest
import pandas as pd
import numpy as np
from apps.indicator.trend.sma import sma
from apps.indicator.trend.ema import ema
from apps.indicator.trend.wma import wma

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "close": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        "open": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        "high": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        "low": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    })

def test_sma_calculation(sample_data):
    window = 5
    result = sma(sample_data, window)
    
    assert f"sma_{window}" in result.columns
    # First 4 should be NaN
    assert pd.isna(result[f"sma_{window}"].iloc[3])
    # 5th element (index 4) should be average of 0..4 (10..14) -> 12
    assert result[f"sma_{window}"].iloc[4] == 12.0
    # 6th element (index 5) -> 11..15 -> 13
    assert result[f"sma_{window}"].iloc[5] == 13.0

def test_sma_invalid_window(sample_data):
    with pytest.raises(ValueError, match="Window must be positive"):
        sma(sample_data, 0)

def test_sma_missing_column(sample_data):
    # 'volume' is not in sample_data
    with pytest.raises(ValueError, match="Price column 'volume' is required"):
        sma(sample_data, 5, price_col="volume")

def test_ema_calculation(sample_data):
    span = 2
    result = ema(sample_data, span)
    
    assert f"ema_{span}" in result.columns
    # With min_periods=span(2), index 0 is NaN
    assert pd.isna(result[f"ema_{span}"].iloc[0])
    # Index 1 has value
    assert not pd.isna(result[f"ema_{span}"].iloc[1])

def test_ema_consistency(sample_data):
    # EMA with span 1 should be equal to the data itself approx
    result = ema(sample_data, 1)
    # Compare values directly to avoid attribute mismatch issues
    np.testing.assert_allclose(
        result["ema_1"].values, 
        sample_data["close"].values
    )
    # Compare index
    pd.testing.assert_index_equal(
        result["ema_1"].index, 
        sample_data["close"].index
    )

def test_ema_invalid_span(sample_data):
    with pytest.raises(ValueError, match="Span must be positive"):
        ema(sample_data, -1)

def test_ema_missing_column(sample_data):
    with pytest.raises(ValueError, match="Price column 'volume' is required"):
        ema(sample_data, 5, price_col="volume")

def test_wma_calculation(sample_data):
    window = 3
    result = wma(sample_data, window)
    
    assert f"wma_{window}" in result.columns
    # Weights for window 3: 1, 2, 3. Sum = 6
    # Data: [10, 11, 12, 13, ...]
    # index 2: values 10, 11, 12.
    # WMA = (10*1 + 11*2 + 12*3) / 6 = (10 + 22 + 36) / 6 = 68 / 6 = 11.3333...
    
    expected_val = (10*1 + 11*2 + 12*3) / 6
    assert np.isclose(result[f"wma_{window}"].iloc[2], expected_val)

def test_wma_invalid_window(sample_data):
    with pytest.raises(ValueError, match="Window must be positive"):
        wma(sample_data, 0)

def test_wma_missing_column(sample_data):
    with pytest.raises(ValueError, match="Price column 'volume' is required"):
        wma(sample_data, 3, price_col="volume")
