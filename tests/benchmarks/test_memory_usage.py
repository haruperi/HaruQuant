"""
Memory Usage Benchmark Tests.

Tracks memory consumption during backtesting to ensure optimizations
don't increase memory footprint and to establish memory baselines.

Usage:
    pytest tests/benchmarks/test_memory_usage.py -v
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import psutil
import pytest

from apps.backtest.engine.event_driven import EventDrivenEngine
from apps.backtest.engine.vectorized import VectorizedEngine

from tests.benchmarks.fixtures import (
    engine_config_minimal,
    sample_data_1k,
    sample_data_10k,
    sample_data_100k,
    simple_strategy,
)


def get_memory_usage_mb():
    """Get current process memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


class TestMemoryUsage:
    """Test memory consumption during backtesting."""
    
    def test_event_driven_memory_1k(self, sample_data_1k, simple_strategy, engine_config_minimal):
        """Measure memory usage for EventDrivenEngine with 1K bars."""
        # Measure baseline memory
        baseline_memory = get_memory_usage_mb()
        
        # Run backtest
        engine = EventDrivenEngine(
            strategy=simple_strategy,
            data=sample_data_1k,
            **engine_config_minimal
        )
        result = engine.run()
        
        # Measure peak memory
        peak_memory = get_memory_usage_mb()
        memory_used = peak_memory - baseline_memory
        
        # Calculate memory per bar
        memory_per_bar_kb = (memory_used * 1024) / len(sample_data_1k)
        
        print(f"\nMemory usage for 1K bars:")
        print(f"  Total: {memory_used:.2f} MB")
        print(f"  Per bar: {memory_per_bar_kb:.2f} KB")
        
        # Assert reasonable memory usage (< 100MB for 1K bars)
        assert memory_used < 100, f"Memory usage too high: {memory_used:.2f} MB"
        assert result.total_trades >= 0
    
    def test_event_driven_memory_10k(self, sample_data_10k, simple_strategy, engine_config_minimal):
        """Measure memory usage for EventDrivenEngine with 10K bars."""
        baseline_memory = get_memory_usage_mb()
        
        engine = EventDrivenEngine(
            strategy=simple_strategy,
            data=sample_data_10k,
            **engine_config_minimal
        )
        result = engine.run()
        
        peak_memory = get_memory_usage_mb()
        memory_used = peak_memory - baseline_memory
        memory_per_bar_kb = (memory_used * 1024) / len(sample_data_10k)
        
        print(f"\nMemory usage for 10K bars:")
        print(f"  Total: {memory_used:.2f} MB")
        print(f"  Per bar: {memory_per_bar_kb:.2f} KB")
        
        # Assert reasonable memory usage (< 500MB for 10K bars)
        assert memory_used < 500, f"Memory usage too high: {memory_used:.2f} MB"
        assert result.total_trades >= 0
    
    def test_event_driven_memory_100k(self, sample_data_100k, simple_strategy, engine_config_minimal):
        """Measure memory usage for EventDrivenEngine with 100K bars."""
        baseline_memory = get_memory_usage_mb()
        
        engine = EventDrivenEngine(
            strategy=simple_strategy,
            data=sample_data_100k,
            **engine_config_minimal
        )
        result = engine.run()
        
        peak_memory = get_memory_usage_mb()
        memory_used = peak_memory - baseline_memory
        memory_per_bar_kb = (memory_used * 1024) / len(sample_data_100k)
        
        print(f"\nMemory usage for 100K bars:")
        print(f"  Total: {memory_used:.2f} MB")
        print(f"  Per bar: {memory_per_bar_kb:.2f} KB")
        
        # Assert reasonable memory usage (< 2GB for 100K bars)
        assert memory_used < 2000, f"Memory usage too high: {memory_used:.2f} MB"
        assert result.total_trades >= 0
    
    def test_vectorized_memory_100k(self, sample_data_100k, simple_strategy, engine_config_minimal):
        """Measure memory usage for VectorizedEngine with 100K bars."""
        baseline_memory = get_memory_usage_mb()
        
        engine = VectorizedEngine(
            strategy=simple_strategy,
            data=sample_data_100k,
            **engine_config_minimal
        )
        result = engine.run()
        
        peak_memory = get_memory_usage_mb()
        memory_used = peak_memory - baseline_memory
        memory_per_bar_kb = (memory_used * 1024) / len(sample_data_100k)
        
        print(f"\nVectorized memory usage for 100K bars:")
        print(f"  Total: {memory_used:.2f} MB")
        print(f"  Per bar: {memory_per_bar_kb:.2f} KB")
        
        # Vectorized should use less memory than event-driven
        assert memory_used < 1000, f"Memory usage too high: {memory_used:.2f} MB"
        assert result.total_trades >= 0
    
    def test_memory_scaling(self, simple_strategy, engine_config_minimal):
        """Test that memory scales linearly with data size."""
        import numpy as np
        import pandas as pd
        
        sizes = [1000, 5000, 10000]
        memory_usage = []
        
        for n in sizes:
            # Generate data
            np.random.seed(42)
            base_price = 100.0
            returns = np.random.randn(n) * 0.01
            close = base_price * (1 + returns).cumprod()
            
            data = pd.DataFrame({
                'open': np.roll(close, 1),
                'high': close * 1.005,
                'low': close * 0.995,
                'close': close,
                'volume': np.random.randint(1000, 10000, n),
            }, index=pd.date_range('2020-01-01', periods=n, freq='1H'))
            
            # Measure memory
            baseline = get_memory_usage_mb()
            
            engine = EventDrivenEngine(
                strategy=simple_strategy,
                data=data,
                **engine_config_minimal
            )
            engine.run()
            
            peak = get_memory_usage_mb()
            memory_usage.append(peak - baseline)
        
        # Check that memory scales roughly linearly
        # (within 2x tolerance for overhead)
        ratio_1_to_2 = memory_usage[1] / memory_usage[0]
        ratio_2_to_3 = memory_usage[2] / memory_usage[1]
        
        print(f"\nMemory scaling:")
        print(f"  1K bars: {memory_usage[0]:.2f} MB")
        print(f"  5K bars: {memory_usage[1]:.2f} MB (ratio: {ratio_1_to_2:.2f}x)")
        print(f"  10K bars: {memory_usage[2]:.2f} MB (ratio: {ratio_2_to_3:.2f}x)")
        
        # Memory should scale sub-linearly or linearly (not exponentially)
        assert ratio_1_to_2 < 10, "Memory scaling is too steep"
        assert ratio_2_to_3 < 10, "Memory scaling is too steep"


class TestMemoryLeaks:
    """Test for memory leaks during repeated backtests."""
    
    def test_no_memory_leak_repeated_runs(self, sample_data_1k, simple_strategy, engine_config_minimal):
        """Ensure memory doesn't grow with repeated backtests."""
        import gc
        
        memory_readings = []
        
        for i in range(5):
            # Force garbage collection
            gc.collect()
            
            # Measure memory before
            before = get_memory_usage_mb()
            
            # Run backtest
            engine = EventDrivenEngine(
                strategy=simple_strategy,
                data=sample_data_1k,
                **engine_config_minimal
            )
            result = engine.run()
            
            # Clean up
            del engine
            del result
            gc.collect()
            
            # Measure memory after
            after = get_memory_usage_mb()
            memory_readings.append(after)
        
        # Check that memory doesn't grow significantly
        memory_growth = memory_readings[-1] - memory_readings[0]
        
        print(f"\nMemory leak test (5 iterations):")
        print(f"  Initial: {memory_readings[0]:.2f} MB")
        print(f"  Final: {memory_readings[-1]:.2f} MB")
        print(f"  Growth: {memory_growth:.2f} MB")
        
        # Allow some growth for caching, but not excessive
        assert memory_growth < 50, f"Possible memory leak: {memory_growth:.2f} MB growth"
