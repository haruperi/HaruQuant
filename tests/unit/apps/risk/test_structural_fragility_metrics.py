from __future__ import annotations

import pandas as pd

from services.risk import PortfolioStateEngine, RiskLimits, RiskSnapshotEngine


def _bars(
    periods: int = 100,
    start: str = "2024-01-01",
    drift: float = 0.0004,
    scale: float = 1.0,
) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    base = pd.Series(range(periods), index=idx, dtype=float)
    wave = ((base % 7) - 3) * 0.00015 * scale
    close = 1.10 + (base * drift * scale) + wave
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


def _build_state():
    return PortfolioStateEngine().build_state(
        account={
            "equity": 12000.0,
            "balance": 12000.0,
            "free_margin": 9600.0,
            "margin_used": 2400.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.5, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.4, "type": "BUY"},
            {"symbol": "USDJPY", "volume": 0.3, "type": "SELL"},
            {"symbol": "XAUUSD", "volume": 0.1, "type": "BUY"},
        ],
        symbol_specs={
            "EURUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "GBPUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "USDJPY": {"trade_contract_size": 100000, "lots_step": 0.01},
            "XAUUSD": {"trade_contract_size": 100, "lots_step": 0.01},
        },
        market_data={
            "EURUSD": _bars(scale=1.0),
            "GBPUSD": _bars(scale=1.1),
            "USDJPY": _bars(scale=0.8),
            "XAUUSD": _bars(drift=0.8, scale=3.5),
        },
        limits=RiskLimits(vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={
            "EURUSD": "FOREX",
            "GBPUSD": "FOREX",
            "USDJPY": "FOREX",
            "XAUUSD": "METALS",
        },
        timeframe="H1",
        as_of="2024-01-05T03:00:00",
    )


def _row(snapshot, family: str, metric_key: str, scope: str = "portfolio", scope_key: str | None = None):
    for row in snapshot.metric_rows:
        if row.family != family or row.metric_key != metric_key or row.scope != scope:
            continue
        if scope_key is not None and row.scope_key != scope_key:
            continue
        return row
    raise AssertionError(f"Missing row family={family} key={metric_key} scope={scope} scope_key={scope_key}")


def test_snapshot_includes_phase4_structural_fragility_metrics():
    snapshot = RiskSnapshotEngine().build_snapshot(_build_state())

    assert _row(snapshot, "volatility_risk", "portfolio_realized_volatility").numeric_value > 0.0
    assert _row(snapshot, "volatility_risk", "portfolio_vol_shock_loss_estimate").numeric_value > 0.0
    assert _row(snapshot, "correlation_risk", "average_pair_correlation").numeric_value is not None
    assert _row(snapshot, "correlation_risk", "max_pair_correlation").numeric_value is not None
    assert _row(snapshot, "concentration", "hidden_overlap_score").numeric_value is not None
    assert _row(snapshot, "concentration", "effective_independent_bets").numeric_value > 0.0
    assert _row(snapshot, "concentration", "diversification_ratio").numeric_value >= 0.0


def test_snapshot_summary_surfaces_top_level_phase4_metrics():
    snapshot = RiskSnapshotEngine().build_snapshot(_build_state())

    assert snapshot.summary["portfolio_realized_volatility"] > 0.0
    assert snapshot.summary["portfolio_vol_shock_loss_estimate"] > 0.0
    assert "average_pair_correlation" in snapshot.summary
    assert "effective_independent_bets" in snapshot.summary
    assert "diversification_ratio" in snapshot.summary
