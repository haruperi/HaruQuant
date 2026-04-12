"""
Example 18: Storage and Snapshot Infrastructure

Type: live-broker dependent manual demo

Phase 10 task-by-task walkthrough using the actual HaruQuant stack:
1. create a risk run
2. store a normalized snapshot
3. store a scorecard
4. store recommendations
5. store a replay frame summary
6. load persisted artifacts back

Run:
    python backend/scripts/examples/risk/10_storage_and_snapshot_store.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import pandas as pd

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from backend.services.risk_engine import (
    PortfolioStateEngine,
    RecommendationEngine,
    RiskLimits,
    RiskScorecardEngine,
    RiskSnapshotEngine,
)
from backend.services.risk_engine.simulation import ReplayFrame, build_cockpit_state
from backend.services.risk_engine.storage import RiskRepository, RiskSnapshotStore
from backend.data.database.sqlite import SQLiteDatabase
from backend.services.simulation.engine import Engine`nfrom backend.services.execution.trade import Trade`nfrom backend.services.execution import core


TIMEFRAME = "H1"
BAR_COUNT = 240
SYMBOLS = ["EURUSD", "GBPUSD", "XAUUSD"]
SYMBOL_TO_CLUSTER = {
    "EURUSD": "FOREX",
    "GBPUSD": "FOREX",
    "XAUUSD": "METALS",
}
BASE_LIMITS = RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, vol_lookback=20, corr_lookback=60)


def print_example_header(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def mutable_sim_symbol(engine: Engine, symbol_name: str):
    for idx, symbol_row in enumerate(engine.state.trading_symbols):
        name = str(getattr(symbol_row, "name", "") or "")
        if name != symbol_name:
            continue
        if isinstance(symbol_row, core.SymbolInfo):
            return symbol_row
        mutable = core.SymbolInfo(engine._to_dict(symbol_row))
        engine.state.trading_symbols[idx] = mutable
        return mutable
    return None


def seed_sim_account(engine: Engine) -> None:
    account = engine.account_info()
    account["login"] = 123456
    account["server"] = "Backtest Simulation Server"
    account["company"] = "HaruQuant"
    account["balance"] = 10000.0
    account["credit"] = 0.0
    account["profit"] = 0.0
    account["equity"] = 10000.0
    account["margin"] = 0.0
    account["margin_free"] = 10000.0
    account["margin_level"] = 0.0
    account["commission"] = 7.0
    account["leverage"] = 400


def round_volume(symbol_info, raw_volume: float) -> float:
    volume_min = float(getattr(symbol_info, "volume_min", 0.01) or 0.01)
    volume_max = float(getattr(symbol_info, "volume_max", 100.0) or 100.0)
    volume_step = float(getattr(symbol_info, "volume_step", 0.01) or 0.01)
    volume = max(volume_min, min(raw_volume, volume_max))
    if volume_step > 0:
        volume = round(volume / volume_step) * volume_step
    return float(max(volume, volume_min))


def prepare_symbol(engine: Engine, symbol: str, latest_close: float):
    raw_symbol = engine.client.symbol_info(symbol)
    if raw_symbol is None:
        return None
    if engine.symbol_info(symbol) is None:
        engine.state.trading_symbols.append(raw_symbol)
    mutable = mutable_sim_symbol(engine, symbol)
    if mutable is None:
        return None
    point = float(getattr(mutable, "point", 0.0001) or 0.0001)
    spread_points = float(getattr(mutable, "spread", 2.0) or 2.0)
    spread_value = point * max(spread_points, 1.0)
    mutable.bid = float(latest_close)
    mutable.ask = float(latest_close + spread_value)
    mutable.last = float(latest_close)
    return mutable


def synthetic_equity_curve() -> pd.Series:
    values = [10000.0, 10080.0, 10020.0, 9940.0, 9880.0, 9910.0, 9975.0]
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="h"), dtype=float)


class ExampleContext:
    def __init__(self):
        self.engine = Engine(backend="sim")
        seed_sim_account(self.engine)
        self.market_data = {}
        self.state = None
        self.snapshot = None
        self.scorecard = None
        self.recommendations = None
        self.frame = None
        self.db_dir = os.path.join(repo_root, "build", "phase10_storage_example")
        os.makedirs(self.db_dir, exist_ok=True)
        db_name = f"risk_snapshot_example_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.db"
        self.db_path = os.path.join(self.db_dir, db_name)
        self.db = SQLiteDatabase(db_path=self.db_path)
        self.repository = RiskRepository(self.db)
        self.store = RiskSnapshotStore(self.repository)
        self.run_id = None
        self.snapshot_id = None

    def setup(self) -> None:
        print(f"Initializing SQLite database: {self.db_path}")
        self.db.initialize_database()

        print("Loading real historical bars from connected client...")
        for symbol in SYMBOLS:
            bars = self.engine.client.get_bars(symbol=symbol, timeframe=TIMEFRAME, count=BAR_COUNT, start_pos=0)
            if bars is None or bars.empty:
                print(f"  {symbol}: no data available, skipped")
                continue
            self.market_data[symbol] = bars.copy()
            close_col = "close" if "close" in bars.columns else "Close"
            latest_close = float(bars[close_col].iloc[-1])
            prepared = prepare_symbol(self.engine, symbol, latest_close)
            if prepared is None:
                print(f"  {symbol}: symbol info unavailable, skipped")
                continue
            print(f"  {symbol}: loaded {len(bars)} bars, latest_close={latest_close:.5f}")

        self.open_positions()
        latest_ts = max(df.index[-1] for df in self.market_data.values() if not df.empty)
        self.state = PortfolioStateEngine().build_state_from_engine(
            engine=self.engine,
            symbols=[symbol for symbol in SYMBOLS if symbol in self.market_data],
            timeframe=TIMEFRAME,
            count=BAR_COUNT,
            as_of=pd.Timestamp(latest_ts).isoformat(),
            limits=BASE_LIMITS,
            symbol_to_cluster=SYMBOL_TO_CLUSTER,
            metadata={
                "source": "phase10_storage_example",
                "backend": "sim",
                "example_generated_at": datetime.now(UTC).isoformat(),
                "equity_curve": synthetic_equity_curve(),
            },
        )
        self.snapshot = RiskSnapshotEngine().build_snapshot(self.state)
        self.scorecard = RiskScorecardEngine().build_scorecard(self.snapshot)
        self.recommendations = RecommendationEngine().build_recommendations(
            self.state,
            snapshot=self.snapshot,
            scorecard=self.scorecard,
            candidate_symbols=SYMBOLS,
            hedge_symbols=SYMBOLS,
            max_recommendations=5,
        )
        base_frame = ReplayFrame(
            frame_index=0,
            timestamp=self.snapshot.summary["as_of"],
            capture_timestamp=datetime.now(UTC).isoformat(),
            state=self.state,
            snapshot=self.snapshot,
            scorecard=self.scorecard,
            recommendations=self.recommendations,
            cockpit_state=None,
            context={"source": "phase10_storage_example"},
        )
        cockpit = build_cockpit_state(base_frame)
        self.frame = ReplayFrame(
            frame_index=base_frame.frame_index,
            timestamp=base_frame.timestamp,
            capture_timestamp=base_frame.capture_timestamp,
            state=base_frame.state,
            snapshot=base_frame.snapshot,
            scorecard=base_frame.scorecard,
            recommendations=base_frame.recommendations,
            cockpit_state=cockpit,
            context=base_frame.context,
        )

    def open_positions(self) -> None:
        print("Opening small simulator positions...")
        trade = Trade(self.engine.api)
        for request in [
            {"symbol": "EURUSD", "side": "BUY", "volume": 0.10},
            {"symbol": "GBPUSD", "side": "BUY", "volume": 0.08},
            {"symbol": "XAUUSD", "side": "SELL", "volume": 0.03},
        ]:
            symbol_info = self.engine.symbol_info(request["symbol"])
            if symbol_info is None:
                continue
            volume = round_volume(symbol_info, request["volume"])
            point = float(getattr(symbol_info, "point", 0.0001) or 0.0001)
            ask = float(getattr(symbol_info, "ask", 0.0) or 0.0)
            bid = float(getattr(symbol_info, "bid", 0.0) or 0.0)
            if request["side"] == "BUY":
                price = ask
                sl = price - (50 * point)
            else:
                price = bid
                sl = price + (50 * point)
            trade.SetTypeFillingBySymbol(request["symbol"])
            result = trade.PositionOpen(
                symbol=request["symbol"],
                order_type=request["side"],
                volume=volume,
                price=price,
                sl=sl,
                tp=0.0,
                comment="Phase 10 storage example",
            )
            print(
                f"  {request['symbol']} {request['side']}: retcode={int(result.retcode)} "
                f"order={int(result.order)} volume={volume:.2f}"
            )
        self.engine.monitor_account(verbose=False)

    def close(self) -> None:
        if getattr(self.engine, "client", None) is not None:
            self.engine.client.shutdown()


def example_01_create_risk_run(ctx: ExampleContext) -> None:
    print_example_header("Example 01: Create Risk Run")
    ctx.run_id = ctx.store.create_run(
        label="phase10-storage-example",
        description="Real-data simulator-backed risk snapshot storage example",
        source="example",
        context={"phase": 10, "symbols": SYMBOLS},
    )
    print(f"  run_id={ctx.run_id}")


def example_02_store_normalized_snapshot(ctx: ExampleContext) -> None:
    print_example_header("Example 02: Store Normalized Snapshot")
    ctx.snapshot_id = ctx.store.store_snapshot_bundle(
        run_id=ctx.run_id,
        snapshot=ctx.snapshot,
    )
    print(f"  snapshot_id={ctx.snapshot_id}")
    print(f"  metric_rows={len(ctx.snapshot.metric_rows)}")


def example_03_store_scorecard(ctx: ExampleContext) -> None:
    print_example_header("Example 03: Store Scorecard")
    ctx.db.save_risk_scorecard(snapshot_id=ctx.snapshot_id, scorecard=ctx.scorecard)
    print(f"  score_rows={len(ctx.scorecard.score_rows)} overall={ctx.scorecard.summary.get('overall_risk_quality_score')}")


def example_04_store_recommendations(ctx: ExampleContext) -> None:
    print_example_header("Example 04: Store Recommendations")
    ctx.db.save_risk_recommendations(
        snapshot_id=ctx.snapshot_id,
        recommendations=ctx.recommendations.recommendations,
    )
    print(f"  recommendations={len(ctx.recommendations.recommendations)}")


def example_05_store_replay_frame_summary(ctx: ExampleContext) -> None:
    print_example_header("Example 05: Store Replay Frame Summary")
    replay_frame_id = ctx.store.store_replay_frame(
        run_id=ctx.run_id,
        frame=ctx.frame,
        snapshot_id=ctx.snapshot_id,
    )
    print(f"  replay_frame_id={replay_frame_id}")
    print(f"  cockpit_keys={list(ctx.frame.cockpit_state.risk_summary.keys())}")


def example_06_load_persisted_artifacts(ctx: ExampleContext) -> None:
    print_example_header("Example 06: Load Persisted Artifacts")
    snapshot_bundle = ctx.store.load_snapshot_bundle(ctx.snapshot_id)
    replay_frames = ctx.store.load_replay_frames(ctx.run_id)
    print(f"  loaded_metric_rows={len(snapshot_bundle['metric_rows'])}")
    print(f"  loaded_score_rows={len(snapshot_bundle['score_rows'])}")
    print(f"  loaded_policy_events={len(snapshot_bundle['policy_events'])}")
    print(f"  loaded_recommendations={len(snapshot_bundle['recommendations'])}")
    print(f"  loaded_scenarios={len(snapshot_bundle['scenarios'])}")
    print(f"  replay_frames={len(replay_frames)}")


def main() -> None:
    print_example_header("PHASE 10 STORAGE AND SNAPSHOT INFRASTRUCTURE")
    ctx = ExampleContext()
    try:
        ctx.setup()
        example_01_create_risk_run(ctx)
        example_02_store_normalized_snapshot(ctx)
        example_03_store_scorecard(ctx)
        example_04_store_recommendations(ctx)
        example_05_store_replay_frame_summary(ctx)
        example_06_load_persisted_artifacts(ctx)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
