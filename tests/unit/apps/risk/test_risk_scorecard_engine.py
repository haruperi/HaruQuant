from __future__ import annotations

import pandas as pd

from backend.services.risk_engine import PortfolioStateEngine, RiskLimits, RiskScorecardEngine, RiskSnapshotEngine


def _bars(periods: int = 120, start: str = "2024-01-01", scale: float = 1.0) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    base = pd.Series(range(periods), index=idx, dtype=float)
    close = 1.10 + (base * 0.00035 * scale) + ((base % 5) * 0.00015 * scale)
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


def _equity_curve(drawdown_scale: float = 1.0) -> pd.Series:
    values = [10000.0, 10120.0, 10070.0, 9970.0, 9900.0 - (120.0 * drawdown_scale), 9950.0, 10000.0]
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="h"), dtype=float)


def _build_state(lots_scale: float = 1.0, drawdown_scale: float = 1.0):
    return PortfolioStateEngine().build_state(
        account={
            "equity": 10000.0,
            "balance": 10000.0,
            "free_margin": 8500.0,
            "margin_used": 1500.0 * lots_scale,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.20 * lots_scale, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.15 * lots_scale, "type": "BUY"},
            {"symbol": "USDJPY", "volume": 0.10 * lots_scale, "type": "SELL"},
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
        limits=RiskLimits(vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX"},
        timeframe="H1",
        as_of="2024-01-05T23:00:00",
        metadata={"equity_curve": _equity_curve(drawdown_scale)},
    )


def _score(scorecard, score_key: str) -> float:
    for row in scorecard.score_rows:
        if row.score_key == score_key:
            return float(row.score_value)
    raise AssertionError(f"Missing score {score_key}")


def test_scorecard_engine_builds_explainable_scores():
    snapshot = RiskSnapshotEngine().build_snapshot(_build_state())
    scorecard = RiskScorecardEngine().build_scorecard(snapshot)

    assert scorecard.summary["score_count"] > 0
    assert _score(scorecard, "portfolio_health_score") >= 0.0
    assert _score(scorecard, "concentration_score") >= 0.0
    assert _score(scorecard, "overall_risk_quality_score") >= 0.0
    overall = next(row for row in scorecard.score_rows if row.score_key == "overall_risk_quality_score")
    assert overall.explanation
    assert overall.confidence_label in {"low", "medium", "high"}


def test_fragile_snapshot_scores_worse_than_safer_snapshot():
    snapshot_safe = RiskSnapshotEngine().build_snapshot(_build_state(lots_scale=0.8, drawdown_scale=0.5))
    snapshot_fragile = RiskSnapshotEngine().build_snapshot(_build_state(lots_scale=2.5, drawdown_scale=2.0))

    scorecard_safe = RiskScorecardEngine().build_scorecard(snapshot_safe)
    scorecard_fragile = RiskScorecardEngine().build_scorecard(snapshot_fragile)

    assert _score(scorecard_safe, "overall_risk_quality_score") > _score(scorecard_fragile, "overall_risk_quality_score")
    assert _score(scorecard_safe, "margin_safety_score") > _score(scorecard_fragile, "margin_safety_score")
