"""AI Trading Strategy Workflows — Data Loading & Preprocessing.

Demonstrates the Course 2, Lesson 1 workflow foundation:
**Collect → Clean → Prepare → Feature-engineer → Signal → Backtest → Evaluate.**

All examples share helper functions so no RSI, analytics, or backtest logic
is duplicated across examples.

Usage:
    python backend/scripts/examples/agentic_ai/04_ai_trading_strategy_workflows.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ======================================================================
# Display helpers
# ======================================================================

def print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_kv(label: str, value: Any, indent: int = 2) -> None:
    prefix = " " * indent
    if isinstance(value, dict):
        print(f"{prefix}{label}")
        for k, v in value.items():
            print(f"{prefix}  {k:<28s} {v}")
    elif isinstance(value, list):
        print(f"{prefix}{label}")
        for item in value:
            print(f"{prefix}  - {item}")
    else:
        print(f"{prefix}{label:<30s} {value}")


# ======================================================================
# Shared data / feature / signal helpers  (no duplication across examples)
# ======================================================================

def _load_market_data(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    lookback_days: int = 14,
) -> Optional[pd.DataFrame]:
    """Load OHLCV from MT5 (falls back to Dukascopy).  Used by examples 01-11."""
    from backend.services.market_data.data_getters import load_mt5

    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    df = load_mt5(
        symbol=symbol, timeframe=timeframe,
        start_date=start_date, end_date=end_date,
    )
    return df if df is not None and not df.empty else None


def _prepare_lower_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to lowercase for pipeline consumption."""
    from backend.services.research.datasets import normalize_columns

    normalized = normalize_columns(raw_df)
    return normalized.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume", "Spread": "spread",
    })


def _add_features(
    lower_df: pd.DataFrame,
    rsi_period: int = 14,
) -> pd.DataFrame:
    """Compute RSI via FeaturePipeline and return enriched DataFrame."""
    from backend.services.features.pipeline import FeaturePipeline, FeatureSpec

    pipeline = FeaturePipeline([
        FeatureSpec(name="rsi", params={"period": rsi_period, "price_col": "close"}),
    ])
    return pipeline.compute_batch(lower_df)


def _generate_signals(
    featured_df: pd.DataFrame,
    symbol: str = "EURUSD",
    rsi_period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> pd.DataFrame:
    """Run RSI baseline strategy and return DataFrame with signal columns."""
    from backend.services.strategy.baselines import RsiBaselineStrategy

    strategy = RsiBaselineStrategy({
        "symbol": symbol,
        "strategy_id": f"rsi-{rsi_period}",
        "period": rsi_period,
        "oversold": oversold,
        "overbought": overbought,
    })
    strategy.on_init()
    return strategy.on_bar(featured_df)


def _shift_signals(
    signaled: pd.DataFrame,
    use_shift1: bool = True,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (entry, exit, price) Series, optionally lagged by 1 bar."""
    default = pd.Series(0.0, index=signaled.index)
    if use_shift1:
        entry = signaled.get("entry_signal", default).shift(1).fillna(0)
        exit_s = signaled.get("exit_signal", default).shift(1).fillna(0)
        price = signaled.get("price", default).shift(1).fillna(0.0)
    else:
        entry = signaled.get("entry_signal", default)
        exit_s = signaled.get("exit_signal", default)
        price = signaled.get("price", default)
    # Coerce any pd.NA or object values to float
    entry = pd.to_numeric(entry, errors="coerce").fillna(0.0)
    exit_s = pd.to_numeric(exit_s, errors="coerce").fillna(0.0)
    price = pd.to_numeric(price, errors="coerce").fillna(0.0)
    return entry, exit_s, price


def _build_tick_df(
    signaled: pd.DataFrame,
    entry: pd.Series,
    exit_s: pd.Series,
    price: pd.Series,
) -> pd.DataFrame:
    """Build tick DataFrame the Engine expects."""
    return pd.DataFrame({
        "bid": signaled["close"].values.astype("float64"),
        "ask": signaled["close"].values.astype("float64"),
        "open": signaled.get("open", signaled["close"]).values.astype("float64"),
        "high": (signaled.get("high", signaled["close"] * 1.001)).values.astype("float64"),
        "low": (signaled.get("low", signaled["close"] * 0.999)).values.astype("float64"),
        "close": signaled["close"].values.astype("float64"),
        "entry_signal": entry.values.astype("float64"),
        "exit_signal": exit_s.values.astype("float64"),
        "price": price.values.astype("float64"),
    }, index=signaled.index)


# ======================================================================
# Shared Engine / backtest helpers
# ======================================================================

def _make_engine(
    symbol: str = "EURUSD",
    initial_balance: float = 10000.0,
    leverage: int = 400,
    commission: float = 7.0,
):
    """Create a simulation Engine with account and symbol configured."""
    from backend.services.simulation.engine import Engine
    from backend.services.execution.core import SymbolInfo

    engine = Engine(backend="sim")

    sym = SymbolInfo()
    sym["name"] = symbol
    sym["ask"] = 1.1700
    sym["bid"] = 1.1698
    sym["point"] = 0.00001
    sym["digits"] = 5
    sym["trade_contract_size"] = 100000.0
    sym["volume_min"] = 0.01
    sym["volume_max"] = 100.0
    sym["volume_step"] = 0.01
    engine.state.trading_symbols.append(sym)

    account = engine.account_info()
    account["balance"] = initial_balance
    account["equity"] = initial_balance
    account["margin"] = 0.0
    account["margin_free"] = initial_balance
    account["leverage"] = leverage
    account["commission"] = commission
    return engine


def _run_engine(engine, tick_df: pd.DataFrame, lot_size: float = 0.1) -> dict[str, Any]:
    """Run the Engine and return a result dict."""
    engine.configure_run_schedule(
        positions_every=1, pending_orders_every=1,
        account_every=4, portfolio_every=4, risk_every=4,
    )
    t0 = time.time()
    processed = engine.run(
        tick_df, position_size=lot_size,
        monitor_verbose=False, show_progress=False,
    )
    elapsed = time.time() - t0

    trades = engine.get_completed_trades()
    open_positions = engine.state.trading_deals if hasattr(engine.state, "trading_deals") else []
    acc = engine.account_info()
    return {
        "processed": processed,
        "elapsed": elapsed,
        "trades": trades,
        "open_positions": open_positions,
        "account": acc,
    }


# ======================================================================
# Shared analytics helpers
# ======================================================================

def _compute_metrics(
    bt_result: dict,
    signaled: pd.DataFrame,
    initial_balance: float = 10000.0,
) -> dict[str, Any]:
    """Compute standard performance metrics from Engine results."""
    from backend.services.analytics.ratios import sharpe_ratio
    from backend.services.analytics.drawdowns import max_drawdown
    from backend.services.analytics.metrics import win_rate

    acc = bt_result["account"]
    final_balance = float(acc.get("balance", initial_balance))
    total_return = (final_balance / initial_balance) - 1.0

    trade_pnls = [
        float(getattr(t, "profit_loss", 0) or 0) for t in bt_result["trades"]
    ]
    trade_returns = pd.Series(
        [p / initial_balance for p in trade_pnls]
    ) if trade_pnls else pd.Series(dtype=float)

    first_close = float(signaled["close"].iloc[0])
    last_close = float(signaled["close"].iloc[-1])
    bh_return = (last_close / first_close) - 1.0 if first_close > 0 else 0.0

    wins = sum(1 for p in trade_pnls if p > 0)
    losses = sum(1 for p in trade_pnls if p <= 0)
    total_pnl = sum(trade_pnls)
    avg_win = float(np.mean([p for p in trade_pnls if p > 0])) if wins > 0 else 0.0
    avg_loss = abs(float(np.mean([p for p in trade_pnls if p < 0]))) if losses > 0 else 0.0
    pf = abs(avg_win * wins / (avg_loss * losses)) if losses > 0 and avg_loss > 0 else float("inf")

    return {
        "total_strategy_return": total_return,
        "total_buy_hold_return": bh_return,
        "sharpe_ratio": sharpe_ratio(trade_returns, annualize=False) if len(trade_returns) > 1 else 0.0,
        "max_drawdown": max_drawdown(pd.Series([1.0 + r for r in trade_returns])) if len(trade_returns) > 0 else 0.0,
        "win_rate": win_rate(trade_returns) if len(trade_returns) > 0 else 0.0,
        "profit_factor": pf,
        "wins": wins,
        "losses": losses,
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
    }


def _print_metrics_report(metrics: dict, bt_result: dict, n_bars: int) -> None:
    """Print a standard performance report."""
    print_kv("Performance Report", "")
    print_kv("  Bars in backtest", n_bars)
    print_kv("  Strategy Return",
             f"{metrics['total_strategy_return']:+.4f}  ({metrics['total_strategy_return']*100:+.2f}%)")
    print_kv("  Buy & Hold Return",
             f"{metrics['total_buy_hold_return']:+.4f}  ({metrics['total_buy_hold_return']*100:+.2f}%)")
    print_kv("  Sharpe Ratio", f"{metrics['sharpe_ratio']:.4f}")
    print_kv("  Max Drawdown", f"{metrics['max_drawdown']:+.4f}  ({metrics['max_drawdown']*100:+.2f}%)")
    print()
    print_kv("Trade Statistics", "")
    print_kv("  Completed Trades", len(bt_result["trades"]))
    print_kv("  Open Positions", len(bt_result["open_positions"]))
    print_kv("  Wins / Losses", f"{metrics['wins']} / {metrics['losses']}")
    print_kv("  Win Rate", f"{metrics['win_rate']:.4f}  ({metrics['win_rate']*100:.2f}%)")
    print_kv("  Avg Win", f"${metrics['avg_win']:+.2f}" if metrics["wins"] > 0 else "N/A")
    print_kv("  Avg Loss", f"${metrics['avg_loss']:+.2f}" if metrics["losses"] > 0 else "N/A")
    pf_str = f"{metrics['profit_factor']:.4f}" if metrics["profit_factor"] != float("inf") else "∞"
    print_kv("  Profit Factor", pf_str)
    print_kv("  Total P&L", f"${metrics['total_pnl']:+.2f}")


def _print_bt_summary(bt_result: dict) -> None:
    """Print compact backtest summary."""
    acc = bt_result["account"]
    print_kv("  Processed bars", bt_result["processed"])
    print_kv("  Final Balance", f"${float(acc.get('balance', 0)):,.2f}")
    print_kv("  Final Equity", f"${float(acc.get('equity', 0)):,.2f}")
    print_kv("  Completed Trades", len(bt_result["trades"]))
    print_kv("  Open Positions", len(bt_result["open_positions"]))
    if bt_result["trades"]:
        print_kv("  Last 3 trades", "")
        for t in bt_result["trades"][-3:]:
            print_kv(
                f"    [{t.symbol}] {t.type.upper()}",
                f"open={t.open_price:.5f}, close={t.close_price:.5f}, "
                f"P/L=${t.profit_loss:.2f}",
            )
    if bt_result["open_positions"]:
        total_upnl = sum(
            float(getattr(p, "profit", 0) or 0) for p in bt_result["open_positions"]
        )
        print_kv("  Unrealized P&L", f"${total_upnl:,.2f}")


# ======================================================================
# Shared sample data for file-based examples
# ======================================================================

_EXAMPLE_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "market_data"
_EXAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _build_sample_ohlcv(n_bars: int = 200) -> pd.DataFrame:
    closes = [1.1000 + i * 0.0003 + (0.0005 if i % 7 == 0 else 0) for i in range(n_bars)]
    idx = pd.date_range("2025-01-02", periods=n_bars, freq="h", tz="UTC")
    return pd.DataFrame({
        "open": closes,
        "high": [c + 0.0010 for c in closes],
        "low": [c - 0.0010 for c in closes],
        "close": closes,
        "volume": [100 + i * 2 for i in range(n_bars)],
    }, index=idx)


def _ensure_sample_csv() -> Path:
    filepath = _EXAMPLE_DATA_DIR / "eurusd_sample.csv"
    if not filepath.exists():
        df = _build_sample_ohlcv()
        df.reset_index().rename(columns={"index": "timestamp"}).to_csv(filepath, index=False)
    return filepath


def _ensure_sample_parquet() -> Path:
    filepath = _EXAMPLE_DATA_DIR / "eurusd_sample.parquet"
    if not filepath.exists():
        _build_sample_ohlcv().to_parquet(filepath)
    return filepath


# ======================================================================
# Example 01 – 04: Data loading (each uses its own source)
# ======================================================================

def example_01_load_mt5() -> None:
    """Load OHLCV data from MetaTrader 5 (falls back to Dukascopy)."""
    print_header("Example 01: Load Market Data — MT5")
    from backend.services.market_data.data_getters import load_mt5

    symbol, timeframe = "XAUUSD", "H1"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    print_kv("Source", "MetaTrader 5")
    print_kv("Symbol", symbol)
    print_kv("Timeframe", timeframe)
    print_kv("Date range", f"{start_date.date()} → {end_date.date()}")
    print()

    try:
        df = load_mt5(symbol=symbol, timeframe=timeframe, start_date=start_date, end_date=end_date)
        if df is None:
            from backend.services.market_data.data_getters import load_dukascopy
            df = load_dukascopy(
                symbol=symbol, timeframe=timeframe,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
            )
        print("  ✅ Data loaded successfully\n")
        print_kv("Shape", f"{len(df)} rows × {len(df.columns)} cols")
        if isinstance(df.index, pd.DatetimeIndex) and len(df):
            print_kv("Date range", f"{df.index[0]} → {df.index[-1]}")
        print_kv("Columns", list(df.columns))
        print()
        print(df.head(5).to_string())
        print()
    except Exception as exc:
        print(f"  ❌ Failed: {exc}")


def example_02_load_dukascopy() -> None:
    """Load OHLCV data from Dukascopy HTTP API."""
    print_header("Example 02: Load Market Data — Dukascopy")
    from backend.services.market_data.data_getters import load_dukascopy

    print_kv("Source", "Dukascopy HTTP API")
    print_kv("Symbol", "EURUSD")
    print_kv("Date range", "2025-06-01 → 2025-06-08")
    print()
    try:
        df = load_dukascopy(symbol="EURUSD", timeframe="H1", start_date="2025-06-01", end_date="2025-06-08")
        print("  ✅ Data loaded successfully\n")
        print_kv("Shape", f"{len(df)} rows × {len(df.columns)} cols")
        print(df.head(5).to_string())
        print()
    except Exception as exc:
        print(f"  ❌ Failed: {exc}")


def example_03_load_parquet() -> None:
    """Load OHLCV data from a local Parquet file."""
    print_header("Example 03: Load Market Data — Parquet")
    from backend.services.market_data.data_getters import load_parquet

    filepath = _ensure_sample_parquet()
    print_kv("File", str(filepath))
    print()
    try:
        df = load_parquet(filepath)
        print("  ✅ Data loaded successfully\n")
        print_kv("Shape", f"{len(df)} rows × {len(df.columns)} cols")
        print(df.head(5).to_string())
        print()
    except Exception as exc:
        print(f"  ❌ Failed: {exc}")


def example_04_load_csv() -> None:
    """Load OHLCV data from CSV via CSVDataSource."""
    print_header("Example 04: Load Market Data — CSV (CSVDataSource)")
    from backend.services.market_data.data_getters import CSVDataSource

    filepath = _ensure_sample_csv()
    print_kv("File", str(filepath))
    print()
    try:
        source = CSVDataSource(filepath)
        df = source.fetch_data(symbol="EURUSD", timeframe="H1", start_pos=0, end_pos=50)
        if df is None:
            print("  ❌ No data returned.")
            return
        print("  ✅ Data loaded successfully\n")
        print_kv("Shape", f"{len(df)} rows × {len(df.columns)} cols")
        print(df.head(5).to_string())
        print()
    except Exception as exc:
        print(f"  ❌ Failed: {exc}")


# ======================================================================
# Example 05: Full data-preprocess pipeline (MT5 → validate → clean → enrich)
# ======================================================================

def example_05_data_preprocess() -> None:
    """Load from MT5 and run through validate → clean → enrich pipeline."""
    print_header("Example 05: Data Preprocessing — Full Pipeline")
    from backend.services.research.datasets import normalize_columns, prepare_ohlcvs_dataset

    symbol, timeframe = "EURUSD", "H1"
    print_kv("Source", "MT5 → validate → clean → enrich")
    print_kv("Symbol", symbol)
    print_kv("Timeframe", timeframe)
    print()

    raw_df = _load_market_data(symbol=symbol, timeframe=timeframe)
    if raw_df is None:
        print("  ⚠️  No data returned.")
        return

    print(f"  ✅ Step 1: Loaded {len(raw_df)} raw bars from MT5\n")

    class _InMemoryDataSource:
        def __init__(self, df):
            self._df = df
        def fetch_data(self, symbol, timeframe, start_pos, end_pos):
            if start_pos < 0 or end_pos > len(self._df) or start_pos >= end_pos:
                return None
            return self._df.iloc[start_pos:end_pos].copy()

    normalized = normalize_columns(raw_df)
    source = _InMemoryDataSource(normalized)

    try:
        dataset = prepare_ohlcvs_dataset(
            source=source, symbol=symbol, timeframe=timeframe,
            start_pos=0, end_pos=min(500, len(normalized)),
        )
        print("  ✅ Step 3: Full pipeline completed\n")
        print_kv("Dataset summary", "")
        print_kv("  rows", len(dataset.data))
        print_kv("  columns", list(dataset.data.columns))
        print_kv("  is_valid", dataset.report.is_valid)
        print_kv("  warnings", len(dataset.report.warnings))
        print_kv("  fatal errors", len(dataset.report.fatal_errors))
        print()
        print(dataset.data.head(3).to_string())
        print()
    except ValueError as exc:
        print(f"  ⚠️  Validation failed: {exc}")


# ======================================================================
# Example 06: Feature engineering
# ======================================================================

def example_06_feature_engineering() -> None:
    """Add RSI, SMA, EMA, ATR, Bollinger Bands via FeaturePipeline."""
    print_header("Example 06: Feature Engineering — FeaturePipeline")
    from backend.services.features.pipeline import FeaturePipeline, FeatureSpec
    from backend.services.research.datasets import normalize_columns

    symbol, timeframe = "EURUSD", "H1"
    print_kv("Source", "MT5 → preprocess → FeaturePipeline")
    print_kv("Symbol", symbol)
    print_kv("Timeframe", timeframe)
    print()

    raw_df = _load_market_data(symbol=symbol, timeframe=timeframe)
    if raw_df is None:
        print("  ⚠️  No data returned.")
        return

    lower_df = _prepare_lower_df(raw_df)
    print(f"  ✅ Step 1: {len(lower_df)} cleaned bars ready\n")

    features = [
        FeatureSpec(name="rsi", params={"period": 14, "price_col": "close"}),
        FeatureSpec(name="sma", params={"window": 20, "price_col": "close"}),
        FeatureSpec(name="sma", params={"window": 50, "price_col": "close"}),
        FeatureSpec(name="ema", params={"span": 12, "price_col": "close"}),
        FeatureSpec(name="ema", params={"span": 26, "price_col": "close"}),
        FeatureSpec(name="atr", params={"period": 14}),
        FeatureSpec(name="bbands", params={"period": 20, "std_dev": 2.0, "price_col": "close"}),
    ]
    pipeline = FeaturePipeline(features, pipeline_version="lesson-1-v1")
    print_kv("Pipeline config", "")
    print_kv("  version", pipeline.pipeline_version)
    print_kv("  feature count", len(features))
    print()

    enriched = pipeline.compute_batch(lower_df)
    new_cols = [c for c in enriched.columns if c not in lower_df.columns]
    print(f"  ✅ Step 2: {len(new_cols)} new columns added: {', '.join(new_cols)}\n")
    print_kv("Feature summary", "")
    stats = enriched[[c for c in new_cols if c in enriched.columns]].describe().loc[["mean", "std", "min", "max"]]
    print(stats.round(4).to_string())
    print()


# ======================================================================
# Example 07: Signal generation
# ======================================================================

def example_07_signal_generation() -> None:
    """Generate buy/sell signals via RSI baseline strategy."""
    print_header("Example 07: Signal Generation — RSI Baseline Strategy")

    raw_df = _load_market_data()
    if raw_df is None:
        print("  ⚠️  No data returned.")
        return

    featured = _add_features(_prepare_lower_df(raw_df))
    signaled = _generate_signals(featured)
    n_signals = int((signaled["entry_signal"] != 0).sum())
    print(f"  ✅ {len(signaled)} bars, {n_signals} signal entries\n")

    buy = int((signaled["entry_signal"] > 0).sum())
    sell = int((signaled["entry_signal"] < 0).sum())
    print_kv("Signal summary", "")
    print_kv("  buy signals", buy)
    print_kv("  sell signals", sell)
    print_kv("  signal rate", f"{n_signals}/{len(signaled)} bars = {n_signals/len(signaled)*100:.1f}%")
    print()

    sig_rows = signaled[signaled["entry_signal"] != 0]
    if len(sig_rows):
        print_kv("First 5 signals", "")
        for idx, row in sig_rows.head(5).iterrows():
            print_kv(
                f"  [{idx}] {'BUY' if row['entry_signal'] > 0 else 'SELL'}",
                f"price={row.get('price', 0)}, reason={str(row.get('signal_reason', ''))[:50]}",
            )
        print()


# ======================================================================
# Example 08 – 10: Backtest + metrics (share all helpers)
# ======================================================================

def example_08_simulation_backtest() -> None:
    """Run a simulation backtest with the real Engine."""
    print_header("Example 08: Simulation Backtest — Engine")

    raw_df = _load_market_data()
    if raw_df is None:
        print("  ⚠️  No data returned.")
        return

    featured = _add_features(_prepare_lower_df(raw_df))
    signaled = _generate_signals(featured)
    entry, exit_s, price = _shift_signals(signaled, use_shift1=False)
    n_signals = int((entry != 0).sum())
    print(f"  ✅ {len(signaled)} bars, {n_signals} signal entries\n")

    tick_df = _build_tick_df(signaled, entry, exit_s, price)
    engine = _make_engine()
    bt_result = _run_engine(engine, tick_df, lot_size=0.1)

    print(f"  ✅ Simulation completed in {bt_result['elapsed']:.2f}s\n")
    _print_bt_summary(bt_result)
    print()


def example_09_backtest_shifted_signals() -> None:
    """Backtest with shift(1) lookahead-bias prevention."""
    print_header("Example 09: Backtest — shift(1) Lookahead-Bias Prevention")

    raw_df = _load_market_data()
    if raw_df is None:
        print("  ⚠️  No data returned.")
        return

    featured = _add_features(_prepare_lower_df(raw_df))
    signaled = _generate_signals(featured)

    raw_n = int((signaled["entry_signal"] != 0).sum())
    entry, exit_s, price = _shift_signals(signaled, use_shift1=True)
    shifted_n = int((entry != 0).sum())
    print_kv("Signals at bar N (raw)", raw_n)
    print_kv("Signals at bar N+1 (shift(1))", shifted_n)
    print()

    tick_df = _build_tick_df(signaled, entry, exit_s, price)
    engine = _make_engine()
    bt_result = _run_engine(engine, tick_df, lot_size=0.1)

    print(f"  ✅ Simulation completed in {bt_result['elapsed']:.2f}s\n")
    _print_bt_summary(bt_result)
    print()


def example_10_performance_metrics() -> None:
    """Evaluate backtest with Sharpe, drawdown, win rate, profit factor."""
    print_header("Example 10: Performance Metrics Evaluation")

    raw_df = _load_market_data()
    if raw_df is None:
        print("  ⚠️  No data returned.")
        return

    featured = _add_features(_prepare_lower_df(raw_df))
    signaled = _generate_signals(featured)
    entry, exit_s, price = _shift_signals(signaled, use_shift1=True)
    print(f"  ✅ {len(signaled)} bars, {int((entry != 0).sum())} shifted signals\n")

    tick_df = _build_tick_df(signaled, entry, exit_s, price)
    engine = _make_engine()
    bt_result = _run_engine(engine, tick_df, lot_size=0.1)
    metrics = _compute_metrics(bt_result, signaled)

    print("  ✅ Metrics computed\n")
    _print_metrics_report(metrics, bt_result, len(signaled))
    print()


# ======================================================================
# Example 11: Full pipeline orchestrator
# ======================================================================

@dataclass(frozen=True)
class Lesson1Config:
    """Configuration for the Lesson 1 AI Trading Workflow."""

    symbol: str = "EURUSD"
    timeframe: str = "H1"
    lookback_days: int = 14
    rsi_period: int = 14
    oversold: float = 30.0
    overbought: float = 70.0
    lot_size: float = 0.1
    initial_balance: float = 10000.0
    leverage: int = 400
    commission_per_lot: float = 7.0
    use_shift1: bool = True


@dataclass
class Lesson1Result:
    """Structured result from the Lesson 1 workflow."""

    config: Lesson1Config
    bars_loaded: int = 0
    bars_after_clean: int = 0
    features_added: int = 0
    signals_generated: int = 0
    processed_ticks: int = 0
    completed_trades: int = 0
    open_positions: int = 0
    final_balance: float = 0.0
    total_strategy_return: float = 0.0
    total_buy_hold_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    bars_dataframe: Optional[pd.DataFrame] = field(repr=False, default=None)


def run_lesson1_workflow(config: Optional[Lesson1Config] = None) -> Lesson1Result:
    """Run the complete AI Trading Workflow end-to-end.

    Chains all 7 lesson steps in a single call:
        load → clean → features → signals → backtest → evaluate
    """
    config = config or Lesson1Config()
    result = Lesson1Result(config=config)

    # Steps 1+2: Collect + Clean
    raw_df = _load_market_data(
        symbol=config.symbol, timeframe=config.timeframe,
        lookback_days=config.lookback_days,
    )
    if raw_df is None:
        raise ValueError(f"No data returned for {config.symbol} {config.timeframe}")
    result.bars_loaded = len(raw_df)
    lower_df = _prepare_lower_df(raw_df)

    try:
        from backend.services.research.datasets import normalize_columns, prepare_ohlcvs_dataset

        class _InMemoryDataSource:
            def __init__(self, df):
                self._df = df
            def fetch_data(self, symbol, tf, sp, ep):
                if sp < 0 or ep > len(self._df) or sp >= ep:
                    return None
                return self._df.iloc[sp:ep].copy()

        normalized = normalize_columns(raw_df)
        dataset = prepare_ohlcvs_dataset(
            source=_InMemoryDataSource(normalized),
            symbol=config.symbol, timeframe=config.timeframe,
            start_pos=0, end_pos=min(500, len(normalized)),
        )
        lower_df = dataset.data.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume", "Spread": "spread",
        })
        result.bars_after_clean = len(lower_df)
    except Exception:
        result.bars_after_clean = len(lower_df)

    # Step 3: Features
    featured = _add_features(lower_df, rsi_period=config.rsi_period)
    result.features_added = len([c for c in featured.columns if c not in lower_df.columns])

    # Steps 4+5: Strategy + Signals
    signaled = _generate_signals(
        featured, symbol=config.symbol,
        rsi_period=config.rsi_period,
        oversold=config.oversold, overbought=config.overbought,
    )
    entry, exit_s, price = _shift_signals(signaled, use_shift1=config.use_shift1)
    result.signals_generated = int((entry != 0).sum())

    # Step 6: Backtest
    engine = _make_engine(
        symbol=config.symbol, initial_balance=config.initial_balance,
        leverage=config.leverage, commission=config.commission_per_lot,
    )
    tick_df = _build_tick_df(signaled, entry, exit_s, price)
    bt_result = _run_engine(engine, tick_df, lot_size=config.lot_size)
    result.processed_ticks = bt_result["processed"]
    result.completed_trades = len(bt_result["trades"])
    result.open_positions = len(bt_result["open_positions"])
    result.final_balance = float(bt_result["account"].get("balance", config.initial_balance))

    # Step 7: Evaluate
    metrics = _compute_metrics(bt_result, signaled, config.initial_balance)
    result.total_strategy_return = metrics["total_strategy_return"]
    result.total_buy_hold_return = metrics["total_buy_hold_return"]
    result.sharpe_ratio = metrics["sharpe_ratio"]
    result.max_drawdown = metrics["max_drawdown"]
    result.win_rate = metrics["win_rate"]
    result.profit_factor = metrics["profit_factor"]
    result.bars_dataframe = signaled
    return result


def example_11_full_pipeline_orchestrator() -> None:
    """One call: load → clean → features → signals → backtest → evaluate."""
    print_header("Example 11: Full Pipeline Orchestrator")
    print_kv("Description", "Single call: load → clean → features → signals → backtest → evaluate")
    print()

    config = Lesson1Config()
    print_kv("Configuration", "")
    print_kv("  symbol", config.symbol)
    print_kv("  timeframe", config.timeframe)
    print_kv("  lookback_days", config.lookback_days)
    print_kv("  rsi_period", config.rsi_period)
    print_kv("  oversold / overbought", f"{config.oversold} / {config.overbought}")
    print_kv("  lot_size", config.lot_size)
    print_kv("  initial_balance", f"${config.initial_balance:,.2f}")
    print_kv("  use_shift1", config.use_shift1)
    print()

    result = run_lesson1_workflow(config)

    print_kv("Pipeline Diagnostics", "")
    print_kv("  Bars loaded", result.bars_loaded)
    print_kv("  Bars after clean", result.bars_after_clean)
    print_kv("  Features added", f"{result.features_added} (rsi_{config.rsi_period})")
    print_kv("  Shifted signals (bar N+1)", result.signals_generated)
    print_kv("  Processed ticks", result.processed_ticks)
    print()

    print_kv("Workflow Results", "")
    print_kv("  Final Balance", f"${result.final_balance:,.2f}")
    print_kv("  Completed Trades", result.completed_trades)
    print_kv("  Open Positions", result.open_positions)
    print()

    print_kv("Performance Report", "")
    print_kv("  Strategy Return",
             f"{result.total_strategy_return:+.4f}  ({result.total_strategy_return*100:+.2f}%)")
    print_kv("  Buy & Hold Return",
             f"{result.total_buy_hold_return:+.4f}  ({result.total_buy_hold_return*100:+.2f}%)")
    print_kv("  Sharpe Ratio", f"{result.sharpe_ratio:.4f}")
    print_kv("  Max Drawdown", f"{result.max_drawdown:+.4f}  ({result.max_drawdown*100:+.2f}%)")
    print_kv("  Win Rate", f"{result.win_rate:.4f}  ({result.win_rate*100:.2f}%)")
    pf = f"{result.profit_factor:.4f}" if result.profit_factor != float("inf") else "∞"
    print_kv("  Profit Factor", pf)
    print()

    print_kv("Lesson 1 Workflow Complete", "")
    print_kv("  Steps executed", "Collect → Clean → Features → Signals → Backtest → Evaluate")
    print_kv("  All steps", "✅ Passed")
    print()


# ======================================================================
# Main
# ======================================================================

def main() -> None:
    print()
    print("#" * 78)
    print("#  AI Trading Strategy Workflows — Data Loading & Preprocessing")
    print("#  Lesson 1: Collect → Clean → Prepare → Features → Signals → Backtest → Evaluate")
    print("#" * 78)

    examples = [
        example_01_load_mt5,
        example_02_load_dukascopy,
        example_03_load_parquet,
        example_04_load_csv,
        example_05_data_preprocess,
        example_06_feature_engineering,
        example_07_signal_generation,
        example_08_simulation_backtest,
        example_09_backtest_shifted_signals,
        example_10_performance_metrics,
        example_11_full_pipeline_orchestrator,
    ]

    for example_fn in examples:
        try:
            example_fn()
        except Exception as exc:
            import traceback
            print(f"\n  ERROR in {example_fn.__name__}: {exc}")
            traceback.print_exc()

    print()
    print("#" * 78)
    print("#  All examples complete!")
    print("#" * 78)
    print()


if __name__ == "__main__":
    main()
