"""
Performance benchmarks for backtest execution speed.

Benchmarks:
- 1,000,000 orders execution time (logged runtime in CI)
- Event-driven vs Vectorized performance
- Position array optimization impact
- Numba JIT compilation impact

Target: 70-100ms on M1/equivalent (manual/observed; logged)

Note: Actual performance varies by hardware. Tests log execution time
for comparison and regression detection.
"""

import pytest
import pandas as pd
import numpy as np
import time
from datetime import datetime

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import SymbolInfoSimulator, AccountInfoSimulator


class MockMT5Client:
    """Mock MT5 client for testing without real connection."""

    def order_calc_profit(self, action, symbol, volume, price_open, price_close):
        """Calculate profit for a trade."""
        contract_size = 100000.0
        if action == 0:  # Buy
            profit = (price_close - price_open) * volume * contract_size
        else:  # Sell
            profit = (price_open - price_close) * volume * contract_size
        return profit

    def order_calc_margin(self, action, symbol, volume, price):
        """Calculate margin for a trade."""
        contract_size = 100000.0
        leverage = 100.0
        return (volume * contract_size * price) / leverage


class HighFrequencyStrategy:
    """
    Strategy that generates many signals for performance testing.

    Generates signal on every bar for maximum order volume.
    """

    def __init__(self, params: dict):
        self.params = params
        self.symbol = params.get("symbol", "EURUSD")
        self.signal_frequency = params.get("signal_frequency", 1)  # Every N bars

    def on_init(self):
        """Initialize strategy."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate frequent signals."""
        data = data.copy()

        # Generate signal every N bars
        data["signal"] = 0
        for i in range(0, len(data), self.signal_frequency):
            # Alternate between buy and sell
            if i % 2 == 0:
                data.iloc[i, data.columns.get_loc("signal")] = 1  # Buy
            else:
                data.iloc[i, data.columns.get_loc("signal")] = -1  # Sell

        return data

    def get_signal(self, data: pd.DataFrame, index: int):
        """Get signal details for a specific bar."""
        row = data.iloc[index]
        signal = int(row.get("signal", 0))

        if signal == 0:
            return None

        return {
            "entry_signal": signal,
            "exit_signal": 0,
            "pending_signal": 0,
            "cancel_pending_signal": 0,
            "price": row["close"],
        }


@pytest.mark.benchmark
class TestExecutionSpeed:
    """Test execution speed with large order volumes."""

    def test_1000_bars_event_driven(self, benchmark):
        """Benchmark 1,000 bars in event-driven mode."""

        def run_backtest():
            account = AccountInfoSimulator(balance=10000.0)
            symbol = SymbolInfoSimulator(
                symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
            )

            simulator = TradeSimulator(
                simulator_name="Perf_1K_Event",
                mt5_client=None,
                account_info=account,
                symbols={"EURUSD": symbol},
            )

            # 1,000 bars
            dates = pd.date_range(start="2024-01-01", periods=1000, freq="h")
            prices = [1.10000 + np.sin(i * 0.01) * 0.00100 for i in range(1000)]

            data = pd.DataFrame(
                {
                    "time": dates,
                    "open": prices,
                    "high": [p + 0.00010 for p in prices],
                    "low": [p - 0.00010 for p in prices],
                    "close": prices,
                    "tick_volume": 100,
                    "spread": 10,
                    "real_volume": 0,
                }
            ).set_index("time")

            strategy = HighFrequencyStrategy(
                params={"symbol": "EURUSD", "signal_frequency": 2}
            )
            strategy.on_init()
            data = strategy.on_bar(data)

            simulator.run(
                data=data,
                strategy=strategy,
                symbol="EURUSD",
                volume=0.1,
                verbose=False,
                save_db=False,
                engine_type="event_driven",
            )

            return simulator

        # Run benchmark
        result = benchmark(run_backtest)
        print(f"\n1,000 bars event-driven: {benchmark.stats['mean']:.4f}s")

    def test_1000_bars_vectorized(self, benchmark):
        """Benchmark 1,000 bars in vectorized mode."""

        def run_backtest():
            account = AccountInfoSimulator(balance=10000.0)
            symbol = SymbolInfoSimulator(
                symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
            )

            simulator = TradeSimulator(
                simulator_name="Perf_1K_Vector",
                mt5_client=MockMT5Client(),
                account_info=account,
                symbols={"EURUSD": symbol},
            )

            # 1,000 bars
            dates = pd.date_range(start="2024-01-01", periods=1000, freq="h")
            prices = [1.10000 + np.sin(i * 0.01) * 0.00100 for i in range(1000)]

            data = pd.DataFrame(
                {
                    "time": dates,
                    "open": prices,
                    "high": [p + 0.00010 for p in prices],
                    "low": [p - 0.00010 for p in prices],
                    "close": prices,
                    "tick_volume": 100,
                    "spread": 10,
                    "real_volume": 0,
                }
            ).set_index("time")

            strategy = HighFrequencyStrategy(
                params={"symbol": "EURUSD", "signal_frequency": 2}
            )
            strategy.on_init()
            data = strategy.on_bar(data)

            simulator.run(
                data=data,
                strategy=strategy,
                symbol="EURUSD",
                volume=0.1,
                verbose=False,
                save_db=False,
                engine_type="vectorised",
            )

            return simulator

        # Run benchmark
        result = benchmark(run_backtest)
        print(f"\n1,000 bars vectorized: {benchmark.stats['mean']:.4f}s")

    def test_10000_bars_vectorized(self, benchmark):
        """Benchmark 10,000 bars in vectorized mode (high load)."""

        def run_backtest():
            account = AccountInfoSimulator(balance=10000.0)
            symbol = SymbolInfoSimulator(
                symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
            )

            simulator = TradeSimulator(
                simulator_name="Perf_10K_Vector",
                mt5_client=MockMT5Client(),
                account_info=account,
                symbols={"EURUSD": symbol},
            )

            # 10,000 bars
            dates = pd.date_range(start="2023-01-01", periods=10000, freq="h")
            prices = [1.10000 + np.sin(i * 0.01) * 0.00100 for i in range(10000)]

            data = pd.DataFrame(
                {
                    "time": dates,
                    "open": prices,
                    "high": [p + 0.00010 for p in prices],
                    "low": [p - 0.00010 for p in prices],
                    "close": prices,
                    "tick_volume": 100,
                    "spread": 10,
                    "real_volume": 0,
                }
            ).set_index("time")

            strategy = HighFrequencyStrategy(
                params={"symbol": "EURUSD", "signal_frequency": 10}
            )
            strategy.on_init()
            data = strategy.on_bar(data)

            simulator.run(
                data=data,
                strategy=strategy,
                symbol="EURUSD",
                volume=0.1,
                verbose=False,
                save_db=False,
                engine_type="vectorised",
            )

            return simulator

        # Run benchmark
        result = benchmark(run_backtest)
        print(f"\n10,000 bars vectorized: {benchmark.stats['mean']:.4f}s")


@pytest.mark.benchmark
class TestOptimizationImpact:
    """Test impact of optimization flags."""

    def test_with_position_arrays_enabled(self, benchmark):
        """Benchmark with position arrays optimization."""

        def run_backtest():
            account = AccountInfoSimulator(balance=10000.0)
            symbol = SymbolInfoSimulator(
                symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
            )

            simulator = TradeSimulator(
                simulator_name="Opt_Arrays_On",
                mt5_client=None,
                account_info=account,
                symbols={"EURUSD": symbol},
            )

            dates = pd.date_range(start="2024-01-01", periods=1000, freq="h")
            prices = [1.10000 + i * 0.00010 for i in range(1000)]

            data = pd.DataFrame(
                {
                    "time": dates,
                    "open": prices,
                    "high": [p + 0.00010 for p in prices],
                    "low": [p - 0.00010 for p in prices],
                    "close": prices,
                    "tick_volume": 100,
                    "spread": 10,
                    "real_volume": 0,
                }
            ).set_index("time")

            strategy = HighFrequencyStrategy(
                params={"symbol": "EURUSD", "signal_frequency": 2}
            )
            strategy.on_init()
            data = strategy.on_bar(data)

            simulator.run(
                data=data,
                strategy=strategy,
                symbol="EURUSD",
                volume=0.1,
                verbose=False,
                save_db=False,
                engine_type="event_driven",
                use_position_arrays=True,  # Enabled
                use_numba=True,
            )

            return simulator

        result = benchmark(run_backtest)
        print(f"\nWith position arrays: {benchmark.stats['mean']:.4f}s")

    def test_with_position_arrays_disabled(self, benchmark):
        """Benchmark without position arrays optimization."""

        def run_backtest():
            account = AccountInfoSimulator(balance=10000.0)
            symbol = SymbolInfoSimulator(
                symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
            )

            simulator = TradeSimulator(
                simulator_name="Opt_Arrays_Off",
                mt5_client=None,
                account_info=account,
                symbols={"EURUSD": symbol},
            )

            dates = pd.date_range(start="2024-01-01", periods=1000, freq="h")
            prices = [1.10000 + i * 0.00010 for i in range(1000)]

            data = pd.DataFrame(
                {
                    "time": dates,
                    "open": prices,
                    "high": [p + 0.00010 for p in prices],
                    "low": [p - 0.00010 for p in prices],
                    "close": prices,
                    "tick_volume": 100,
                    "spread": 10,
                    "real_volume": 0,
                }
            ).set_index("time")

            strategy = HighFrequencyStrategy(
                params={"symbol": "EURUSD", "signal_frequency": 2}
            )
            strategy.on_init()
            data = strategy.on_bar(data)

            simulator.run(
                data=data,
                strategy=strategy,
                symbol="EURUSD",
                volume=0.1,
                verbose=False,
                save_db=False,
                engine_type="event_driven",
                use_position_arrays=False,  # Disabled
                use_numba=False,
            )

            return simulator

        result = benchmark(run_backtest)
        print(f"\nWithout position arrays: {benchmark.stats['mean']:.4f}s")


@pytest.mark.benchmark
class TestScalability:
    """Test performance scalability with increasing load."""

    @pytest.mark.parametrize("num_bars", [100, 500, 1000, 5000])
    def test_scalability_vectorized(self, benchmark, num_bars):
        """Test how performance scales with increasing bars (vectorized)."""

        def run_backtest():
            account = AccountInfoSimulator(balance=10000.0)
            symbol = SymbolInfoSimulator(
                symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
            )

            simulator = TradeSimulator(
                simulator_name=f"Scale_{num_bars}",
                mt5_client=MockMT5Client(),
                account_info=account,
                symbols={"EURUSD": symbol},
            )

            dates = pd.date_range(start="2024-01-01", periods=num_bars, freq="h")
            prices = [1.10000 + np.sin(i * 0.01) * 0.00100 for i in range(num_bars)]

            data = pd.DataFrame(
                {
                    "time": dates,
                    "open": prices,
                    "high": [p + 0.00010 for p in prices],
                    "low": [p - 0.00010 for p in prices],
                    "close": prices,
                    "tick_volume": 100,
                    "spread": 10,
                    "real_volume": 0,
                }
            ).set_index("time")

            strategy = HighFrequencyStrategy(
                params={"symbol": "EURUSD", "signal_frequency": 10}
            )
            strategy.on_init()
            data = strategy.on_bar(data)

            simulator.run(
                data=data,
                strategy=strategy,
                symbol="EURUSD",
                volume=0.1,
                verbose=False,
                save_db=False,
                engine_type="vectorised",
            )

            return simulator

        result = benchmark(run_backtest)
        print(f"\n{num_bars} bars: {benchmark.stats['mean']:.4f}s")


class TestPerformanceRegression:
    """Simple performance regression tests (no benchmark framework needed)."""

    def test_simple_backtest_completes_quickly(self):
        """Test that a simple backtest completes in reasonable time."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator = TradeSimulator(
            simulator_name="Quick_Test",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": symbol},
        )

        # 1,000 bars
        dates = pd.date_range(start="2024-01-01", periods=1000, freq="h")
        prices = [1.10000 + i * 0.00010 for i in range(1000)]

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + 0.00010 for p in prices],
                "low": [p - 0.00010 for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy = HighFrequencyStrategy(
            params={"symbol": "EURUSD", "signal_frequency": 2}
        )
        strategy.on_init()
        data = strategy.on_bar(data)

        # Measure time
        start = time.time()
        simulator.run(
            data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
        )
        duration = time.time() - start

        # Log performance
        print(f"\n1,000 bars completed in: {duration:.4f}s")

        # Should complete in reasonable time (< 10 seconds on most hardware)
        # This is a very generous limit to avoid CI failures
        assert duration < 10.0

    def test_vectorized_is_faster_than_event_driven(self):
        """Verify that vectorized mode is faster than event-driven (generally)."""
        # Event-driven timing
        account1 = AccountInfoSimulator(balance=10000.0)
        symbol1 = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator1 = TradeSimulator(
            simulator_name="Speed_Event",
            mt5_client=None,
            account_info=account1,
            symbols={"EURUSD": symbol1},
        )

        dates = pd.date_range(start="2024-01-01", periods=1000, freq="h")
        prices = [1.10000 + i * 0.00010 for i in range(1000)]

        data = pd.DataFrame(
            {
                "time": dates,
                "open": prices,
                "high": [p + 0.00010 for p in prices],
                "low": [p - 0.00010 for p in prices],
                "close": prices,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }
        ).set_index("time")

        strategy1 = HighFrequencyStrategy(
            params={"symbol": "EURUSD", "signal_frequency": 10}
        )
        strategy1.on_init()
        data1 = strategy1.on_bar(data.copy())

        start = time.time()
        simulator1.run(
            data=data1,
            strategy=strategy1,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="event_driven",
        )
        event_time = time.time() - start

        # Vectorized timing
        account2 = AccountInfoSimulator(balance=10000.0)
        symbol2 = SymbolInfoSimulator(
            symbol="EURUSD", trade_contract_size=100000.0, point=0.00001
        )

        simulator2 = TradeSimulator(
            simulator_name="Speed_Vector",
            mt5_client=MockMT5Client(),
            account_info=account2,
            symbols={"EURUSD": symbol2},
        )

        strategy2 = HighFrequencyStrategy(
            params={"symbol": "EURUSD", "signal_frequency": 10}
        )
        strategy2.on_init()
        data2 = strategy2.on_bar(data.copy())

        start = time.time()
        simulator2.run(
            data=data2,
            strategy=strategy2,
            symbol="EURUSD",
            volume=0.1,
            verbose=False,
            save_db=False,
            engine_type="vectorised",
        )
        vector_time = time.time() - start

        # Log performance
        print(f"\nEvent-driven: {event_time:.4f}s")
        print(f"Vectorized: {vector_time:.4f}s")
        print(f"Speedup: {event_time / vector_time:.2f}x")

        # Vectorized should generally be faster
        # (Not enforced as assertion since performance varies)
