"""
Performance Benchmark Tests.

Benchmarks for tracking backtest engine performance using pytest-benchmark.
Tests various data sizes and engine configurations to establish performance baselines.

Usage:
    # Run all benchmarks
    pytest tests/benchmarks/test_backtest_performance.py --benchmark-only
    
    # Save baseline
    pytest tests/benchmarks/test_backtest_performance.py --benchmark-only --benchmark-save=baseline
    
    # Compare against baseline
    pytest tests/benchmarks/test_backtest_performance.py --benchmark-only --benchmark-compare=baseline
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest

from apps.backtest.engine.event_driven import EventDrivenEngine
from apps.backtest.engine.vectorized import VectorizedEngine

from tests.benchmarks.fixtures import (
    complex_strategy,
    engine_config_minimal,
    engine_config_realistic,
    sample_data_1k,
    sample_data_10k,
    sample_data_100k,
    simple_strategy,
)


# ============================================================================
# EventDrivenEngine Benchmarks
# ============================================================================


class TestEventDrivenPerformance:
    """Benchmark EventDrivenEngine with various data sizes."""
    
    def test_event_driven_1k_bars_minimal(
        self, benchmark, sample_data_1k, simple_strategy, engine_config_minimal
    ):
        """Benchmark: EventDrivenEngine with 1K bars (no costs)."""
        def run():
            engine = EventDrivenEngine(
                strategy=simple_strategy,
                data=sample_data_1k,
                **engine_config_minimal
            )
            return engine.run()
        
        result = benchmark(run)
        assert result.total_trades >= 0
    
    def test_event_driven_1k_bars_realistic(
        self, benchmark, sample_data_1k, simple_strategy, engine_config_realistic
    ):
        """Benchmark: EventDrivenEngine with 1K bars (with costs)."""
        def run():
            engine = EventDrivenEngine(
                strategy=simple_strategy,
                data=sample_data_1k,
                **engine_config_realistic
            )
            return engine.run()
        
        result = benchmark(run)
        assert result.total_trades >= 0
    
    def test_event_driven_10k_bars(
        self, benchmark, sample_data_10k, simple_strategy, engine_config_minimal
    ):
        """Benchmark: EventDrivenEngine with 10K bars."""
        def run():
            engine = EventDrivenEngine(
                strategy=simple_strategy,
                data=sample_data_10k,
                **engine_config_minimal
            )
            return engine.run()
        
        result = benchmark(run)
        assert result.total_trades >= 0
    
    def test_event_driven_100k_bars(
        self, benchmark, sample_data_100k, simple_strategy, engine_config_minimal
    ):
        """Benchmark: EventDrivenEngine with 100K bars."""
        def run():
            engine = EventDrivenEngine(
                strategy=simple_strategy,
                data=sample_data_100k,
                **engine_config_minimal
            )
            return engine.run()
        
        result = benchmark.pedantic(run, iterations=1, rounds=1)
        assert result.total_trades >= 0
    
    def test_event_driven_complex_strategy(
        self, benchmark, sample_data_10k, complex_strategy, engine_config_minimal
    ):
        """Benchmark: EventDrivenEngine with complex strategy."""
        def run():
            engine = EventDrivenEngine(
                strategy=complex_strategy,
                data=sample_data_10k,
                **engine_config_minimal
            )
            return engine.run()
        
        result = benchmark(run)
        assert result.total_trades >= 0


# ============================================================================
# VectorizedEngine Benchmarks
# ============================================================================


class TestVectorizedPerformance:
    """Benchmark VectorizedEngine with various data sizes."""
    
    def test_vectorized_1k_bars(
        self, benchmark, sample_data_1k, simple_strategy, engine_config_minimal
    ):
        """Benchmark: VectorizedEngine with 1K bars."""
        def run():
            engine = VectorizedEngine(
                strategy=simple_strategy,
                data=sample_data_1k,
                **engine_config_minimal
            )
            return engine.run()
        
        result = benchmark(run)
        assert result.total_trades >= 0
    
    def test_vectorized_10k_bars(
        self, benchmark, sample_data_10k, simple_strategy, engine_config_minimal
    ):
        """Benchmark: VectorizedEngine with 10K bars."""
        def run():
            engine = VectorizedEngine(
                strategy=simple_strategy,
                data=sample_data_10k,
                **engine_config_minimal
            )
            return engine.run()
        
        result = benchmark(run)
        assert result.total_trades >= 0
    
    def test_vectorized_100k_bars(
        self, benchmark, sample_data_100k, simple_strategy, engine_config_minimal
    ):
        """Benchmark: VectorizedEngine with 100K bars."""
        def run():
            engine = VectorizedEngine(
                strategy=simple_strategy,
                data=sample_data_100k,
                **engine_config_minimal
            )
            return engine.run()
        
        result = benchmark.pedantic(run, iterations=1, rounds=1)
        assert result.total_trades >= 0
    
    def test_vectorized_complex_strategy(
        self, benchmark, sample_data_10k, complex_strategy, engine_config_minimal
    ):
        """Benchmark: VectorizedEngine with complex strategy."""
        def run():
            engine = VectorizedEngine(
                strategy=complex_strategy,
                data=sample_data_10k,
                **engine_config_minimal
            )
            return engine.run()
        
        result = benchmark(run)
        assert result.total_trades >= 0


# ============================================================================
# Throughput Benchmarks
# ============================================================================


class TestThroughput:
    """Benchmark bars per second throughput."""
    
    def test_event_driven_throughput_1k(
        self, benchmark, sample_data_1k, simple_strategy, engine_config_minimal
    ):
        """Measure EventDrivenEngine throughput with 1K bars."""
        def run():
            engine = EventDrivenEngine(
                strategy=simple_strategy,
                data=sample_data_1k,
                **engine_config_minimal
            )
            return engine.run()
        
        result = benchmark(run)
        
        # Calculate bars per second
        bars = len(sample_data_1k)
        time_seconds = benchmark.stats['mean']
        bars_per_second = bars / time_seconds
        
        # Store in benchmark extra info
        benchmark.extra_info['bars'] = bars
        benchmark.extra_info['bars_per_second'] = int(bars_per_second)
        
        assert result.total_trades >= 0
    
    def test_vectorized_throughput_100k(
        self, benchmark, sample_data_100k, simple_strategy, engine_config_minimal
    ):
        """Measure VectorizedEngine throughput with 100K bars."""
        def run():
            engine = VectorizedEngine(
                strategy=simple_strategy,
                data=sample_data_100k,
                **engine_config_minimal
            )
            return engine.run()
        
        result = benchmark.pedantic(run, iterations=1, rounds=1)
        
        # Calculate bars per second
        bars = len(sample_data_100k)
        time_seconds = benchmark.stats['mean']
        bars_per_second = bars / time_seconds
        
        # Store in benchmark extra info
        benchmark.extra_info['bars'] = bars
        benchmark.extra_info['bars_per_second'] = int(bars_per_second)
        
        assert result.total_trades >= 0


# ============================================================================
# Strategy Complexity Benchmarks
# ============================================================================


class TestStrategyComplexity:
    """Benchmark impact of strategy complexity."""
    
    def test_simple_vs_complex_event_driven(
        self, benchmark, sample_data_10k, simple_strategy, complex_strategy, engine_config_minimal
    ):
        """Compare simple vs complex strategy on EventDrivenEngine."""
        # This test demonstrates how to compare different configurations
        # In practice, you'd run this twice with different strategies
        def run():
            engine = EventDrivenEngine(
                strategy=simple_strategy,
                data=sample_data_10k,
                **engine_config_minimal
            )
            return engine.run()
        
        result = benchmark(run)
        assert result.total_trades >= 0
