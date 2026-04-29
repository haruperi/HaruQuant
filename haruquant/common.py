import pandas as pd
from typing import Union
from .data import Data
from backend.common.datasets import resample_ohlc as _resample_ohlc, OHLCVSchema

# Schema for HaruQuant Data objects which use lowercase column names
HQT_SCHEMA = OHLCVSchema(
    open="open",
    high="high",
    low="low",
    close="close",
    volume="volume"
)

def resample(data: Union[Data, pd.DataFrame], rule: str) -> Data:
    """
    Resample OHLCV data to a different timeframe.
    Supports MT5-style strings (e.g., 'H1', 'M5') and standard pandas rules (e.g., '1h', '5min').
    
    Args:
        data: Source Data object or DataFrame
        rule: Resample rule (e.g., 'H1', 'M5', '1h', '4h', '1d')
    """
    df = data.df if isinstance(data, Data) else data
    
    # Map MT5-style timeframes to Pandas-style
    rule_upper = rule.upper()
    if rule_upper.startswith('H') and rule_upper[1:].isdigit():
        rule = f"{rule_upper[1:]}h"
    elif rule_upper.startswith('M') and rule_upper[1:].isdigit():
        rule = f"{rule_upper[1:]}min"
    elif rule_upper.startswith('D') and (len(rule_upper) == 1 or rule_upper[1:].isdigit()):
        num = rule_upper[1:] or "1"
        rule = f"{num}d"
    else:
        rule = rule.lower()
    
    # Use the centralized implementation from backend.common
    # We pass the HQT_SCHEMA to ensure it looks for 'open', 'high', etc.
    resampled_df = _resample_ohlc(df, rule, schema=HQT_SCHEMA)
    
    symbol = data._symbol if isinstance(data, Data) else None
    return Data(resampled_df, symbol=symbol, timeframe=rule)

def merge(
    lower_data: Union[Data, pd.DataFrame], 
    higher_data: Union[Data, pd.DataFrame], 
    suffix: str = "_H"
) -> Data:
    """
    Merge a higher timeframe dataset into a lower timeframe dataset.
    Commonly used for multi-timeframe analysis.
    
    Args:
        lower_data: The base data (lower timeframe, e.g., M5)
        higher_data: The data to merge in (higher timeframe, e.g., H1)
        suffix: Suffix to add to the higher timeframe columns
    """
    ldf = lower_data.df if isinstance(lower_data, Data) else lower_data
    hdf = higher_data.df if isinstance(higher_data, Data) else higher_data
    
    # Add suffix to higher timeframe columns to avoid collisions
    hdf_renamed = hdf.add_suffix(suffix)
    
    # Join and forward fill
    merged_df = ldf.join(hdf_renamed, how='left').ffill()
    
    symbol = lower_data._symbol if isinstance(lower_data, Data) else None
    timeframe = lower_data._timeframe if isinstance(lower_data, Data) else None
    
    return Data(merged_df, symbol=symbol, timeframe=timeframe)

def concat(
    data_list: List[Union[Data, pd.DataFrame, pd.Series]], 
    keys: Optional[List[str]] = None,
    axis: int = 1
) -> Data:
    """
    Concatenate multiple datasets (usually different symbols) into a single Data object.
    
    Args:
        data_list: List of Data objects, DataFrames, or Series to combine.
        keys: Optional list of labels (e.g., symbols) for the new MultiIndex levels.
        axis: Axis to concatenate along (default is 1 for columns).
    """
    dfs = []
    for item in data_list:
        if isinstance(item, Data):
            dfs.append(item.df)
        else:
            dfs.append(item)
            
    combined_df = pd.concat(dfs, axis=axis, keys=keys)
    
    # Use the first item's timeframe if it's a Data object
    timeframe = None
    for item in data_list:
        if isinstance(item, Data) and item._timeframe:
            timeframe = item._timeframe
            break
            
    return Data(combined_df, symbol=str(keys) if keys else None, timeframe=timeframe)
