from __future__ import annotations

import pandas as pd

from apps.risk import (
    GovernanceEngine,
    PortfolioRiskEngine,
    PortfolioStateEngine,
    RiskLimits,
    RiskSnapshotEngine,
)


def _bars(periods: int = 80, start: str = "2024-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    base = pd.Series(range(periods), index=idx, dtype=float)
    close = 1.10 + (base * 0.0005) + (base % 5) * 0.0001
    return pd.DataFrame(
        {
            "Close": close,
            "Open": close - 0.0003,
            "High": close + 0.0006,
            "Low": close - 0.0006,
            "Volume": [100 + i for i in range(periods)],
            "Spread": [1 for _ in range(periods)],
        },
        index=idx,
    )


def _build_state():
    state_engine = PortfolioStateEngine()
    return state_engine.build_state(
        account={
            "equity": 10000.0,
            "balance": 10000.0,
            "free_margin": 8500.0,
            "margin_used": 1500.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.5, "type": "BUY", "strategy_id": "trend"},
            {"symbol": "GBPUSD", "volume": 0.3, "type": "BUY", "strategy_id": "trend"},
            {"symbol": "USDJPY", "volume": 0.2, "type": "SELL", "strategy_id": "mean_reversion"},
        ],
        symbol_specs={
            "EURUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "GBPUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "USDJPY": {"trade_contract_size": 100000, "lots_step": 0.01},
        },
        market_data={
            "EURUSD": _bars(),
            "GBPUSD": _bars(),
            "USDJPY": _bars(),
        },
        limits=RiskLimits(vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX"},
        timeframe="H1",
        as_of="2024-01-04T07:00:00",
    )


def _snapshot_value(snapshot, key: str):
    for row in snapshot.metric_rows:
        if row.scope == "portfolio" and row.metric_key == key:
            return row.numeric_value
    raise AssertionError(f"Missing metric {key}")


class _DummyRiskAdapter:
    def __init__(self, state):
        self._state = state

    def get_account_equity(self):
        return float(self._state.account.equity)

    def get_symbol_info(self, symbol):
        spec = self._state.symbols[symbol]
        return {
            "trade_contract_size": spec.contract_size,
            "trade_tick_value": spec.tick_value,
            "trade_tick_size": spec.tick_size,
        }

    def get_margin_required(self, symbol, lots):
        return abs(float(lots)) * 500.0

    def get_bars(self, symbol, timeframe, count=100, start_pos=0):
        bars = self._state.markets[symbol].bars.copy()
        if "Close" in bars.columns and "close" not in bars.columns:
            bars = bars.rename(columns={"Close": "close"})
        if start_pos > 0:
            bars = bars.iloc[start_pos:]
        if count is not None and count > 0:
            bars = bars.tail(int(count))
        return bars


def test_snapshot_engine_builds_useful_top_level_summary():
    state = _build_state()
    engine = RiskSnapshotEngine()

    snapshot = engine.build_snapshot(state)

    assert snapshot.summary["metric_count"] > 0
    assert snapshot.summary["has_validation_errors"] is False
    assert snapshot.summary["gross_exposure"] > 0
    assert snapshot.summary["portfolio_var"] > 0
    assert snapshot.summary["portfolio_es"] > snapshot.summary["portfolio_var"]


def test_snapshot_engine_matches_shared_portfolio_risk_engine_var_es_math():
    state = _build_state()
    snapshot_engine = RiskSnapshotEngine()
    snapshot = snapshot_engine.build_snapshot(state)

    governance_engine = GovernanceEngine(
        risk_engine=PortfolioRiskEngine(
            mt5_client=_DummyRiskAdapter(state),
            timeframe="H1",
            start_pos=0,
            end_pos=80,
        ),
        limits=state.limits or RiskLimits(),
    )
    gov_var, gov_es, _, _ = governance_engine.risk_engine.compute_portfolio_risk(
        state.position_map,
        float(state.account.equity),
        state.limits or RiskLimits(),
    )

    assert round(float(_snapshot_value(snapshot, "portfolio_var")), 6) == round(float(gov_var), 6)
    assert round(float(_snapshot_value(snapshot, "portfolio_es")), 6) == round(float(gov_es), 6)
