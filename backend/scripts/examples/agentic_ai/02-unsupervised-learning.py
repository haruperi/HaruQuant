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
# Shared sample data for file-based examples
# ======================================================================


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



# ======================================================================
# Shared data / feature / signal helpers  (no duplication across examples)
# ======================================================================

def _load_market_data(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    lookback_days: int = 14,
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
    """Compute EMA features for trend-following strategy."""
    from backend.services.features.pipeline import FeaturePipeline, FeatureSpec

    pipeline = FeaturePipeline([
        FeatureSpec(name="ema", params={"span": fast_period, "price_col": "close"}),
        FeatureSpec(name="ema", params={"span": slow_period, "price_col": "close"}),
        FeatureSpec(name="ema", params={"span": bias_period, "price_col": "close"}),
    ])
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
















def _prepare_lesson2_sample_inputs() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Build deterministic sample features/signals for Lesson 2 examples."""
    from backend.orchestration.workflow.steps_data_transformation import (
        _build_unsupervised_feature_frame,
    )

    sample = _build_sample_ohlcv(n_bars=260)
    featured = _add_features(_prepare_lower_df(sample))
    signaled = _generate_signals(featured)
    feature_frame, feature_columns = _build_unsupervised_feature_frame(signaled)
    return feature_frame, signaled.reindex(feature_frame.index), feature_columns


# ======================================================================
# Examples 13 - 17: Lesson 2 unsupervised learning research layer
# ======================================================================

def example_13_unsupervised_data_summary() -> None:
    """Explore investment data before PCA/K-Means."""
    print_header("Example 13: Unsupervised Learning - Investment Data Summary")
    from backend.services.modeling.unsupervised_insights import summarize_investment_data

    feature_frame, _, feature_columns = _prepare_lesson2_sample_inputs()
    summary = summarize_investment_data(feature_frame)

    print_kv("Rows analyzed", summary.row_count)
    print_kv("Date range", f"{summary.start} -> {summary.end}")
    print_kv("Feature columns", feature_columns)
    print_kv("Duplicate timestamps", summary.duplicate_index_count)
    print()
    print_kv("Return stats", "")
    for key, value in summary.return_stats.items():
        print_kv(f"  {key}", f"{value:+.6f}")
    print()


def example_14_pca_risk_factor_analysis() -> None:
    """Reduce feature space and interpret dominant PCA loadings."""
    print_header("Example 14: PCA Risk Factor Analysis")
    from backend.services.modeling.unsupervised import run_pca
    from backend.services.modeling.unsupervised_insights import identify_pca_risk_factors

    feature_frame, _, feature_columns = _prepare_lesson2_sample_inputs()
    pca = run_pca(feature_frame, feature_columns=feature_columns, n_components=2)
    risk_factors = identify_pca_risk_factors(pca, top_n_per_component=2)

    print_kv("PCA metadata", pca.to_metadata())
    print()
    print_kv("Dominant risk-factor loadings", "")
    for factor in risk_factors:
        print_kv(
            f"  {factor.component} / {factor.feature}",
            f"loading={factor.loading:+.4f}, variance={factor.explained_variance_ratio:.4f}",
        )
    print()


def example_15_kmeans_regime_clustering() -> None:
    """Cluster market-feature rows into unsupervised regimes."""
    print_header("Example 15: K-Means Regime Clustering")
    from backend.services.modeling.unsupervised import (
        attach_cluster_labels,
        cluster_feature_space,
    )

    feature_frame, _, feature_columns = _prepare_lesson2_sample_inputs()
    clusters = cluster_feature_space(
        feature_frame,
        feature_columns=feature_columns,
        n_clusters=3,
        random_state=42,
    )
    labeled = attach_cluster_labels(feature_frame, clusters)

    print_kv("Cluster metadata", clusters.to_metadata())
    print()
    print_kv("Cluster counts", "")
    for label, count in labeled["cluster_label"].value_counts().sort_index().items():
        print_kv(f"  Cluster {label}", int(count))
    print()


def example_16_cluster_outperformance_and_signal_filter() -> None:
    """Score clusters by forward returns and adapt entries by cluster quality."""
    print_header("Example 16: Cluster Outperformance and Signal Filter")
    from backend.services.modeling.unsupervised_insights import (
        build_unsupervised_insight_report,
    )

    feature_frame, signaled, feature_columns = _prepare_lesson2_sample_inputs()
    report = build_unsupervised_insight_report(
        feature_frame,
        feature_columns=feature_columns,
        n_components=2,
        n_clusters=3,
        random_state=42,
        signal_frame=signaled,
    )

    print_kv("Cluster outperformance", "")
    for item in report.cluster_outperformance:
        print_kv(
            f"  Cluster {item.cluster_label}",
            (
                f"n={item.observations}, forward={item.mean_forward_return:+.6f}, "
                f"hit_rate={item.hit_rate:.2f}, excess={item.outperformance_vs_overall:+.6f}"
            ),
        )
    print()
    if report.signal_adaptation is not None:
        print_kv("Signal adaptation", report.signal_adaptation.to_metadata())
    print()


def example_17_registry_driven_unsupervised_workflow() -> None:
    """Run the Lesson 2 step through the workflow step registry."""
    print_header("Example 17: Registry-Driven Unsupervised Workflow Stage")
    from backend.orchestration.workflow.steps_data_transformation import (
        WorkflowContext,
        step_run_unsupervised_research,
    )

    feature_frame, signaled, _ = _prepare_lesson2_sample_inputs()
    ctx = WorkflowContext()
    ctx["featured"] = feature_frame
    ctx["signaled"] = signaled

    result = step_run_unsupervised_research(ctx)

    print_kv("Status", result.get("status"))
    print_kv("Rows analyzed", result.get("rows_analyzed"))
    print_kv("Feature columns", result.get("feature_columns", []))
    print_kv("PCA", result.get("pca", {}))
    print_kv("Clusters", result.get("clusters", {}))
    print()
    print_kv("Signal adaptation", result.get("signal_adaptation"))
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
        example_13_unsupervised_data_summary,
        example_14_pca_risk_factor_analysis,
        example_15_kmeans_regime_clustering,
        example_16_cluster_outperformance_and_signal_filter,
        example_17_registry_driven_unsupervised_workflow,
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
