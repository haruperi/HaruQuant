"""Performance optimization utilities for plotting.

This module provides performance optimization features for large dataset visualization:
- LTTB (Largest-Triangle-Three-Buckets) downsampling algorithm
- Caching for computed metrics and transformations
- Lazy evaluation for plot generation
- Memory-efficient data handling

The optimizations maintain visual fidelity while significantly improving
rendering performance for large datasets (>10,000 points).
"""

from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd

from apps.logger import logger

# =============================================================================
# CONSTANTS
# =============================================================================

# Threshold for automatic downsampling
DOWNSAMPLE_THRESHOLD = 10000

# Default target points after downsampling
DEFAULT_TARGET_POINTS = 5000

# Cache size for computed metrics
CACHE_SIZE = 128


# =============================================================================
# LTTB DOWNSAMPLING
# =============================================================================


def downsample_lttb(  # pylint: disable=invalid-name
    data: Union[pd.Series, pd.DataFrame, np.ndarray],
    threshold: int = DEFAULT_TARGET_POINTS,
    x: Optional[np.ndarray] = None,
) -> Union[pd.Series, pd.DataFrame, Tuple[np.ndarray, np.ndarray]]:
    """Downsample data using Largest-Triangle-Three-Buckets algorithm.

    LTTB preserves visual appearance by selecting points that form the largest
    triangles, maintaining peaks, troughs, and overall shape while reducing
    data density.

    Args:
        data: Data to downsample (Series, DataFrame, or array)
        threshold: Target number of points after downsampling
        x: Optional x-axis values (if data is array)

    Returns:
        Downsampled data in same format as input

    Examples:
        >>> # Downsample a pandas Series
        >>> series = pd.Series(range(100000))
        >>> downsampled = downsample_lttb(series, threshold=5000)
        >>> len(downsampled)
        5000

        >>> # Downsample numpy array with x-values
        >>> y = np.random.randn(100000)
        >>> x = np.arange(100000)
        >>> x_down, y_down = downsample_lttb(y, threshold=5000, x=x)

    Reference:
        Sveinn Steinarsson (2013). Downsampling Time Series for Visual Representation.
        https://skemman.is/bitstream/1946/15343/3/SS_MSthesis.pdf
    """
    logger.trace("Starting LTTB downsampling")

    # Handle different input types
    if isinstance(data, pd.Series):
        logger.debug(f"Downsampling Series: {len(data)} -> {threshold} points")
        values = data.values
        index = data.index
        result = _lttb_core(values, threshold)
        return pd.Series(result["y"], index=index[result["indices"]], name=data.name)

    if isinstance(data, pd.DataFrame):
        logger.debug(f"Downsampling DataFrame: {len(data)} -> {threshold} points")
        # For DataFrames, downsample based on first column and apply to all
        first_col = data.iloc[:, 0].values
        result = _lttb_core(first_col, threshold)
        return data.iloc[result["indices"]].copy()

    # numpy array
    logger.debug(f"Downsampling array: {len(data)} -> {threshold} points")
    if x is None:
        x = np.arange(len(data))
    result = _lttb_core(data, threshold, x=x)
    return result["x"], result["y"]


def _lttb_core(  # pylint: disable=invalid-name,too-many-locals
    y: Union[np.ndarray, Any],
    threshold: int,
    x: Optional[Union[np.ndarray, Any]] = None,
) -> Dict[str, np.ndarray]:
    """Core LTTB algorithm implementation.

    Args:
        y: Y-axis values (array-like)
        threshold: Target number of points
        x: Optional x-axis values (array-like)

    Returns:
        Dictionary with 'x', 'y', and 'indices' arrays
    """
    # Ensure inputs are numpy arrays
    y = np.asarray(y)
    if x is not None:
        x = np.asarray(x)

    n = len(y)

    # If data is smaller than threshold, return as-is
    if n <= threshold or threshold < 3:
        if x is None:
            x = np.arange(n)
        return {"x": x, "y": y, "indices": np.arange(n)}

    if x is None:
        x = np.arange(n)

    # Always include first and last points
    sampled_x = [x[0]]
    sampled_y = [y[0]]
    sampled_indices = [0]

    # Bucket size
    bucket_size = (n - 2) / (threshold - 2)

    # Initialize
    a = 0  # Initially, a is the first point

    for i in range(threshold - 2):
        # Calculate bucket range
        avg_range_start = int((i + 1) * bucket_size) + 1
        avg_range_end = int((i + 2) * bucket_size) + 1

        # Avoid going past array bounds
        avg_range_end = min(avg_range_end, n)

        # Calculate average point in next bucket
        avg_range_length = avg_range_end - avg_range_start
        if avg_range_length > 0:
            avg_x = float(np.mean(x[avg_range_start:avg_range_end]))
            avg_y = float(np.mean(y[avg_range_start:avg_range_end]))
        else:
            avg_x = float(x[avg_range_start])
            avg_y = float(y[avg_range_start])

        # Get the range for this bucket
        range_start = int(i * bucket_size) + 1
        range_end = int((i + 1) * bucket_size) + 1
        range_end = min(range_end, n - 1)

        # Point a (previous selected point)
        point_a_x = x[a]
        point_a_y = y[a]

        # Find point with largest triangle area in current bucket
        max_area = -1
        max_area_point = range_start

        for j in range(range_start, range_end):
            # Calculate triangle area
            area = abs(
                (point_a_x - avg_x) * (y[j] - point_a_y)
                - (point_a_x - x[j]) * (avg_y - point_a_y)
            )

            if area > max_area:
                max_area = area
                max_area_point = j

        # Add the selected point
        sampled_x.append(x[max_area_point])
        sampled_y.append(y[max_area_point])
        sampled_indices.append(max_area_point)
        a = max_area_point

    # Always include last point
    sampled_x.append(x[-1])
    sampled_y.append(y[-1])
    sampled_indices.append(n - 1)

    return {
        "x": np.array(sampled_x),
        "y": np.array(sampled_y),
        "indices": np.array(sampled_indices),
    }


def should_downsample(data: Union[pd.Series, pd.DataFrame, np.ndarray]) -> bool:
    """Check if data should be downsampled based on size.

    Args:
        data: Data to check

    Returns:
        True if data exceeds downsample threshold

    Example:
        >>> data = pd.Series(range(50000))
        >>> should_downsample(data)
        True
    """
    if isinstance(data, (pd.Series, pd.DataFrame)):
        size = len(data)
    else:
        size = len(data) if hasattr(data, "__len__") else 0

    return size > DOWNSAMPLE_THRESHOLD


# =============================================================================
# CACHING
# =============================================================================


class PlotCache:
    """Cache for computed metrics and transformations.

    This class provides a simple caching mechanism for expensive computations
    like rolling metrics, drawdown calculations, and indicator transformations.

    Example:
        >>> cache = PlotCache()
        >>> cache.set('sharpe_ratio', 1.87)
        >>> cache.get('sharpe_ratio')
        1.87
        >>> cache.clear()
    """

    def __init__(self, max_size: int = CACHE_SIZE):
        """Initialize cache.

        Args:
            max_size: Maximum number of cached items
        """
        self._cache: Dict[str, Any] = {}
        self._max_size = max_size
        self._enabled = True
        logger.debug(f"PlotCache initialized with max_size={max_size}")

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._enabled:
            return None

        value = self._cache.get(key)
        if value is not None:
            logger.trace(f"Cache hit: {key}")
        return value

    def set(self, key: str, value: Any) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        if not self._enabled:
            return

        # Simple LRU: remove oldest if at capacity
        if len(self._cache) >= self._max_size and key not in self._cache:
            # Remove first item (oldest in insertion order)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.trace(f"Cache evicted: {oldest_key}")

        self._cache[key] = value
        logger.trace(f"Cache set: {key}")

    def clear(self) -> None:
        """Clear all cached values."""
        count = len(self._cache)
        self._cache.clear()
        logger.debug(f"Cache cleared: {count} items removed")

    def enable(self) -> None:
        """Enable caching."""
        self._enabled = True
        logger.debug("Cache enabled")

    def disable(self) -> None:
        """Disable caching and clear cache."""
        self._enabled = False
        self.clear()
        logger.debug("Cache disabled")

    def __len__(self) -> int:
        """Return number of cached items."""
        return len(self._cache)


# Global cache instance
_global_cache = PlotCache()


def get_cache() -> PlotCache:
    """Get global plot cache instance.

    Returns:
        Global PlotCache instance

    Example:
        >>> cache = get_cache()
        >>> cache.set('key', 'value')
    """
    return _global_cache


def cached(cache_key_func: Optional[Callable] = None):
    """Cache function results.

    Args:
        cache_key_func: Optional function to generate cache key from arguments.
                       If None, uses str(args) + str(kwargs)

    Returns:
        Decorated function with caching

    Example:
        >>> @cached()
        ... def expensive_calculation(data):
        ...     return data.rolling(100).mean()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()

            # Generate cache key
            if cache_key_func:
                key = f"{func.__name__}:{cache_key_func(*args, **kwargs)}"
            else:
                key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Using cached result for {func.__name__}")
                return result

            # Compute and cache result
            logger.debug(f"Computing and caching {func.__name__}")
            result = func(*args, **kwargs)
            cache.set(key, result)

            return result

        return wrapper

    return decorator


# =============================================================================
# LAZY EVALUATION
# =============================================================================


class LazyPlot:
    """Lazy plot generation for progressive rendering.

    This class delays plot generation until explicitly requested,
    allowing for efficient batch processing and conditional rendering.

    Example:
        >>> lazy = LazyPlot(plot_equity, results=results)
        >>> # Plot not generated yet
        >>> fig = lazy.render()  # Now it's generated
    """

    def __init__(self, plot_func: Callable, *args, **kwargs):
        """Initialize lazy plot.

        Args:
            plot_func: Function to call for plotting
            *args: Positional arguments for plot_func
            **kwargs: Keyword arguments for plot_func
        """
        self._plot_func = plot_func
        self._args = args
        self._kwargs = kwargs
        self._result = None
        self._rendered = False
        logger.trace(f"LazyPlot created for {plot_func.__name__}")

    def render(self) -> Any:
        """Render the plot.

        Returns:
            Plot result (Figure or other object)
        """
        if not self._rendered:
            logger.debug(f"Rendering lazy plot: {self._plot_func.__name__}")
            self._result = self._plot_func(*self._args, **self._kwargs)
            self._rendered = True
        else:
            logger.trace(f"Using cached lazy plot: {self._plot_func.__name__}")

        return self._result

    @property
    def is_rendered(self) -> bool:
        """Check if plot has been rendered."""
        return self._rendered

    def clear(self) -> None:
        """Clear rendered result to free memory."""
        self._result = None
        self._rendered = False
        logger.trace("LazyPlot cleared")


def lazy(func: Callable) -> Callable:
    """Make plot function lazy.

    Args:
        func: Plot function to make lazy

    Returns:
        Function that returns LazyPlot instance

    Example:
        >>> @lazy
        ... def plot_equity(results):
        ...     # Plotting code
        ...     pass
        >>> lazy_plot = plot_equity(results)
        >>> fig = lazy_plot.render()
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> LazyPlot:
        return LazyPlot(func, *args, **kwargs)

    return wrapper


# =============================================================================
# MEMORY OPTIMIZATION
# =============================================================================


def optimize_dataframe_memory(
    df: pd.DataFrame, verbose: bool = False
) -> pd.DataFrame:  # pylint: disable=invalid-name
    """Optimize DataFrame memory usage by downcasting numeric types.

    Args:
        df: DataFrame to optimize
        verbose: Whether to log memory savings

    Returns:
        Optimized DataFrame

    Example:
        >>> df = pd.DataFrame({'a': [1, 2, 3], 'b': [1.0, 2.0, 3.0]})
        >>> optimized = optimize_dataframe_memory(df)
    """
    start_mem = df.memory_usage().sum() / 1024**2 if verbose else 0

    for col in df.columns:
        col_type = df[col].dtype

        if col_type != object:
            c_min = df[col].min()
            c_max = df[col].max()

            if str(col_type)[:3] == "int":
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
                elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max:
                    df[col] = df[col].astype(np.int64)

            else:  # float
                if (
                    c_min > np.finfo(np.float32).min
                    and c_max < np.finfo(np.float32).max
                ):
                    df[col] = df[col].astype(np.float32)
                else:
                    df[col] = df[col].astype(np.float64)

    if verbose:
        end_mem = df.memory_usage().sum() / 1024**2
        logger.success(
            f"Memory optimized: {start_mem:.2f} MB -> {end_mem:.2f} MB "
            f"({100 * (start_mem - end_mem) / start_mem:.1f}% reduction)"
        )

    return df


def chunk_data(
    data: Union[pd.Series, pd.DataFrame], chunk_size: int = 10000
) -> list:  # pylint: disable=invalid-name
    """Split data into chunks for processing.

    Args:
        data: Data to chunk
        chunk_size: Size of each chunk

    Returns:
        List of data chunks

    Example:
        >>> data = pd.Series(range(100000))
        >>> chunks = chunk_data(data, chunk_size=10000)
        >>> len(chunks)
        10
    """
    n = len(data)  # pylint: disable=invalid-name
    chunks = []

    for i in range(0, n, chunk_size):
        end = min(i + chunk_size, n)
        chunks.append(data[i:end])
        logger.trace(f"Created chunk {len(chunks)}: [{i}:{end}]")

    logger.debug(f"Split data into {len(chunks)} chunks of size {chunk_size}")
    return chunks


# =============================================================================
# PERFORMANCE HELPERS
# =============================================================================


@cached()
def cached_rolling_metric(
    data: pd.Series, window: int, metric: str = "mean"
) -> pd.Series:
    """Compute and cache rolling metric.

    Args:
        data: Input data
        window: Rolling window size
        metric: Metric to compute ('mean', 'std', 'min', 'max')

    Returns:
        Rolling metric series

    Example:
        >>> data = pd.Series(range(10000))
        >>> rolling_mean = cached_rolling_metric(data, 100, 'mean')
    """
    logger.debug(f"Computing rolling {metric} with window={window}")

    rolling = data.rolling(window)

    if metric == "mean":
        return rolling.mean()
    if metric == "std":
        return rolling.std()
    if metric == "min":
        return rolling.min()
    if metric == "max":
        return rolling.max()
    raise ValueError(f"Unknown metric: {metric}")


@cached()
def cached_drawdown(equity: pd.Series) -> pd.Series:
    """Compute and cache drawdown series.

    Args:
        equity: Equity curve

    Returns:
        Drawdown series

    Example:
        >>> equity = pd.Series([100, 110, 105, 115, 120])
        >>> dd = cached_drawdown(equity)
    """
    logger.debug("Computing drawdown")

    running_max = equity.expanding().max()
    drawdown = (equity - running_max) / running_max

    return drawdown


def auto_downsample(
    data: Union[pd.Series, pd.DataFrame],
    threshold: int = DOWNSAMPLE_THRESHOLD,
    target: int = DEFAULT_TARGET_POINTS,
) -> Union[pd.Series, pd.DataFrame]:
    """Automatically downsample data if it exceeds threshold.

    Args:
        data: Data to potentially downsample
        threshold: Size threshold for downsampling
        target: Target size after downsampling

    Returns:
        Original or downsampled data (Series or DataFrame only)

    Example:
        >>> data = pd.Series(range(50000))
        >>> downsampled = auto_downsample(data)
        >>> len(downsampled) <= 5000
        True
    """
    if len(data) > threshold:
        logger.info(
            f"Auto-downsampling: {len(data)} points -> {target} points "
            f"({100 * target / len(data):.1f}% of original)"
        )
        result = downsample_lttb(data, threshold=target)
        # downsample_lttb returns same type as input for Series/DataFrame
        assert isinstance(result, (pd.Series, pd.DataFrame))
        return result
    logger.trace(f"No downsampling needed: {len(data)} <= {threshold}")
    return data


__all__ = [
    "downsample_lttb",
    "should_downsample",
    "auto_downsample",
    "PlotCache",
    "get_cache",
    "cached",
    "LazyPlot",
    "lazy",
    "optimize_dataframe_memory",
    "chunk_data",
    "cached_rolling_metric",
    "cached_drawdown",
    "DOWNSAMPLE_THRESHOLD",
    "DEFAULT_TARGET_POINTS",
]
