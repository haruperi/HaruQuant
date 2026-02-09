
import pytest
import pandas as pd
import numpy as np
from apps.indicator.volume.accumulation_distribution import accumulation_distribution

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "close":  [10, 11, 12, 11, 10],
        "high":   [11, 12, 13, 12, 11],
        "low":    [9, 10, 11, 10, 9],
        "volume": [100, 200, 300, 200, 100],
        "open":   [10, 10, 10, 10, 10]
    })

def test_adl_calculation(sample_data):
    result = accumulation_distribution(sample_data)
    
    assert "adl" in result.columns
    # Check that ADL is calculated and accumulated
    assert not result["adl"].isna().any()
    # It calculates cumulative sum, so check values roughly
    # Row 0: high 11, low 9, close 10. (10-9) - (11-10) = 1 - 1 = 0. Multiplier 0. ADL = 0
    # Row 1: high 12, low 10, close 11. (11-10) - (12-11) = 1 - 1 = 0. Multiplier 0. ADL = 0
    # Let's change data to have non-zero multiplier
    
    data2 = pd.DataFrame({
        "close": [10],
        "high": [10],
        "low": [0],
        "volume": [100]
    })
    # Multiplier: ((10-0) - (10-10)) / (10-0) = (10 - 0) / 10 = 1.
    # Flow Volume = 1 * 100 = 100. ADL = 100.
    res2 = accumulation_distribution(data2)
    assert res2["adl"].iloc[0] == 100.0

def test_adl_missing_columns(sample_data):
    incomplete = sample_data.drop(columns=["volume"])
    with pytest.raises(ValueError, match="Missing required columns"):
        accumulation_distribution(incomplete)

def test_adl_zero_range(sample_data):
    # If high == low, division by zero protection needed
    flat_data = pd.DataFrame({
        "close": [10, 10],
        "high": [10, 10],
        "low": [10, 10],
        "volume": [100, 100]
    })
    # Multiplier should be filled with 0
    result = accumulation_distribution(flat_data)
    assert result["adl"].iloc[0] == 0.0
