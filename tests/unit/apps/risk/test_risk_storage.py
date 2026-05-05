from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from services.risk import (
    PortfolioStateEngine,
    RecommendationEngine,
    RiskLimits,
    RiskScorecardEngine,
    RiskSnapshotEngine,
)
from services.risk.simulation import ReplayFrame, build_cockpit_state
from services.risk.storage import RiskRepository, RiskScenarioStore, RiskSnapshotStore
from services.risk.scenarios import ScenarioResult
from backend.data.database.sqlite import SQLiteDatabase


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


def _equity_curve() -> pd.Series:
    return pd.Series(
        [10000.0, 10120.0, 10070.0, 9980.0, 9890.0, 9950.0, 10010.0],
        index=pd.date_range("2024-01-01", periods=7, freq="h"),
        dtype=float,
    )


def _build_state():
    return PortfolioStateEngine().build_state(
        account={
            "equity": 10000.0,
            "balance": 10000.0,
            "free_margin": 8400.0,
            "margin_used": 1600.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.35, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.12, "type": "BUY"},
            {"symbol": "USDJPY", "volume": 0.08, "type": "SELL"},
        ],
        symbol_specs={
            "EURUSD": {"trade_contract_size": 100000, "lots_step": 0.01, "volume_min": 0.01},
            "GBPUSD": {"trade_contract_size": 100000, "lots_step": 0.01, "volume_min": 0.01},
            "USDJPY": {"trade_contract_size": 100000, "lots_step": 0.01, "volume_min": 0.01},
            "XAUUSD": {"trade_contract_size": 100, "lots_step": 0.01, "volume_min": 0.01},
        },
        market_data={
            "EURUSD": _bars(scale=1.0),
            "GBPUSD": _bars(scale=1.1),
            "USDJPY": _bars(scale=0.9),
            "XAUUSD": _bars(scale=2.4),
        },
        limits=RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={
            "EURUSD": "FOREX",
            "GBPUSD": "FOREX",
            "USDJPY": "FOREX",
            "XAUUSD": "METALS",
        },
        timeframe="H1",
        as_of="2024-01-06T15:00:00",
        metadata={"equity_curve": _equity_curve()},
    )


def test_snapshot_store_round_trips_snapshot_scorecard_and_recommendations(tmp_path):
    db = SQLiteDatabase(db_path=str(tmp_path / "risk_storage.db"))
    assert db.initialize_database()

    state = _build_state()
    snapshot = RiskSnapshotEngine().build_snapshot(state)
    scorecard = RiskScorecardEngine().build_scorecard(snapshot)
    recommendations = RecommendationEngine().build_recommendations(
        state,
        snapshot=snapshot,
        scorecard=scorecard,
        candidate_symbols=["XAUUSD"],
        hedge_symbols=["USDJPY", "XAUUSD"],
        max_recommendations=5,
    )

    store = RiskSnapshotStore(RiskRepository(db))
    run_id = store.create_run(label="phase10-test", source="unit-test", context={"phase": 10})
    snapshot_id = store.store_snapshot_bundle(
        run_id=run_id,
        snapshot=snapshot,
        scorecard=scorecard,
        recommendations=recommendations,
    )
    loaded = store.load_snapshot_bundle(snapshot_id)

    assert loaded["snapshot"]["run_id"] == run_id
    assert loaded["snapshot"]["summary_json"]["portfolio_var"] == snapshot.summary["portfolio_var"]
    assert len(loaded["metric_rows"]) == len(snapshot.metric_rows)
    assert len(loaded["score_rows"]) == len(scorecard.score_rows)
    assert len(loaded["policy_events"]) == len(snapshot.policy_events)
    assert len(loaded["recommendations"]) == len(recommendations.recommendations)
    assert len(loaded["scenarios"]) > 0


def test_scenario_store_and_replay_frames_are_reloadable(tmp_path):
    db = SQLiteDatabase(db_path=str(tmp_path / "risk_replay_storage.db"))
    assert db.initialize_database()

    state = _build_state()
    snapshot = RiskSnapshotEngine().build_snapshot(state)
    scorecard = RiskScorecardEngine().build_scorecard(snapshot)
    recommendations = RecommendationEngine().build_recommendations(
        state,
        snapshot=snapshot,
        scorecard=scorecard,
        candidate_symbols=["XAUUSD"],
        hedge_symbols=["USDJPY"],
        max_recommendations=3,
    )

    frame = ReplayFrame(
        frame_index=0,
        timestamp=snapshot.summary["as_of"],
        capture_timestamp=datetime.now(UTC).isoformat(),
        state=state,
        snapshot=snapshot,
        scorecard=scorecard,
        recommendations=recommendations,
        cockpit_state=None,
        context={"mode": "unit-test"},
    )
    cockpit = build_cockpit_state(frame)
    frame = ReplayFrame(
        frame_index=frame.frame_index,
        timestamp=frame.timestamp,
        capture_timestamp=frame.capture_timestamp,
        state=frame.state,
        snapshot=frame.snapshot,
        scorecard=frame.scorecard,
        recommendations=frame.recommendations,
        cockpit_state=cockpit,
        context=frame.context,
    )

    store = RiskSnapshotStore(RiskRepository(db))
    run_id = store.create_run(label="phase10-replay", source="unit-test")
    snapshot_id = store.store_snapshot_bundle(run_id=run_id, snapshot=snapshot, scorecard=scorecard)
    store.store_replay_frame(run_id=run_id, frame=frame, snapshot_id=snapshot_id)

    scenario_store = RiskScenarioStore(RiskRepository(db))
    scenario_store.store(
        snapshot_id=snapshot_id,
        scenarios=[
            ScenarioResult(
                name="manual_liquidity_crunch",
                loss=250.0,
                stressed_var=175.0,
                stressed_es=220.0,
                context={"source": "manual-test"},
            )
        ],
    )

    loaded = store.load_snapshot_bundle(snapshot_id)
    replay_frames = store.load_replay_frames(run_id)

    assert any(item["scenario_name"] == "manual_liquidity_crunch" for item in loaded["scenarios"])
    assert len(replay_frames) == 1
    assert replay_frames[0]["frame_index"] == 0
    assert replay_frames[0]["cockpit_payload_json"]["governance"]["status"] == snapshot.summary["compliance_state"]
