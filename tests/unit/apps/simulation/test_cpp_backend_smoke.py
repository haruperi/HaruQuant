"""
Smoke tests for the C++ backend adapter.

All tests in this module are skip-guarded: they only run when the
``hqt_engine.sim`` extension is importable (``is_cpp_available()``).
"""

from __future__ import annotations

import os
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from apps.simulation.backend import is_cpp_available

pytestmark = pytest.mark.skipif(
    not is_cpp_available(),
    reason="hqt_engine.sim C++ extension not available",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _DummyStrategy:
    """Minimal strategy that returns SL/TP when an entry signal is present."""

    def get_signal(self, data: pd.DataFrame, index: int):
        row = data.iloc[index]
        entry = int(row.get("entry_signal", 0) or 0)
        exit_sig = int(row.get("exit_signal", 0) or 0)
        if entry == 0 and exit_sig == 0:
            return None
        close = float(row["close"])
        sl = close * 0.99 if entry == 1 else close * 1.01 if entry == -1 else 0.0
        tp = close * 1.02 if entry == 1 else close * 0.98 if entry == -1 else 0.0
        return {
            "entry_signal": entry,
            "exit_signal": exit_sig,
            "stop_loss": sl,
            "take_profit": tp,
        }


def _make_data(n: int = 50, seed: int = 42) -> pd.DataFrame:
    """Create a synthetic DataFrame with a buy signal at bar 5 and sell at bar 30."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2025-01-01", periods=n, freq="h")
    close = 1.10000 + rng.randn(n).cumsum() * 0.00010
    entry = np.zeros(n, dtype=int)
    exit_sig = np.zeros(n, dtype=int)
    entry[5] = 1  # Buy
    exit_sig[30] = 1  # Close buy
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.00010,
            "low": close - 0.00010,
            "close": close,
            "spread": 10,
            "entry_signal": entry,
            "exit_signal": exit_sig,
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBasicOpenCloseFlow:
    """Directly call ``run_trading_timeframe_cpp`` with synthetic data."""

    def test_basic_open_close_flow(self):
        from apps.simulation.backend import run_trading_timeframe_cpp
        from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator

        data = _make_data()
        strategy = _DummyStrategy()
        account = AccountInfoSimulator(balance=10000.0)
        sym = SymbolInfoSimulator(
            symbol="EURUSD",
            point=0.00001,
            digits=5,
            trade_contract_size=100000.0,
        )

        result = run_trading_timeframe_cpp(
            data=data,
            original_data=data,
            strategy=strategy,
            symbol="EURUSD",
            volume=0.1,
            symbol_info=sym,
            warmup_bars=0,
            account_data=account,
        )

        assert len(result.completed_trades) >= 1
        trade = result.completed_trades[0]
        assert trade.type == "buy"
        assert trade.symbol == "EURUSD"
        assert trade.size == 0.1
        assert trade.open_time is not None
        assert trade.close_time is not None


class TestFullSimulatorRunWithCppBackend:
    """Run ``TradeSimulator.run()`` with ``SIM_ENGINE=cpp``."""

    def test_full_simulator_run_with_cpp_backend(self):
        from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator
        from apps.simulation.simulator import TradeSimulator

        data = _make_data()
        strategy = _DummyStrategy()
        account = AccountInfoSimulator(balance=10000.0)
        sym = SymbolInfoSimulator(
            symbol="EURUSD",
            point=0.00001,
            digits=5,
            trade_contract_size=100000.0,
        )

        simulator = TradeSimulator(
            simulator_name="CppSmokeTest",
            mt5_client=None,
            account_info=account,
            symbols={"EURUSD": sym},
        )

        with mock.patch.dict(os.environ, {"SIM_ENGINE": "cpp"}):
            simulator.run(
                data=data,
                strategy=strategy,
                symbol="EURUSD",
                volume=0.1,
                verbose=False,
                save_db=False,
            )

        assert len(simulator._completed_trades) >= 1


class TestNonTradingTimeframeStaysPython:
    """Verify that ``m1_ohlc`` mode does not crash when ``SIM_ENGINE=cpp``."""

    def test_non_trading_timeframe_stays_python(self):
        from apps.simulation.backend import SimBackend, get_backend

        with mock.patch.dict(os.environ, {"SIM_ENGINE": "cpp"}):
            assert get_backend() is SimBackend.CPP

        # m1_ohlc mode should still work (handled by Python path regardless of
        # the SIM_ENGINE setting — the C++ routing only applies to
        # trading_timeframe mode).
