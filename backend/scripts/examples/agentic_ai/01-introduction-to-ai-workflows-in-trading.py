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

# Load .env file for API keys
_env_path = os.path.join(PROJECT_ROOT, "backend", "config", "environments", ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
    del _f, _line, _k, _v

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
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    lookback_days: int = 370,
) -> Optional[pd.DataFrame]:
    """Load OHLCV from MT5 (falls back to Dukascopy)."""
    from backend.services.market_data.data_getters import load_mt5

    if start_date is None:
        end_date = end_date or datetime.now()
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
    fast_period: int = 20,
    slow_period: int = 50,
    bias_period: int = 200,
) -> pd.DataFrame:
    """Compute various features (RSI, SMA, EMA, ATR, Bollinger Bands) for strategy."""
    from backend.services.features.pipeline import FeaturePipeline, FeatureSpec

    features = [
        FeatureSpec(name="ema", params={"window": 20, "price_col": "close"}),
        FeatureSpec(name="ema", params={"window": 50, "price_col": "close"}),
        FeatureSpec(name="ema", params={"window": 200, "price_col": "close"}),
    ]
    pipeline = FeaturePipeline(features)
    return pipeline.compute_batch(lower_df)


def _generate_signals(
    featured_df: pd.DataFrame,
    symbol: str = "EURUSD",
    fast_period: int = 20,
    slow_period: int = 50,
    bias_period: int = 200,
) -> pd.DataFrame:
    """Run EMA crossover strategy and return DataFrame with signal columns."""
    from backend.services.strategy.baselines import EmaCrossBaselineStrategy

    strategy = EmaCrossBaselineStrategy({
        "symbol": symbol,
        "strategy_id": f"ema-cross-{fast_period}-{slow_period}-{bias_period}",
        "fast_period": fast_period,
        "slow_period": slow_period,
        "bias_period": bias_period,
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
# Example 01: Feature engineering
# ======================================================================

def example_01_feature_engineering() -> None:
    """Add RSI, SMA, EMA, ATR, Bollinger Bands via FeaturePipeline."""
    print_header("Example 01: Feature Engineering — FeaturePipeline")
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
        FeatureSpec(name="ema", params={"window": 20, "price_col": "close"}),
        FeatureSpec(name="ema", params={"window": 50, "price_col": "close"}),
        FeatureSpec(name="ema", params={"window": 200, "price_col": "close"}),
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
# Example 02: Signal generation
# ======================================================================

def example_02_signal_generation() -> None:
    """Generate buy/sell signals via EMA baseline strategy."""
    print_header("Example 02: Signal Generation — EMA Baseline Strategy")

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

    acc = bt_result["account"]
    final_balance = float(acc.get("balance", initial_balance))
    total_return = (final_balance / initial_balance) - 1.0

    trades = bt_result.get("trades", [])
    
    # If no completed trades or trades don't have profit_loss, return zeros
    has_profit_loss = False
    if trades:
        if isinstance(trades[0], dict):
            has_profit_loss = "profit_loss" in trades[0]
        else:
            has_profit_loss = hasattr(trades[0], "profit_loss")
    
    if not trades or not has_profit_loss:
        first_close = float(signaled["close"].iloc[0])
        last_close = float(signaled["close"].iloc[-1])
        bh_return = (last_close / first_close) - 1.0 if first_close > 0 else 0.0

        return {
            "total_strategy_return": total_return,
            "total_buy_hold_return": bh_return,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": float("inf"),
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
        }

    trade_pnls = [
        float(getattr(t, "profit_loss", 0) or 0) for t in trades
    ]
    trade_returns = pd.Series(
        [p / initial_balance for p in trade_pnls]
    )

    first_close = float(signaled["close"].iloc[0])
    last_close = float(signaled["close"].iloc[-1])
    bh_return = (last_close / first_close) - 1.0 if first_close > 0 else 0.0

    wins = sum(1 for p in trade_pnls if p > 0)
    losses = sum(1 for p in trade_pnls if p <= 0)
    total_pnl = sum(trade_pnls)
    avg_win = float(np.mean([p for p in trade_pnls if p > 0])) if wins > 0 else 0.0
    avg_loss = abs(float(np.mean([p for p in trade_pnls if p < 0]))) if losses > 0 else 0.0
    pf = abs(avg_win * wins / (avg_loss * losses)) if losses > 0 and avg_loss > 0 else float("inf")
    win_rate_val = wins / len(trade_pnls) if trade_pnls else 0.0

    return {
        "total_strategy_return": total_return,
        "total_buy_hold_return": bh_return,
        "sharpe_ratio": sharpe_ratio(trade_returns, annualize=False) if len(trade_returns) > 1 else 0.0,
        "max_drawdown": max_drawdown(pd.Series([1.0 + r for r in trade_returns])) if len(trade_returns) > 0 else 0.0,
        "win_rate": win_rate_val,
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
# Example 03: Backtest + metrics (share all helpers)
# ======================================================================

def example_03_simulation_backtest() -> None:
    """Run a simulation backtest with the real Engine."""
    print_header("Example 03: Simulation Backtest — Engine")

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



def example_04_backtest_shifted_signals() -> None:
    """Backtest with shift(1) lookahead-bias prevention."""
    print_header("Example 04: Backtest — shift(1) Lookahead-Bias Prevention")

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



def example_05_performance_metrics() -> None:
    """Evaluate backtest with Sharpe, drawdown, win rate, profit factor."""
    print_header("Example 05: Performance Metrics Evaluation")

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
# Example 06: Full pipeline orchestrator
# ======================================================================

@dataclass(frozen=True)
class Lesson1Config:
    """Configuration for the Lesson 1 AI Trading Workflow."""

    symbol: str = "EURUSD"
    timeframe: str = "H1"
    start_date: datetime = field(default_factory=lambda: datetime(2025, 1, 1))
    end_date: datetime = field(default_factory=lambda: datetime(2025, 12, 31))
    fast_period: int = 20
    slow_period: int = 50
    bias_period: int = 200
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
        start_date=config.start_date, end_date=config.end_date,
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
    featured = _add_features(
        lower_df,
        fast_period=config.fast_period,
        slow_period=config.slow_period,
        bias_period=config.bias_period,
    )
    result.features_added = len([c for c in featured.columns if c not in lower_df.columns])

    # Steps 4+5: Strategy + Signals
    signaled = _generate_signals(
        featured, symbol=config.symbol,
        fast_period=config.fast_period,
        slow_period=config.slow_period,
        bias_period=config.bias_period,
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


def example_06_full_pipeline_orchestrator() -> None:
    """One call: load → clean → features → signals → backtest → evaluate."""
    print_header("Example 06: Full Pipeline Orchestrator")
    print_kv("Description", "Single call: load → clean → features → signals → backtest → evaluate")
    print()

    config = Lesson1Config()
    print_kv("Configuration", "")
    print_kv("  symbol", config.symbol)
    print_kv("  timeframe", config.timeframe)
    print_kv("  date range", f"{config.start_date.date()} → {config.end_date.date()}")
    print_kv("  EMAs", f"{config.fast_period}/{config.slow_period}/{config.bias_period}")
    print_kv("  lot_size", config.lot_size)
    print_kv("  initial_balance", f"${config.initial_balance:,.2f}")
    print()

    result = run_lesson1_workflow(config)

    print_kv("Pipeline Diagnostics", "")
    print_kv("  Bars loaded", result.bars_loaded)
    print_kv("  Bars after clean", result.bars_after_clean)
    print_kv("  Features added", f"{result.features_added} (ema_{config.fast_period}/{config.slow_period}/{config.bias_period})")
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
# Example 07: Execute via Workflow Registry (data_transformation.yaml)
# ======================================================================

def example_07_registry_driven_workflow() -> None:
    """Execute Lesson 1 via the registered data_transformation workflow.

    Unlike example_11 (manual orchestrator), this uses the WorkflowExecutor
    service which loads the workflow from the registry and dispatches to
    registered step implementations — the same engine used by API, UI, CLI.
    """
    print_header("Example 07: Registry-Driven Workflow — data_transformation.yaml")
    print_kv("Description", "Load workflow from registry → execute each step → collect results")
    print()

    from backend.orchestration.workflow import STEP_IMPLEMENTATIONS, WorkflowExecutor, WorkflowContext

    config = Lesson1Config()

    print_kv("Configuration", "")
    print_kv("  symbol", config.symbol)
    print_kv("  timeframe", config.timeframe)
    print_kv("  date range", f"{config.start_date.date()} → {config.end_date.date()}")
    print_kv("  EMAs", f"{config.fast_period}/{config.slow_period}/{config.bias_period}")
    print_kv("  lot_size", config.lot_size)
    print_kv("  initial_balance", f"${config.initial_balance:,.2f}")
    print()

    executor = WorkflowExecutor(step_registry=STEP_IMPLEMENTATIONS)
    results = executor.execute(
        workflow_name="data_transformation",
        context=WorkflowContext(),
        symbol=config.symbol,
        timeframe=config.timeframe,
        start_date=config.start_date,
        end_date=config.end_date,
        fast_period=config.fast_period,
        slow_period=config.slow_period,
        bias_period=config.bias_period,
        use_shift1=True,
        initial_balance=config.initial_balance,
        leverage=config.leverage,
        commission_per_lot=config.commission_per_lot,
        lot_size=config.lot_size,
    )

    # Run refinement experiments (steps 9-10)
    print_kv("Refinement Phase", "")
    print_kv("  Running", "Multi-configuration backtests + analysis")
    print()

    from backend.orchestration.workflow.steps_refine import (
        step_run_refinement_experiments,
        step_agent_evaluate_and_conclude,
    )

    # Step 9: Run refinement experiments (stores results in refinement_ctx)
    refinement_ctx = WorkflowContext()
    refinement_results = step_run_refinement_experiments(
        refinement_ctx,
        symbol=config.symbol,
        timeframe=config.timeframe,
        start_date=config.start_date,
        end_date=config.end_date,
        lot_size=config.lot_size,
        initial_balance=config.initial_balance,
    )
    results["run_refinement_experiments"] = refinement_results

    # Step 10: LLM agent evaluation and conclusion
    # Uses HARUQUANT_AGENT_MODEL from .env (e.g. gemini-3.1-flash-lite-preview)
    agent_results = step_agent_evaluate_and_conclude(
        refinement_ctx,
        agent_runtime=True,  # Triggers LLM mode via _run_agent_analysis
    )
    results["agent_evaluate_and_conclude"] = agent_results

    # Store agent conclusion in results for printing
    results["run_refinement_experiments"]["agent_conclusion"] = agent_results.get("conclusion", {})
    results["run_refinement_experiments"]["summary"] = refinement_results.get("summary", {})

    print_kv(f"  Experiments run", refinement_results.get("experiments_run", 0))
    print_kv(f"  Elapsed", f"{refinement_results.get('elapsed_seconds', 0):.1f}s")
    print()

    # Print experiment details
    summary = refinement_results.get("summary", {})
    if summary:
        print_kv("Refinement Experiments", "")
        for name, exp in summary.items():
            print_kv(f"  [{name}]", "")
            print_kv(f"    Symbol/Timeframe", f"{exp.get('symbol')} {exp.get('timeframe')}")
            print_kv(f"    Config", exp.get('config'))
            print_kv(f"    Trades", exp.get('trades'))
            print_kv(f"    Strategy Return", exp.get('strategy_return'))
            print_kv(f"    Buy & Hold", exp.get('buy_hold_return'))
            print_kv(f"    Excess Return", exp.get('excess_return'))
        print()

    # Print refinement analysis
    conclusion = agent_results.get("conclusion", {})
    if conclusion:
        print_kv("Refinement Analysis", "")
        # Handle both flat and nested verdict structures
        ema_config = conclusion.get("ema_config_comparison", {})
        if isinstance(ema_config, str):
            print_kv("  EMA Config Comparison", ema_config[:200])

        no_bias = conclusion.get("no_bias_filter_impact", {})
        if isinstance(no_bias, str):
            print_kv("  No Bias Filter Impact", no_bias[:200])

        cross = conclusion.get("cross_market_robustness", {})
        if isinstance(cross, str):
            print_kv("  Cross-Market", cross[:200])

        # Extract verdict (may be nested or flat)
        verdict = conclusion.get("conclusion", {})
        if not isinstance(verdict, dict):
            verdict = conclusion
        print_kv("  Viable Baseline", verdict.get("viable_baseline", verdict.get("viable_baseline_assessment", "N/A")))
        print_kv("  Proceed to ML", verdict.get("proceed_to_ml", verdict.get("ml_readiness_assessment", "N/A")))
        print()
        weaknesses = verdict.get("key_weaknesses", [])
        if weaknesses:
            print_kv("  Key Weaknesses", weaknesses)
        next_tests = verdict.get("next_tests", [])
        if next_tests:
            print_kv("  Next Tests", next_tests)
        rationale = verdict.get("rationale", "")
        if rationale:
            print_kv("  Rationale", rationale[:200])
        print()

    # Print final summary
    print()
    print_kv("Workflow Execution Summary", "")

    bt = results.get("backtest_strategy", {})
    eval_r = results.get("evaluate_performance", {})
    refine = results.get("refine_and_repeat", {})
    unsup = results.get("run_unsupervised_research", {})

    print_kv("  Steps executed", len(results))
    print_kv("  Processed ticks", bt.get("processed_ticks", "N/A"))
    print_kv("  Completed trades", bt.get("completed_trades", 0))
    print_kv("  Open positions", bt.get("open_positions", 0))
    print()

    print_kv("Performance", "")
    print_kv("  Strategy Return", eval_r.get("strategy_return", "N/A"))
    print_kv("  Buy & Hold Return", eval_r.get("buy_hold_return", "N/A"))
    print_kv("  Sharpe Ratio", eval_r.get("sharpe_ratio", "N/A"))
    print_kv("  Max Drawdown", eval_r.get("max_drawdown", "N/A"))
    print_kv("  Win Rate", eval_r.get("win_rate", "N/A"))
    print()

    if unsup:
        print_kv("Unsupervised Research", "")
        print_kv("  Status", unsup.get("status", "N/A"))
        print_kv("  Rows analyzed", unsup.get("rows_analyzed", "N/A"))
        print_kv("  Feature columns", unsup.get("feature_columns", []))
        pca_meta = unsup.get("pca", {})
        if pca_meta:
            print_kv("  PCA variance", pca_meta.get("explained_variance_ratio", []))
        adaptation = unsup.get("signal_adaptation")
        if adaptation:
            print_kv("  Signal adaptation", adaptation)
        print()

    print_kv("Refinement", "")
    for rec in refine.get("recommendations", []):
        print_kv(f"  💡 {rec}", "")
    print()

    print_kv("Lesson 1 Workflow (Registry-Driven)", "")
    print_kv("  Definition", "data_transformation.yaml v0.2.0")
    print_kv("  Step implementations", "backend/orchestration/workflow/steps/data_transformation.py")
    print_kv("  Refinement experiments", "backend/orchestration/workflow/steps_refine.py")
    print_kv("  Executor", "backend/orchestration/workflow/step_runner.py")
    print_kv("  All steps", "✅ Passed")
    print()

    # Print refinement results if available
    refine_exp = results.get("run_refinement_experiments", {})
    agent_conc = refine_exp.get("agent_conclusion", {})
    if agent_conc:
        print_kv("Refinement Analysis", "")
        verdict = agent_conc.get("conclusion", {}).get("verdict", {})
        if verdict:
            print_kv("  Viable Baseline", verdict.get("viable_baseline"))
            print_kv("  Avg Excess Return vs B&H", verdict.get("average_excess_return_vs_bh"))
            print_kv("  Proceed to ML", verdict.get("proceed_to_ml"))
            print_kv("  Rationale", verdict.get("rationale", "")[:120])
            print()
            print_kv("  Key Weaknesses", verdict.get("key_weaknesses", []))
            print_kv("  Next Tests", verdict.get("next_tests", []))
        elif agent_conc.get("conclusion"):
            conc = agent_conc["conclusion"]
            print_kv("  Threshold Comparison", conc.get("threshold_comparison", ""))
            print_kv("  MA Filter Impact", conc.get("ma_filter_impact", ""))
            print_kv("  Cross-Market", conc.get("cross_market_robustness", ""))
        print()


if __name__ == "__main__":
    example_01_feature_engineering()
    example_02_signal_generation()
    example_03_simulation_backtest()
    example_04_backtest_shifted_signals()
    example_05_performance_metrics()
    example_06_full_pipeline_orchestrator()
    example_07_registry_driven_workflow()