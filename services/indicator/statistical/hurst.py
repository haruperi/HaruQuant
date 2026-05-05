"""Hurst Exponent indicator."""

import numpy as np
import pandas as pd
from services.utils.logger import logger
from services.indicator.validation import (
    require_columns,
    require_dataframe,
    require_positive_int,
)

def calculate_hurst(series: np.ndarray) -> float:
    """
    Calculate the Hurst exponent of a time series using Rescaled Range (R/S) method.
    
    Hurst Exponent (H) interprets the long-term memory of time series:
    - H < 0.5: Mean-reverting (anti-persistent)
    - H = 0.5: Random walk (Brownian motion)
    - H > 0.5: Trending (persistent)
    """
    if len(series) < 50:
        return np.nan
        
    # We work on log returns to ensure stationarity of increments
    series = np.diff(np.log(series))
    N = len(series)
    
    lags = np.unique(np.floor(np.geomspace(10, N // 2, num=8)).astype(int))
    
    rescaled_ranges = []
    for lag in lags:
        # Rescaled range for this lag
        rs_list = []
        for i in range(0, N - lag + 1, lag):
            chunk = series[i : i + lag]
            if len(chunk) < lag: break
            
            # Mean centering
            mean_adj = chunk - np.mean(chunk)
            # Cumulative deviation
            cum_dev = np.cumsum(mean_adj)
            # Range
            r = np.max(cum_dev) - np.min(cum_dev)
            # Standard deviation
            s = np.std(chunk)
            if s > 1e-12:
                rs_list.append(r / s)
        
        if rs_list:
            rescaled_ranges.append(np.mean(rs_list))
        else:
            lags = lags[lags != lag] # remove if no data
            
    if len(rescaled_ranges) < 2:
        return np.nan
        
    # Fit log(lags) vs log(rescaled_ranges)
    poly = np.polyfit(np.log(lags[:len(rescaled_ranges)]), np.log(rescaled_ranges), 1)
    return poly[0]

def hurst(
    data: pd.DataFrame,
    period: int = 100,
    price_col: str = "close",
) -> pd.DataFrame:
    """Compute the Rolling Hurst Exponent.

    The Hurst exponent provides a measure of the "memory" of a time series.
    Values near 0.5 indicate a random walk, while values moving towards 1.0 
    indicate a trending series and values towards 0 indicate mean-reversion.

    Calculation steps:
        1. Extract the price series.
        2. Apply a rolling window of the specified period.
        3. For each window, calculate the R/S range and fit the Hurst exponent.

    Args:
        data: DataFrame containing the necessary market data.
        period: Window size for calculation (default: 100).
        price_col: Column to use for calculation (default: "close").

    Returns:
        DataFrame with the new Hurst column appended.
        Example column name: `hurst_{period}`

    Raises:
        ValueError: If parameters are invalid or required columns are missing.
        TypeError: If input types are incorrect.
    """
    require_dataframe(data)
    require_positive_int(period, name="period")
    require_columns(data, (price_col,))

    logger.debug(f"Calculating Hurst Exponent with period={period} on column '{price_col}'")
    
    # Rolling apply (this can be slow, but it's the standard way for custom rolling functions)
    def _rolling_hurst(x):
        return calculate_hurst(x.values)
        
    result = data.copy()
    col_name = f"hurst_{period}"
    result[col_name] = data[price_col].rolling(window=period).apply(_rolling_hurst, raw=False)
    
    logger.success(f"Hurst calculation complete: {col_name}")
    return result
