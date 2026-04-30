import numpy as np
import pandas as pd
from typing import Optional, Union

def calculate_hurst(series: np.ndarray) -> float:
    """
    Calculate the Hurst exponent of a time series using Rescaled Range (R/S) method.
    """
    if len(series) < 50:
        return np.nan
        
    # We work on log returns to ensure stationarity of increments
    # This is standard for price series
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
    df: pd.DataFrame,
    period: int = 100,
    column: str = "close",
) -> pd.DataFrame:
    """
    Rolling Hurst Exponent.
    
    Args:
        df: Input DataFrame
        period: Window size for calculation
        column: Column to use (default: "close")
    """
    res = df.copy()
    col_name = f"hurst_{period}"
    
    # Rolling apply (this can be slow, but it's the standard way for custom rolling functions)
    # We use a helper function to avoid creating overhead
    def _rolling_hurst(x):
        return calculate_hurst(x.values)
        
    res[col_name] = df[column].rolling(window=period).apply(_rolling_hurst, raw=False)
    
    return res
