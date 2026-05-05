"""Public utility API.

Thin facade over `services.utils`; implementation remains in services.
"""

from __future__ import annotations

from . import ServiceNamespace, load_service_module, resolve_service_attr, service_modules


_SERVICE_MODULES = service_modules("services.utils")
logger_module = load_service_module("services.utils.logger")


class Utils(ServiceNamespace):
    _service_module = "services.utils"
    _service_modules = _SERVICE_MODULES


def __getattr__(name: str):
    return resolve_service_attr(name, _SERVICE_MODULES)


__all__ = ["Utils"]


# VectorBT-style common utilities.
from typing import Union, Dict, List, Any, Optional
import pandas as pd
import numpy as np

class Param:
    """
    Helper class to wrap parameter values for optimization.
    Mimics vbt.Param.
    """
    def __init__(self, values: Any, name: Optional[str] = None, level: Optional[int] = None):
        if isinstance(values, np.ndarray):
            self.values = values.tolist()
        elif not isinstance(values, (list, tuple)):
            self.values = [values]
        else:
            self.values = list(values)
        self.name = name
        self.level = level

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)

    def __repr__(self):
        return f"Param(values={self.values}, name={self.name}, level={self.level})"

def combine_params(params_dict: Dict[str, Any], random_subset: Optional[int] = None, build_index: bool = False) -> List[Dict[str, Any]]:
    """
    Combine multiple parameters into a list of parameter sets.
    Supports grouping by 'level' (parameters with same level are zipped).
    Mimics vbt.combine_params.
    
    Args:
        params_dict: Dict mapping param names to values or Param objects.
        random_subset: Optional number of random combinations to return.
        build_index: (Currently ignored) Whether to return a MultiIndex.
    """
    from itertools import product
    import random

    # 1. Standardize everything to lists and collect levels
    levels = {} # level -> {name: [values]}
    default_level_counter = 1000 # For params without level
    
    for name, p in params_dict.items():
        if isinstance(p, Param):
            lvl = p.level if p.level is not None else default_level_counter
            if p.level is None: default_level_counter += 1
            vals = p.values
        else:
            lvl = default_level_counter
            default_level_counter += 1
            vals = p if isinstance(p, (list, tuple)) else [p]
            
        if lvl not in levels:
            levels[lvl] = {}
        levels[lvl][name] = vals

    # 2. For each level, zip the parameters (must have same length)
    level_combinations = [] # List of list of dicts
    for lvl in sorted(levels.keys()):
        group = levels[lvl]
        # Check lengths
        lengths = {name: len(vals) for name, vals in group.items()}
        max_len = max(lengths.values())
        
        for name, length in lengths.items():
            if length != max_len and length != 1:
                raise ValueError(f"Parameters in level {lvl} must have same length or length 1. Error in {name}.")
        
        # Zip them
        group_combos = []
        for i in range(max_len):
            combo = {}
            for name, vals in group.items():
                combo[name] = vals[i] if len(vals) > 1 else vals[0]
            group_combos.append(combo)
        level_combinations.append(group_combos)

    # 3. Cartesian product across levels
    final_combos = []
    for product_tuple in product(*level_combinations):
        # Merge dicts in product_tuple
        merged = {}
        for d in product_tuple:
            merged.update(d)
        final_combos.append(merged)

    # 4. Apply random subset
    if random_subset and random_subset < len(final_combos):
        final_combos = random.sample(final_combos, random_subset)
        
    return final_combos
from .data import Data
from services.utils.datasets import OHLCVSchema, resample_ohlc as _resample_ohlc

# Schema for HaruQuant Data objects which use lowercase column names
HQT_SCHEMA = OHLCVSchema(
    open="open",
    high="high",
    low="low",
    close="close",
    volume="volume"
)

def symbol_dict(mapping: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper to create a dictionary mapping symbols to metadata.
    Mimics vbt.symbol_dict.
    """
    return mapping

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
    
    # Use the centralized implementation from services.utils
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


# VectorBT-style performance utilities.
import numpy as np
import pandas as pd
from typing import Union, Optional, Dict, Any, Callable
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

@pd.api.extensions.register_dataframe_accessor("hqt")
class HQTAccessor:
    def __init__(self, pandas_obj):
        self._obj = pandas_obj
        
    def rolling_mean(self, window, jitted=None):
        return rolling_mean(self._obj, window, jitted=jitted)

@pd.api.extensions.register_series_accessor("hqt")
class HQTSeriesAccessor:
    def __init__(self, pandas_obj):
        self._obj = pandas_obj
        
    def rolling_mean(self, window, jitted=None):
        return rolling_mean(self._obj, window, jitted=jitted)
try:
    from numba import njit, prange
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    # Mock njit for environments without numba
    def njit(*args, **kwargs):
        def wrapper(f):
            return f
        return wrapper
    prange = range

@njit
def _rolling_mean_nb(arr: np.ndarray, window: int):
    n, m = arr.shape
    out = np.empty((n, m))
    out[:] = np.nan
    for j in range(m):
        for i in range(window - 1, n):
            val = 0.0
            for k in range(window):
                val += arr[i - k, j]
            out[i, j] = val / window
    return out

@njit(parallel=True)
def _rolling_mean_parallel_nb(arr: np.ndarray, window: int):
    n, m = arr.shape
    out = np.empty((n, m))
    out[:] = np.nan
    for j in prange(m):
        for i in range(window - 1, n):
            val = 0.0
            for k in range(window):
                val += arr[i - k, j]
            out[i, j] = val / window
    return out

def rolling_mean(
    data: Union[pd.DataFrame, pd.Series, np.ndarray], 
    window: int, 
    jitted: Optional[Dict[str, Any]] = None
) -> Union[pd.DataFrame, pd.Series, np.ndarray]:
    """
    High-performance rolling mean using Numba.
    
    Args:
        data: Input data.
        window: Rolling window size.
        jitted: Dictionary of Numba options (e.g., {'parallel': True}).
    """
    if isinstance(data, (pd.DataFrame, pd.Series)):
        arr = data.values
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
            is_series = True
        else:
            is_series = False
    else:
        arr = data
        is_series = False

    parallel = jitted.get('parallel', False) if jitted else False
    
    if HAS_NUMBA:
        if parallel:
            res = _rolling_mean_parallel_nb(arr, window)
        else:
            res = _rolling_mean_nb(arr, window)
    else:
        # Fallback to pandas if numba is missing
        return pd.DataFrame(arr).rolling(window).mean().values

    if isinstance(data, pd.DataFrame):
        return pd.DataFrame(res, index=data.index, columns=data.columns)
    elif isinstance(data, pd.Series):
        return pd.Series(res.flatten(), index=data.index, name=data.name)
    
    return res

def _chunk_worker(func, chunk, args, kwargs):
    """Helper for multiprocessing to avoid lambda pickling issues."""
    return func(chunk, *args, **kwargs)

def chunked(
    size: Optional[int] = 1,
    axis: int = 1,
    engine: str = "sequential",
    merge_func: Callable = np.column_stack
):
    """
    Decorator to run a function on chunks of data.
    Allows for easy parallelization of column-wise operations.
    
    Args:
        size: Number of elements (columns/rows) per chunk.
        axis: Axis to split along (0 for rows, 1 for columns).
        engine: Default engine ('sequential', 'threadpool', 'processpool').
        merge_func: Function to merge results back together.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract execution overrides
            exec_kwargs = kwargs.pop("_execute_kwargs", {})
            _engine = exec_kwargs.get("engine", engine)
            
            # The first argument is typically the data to be chunked
            if not args:
                return func(*args, **kwargs)
            
            data = args[0]
            other_args = args[1:]

            if isinstance(data, np.ndarray):
                n_chunks = max(1, data.shape[axis] // size) if size else 1
                chunks = np.array_split(data, n_chunks, axis=axis)
            elif isinstance(data, (pd.DataFrame, pd.Series)):
                arr = data.values
                n_chunks = max(1, arr.shape[axis] // size) if size else 1
                chunks = np.array_split(arr, n_chunks, axis=axis)
            else:
                chunks = [data]

            if _engine == "sequential":
                results = [func(c, *other_args, **kwargs) for c in chunks]
            elif _engine == "threadpool":
                with ThreadPoolExecutor() as executor:
                    from functools import partial
                    worker = partial(_chunk_worker, func, args=other_args, kwargs=kwargs)
                    results = list(executor.map(worker, chunks))
            elif _engine == "processpool":
                with ProcessPoolExecutor() as executor:
                    from functools import partial
                    worker = partial(_chunk_worker, func, args=other_args, kwargs=kwargs)
                    results = list(executor.map(worker, chunks))
            else:
                raise ValueError(f"Unknown engine: {_engine}")

            if not results:
                return None
            
            return merge_func(results) if len(results) > 1 else results[0]
        return wrapper
    return decorator
