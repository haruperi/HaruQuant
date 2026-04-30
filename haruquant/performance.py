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
