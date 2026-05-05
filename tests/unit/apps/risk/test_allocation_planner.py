from __future__ import annotations

import pandas as pd

from haruquant.risk import (
    AllocationPlanner,
    CorrelationPreference,
    GovernanceEngine,
    PortfolioRiskEngine,
    PortfolioStateEngine,
    RiskLimits,
)


def _bars(periods: int = 160, start: str = "2024-01-01", scale: float = 1.0) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    base = pd.Series(range(periods), index=idx, dtype=float)
    close = 1.10 + (base * 0.00030 * scale) + ((base % 7) * 0.00012 * scale)
    return pd.DataFrame(
        {
            "Close": close,
            "Open": close - 0.0002,
            "High": close + 0.0005,
            "Low": close - 0.0005,
            "Volume": [100 + i for i in range(periods)],
            "Spread": [1 + (i % 3) for i in range(periods)],
        },
        index=idx,
    )


def _build_state():
    return PortfolioStateEngine().build_state(
        account={"equity": 10000.0, "balance": 10000.0, "currency": "USD"},
        positions=[
            {"symbol": "EURUSD", "volume": 0.30, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.25, "type": "BUY"},
            {"symbol": "USDJPY", "volume": 0.35, "type": "SELL"},
        ],
        symbol_specs={
            "EURUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "GBPUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "USDJPY": {"trade_contract_size": 100000, "lots_step": 0.01},
        },
        market_data={
            "EURUSD": _bars(scale=1.0),
            "GBPUSD": _bars(scale=1.1),
            "USDJPY": _bars(scale=0.9),
        },
        limits=RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX"},
        timeframe="H1",
        as_of="2024-01-06T15:00:00",
    )


class _StateRiskAdapter:
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
        _ = symbol
        return abs(float(lots)) * 100.0

    def get_bars(self, symbol, timeframe, count=100, start_pos=0):
        _ = timeframe
        frame = self._state.markets[symbol].bars.copy()
        if start_pos > 0:
            frame = frame.iloc[start_pos:]
        if count is not None and count > 0:
            frame = frame.tail(int(count))
        return frame


def test_allocation_planner_returns_target_map_and_deltas():
    state = _build_state()
    governance_engine = GovernanceEngine(
        risk_engine=PortfolioRiskEngine(
            mt5_client=_StateRiskAdapter(state),
            timeframe="H1",
            start_pos=0,
            end_pos=160,
        ),
        limits=state.limits,
    )
    planner = AllocationPlanner(
        governance_engine,
        corr_pref=CorrelationPreference(target_corr=0.5, penalty_strength=1.5),
    )

    current = state.position_map
    target = planner.compute_target_lots(
        symbols=list(current.keys()),
        base_lots=current,
        budgets={"EURUSD": 0.50, "GBPUSD": 0.30, "USDJPY": 0.20},
    )
    deltas = planner.lots_to_deltas(current, target)

    assert set(target.keys()) == set(current.keys())
    assert set(deltas.keys()) == set(current.keys())
    for symbol in current:
        assert deltas[symbol] == target[symbol] - current[symbol]
