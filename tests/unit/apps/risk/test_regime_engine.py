from __future__ import annotations

import pandas as pd

from apps.risk import PortfolioStateEngine, RiskLimits, RiskSnapshotEngine
from apps.risk.regimes import RegimeEngine, RegimeState, RiskRegimeDetector


def _bars(periods: int = 120, start: str = "2024-01-01", scale: float = 1.0) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    base = pd.Series(range(periods), index=idx, dtype=float)
    close = 1.10 + (base * 0.0004 * scale) + ((base % 6) * 0.00015 * scale)
    return pd.DataFrame(
        {
            "Close": close,
            "Open": close - 0.0002,
            "High": close + 0.0005,
            "Low": close - 0.0005,
            "Volume": [100 + i for i in range(periods)],
            "Spread": [1 + (i % 2) for i in range(periods)],
        },
        index=idx,
    )


def _build_state() -> object:
    equity_curve = pd.Series(
        [10000.0, 10100.0, 10050.0, 9950.0, 9850.0, 9800.0],
        index=pd.date_range("2024-01-01", periods=6, freq="h"),
        dtype=float,
    )
    return PortfolioStateEngine().build_state(
        account={
            "equity": 9800.0,
            "balance": 10000.0,
            "free_margin": 8300.0,
            "margin_used": 1700.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.5, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.4, "type": "BUY"},
            {"symbol": "USDJPY", "volume": 0.3, "type": "SELL"},
        ],
        symbol_specs={
            "EURUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "GBPUSD": {"trade_contract_size": 100000, "lots_step": 0.01},
            "USDJPY": {"trade_contract_size": 100000, "lots_step": 0.01},
        },
        market_data={
            "EURUSD": _bars(scale=1.0),
            "GBPUSD": _bars(scale=1.0),
            "USDJPY": _bars(scale=1.0),
        },
        limits=RiskLimits(vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX"},
        timeframe="H1",
        as_of="2024-01-05T23:00:00",
        metadata={"equity_curve": equity_curve},
    )


def test_legacy_risk_regime_detector_interface_still_returns_normalized_state():
    returns_df = pd.DataFrame(
        {
            "EURUSD": [0.001] * 80,
            "GBPUSD": [0.001] * 80,
        }
    )
    detector = RiskRegimeDetector()
    regime = detector.detect(returns_df)

    assert regime.name in {"NORMAL", "STRESS"}
    assert regime.family == "crisis"


def test_regime_engine_builds_regime_report_and_snapshot_summary():
    state = _build_state()
    engine = RegimeEngine()
    report = engine.evaluate_state(state, previous=RegimeState(name="NORMAL"))

    assert report.current.name in {"NORMAL", "STRESS"}
    assert report.crisis.family == "crisis"
    assert report.market.family == "market"
    assert report.volatility.family == "volatility"
    assert report.liquidity.family == "liquidity"

    snapshot = RiskSnapshotEngine().build_snapshot(state, shared={"previous_regime": RegimeState(name="NORMAL")})

    assert snapshot.regime_state is not None
    assert snapshot.regime_report is not None
    assert "regime_name" in snapshot.summary
    assert "regime_confidence" in snapshot.summary
    assert isinstance(snapshot.summary["regime_signals_triggered"], list)
