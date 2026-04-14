"""Step implementations for the data_transformation workflow (Lesson 1).

Each step function maps to one YAML step name and executes the corresponding
operation. These are pure functions that receive context from prior steps
and return structured results — making them reusable across any consumer
(API, UI, CLI, scheduler, examples).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd


class WorkflowContext(dict):
    """Mutable context shared across workflow steps."""
    pass


# ── Step 1: collect_market_data ────────────────────────────────────────

def step_collect_market_data(
    ctx: WorkflowContext,
    *,
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    lookback_days: int = 14,
) -> dict[str, Any]:
    """Collect OHLCV market data from MT5 (with Dukascopy fallback)."""
    from backend.services.market_data.data_getters import load_mt5

    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    raw_df = load_mt5(
        symbol=symbol, timeframe=timeframe,
        start_date=start_date, end_date=end_date,
    )
    if raw_df is None or raw_df.empty:
        raise ValueError(f"No data returned for {symbol} {timeframe}")

    ctx["raw_df"] = raw_df
    return {
        "status": "COMPLETED",
        "bars_loaded": len(raw_df),
        "date_range": f"{raw_df.index[0]} → {raw_df.index[-1]}",
    }


# ── Step 2: clean_and_prepare_data ──────────────────────────────────────

def step_clean_and_prepare_data(
    ctx: WorkflowContext,
) -> dict[str, Any]:
    """Normalize column names and validate data integrity."""
    from backend.services.research.datasets import normalize_columns

    raw_df = ctx["raw_df"]
    normalized = normalize_columns(raw_df)
    lower_df = normalized.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume", "Spread": "spread",
    })
    ctx["lower_df"] = lower_df
    return {
        "status": "COMPLETED",
        "bars_after_clean": len(lower_df),
        "columns": list(lower_df.columns),
    }


# ── Step 3: create_features ─────────────────────────────────────────────

def step_create_features(
    ctx: WorkflowContext,
    *,
    rsi_period: int = 14,
) -> dict[str, Any]:
    """Compute technical indicators via FeaturePipeline."""
    from backend.services.features.pipeline import FeaturePipeline, FeatureSpec

    lower_df = ctx["lower_df"]
    pipeline = FeaturePipeline([
        FeatureSpec(name="rsi", params={"period": rsi_period, "price_col": "close"}),
    ])
    featured = pipeline.compute_batch(lower_df)
    new_cols = [c for c in featured.columns if c not in lower_df.columns]
    ctx["featured"] = featured
    return {
        "status": "COMPLETED",
        "features_added": new_cols,
    }


# ── Step 4: define_strategy_or_model ────────────────────────────────────

def step_define_strategy_or_model(
    ctx: WorkflowContext,
    *,
    strategy: str = "rsi",
    oversold: float = 30.0,
    overbought: float = 70.0,
    period: int = 14,
) -> dict[str, Any]:
    """Declare the strategy configuration."""
    ctx["strategy_config"] = {
        "strategy": strategy,
        "period": period,
        "oversold": oversold,
        "overbought": overbought,
    }
    return {
        "status": "COMPLETED",
        "strategy": strategy,
        "parameters": ctx["strategy_config"],
    }


# ── Step 5: generate_signals ────────────────────────────────────────────

def step_generate_signals(
    ctx: WorkflowContext,
    *,
    symbol: str = "EURUSD",
    use_shift1: bool = True,
) -> dict[str, Any]:
    """Run the strategy and generate entry/exit signals with lookahead prevention."""
    from backend.services.strategy.baselines import RsiBaselineStrategy

    featured = ctx["featured"]
    cfg = ctx["strategy_config"]

    strategy = RsiBaselineStrategy({
        "symbol": symbol,
        "strategy_id": f"{cfg['strategy']}-{cfg['period']}",
        "period": cfg["period"],
        "oversold": cfg["oversold"],
        "overbought": cfg["overbought"],
    })
    strategy.on_init()
    signaled = strategy.on_bar(featured)

    # shift(1) prevents lookahead bias
    default = pd.Series(0.0, index=signaled.index)
    if use_shift1:
        entry = signaled.get("entry_signal", default).shift(1).fillna(0)
        exit_s = signaled.get("exit_signal", default).shift(1).fillna(0)
        price = signaled.get("price", default).shift(1).fillna(0.0)
    else:
        entry = signaled.get("entry_signal", default)
        exit_s = signaled.get("exit_signal", default)
        price = signaled.get("price", default)

    entry = pd.to_numeric(entry, errors="coerce").fillna(0.0)
    exit_s = pd.to_numeric(exit_s, errors="coerce").fillna(0.0)
    price = pd.to_numeric(price, errors="coerce").fillna(0.0)

    ctx["signaled"] = signaled
    ctx["entry"] = entry
    ctx["exit_s"] = exit_s
    ctx["price"] = price

    return {
        "status": "COMPLETED",
        "raw_signals": int((signaled["entry_signal"] != 0).sum()),
        "shifted_signals": int((entry != 0).sum()),
    }


# ── Step 6: backtest_strategy ───────────────────────────────────────────

def step_backtest_strategy(
    ctx: WorkflowContext,
    *,
    symbol: str = "EURUSD",
    initial_balance: float = 10000.0,
    leverage: int = 400,
    commission_per_lot: float = 7.0,
    lot_size: float = 0.1,
) -> dict[str, Any]:
    """Run simulation backtest with the generated signals."""
    from backend.services.execution.core import SymbolInfo
    from backend.services.simulation.engine import Engine

    signaled = ctx["signaled"]
    entry = ctx["entry"]
    exit_s = ctx["exit_s"]
    price = ctx["price"]

    tick_df = pd.DataFrame({
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
    account["commission"] = commission_per_lot

    engine.configure_run_schedule(
        positions_every=1, pending_orders_every=1,
        account_every=4, portfolio_every=4, risk_every=4,
    )
    processed = engine.run(
        tick_df, position_size=lot_size,
        monitor_verbose=False, show_progress=False,
    )

    trades = engine.get_completed_trades()
    open_positions = engine.state.trading_deals if hasattr(engine.state, "trading_deals") else []
    acc = engine.account_info()

    ctx["bt_result"] = {
        "processed": processed,
        "trades": trades,
        "open_positions": open_positions,
        "account": dict(acc) if hasattr(acc, "items") else {},
    }
    return {
        "status": "COMPLETED",
        "processed_ticks": processed,
        "completed_trades": len(trades),
        "open_positions": len(open_positions),
    }


# ── Step 7: evaluate_performance ────────────────────────────────────────

def step_evaluate_performance(
    ctx: WorkflowContext,
    *,
    initial_balance: float = 10000.0,
) -> dict[str, Any]:
    """Compute performance metrics from backtest results."""
    from backend.services.analytics.drawdowns import max_drawdown
    from backend.services.analytics.metrics import win_rate
    from backend.services.analytics.ratios import sharpe_ratio

    bt_result = ctx["bt_result"]
    signaled = ctx["signaled"]
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

    metrics = {
        "total_strategy_return": total_return,
        "total_buy_hold_return": bh_return,
        "sharpe_ratio": sharpe_ratio(trade_returns, annualize=False) if len(trade_returns) > 1 else 0.0,
        "max_drawdown": max_drawdown(pd.Series([1.0 + r for r in trade_returns])) if len(trade_returns) > 0 else 0.0,
        "win_rate": win_rate(trade_returns) if len(trade_returns) > 0 else 0.0,
        "wins": wins,
        "losses": losses,
    }
    ctx["metrics"] = metrics

    return {
        "status": "COMPLETED",
        "strategy_return": f"{metrics['total_strategy_return']*100:.2f}%",
        "buy_hold_return": f"{metrics['total_buy_hold_return']*100:.2f}%",
        "sharpe_ratio": f"{metrics['sharpe_ratio']:.4f}",
        "max_drawdown": f"{metrics['max_drawdown']*100:.2f}%",
        "win_rate": f"{metrics['win_rate']*100:.2f}%",
    }


# ── Step 8: refine_and_repeat ───────────────────────────────────────────

def step_refine_and_repeat(
    ctx: WorkflowContext,
    *,
    workflow_version: str = "0.1.0",
) -> dict[str, Any]:
    """Generate refinement recommendations based on performance results."""
    metrics = ctx.get("metrics", {})
    recommendations: list[str] = []

    if metrics.get("win_rate", 0) < 0.5:
        recommendations.append(
            "Win rate below 50% — consider adjusting RSI thresholds or adding a trend filter"
        )
    if metrics.get("max_drawdown", 0) < -0.05:
        recommendations.append(
            "Max drawdown exceeds 5% — add stop-loss or reduce position size"
        )
    if not recommendations:
        recommendations.append(
            "Strategy is a viable baseline — consider ML feature extensions for Lesson 2+"
        )

    return {
        "status": "COMPLETED",
        "recommendations": recommendations,
        "workflow_version": workflow_version,
    }


# ── Step registry: maps YAML step names → implementations ───────────────

STEP_IMPLEMENTATIONS: dict[str, Any] = {
    "collect_market_data": step_collect_market_data,
    "clean_and_prepare_data": step_clean_and_prepare_data,
    "create_features": step_create_features,
    "define_strategy_or_model": step_define_strategy_or_model,
    "generate_signals": step_generate_signals,
    "backtest_strategy": step_backtest_strategy,
    "evaluate_performance": step_evaluate_performance,
    "refine_and_repeat": step_refine_and_repeat,
}
