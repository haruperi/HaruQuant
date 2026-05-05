"""Refinement step implementations for the data_transformation workflow.

These steps run AFTER the initial backtest to compare multiple strategy
configurations and produce agent-driven conclusions.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from haruquant.utils import logger


# ======================================================================
# Configuration for refinement experiments
# ======================================================================

EMA_CONFIGS = {
    "baseline": {"fast_period": 20, "slow_period": 50, "bias_period": 200},
    "faster": {"fast_period": 12, "slow_period": 50, "bias_period": 200},
    "slower": {"fast_period": 25, "slow_period": 60, "bias_period": 200},
    "no_bias": {"fast_period": 20, "slow_period": 50, "bias_period": None},
}

SYMBOLS_TO_TEST = ["EURUSD", "GBPUSD"]
TIMEFRAMES_TO_TEST = ["H1", "D1"]


# ======================================================================
# Backtest helper functions
# ======================================================================

def _run_single_backtest(
    symbol: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
    fast_period: int = 20,
    slow_period: int = 50,
    bias_period: Optional[int] = 200,
    lot_size: float = 0.1,
    initial_balance: float = 10000.0,
) -> Dict[str, Any]:
    """Run a single backtest and return metrics."""
    from haruquant.data import FeaturePipeline, FeatureSpec, load_mt5
    from haruquant.execution import SymbolInfo
    from haruquant.strategy import EmaCrossBaselineStrategy
    from haruquant.utils import normalize_columns
    from haruquant.simulation import Engine

    raw_df = load_mt5(
        symbol=symbol, timeframe=timeframe,
        start_date=start_date, end_date=end_date,
    )
    if raw_df is None or raw_df.empty:
        return {"error": f"No data for {symbol} {timeframe}"}

    normalized = normalize_columns(raw_df)
    lower_df = normalized.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume", "Spread": "spread",
    })

    # Features: EMA cross
    features = [
        FeatureSpec(name="ema", params={"span": fast_period, "price_col": "close"}),
        FeatureSpec(name="ema", params={"span": slow_period, "price_col": "close"}),
    ]
    if bias_period:
        features.append(
            FeatureSpec(name="ema", params={"span": bias_period, "price_col": "close"}),
        )

    pipeline = FeaturePipeline(features)
    featured = pipeline.compute_batch(lower_df)

    # Strategy
    strategy_params = {
        "symbol": symbol,
        "strategy_id": f"ema-{fast_period}-{slow_period}",
        "fast_period": fast_period,
        "slow_period": slow_period,
    }
    if bias_period:
        strategy_params["bias_period"] = bias_period

    strategy = EmaCrossBaselineStrategy(strategy_params)
    strategy.on_init()
    signaled = strategy.on_bar(featured)

    # Shift signals to prevent lookahead bias
    default = pd.Series(0.0, index=signaled.index)
    entry = signaled.get("entry_signal", default).shift(1).fillna(0)
    exit_s = signaled.get("exit_signal", default).shift(1).fillna(0)
    price = signaled.get("price", default).shift(1).fillna(0.0)

    entry = pd.to_numeric(entry, errors="coerce").fillna(0.0)
    exit_s = pd.to_numeric(exit_s, errors="coerce").fillna(0.0)
    price = pd.to_numeric(price, errors="coerce").fillna(0.0)

    # Build tick DataFrame
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

    # Run engine
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
    account["leverage"] = 400
    account["commission"] = 7.0

    engine.configure_run_schedule(
        positions_every=1, pending_orders_every=1,
        account_every=4, portfolio_every=4, risk_every=4,
    )
    processed = engine.run(
        tick_df,
        engine_type="event_driven",
        position_size=lot_size,
        monitor_verbose=False, show_progress=False,
    )

    acc = engine.account_info()
    final_balance = float(acc.get("balance", initial_balance))
    strategy_return = (final_balance / initial_balance) - 1.0

    # Buy & hold return
    first_close = float(signaled["close"].iloc[0])
    last_close = float(signaled["close"].iloc[-1])
    bh_return = (last_close / first_close) - 1.0 if first_close > 0 else 0.0

    trades = engine.get_completed_trades()
    n_signals = int((entry != 0).sum())
    n_trades = len(trades)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "fast_period": fast_period,
        "slow_period": slow_period,
        "bias_period": bias_period,
        "bars": len(signaled),
        "signals": n_signals,
        "trades": n_trades,
        "final_balance": final_balance,
        "strategy_return": strategy_return,
        "buy_hold_return": bh_return,
        "excess_return": strategy_return - bh_return,
    }


# ======================================================================
# Step: run_refinement_experiments
# ======================================================================

def step_run_refinement_experiments(
    ctx: dict,
    *,
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    lot_size: float = 0.1,
    initial_balance: float = 10000.0,
) -> Dict[str, Any]:
    """Run multiple backtests with different EMA configurations.

    Tests:
    1. Baseline EMA(20/50/200)
    2. Faster EMA(12/50/200)
    3. Slower EMA(25/60/200)
    4. No bias filter EMA(20/50)
    5. Cross-symbol test (GBPUSD)
    6. Cross-timeframe test (D1)
    """
    logger.info("Refinement: running multi-configuration backtests")
    t0 = time.time()

    # Default to 2025 full year if not specified
    if start_date is None:
        start_date = datetime(2025, 1, 1)
    if end_date is None:
        end_date = datetime(2025, 12, 31)

    results = {}

    # 1. Baseline (20/50/200)
    results["baseline_20_50_200"] = _run_single_backtest(
        symbol=symbol, timeframe=timeframe,
        start_date=start_date, end_date=end_date,
        fast_period=20, slow_period=50, bias_period=200,
        lot_size=lot_size, initial_balance=initial_balance,
    )

    # 2. Faster (12/50/200)
    results["faster_12_50_200"] = _run_single_backtest(
        symbol=symbol, timeframe=timeframe,
        start_date=start_date, end_date=end_date,
        fast_period=12, slow_period=50, bias_period=200,
        lot_size=lot_size, initial_balance=initial_balance,
    )

    # 3. Slower (25/60/200)
    results["slower_25_60_200"] = _run_single_backtest(
        symbol=symbol, timeframe=timeframe,
        start_date=start_date, end_date=end_date,
        fast_period=25, slow_period=60, bias_period=200,
        lot_size=lot_size, initial_balance=initial_balance,
    )

    # 4. No bias filter (20/50)
    results["no_bias_20_50"] = _run_single_backtest(
        symbol=symbol, timeframe=timeframe,
        start_date=start_date, end_date=end_date,
        fast_period=20, slow_period=50, bias_period=None,
        lot_size=lot_size, initial_balance=initial_balance,
    )

    # 5. Cross-symbol: GBPUSD baseline
    results["cross_symbol_gbpusd"] = _run_single_backtest(
        symbol="GBPUSD", timeframe=timeframe,
        start_date=start_date, end_date=end_date,
        fast_period=20, slow_period=50, bias_period=200,
        lot_size=lot_size, initial_balance=initial_balance,
    )

    # 6. Cross-timeframe: D1 baseline (needs more days)
    d1_start = start_date - timedelta(days=365)
    results["cross_timeframe_d1"] = _run_single_backtest(
        symbol=symbol, timeframe="D1",
        start_date=d1_start, end_date=end_date,
        fast_period=20, slow_period=50, bias_period=200,
        lot_size=lot_size, initial_balance=initial_balance,
    )

    elapsed = time.time() - t0
    logger.info(f"Refinement: completed {len(results)} experiments in {elapsed:.1f}s")

    ctx["refinement_results"] = results
    return {
        "status": "COMPLETED",
        "experiments_run": len(results),
        "elapsed_seconds": round(elapsed, 1),
        "summary": {
            k: {
                "symbol": v.get("symbol"),
                "timeframe": v.get("timeframe"),
                "config": f"EMA({v.get('fast_period')}/{v.get('slow_period')}/{v.get('bias_period')})",
                "trades": v.get("trades"),
                "strategy_return": f"{v.get('strategy_return', 0)*100:.2f}%",
                "buy_hold_return": f"{v.get('buy_hold_return', 0)*100:.2f}%",
                "excess_return": f"{v.get('excess_return', 0)*100:.2f}%",
            }
            for k, v in results.items()
            if "error" not in v
        },
    }


# ======================================================================
# Step: agent_evaluate_and_conclude
# ======================================================================

def step_agent_evaluate_and_conclude(
    ctx: dict,
    *,
    agent_runtime: Any = None,
) -> Dict[str, Any]:
    """Use LLM agent to analyze refinement results and produce conclusions.

    If agent_runtime is None, returns a deterministic analysis instead.
    """
    results = ctx.get("refinement_results", {})

    if not results:
        return {
            "status": "FAILED",
            "reason": "No refinement results available",
        }

    # Build the analysis context for the agent
    analysis_input = _build_analysis_context(results)

    if agent_runtime is not None:
        # Agent-based analysis
        return _run_agent_analysis(agent_runtime, analysis_input, ctx)
    else:
        # Deterministic fallback analysis
        return _deterministic_analysis(analysis_input, ctx)


def _build_analysis_context(results: Dict[str, Any]) -> str:
    """Format refinement results into a text prompt for the agent."""
    lines = ["# Refinement Experiment Results\n"]

    for name, r in results.items():
        if "error" in r:
            lines.append(f"\n## {name}: ERROR - {r['error']}")
            continue
        lines.append(f"\n## {name}")
        lines.append(f"- Symbol: {r['symbol']} {r['timeframe']}")
        lines.append(f"- Signals generated: {r['signals']}")
        lines.append(f"- Strategy return: {r['strategy_return']*100:.2f}%")
        lines.append(f"- Buy & hold return: {r['buy_hold_return']*100:.2f}%")
        lines.append(f"- Excess return: {r['excess_return']*100:.2f}%")
        lines.append(f"- Final balance: ${r['final_balance']:,.2f}")

    return "\n".join(lines)


def _run_agent_analysis(
    agent_runtime: Any,
    analysis_input: str,
    ctx: dict,
) -> Dict[str, Any]:
    """Run the LLM agent to analyze results."""
    from datetime import datetime, timezone
    from backend.config.agent_model import AGENT_MODEL
    from backend.agents.runtime import (
        ADKRunRequest,
        ADKRunnerConfig,
        ADKRunnerService,
        create_llm_runtime,
    )
    from backend.orchestration.workflow import REFINE_AGENT_INSTRUCTION

    logger.info("Refinement: running LLM agent analysis")

    runtime = create_llm_runtime(model=AGENT_MODEL)
    config = ADKRunnerConfig(runner_name="refine_runner")
    runner = ADKRunnerService(config=config)

    request = ADKRunRequest(
        workflow_id="data_transformation",
        correlation_id=f"refine-{int(time.time())}",
        agent_name="refine_agent",
        input_payload={
            "_system_prompt": REFINE_AGENT_INSTRUCTION,
            "analysis_input": analysis_input,
            "contract_type": "RefinementReport",
            "schema_version": "1.0.0",
        },
    )

    try:
        result = runner.run(agent=runtime, request=request)
        raw_output = result.output_payload

        # Build the proper envelope around the LLM's output
        envelope = {
            "schema_version": "1.0.0",
            "contract_type": "RefinementReport",
            "workflow_id": "data_transformation",
            "correlation_id": request.correlation_id,
            "causation_id": request.correlation_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "originator": {"type": "agent", "id": "refine_agent"},
            "environment": "dev",
            "operating_mode": "MODE-000",
            "payload": raw_output if isinstance(raw_output, dict) else {"raw": str(raw_output)},
            "tenant_id": None,
            "account_scope_id": None,
            "strategy_scope_id": None,
            "compliance_profile_id": None,
            "content_hash": None,
            "signature": None,
            "trace_id": None,
            "replay_bundle_hint": None,
        }

        from backend.contracts import validate_contract_payload, load_initial_schema_registry_seeds, SchemaRegistryService
        registry = SchemaRegistryService(load_initial_schema_registry_seeds())
        validate_contract_payload(envelope, registry)

        # Extract just the payload for the conclusion
        conclusion = envelope.get("payload", raw_output)
        ctx["agent_conclusion"] = conclusion
        return {
            "status": "COMPLETED",
            "analysis_type": "agent_based",
            "model": AGENT_MODEL,
            "conclusion": conclusion,
        }
    except Exception as exc:
        logger.warning(f"Refinement: agent analysis failed, using deterministic: {exc}")
        return _deterministic_analysis(analysis_input, ctx)


def _deterministic_analysis(
    analysis_input: str,
    ctx: dict,
) -> Dict[str, Any]:
    """Produce a deterministic analysis when LLM is unavailable."""
    results = ctx.get("refinement_results", {})
    valid_results = {k: v for k, v in results.items() if "error" not in v}

    if not valid_results:
        return {
            "status": "FAILED",
            "reason": "No valid refinement results to analyze",
        }

    # EMA config comparison
    baseline = valid_results.get("baseline_20_50_200", {})
    faster = valid_results.get("faster_12_50_200", {})
    slower = valid_results.get("slower_25_60_200", {})
    no_bias = valid_results.get("no_bias_20_50", {})

    # Find best config
    configs = [("baseline", baseline), ("faster", faster), ("slower", slower), ("no_bias", no_bias)]
    best_config = max(
        [(name, r.get("strategy_return", -999)) for name, r in configs if r],
        key=lambda x: x[1],
        default=("unknown", 0),
    )

    config_conclusion = f"Best config: {best_config[0]} with {best_config[1]*100:.2f}% return"

    # No bias filter impact
    no_bias_conclusion = "No bias filter comparison available"
    if baseline and no_bias:
        b_ret = baseline.get("strategy_return", 0)
        nb_ret = no_bias.get("strategy_return", 0)
        b_trades = baseline.get("trades", 0)
        nb_trades = no_bias.get("trades", 0)
        no_bias_conclusion = (
            f"No bias filter: {nb_ret*100:.2f}% vs baseline {b_ret*100:.2f}%. "
            f"Trades: {nb_trades} vs {b_trades}."
        )

    # Cross-market
    gbp = valid_results.get("cross_symbol_gbpusd", {})
    d1 = valid_results.get("cross_timeframe_d1", {})

    cross_conclusion = "Cross-market data insufficient"
    if gbp or d1:
        parts = []
        if gbp:
            parts.append(f"GBPUSD: {gbp.get('strategy_return', 0)*100:.2f}%")
        if d1:
            parts.append(f"D1: {d1.get('strategy_return', 0)*100:.2f}%")
        cross_conclusion = " ".join(parts)

    # Overall verdict
    excess_returns = [
        v.get("excess_return", 0) for v in valid_results.values()
    ]
    avg_excess = np.mean(excess_returns) if excess_returns else 0

    viable = any(r.get("strategy_return", 0) > 0 for r in [baseline, faster, slower, no_bias])
    proceed_to_ml = viable and avg_excess > -0.05

    conclusion = {
        "ema_config_comparison": config_conclusion,
        "no_bias_filter_impact": no_bias_conclusion,
        "cross_market_robustness": cross_conclusion,
        "verdict": {
            "viable_baseline": viable,
            "average_excess_return_vs_bh": f"{avg_excess*100:.2f}%",
            "key_weaknesses": [
                "EMA crossover struggles in ranging/choppy markets",
                "200-period bias filter causes late entries in strong trends",
                "No stop-loss or take-profit logic",
                "Single indicator — no regime awareness",
            ],
            "next_tests": [
                "Add ATR-based stop-loss and take-profit",
                "Test EMA + ADX trend strength filter",
                "Optimize EMA periods via walk-forward analysis",
                "Add position sizing based on volatility",
                "Test without 200-period bias filter",
            ],
            "proceed_to_ml": proceed_to_ml,
            "rationale": (
                f"Average excess return vs buy-and-hold: {avg_excess*100:.2f}%. "
                f"{'Positive or near-neutral excess returns suggest the workflow produces actionable signals. ' if viable else 'Negative excess returns suggest the baseline needs improvement. '}"
                "ML models should replace fixed EMA crossover rules with learned thresholds "
                "and multi-feature signal generation to outperform buy-and-hold."
            ),
        },
    }

    ctx["agent_conclusion"] = conclusion
    return {
        "status": "COMPLETED",
        "analysis_type": "deterministic",
        "conclusion": conclusion,
    }
