import pytest
import pandas as pd
import numpy as np
import time
from unittest.mock import MagicMock, patch
from apps.plotting.optimization import (
    downsample_lttb,
    should_downsample,
    auto_downsample,
    PlotCache,
    get_cache,
    cached,
    LazyPlot,
    lazy,
    optimize_dataframe_memory,
    chunk_data,
    cached_rolling_metric,
    cached_drawdown,
    DOWNSAMPLE_THRESHOLD
)

@pytest.fixture
def large_dataset():
    """Create a dataset larger than threshold."""
    size = DOWNSAMPLE_THRESHOLD + 1000
    return pd.Series(np.random.randn(size), index=pd.date_range("2024-01-01", periods=size))

@pytest.fixture
def clean_cache():
    """Clear global cache before/after tests."""
    get_cache().clear()
    yield
    get_cache().clear()

class TestLTTB:
    def test_downsample_lttb_series(self, large_dataset):
        """Test downsampling a Series."""
        target = 500
        result = downsample_lttb(large_dataset, threshold=target)
        assert len(result) == target
        assert isinstance(result, pd.Series)
        # First and last points should be preserved
        assert result.iloc[0] == large_dataset.iloc[0]
        assert result.iloc[-1] == large_dataset.iloc[-1]

    def test_downsample_lttb_dataframe(self):
        """Test downsampling a DataFrame."""
        df = pd.DataFrame({'a': range(100), 'b': range(100)})
        result = downsample_lttb(df, threshold=10)
        assert len(result) == 10
        assert isinstance(result, pd.DataFrame)
        assert len(result.columns) == 2

    def test_downsample_lttb_array(self):
        """Test downsampling a numpy array."""
        arr = np.arange(100)
        x, y = downsample_lttb(arr, threshold=10)
        assert len(y) == 10
        assert isinstance(y, np.ndarray)

    def test_lttb_small_data(self):
        """Test LTTB with data smaller than threshold."""
        data = pd.Series(range(10))
        result = downsample_lttb(data, threshold=20)
        assert len(result) == 10 # Retains original size

class TestAutoDownsample:
    def test_should_downsample(self, large_dataset):
        assert should_downsample(large_dataset) is True
        assert should_downsample(pd.Series(range(100))) is False

    def test_auto_downsample_triggers(self, large_dataset):
        result = auto_downsample(large_dataset, target=500)
        assert len(result) == 500

    def test_auto_downsample_skips(self):
        data = pd.Series(range(100))
        result = auto_downsample(data)
        assert len(result) == 100

class TestCaching:
    def test_cache_set_get(self, clean_cache):
        cache = get_cache()
        cache.set("key", "value")
        assert cache.get("key") == "value"
        assert cache.get("missing") is None

    def test_cache_decorator(self, clean_cache):
        mock_func = MagicMock(return_value=42)
        
        @cached()
        def expensive_func(x):
            return mock_func(x)
            
        # First call
        assert expensive_func(1) == 42
        assert mock_func.call_count == 1
        
        # Second call (cached)
        assert expensive_func(1) == 42
        assert mock_func.call_count == 1 # Still 1

        # Different arg
        assert expensive_func(2) == 42
        assert mock_func.call_count == 2

    def test_cached_rolling_metric(self, clean_cache):
        data = pd.Series(range(100))
        res1 = cached_rolling_metric(data, 10, "mean")
        res2 = cached_rolling_metric(data, 10, "mean")
        assert res1.equals(res2)

class TestLazyPlot:
    def test_lazy_plot_execution(self):
        mock_plot = MagicMock(return_value="figure")
        mock_plot.__name__ = "mock_plot"
        lazy_obj = LazyPlot(mock_plot, 1, a=2)
        
        assert not lazy_obj.is_rendered
        assert mock_plot.call_count == 0
        
        res = lazy_obj.render()
        assert res == "figure"
        assert lazy_obj.is_rendered
        assert mock_plot.call_count == 1
        
        # Subsequent render returns cached result
        res2 = lazy_obj.render()
        assert res2 == "figure"
        assert mock_plot.call_count == 1

    def test_lazy_decorator(self):
        @lazy
        def my_plot(x):
            return x * 2
            
        lazy_obj = my_plot(10)
        assert isinstance(lazy_obj, LazyPlot)
        assert lazy_obj.render() == 20

class TestMemoryOptimization:
    def test_optimize_dataframe_memory(self):
        df = pd.DataFrame({
            'int': np.array([1, 2, 3], dtype='int64'),
            'float': np.array([1.1, 2.2, 3.3], dtype='float64'),
            'obj': ['a', 'b', 'c']
        })
        
        opt_df = optimize_dataframe_memory(df)
        
        assert opt_df['int'].dtype == 'int8' # Should downcast
        assert opt_df['float'].dtype == 'float32'
        assert opt_df['obj'].dtype == object # Unchanged

    def test_chunk_data(self):
        data = pd.Series(range(100))
        chunks = chunk_data(data, chunk_size=30)
        assert len(chunks) == 4 # 30, 30, 30, 10
        assert len(chunks[0]) == 30
        assert len(chunks[-1]) == 10
