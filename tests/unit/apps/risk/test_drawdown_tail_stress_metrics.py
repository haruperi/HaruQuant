from __future__ import annotations

import pandas as pd

from apps.risk import PortfolioStateEngine, RiskLimits, RiskSnapshotEngine


def _bars(periods: int = 100, start: str = "2024-01-01", scale: float = 1.0) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    base = pd.Series(range(periods), index=idx, dtype=float)
    close = 1.10 + (base * 0.0004 * scale) + ((base % 5) * 0.00015 * scale)
    return pd.DataFrame(
        {
            "Close": close,
            "Open": close - 0.0002,
            "High": close + 0.0005,
            "Low": close - 0.0005,
            "Volume": [100 + i for i in range(periods)],
            "Spread": [1 for _ in range(periods)],
        },
        index=idx,
    )


def _equity_curve() -> pd.Series:
    values = [
        10000.0,
        10150.0,
        10080.0,
        9980.0,
        9870.0,
        9925.0,
        10010.0,
    ]
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="h"), dtype=float)


def _build_state():
    return PortfolioStateEngine().build_state(
        account={
            "equity": 10010.0,
            "balance": 10000.0,
            "free_margin": 8200.0,
            "margin_used": 1800.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.5, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.3, "type": "BUY"},
            {"symbol": "USDJPY", "volume": 0.2, "type": "SELL"},
        ],
        symbol_specs={
            "EURUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "GBPUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "USDJPY": {"trade_contract_size": 100000, "lots_step": 0.01},
        },
        market_data={
            "EURUSD": _bars(scale=1.0),
            "GBPUSD": _bars(scale=1.1),
            "USDJPY": _bars(scale=0.8),
        },
        limits=RiskLimits(vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX"},
        timeframe="H1",
        as_of="2024-01-05T03:00:00",
        metadata={"equity_curve": _equity_curve()},
    )


def _row(snapshot, family: str, metric_key: str, scope: str = "portfolio", scope_key: str | None = None):
    for row in snapshot.metric_rows:
        if row.family != family or row.metric_key != metric_key or row.scope != scope:
            continue
        if scope_key is not None and row.scope_key != scope_key:
            continue
        return row
    raise AssertionError(f"Missing row family={family} key={metric_key} scope={scope} scope_key={scope_key}")


def test_snapshot_includes_drawdown_tail_and_stress_metrics():
    snapshot = RiskSnapshotEngine().build_snapshot(_build_state())

    assert _row(snapshot, "drawdown_risk", "current_drawdown").numeric_value < 0.0
    assert _row(snapshot, "drawdown_risk", "max_drawdown").numeric_value < 0.0
    assert _row(snapshot, "tail_risk", "portfolio_var_method").text_value == "parametric_normal"
    assert _row(snapshot, "tail_risk", "portfolio_cvar_parametric").numeric_value > 0.0
    assert _row(snapshot, "stress_risk", "scenario_loss", scope="scenario", scope_key="volatility_shock").numeric_value > 0.0
    assert _row(snapshot, "stress_risk", "worst_scenario_name").text_value is not None


def test_snapshot_summary_surfaces_phase5_metrics():
    snapshot = RiskSnapshotEngine().build_snapshot(_build_state())

    assert snapshot.summary["current_drawdown"] < 0.0
    assert snapshot.summary["max_drawdown"] < 0.0
    assert snapshot.summary["portfolio_var_parametric"] > 0.0
    assert snapshot.summary["worst_scenario_loss"] > 0.0
    assert isinstance(snapshot.summary["worst_scenario_name"], str)
