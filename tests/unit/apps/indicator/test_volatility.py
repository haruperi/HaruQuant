
import pytest
import pandas as pd
import numpy as np
from apps.indicator.volatility.atr import atr
from apps.indicator.volatility.bbands import bbands

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "close": [10, 11, 12, 13, 14, 15, 14, 13, 12, 11] * 2,
        "high":  [11, 12, 13, 14, 15, 16, 15, 14, 13, 12] * 2,
        "low":   [9, 10, 11, 12, 13, 14, 13, 12, 11, 10] * 2,
        "open":  [10] * 20
    })

# --- ATR Tests ---

def test_atr_calculation(sample_data):
    period = 14
    result = atr(sample_data, period)
    
    assert f"atr_{period}" in result.columns
    # Check for non-negative values
    atr_vals = result[f"atr_{period}"].dropna()
    assert (atr_vals >= 0).all()

def test_atr_invalid_period(sample_data):
    with pytest.raises(ValueError, match="Period must be positive"):
        atr(sample_data, 0)

def test_atr_missing_columns(sample_data):
    # Drop 'high'
    incomplete_data = sample_data.drop(columns=["high"])
    with pytest.raises(ValueError, match="Missing required columns"):
        atr(incomplete_data, 14)

# --- Bollinger Bands Tests ---

def test_bbands_calculation(sample_data):
    period = 10
    std_dev = 2.0
    result = bbands(sample_data, period, std_dev)
    
    suffix = f"{period}_{int(std_dev)}"
    assert f"bb_upper_{suffix}" in result.columns
    assert f"bb_middle_{suffix}" in result.columns
    assert f"bb_lower_{suffix}" in result.columns
    
    # Check band ordering: Upper >= Middle >= Lower
    # (ignoring NaNs at start)
    valid_mask = result[f"bb_middle_{suffix}"].notna()
    
    assert (result.loc[valid_mask, f"bb_upper_{suffix}"] >= result.loc[valid_mask, f"bb_middle_{suffix}"]).all()
    assert (result.loc[valid_mask, f"bb_middle_{suffix}"] >= result.loc[valid_mask, f"bb_lower_{suffix}"]).all()

def test_bbands_invalid_period(sample_data):
    with pytest.raises(ValueError, match="Period must be positive"):
        bbands(sample_data, 0)

def test_bbands_missing_column(sample_data):
    with pytest.raises(ValueError, match="Price column 'volume' is required"):
        bbands(sample_data, 20, price_col="volume")

def test_bbands_fractional_std(sample_data):
    # Test with fractional std_dev to ensure column naming is handled
    # Although code uses int casting if it's integer, let's see for 1.5
    result = bbands(sample_data, 10, 1.5)
    assert "bb_upper_10_1.5" in result.columns
