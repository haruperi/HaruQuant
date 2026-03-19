from __future__ import annotations

import pandas as pd

from apps.risk import PortfolioStateEngine, RiskLimits


def _bars(start: str = "2024-01-01", periods: int = 6) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    open_values = [1.10, 1.11, 1.12, 1.13, 1.14, 1.15][:periods]
    high_values = [1.11, 1.12, 1.13, 1.14, 1.15, 1.16][:periods]
    low_values = [1.09, 1.10, 1.11, 1.12, 1.13, 1.14][:periods]
    close_values = [1.105, 1.115, 1.125, 1.135, 1.145, 1.155][:periods]
    volume_values = [100, 110, 120, 130, 140, 150][:periods]
    spread_values = [1, 1, 1, 1, 1, 1][:periods]
    return pd.DataFrame(
        {
            "Open": open_values,
            "High": high_values,
            "Low": low_values,
            "Close": close_values,
            "Volume": volume_values,
            "Spread": spread_values,
        },
        index=idx,
    )


def test_build_state_normalizes_existing_style_inputs():
    engine = PortfolioStateEngine()

    state = engine.build_state(
        account={"equity": 10000.0, "balance": 9800.0, "currency": "USD"},
        positions={"EURUSD": 0.5, "XAUUSD": -0.2},
        symbol_specs={
            "EURUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "XAUUSD": {"trade_contract_size": 100, "lots_step": 0.01},
        },
        market_data={"EURUSD": _bars(), "XAUUSD": _bars()},
        limits=RiskLimits(),
        symbol_to_cluster={"EURUSD": "FOREX", "XAUUSD": "METALS"},
        timeframe="H1",
        as_of="2024-01-01T05:00:00Z",
    )

    assert not state.validation_summary.has_errors
    assert state.account.equity == 10000.0
    assert state.position_map == {"EURUSD": 0.5, "XAUUSD": -0.2}
    assert state.symbol_to_cluster["EURUSD"] == "FOREX"
    assert state.markets["EURUSD"].timeframe == "H1"
    assert state.exposures["EURUSD"] > 0
    assert state.exposures["XAUUSD"] < 0


def test_build_state_flags_missing_symbol_specs_and_market_data():
    engine = PortfolioStateEngine()

    state = engine.build_state(
        account={"equity": 10000.0},
        positions={"EURUSD": 0.5, "GBPUSD": 0.3},
        symbol_specs={"EURUSD": {"trade_contract_size": 100000}},
        market_data={"EURUSD": _bars()},
        timeframe="H1",
    )

    issue_codes = {issue.code for issue in state.validation_summary.issues}
    assert "symbol_spec_insufficient_risk_math" in issue_codes
    assert "market_data_missing" in issue_codes
    assert state.validation_summary.has_errors


def test_build_state_warns_when_market_coverage_is_unsynchronized():
    engine = PortfolioStateEngine()

    state = engine.build_state(
        account={"equity": 10000.0},
        positions={"EURUSD": 0.5, "GBPUSD": 0.3},
        symbol_specs={
            "EURUSD": {"trade_contract_size": 100000},
            "GBPUSD": {"trade_contract_size": 100000},
        },
        market_data={"EURUSD": _bars(periods=6), "GBPUSD": _bars(periods=4)},
        timeframe="H1",
    )

    issue_codes = {issue.code for issue in state.validation_summary.issues}
    assert "market_data_unsynchronized" in issue_codes
    assert not state.validation_summary.has_errors


class _DummyClient:
    def __init__(self, bars_by_symbol):
        self._bars_by_symbol = bars_by_symbol

    def get_bars(self, symbol: str, timeframe: str, count: int = 100, start_pos: int = 0):
        frame = self._bars_by_symbol.get(symbol, pd.DataFrame()).copy()
        if start_pos > 0:
            frame = frame.iloc[start_pos:]
        if count is not None and count > 0:
            frame = frame.tail(int(count))
        return frame


class _DummyEngine:
    def __init__(self, bars_by_symbol):
        self.client = _DummyClient(bars_by_symbol)

    def account_info(self):
        return {"equity": 10000.0, "balance": 10000.0, "currency": "USD"}

    def positions_get(self):
        return [{"symbol": "EURUSD", "volume": 0.5, "type": "BUY"}]

    def symbol_info(self, symbol: str):
        return {
            "name": symbol,
            "trade_contract_size": 100000,
            "lots_min": 0.01,
            "lots_max": 100.0,
            "lots_step": 0.01,
        }


def test_build_state_from_engine_trims_market_data_by_as_of_timestamp():
    bars = _bars()
    engine = _DummyEngine({"EURUSD": bars})
    state_engine = PortfolioStateEngine()

    state = state_engine.build_state_from_engine(
        engine=engine,
        symbols=["EURUSD"],
        timeframe="H1",
        count=6,
        as_of="2024-01-01T03:00:00",
        limits=RiskLimits(),
    )

    assert not state.validation_summary.has_errors
    assert state.as_of == "2024-01-01T03:00:00"
    assert state.markets["EURUSD"].row_count == 4
    assert state.markets["EURUSD"].last_close == 1.135


def test_build_state_from_engine_trims_market_data_by_bar_index():
    bars = _bars()
    engine = _DummyEngine({"EURUSD": bars})
    state_engine = PortfolioStateEngine()

    state = state_engine.build_state_from_engine(
        engine=engine,
        symbols=["EURUSD"],
        timeframe="H1",
        count=6,
        bar_index=2,
        limits=RiskLimits(),
    )

    assert not state.validation_summary.has_errors
    assert state.markets["EURUSD"].row_count == 3
    assert state.markets["EURUSD"].last_close == 1.125
