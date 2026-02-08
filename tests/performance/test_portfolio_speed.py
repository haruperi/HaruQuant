"""
Performance benchmarks for portfolio backtesting.

Tests execution speed and memory usage for multi-symbol portfolios.
"""

import pytest
import pandas as pd
import numpy as np
import time
import tracemalloc
from apps.simulation.portfolio import PortfolioStrategy, PortfolioEngine
from apps.simulation.data import SymbolInfoSimulator
from apps.strategy.base import BaseStrategy


class SimpleStrategy(BaseStrategy):
    """Minimal strategy for performance testing."""

    def __init__(self, params=None):
        self.params = params or {}

    def on_init(self) -> None:
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        # Minimal processing - just add signal columns
        data['entry_signal'] = 0
        data['exit_signal'] = 0
        return data

    def get_signal(self, data: pd.DataFrame, current_index: int):
        # Minimal logic - rarely trade
        if current_index % 100 == 0:  # Trade every 100 bars
            return {'entry_signal': 1, 'exit_signal': 0, 'type': 'buy'}
        return None


def generate_perf_data(symbol: str, periods: int):
    """Generate synthetic data for performance testing."""
    dates = pd.date_range('2024-01-01', periods=periods, freq='1h')
    prices = 1.1 + np.cumsum(np.random.randn(periods) * 0.0001)

    return pd.DataFrame({
        'open': prices,
        'high': prices * 1.001,
        'low': prices * 0.999,
        'close': prices,
        'volume': 1000
    }, index=dates)


@pytest.mark.performance
class TestPortfolioPerformance:
    """Performance benchmark tests."""

    def test_benchmark_2_asset_1000_bars(self, benchmark):
        """Benchmark 2-asset portfolio with 1000 bars."""
        # Generate data
        data = {
            'EURUSD': generate_perf_data('EURUSD', 1000),
            'GBPUSD': generate_perf_data('GBPUSD', 1000)
        }

        symbol_specs = {
            symbol: SymbolInfoSimulator(symbol=symbol)
            for symbol in data.keys()
        }

        strategies = {
            symbol: SimpleStrategy({'symbol': symbol})
            for symbol in data.keys()
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs,
            data=data,
            allocation_method='equal_weight'
        )

        def run_backtest():
            engine = PortfolioEngine(
                portfolio_strategy=portfolio,
                initial_balance=10000.0,
                config={'volume': 0.01, 'verbose': False}
            )
            return engine.run(synchronize_data=True)

        # Benchmark
        result = benchmark(run_backtest)

        # Verify it completed
        assert result.final_balance > 0

        print(f"\n2 assets × 1000 bars:")
        print(f"  Mean: {benchmark.stats['mean']:.3f}s")
        print(f"  Median: {benchmark.stats['median']:.3f}s")
        print(f"  Min: {benchmark.stats['min']:.3f}s")
        print(f"  Max: {benchmark.stats['max']:.3f}s")

    def test_benchmark_5_asset_5000_bars(self, benchmark):
        """Benchmark 5-asset portfolio with 5000 bars."""
        # Generate data
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCHF']
        data = {
            symbol: generate_perf_data(symbol, 5000)
            for symbol in symbols
        }

        symbol_specs = {
            symbol: SymbolInfoSimulator(symbol=symbol)
            for symbol in symbols
        }

        strategies = {
            symbol: SimpleStrategy({'symbol': symbol})
            for symbol in symbols
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs,
            data=data,
            allocation_method='equal_weight'
        )

        def run_backtest():
            engine = PortfolioEngine(
                portfolio_strategy=portfolio,
                initial_balance=50000.0,
                config={'volume': 0.01, 'verbose': False}
            )
            return engine.run(synchronize_data=True)

        # Benchmark
        result = benchmark(run_backtest)

        # Verify it completed
        assert result.final_balance > 0

        print(f"\n5 assets × 5000 bars:")
        print(f"  Mean: {benchmark.stats['mean']:.3f}s")
        print(f"  Median: {benchmark.stats['median']:.3f}s")
        print(f"  Min: {benchmark.stats['min']:.3f}s")
        print(f"  Max: {benchmark.stats['max']:.3f}s")

    def test_memory_usage_scaling(self):
        """Test memory usage scales linearly with number of symbols."""
        results = []

        for n_symbols in [1, 2, 3, 5]:
            # Generate data
            symbols = [f'SYM{i}' for i in range(n_symbols)]
            data = {
                symbol: generate_perf_data(symbol, 1000)
                for symbol in symbols
            }

            symbol_specs = {
                symbol: SymbolInfoSimulator(symbol=symbol)
                for symbol in symbols
            }

            strategies = {
                symbol: SimpleStrategy({'symbol': symbol})
                for symbol in symbols
            }

            portfolio = PortfolioStrategy(
                strategies=strategies,
                symbol_specs=symbol_specs,
                data=data,
                allocation_method='equal_weight'
            )

            # Measure memory
            tracemalloc.start()
            start_mem = tracemalloc.get_traced_memory()[0]

            engine = PortfolioEngine(
                portfolio_strategy=portfolio,
                initial_balance=10000.0 * n_symbols,
                config={'volume': 0.01, 'verbose': False}
            )

            result = engine.run(synchronize_data=True)

            current_mem, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            mem_used_mb = (peak_mem - start_mem) / 1024 / 1024

            results.append({
                'symbols': n_symbols,
                'memory_mb': mem_used_mb,
                'trades': len(result.trades)
            })

            print(f"\n{n_symbols} symbols:")
            print(f"  Memory: {mem_used_mb:.2f} MB")
            print(f"  Trades: {len(result.trades)}")

        # Verify linear scaling (roughly)
        # Memory for N symbols should be < N × memory for 1 symbol × 1.5 (50% overhead)
        if len(results) >= 2:
            base_mem = results[0]['memory_mb']
            for r in results[1:]:
                expected_max = base_mem * r['symbols'] * 1.5
                assert r['memory_mb'] < expected_max, \
                    f"{r['symbols']} symbols used {r['memory_mb']:.2f} MB, " \
                    f"expected < {expected_max:.2f} MB"

    @pytest.mark.slow
    def test_benchmark_10_asset_10000_bars(self):
        """Benchmark 10-asset portfolio with 10000 bars (stress test)."""
        # Generate data
        symbols = [f'ASSET{i:02d}' for i in range(10)]
        data = {
            symbol: generate_perf_data(symbol, 10000)
            for symbol in symbols
        }

        symbol_specs = {
            symbol: SymbolInfoSimulator(symbol=symbol)
            for symbol in symbols
        }

        strategies = {
            symbol: SimpleStrategy({'symbol': symbol})
            for symbol in symbols
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs,
            data=data,
            allocation_method='equal_weight'
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio,
            initial_balance=100000.0,
            config={'volume': 0.01, 'verbose': False}
        )

        # Time execution
        start_time = time.time()
        result = engine.run(synchronize_data=True)
        elapsed = time.time() - start_time

        # Verify it completed
        assert result.final_balance > 0

        print(f"\n10 assets × 10000 bars:")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Bars/second: {100000/elapsed:.0f}")
        print(f"  Total trades: {len(result.trades)}")

        # Should complete in reasonable time (< 5 minutes)
        assert elapsed < 300, f"Took {elapsed:.1f}s, expected < 300s"

    def test_synchronization_overhead(self):
        """Measure overhead of data synchronization."""
        # Generate data with identical timestamps (no sync needed)
        dates = pd.date_range('2024-01-01', periods=1000, freq='1h')
        data_aligned = {
            'EURUSD': generate_perf_data('EURUSD', 1000),
            'GBPUSD': generate_perf_data('GBPUSD', 1000)
        }

        symbol_specs = {
            'EURUSD': SymbolInfoSimulator(symbol='EURUSD'),
            'GBPUSD': SymbolInfoSimulator(symbol='GBPUSD')
        }

        strategies = {
            'EURUSD': SimpleStrategy(),
            'GBPUSD': SimpleStrategy()
        }

        portfolio = PortfolioStrategy(
            strategies=strategies,
            symbol_specs=symbol_specs,
            data=data_aligned,
            allocation_method='equal_weight'
        )

        engine = PortfolioEngine(
            portfolio_strategy=portfolio,
            initial_balance=10000.0,
            config={'volume': 0.01, 'verbose': False}
        )

        # Time with synchronization
        start = time.time()
        result_sync = engine.run(synchronize_data=True)
        time_sync = time.time() - start

        # Time without synchronization
        engine2 = PortfolioEngine(
            portfolio_strategy=portfolio,
            initial_balance=10000.0,
            config={'volume': 0.01, 'verbose': False}
        )

        start = time.time()
        result_no_sync = engine2.run(synchronize_data=False)
        time_no_sync = time.time() - start

        print(f"\nSynchronization overhead:")
        print(f"  With sync: {time_sync:.3f}s")
        print(f"  Without sync: {time_no_sync:.3f}s")
        print(f"  Overhead: {(time_sync - time_no_sync):.3f}s ({(time_sync/time_no_sync - 1)*100:.1f}%)")

        # Both should produce valid results
        assert result_sync.final_balance > 0
        assert result_no_sync.final_balance > 0
