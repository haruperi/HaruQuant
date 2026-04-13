"""AI trading strategy workflow usage example.

Demonstrates the Course 2 workflow foundation using the HaruQuant agentic
runtime surface without live broker access, LLM calls, or network access.

What this example does:
  1. Loads the descriptive project workflow definitions from backend/workflows.
  2. Builds deterministic synthetic OHLCV bars.
  3. Runs the RSI, EMA crossover, and naive momentum baseline strategies.
  4. Converts strategy signals into canonical SignalIntent payloads with
     StrategyAdapter.
  5. Prints a compact baseline comparison that can be used as a smoke check.

Usage:
    python backend/scripts/examples/agentic_ai/04_ai_trading_strategy_workflows.py
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any

import pandas as pd

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.agents.runtime.workflow_definition import WorkflowRegistry
from backend.services.strategy.adapter import StrategyAdapter
from backend.services.strategy.baselines import (
    EmaCrossBaselineStrategy,
    NaiveMomentumStrategy,
    RsiBaselineStrategy,
)


@dataclass(frozen=True)
class StrategyRunSummary:
    """Small printable summary for a deterministic baseline strategy run."""

    strategy_id: str
    workflow_name: str
    bars_processed: int
    signal_count: int
    latest_action: str
    latest_reason: str


def print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_section(label: str, value: Any) -> None:
    if not isinstance(value, str):
        value = json.dumps(value, default=str)
    print(f"  {label:<28s} {value}")


def build_synthetic_bars() -> pd.DataFrame:
    """Build deterministic OHLCV bars with trend and pullback regions."""
    closes = [
        1.1000,
        1.1010,
        1.1025,
        1.1040,
        1.1055,
        1.1070,
        1.1085,
        1.1090,
        1.1080,
        1.1065,
        1.1050,
        1.1035,
        1.1020,
        1.1010,
        1.1000,
        1.1015,
        1.1030,
        1.1050,
        1.1075,
        1.1100,
    ]
    index = pd.date_range("2024-01-01", periods=len(closes), freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "open": closes,
            "high": [close + 0.0010 for close in closes],
            "low": [close - 0.0010 for close in closes],
            "close": closes,
            "volume": [1000 + i * 10 for i in range(len(closes))],
        },
        index=index,
    )


def load_project_workflows() -> dict[str, dict[str, Any]]:
    """Load workflow skeletons through the existing registry."""
    workflow_names = [
        "data_transformation",
        "dynamic_strategy",
        "classification_optimization",
        "rl_trading",
        "momentum_trading",
    ]
    registry = WorkflowRegistry("backend/workflows")
    loaded: dict[str, dict[str, Any]] = {}

    for name in workflow_names:
        definition = registry.load(name)
        loaded[name] = {
            "pattern": definition.pattern.value,
            "version": definition.version,
            "steps": [step.name for step in definition.steps],
        }

    return loaded


def run_strategy(
    *,
    strategy: Any,
    bars: pd.DataFrame,
    workflow_name: str,
) -> tuple[StrategyRunSummary, list[dict[str, Any]]]:
    """Run a baseline strategy and normalize outputs as SignalIntent payloads."""
    processed = strategy.on_bar(bars)
    adapter = StrategyAdapter(strategy, default_qty=1.0)

    intents: list[dict[str, Any]] = []
    for index in range(len(processed)):
        signal = strategy.get_signal(processed, index)
        if signal is None:
            continue

        features = {
            column: processed.iloc[index][column]
            for column in processed.columns
            if column.startswith(("rsi_", "ema_", "momentum_"))
        }
        intent = adapter.build_signal_intent(
            processed,
            index,
            features=features,
            tags=["baseline", workflow_name],
            metadata={
                "workflow": workflow_name,
                "source": "agentic_ai_example",
                "bar_index": index,
            },
        )
        if intent is not None:
            intents.append(dict(intent))

    latest = intents[-1] if intents else {}
    summary = StrategyRunSummary(
        strategy_id=strategy.strategy_id,
        workflow_name=workflow_name,
        bars_processed=len(processed),
        signal_count=len(intents),
        latest_action=str(latest.get("action", "NONE")),
        latest_reason=str(latest.get("reason", "No signal")),
    )
    return summary, intents


def main() -> None:
    print_header("AI Trading Strategy Workflows - Baseline Usage Example")

    workflows = load_project_workflows()
    print_section("Loaded workflows", len(workflows))
    for workflow_name, metadata in workflows.items():
        print_section(
            workflow_name,
            f"{metadata['pattern']} / {len(metadata['steps'])} steps",
        )

    bars = build_synthetic_bars()
    print_header("Synthetic Market Data")
    print_section("Symbol", "EURUSD")
    print_section("Bars", len(bars))
    print_section("Start", bars.index[0])
    print_section("End", bars.index[-1])
    print_section("First close", f"{bars['close'].iloc[0]:.5f}")
    print_section("Last close", f"{bars['close'].iloc[-1]:.5f}")

    strategies = [
        RsiBaselineStrategy(
            {
                "symbol": "EURUSD",
                "strategy_id": "baseline-rsi",
                "period": 3,
                "oversold": 30,
                "overbought": 70,
            }
        ),
        EmaCrossBaselineStrategy(
            {
                "symbol": "EURUSD",
                "strategy_id": "baseline-ema-cross",
                "fast_period": 2,
                "slow_period": 4,
            }
        ),
        NaiveMomentumStrategy(
            {
                "symbol": "EURUSD",
                "strategy_id": "baseline-naive-momentum",
                "lookback": 3,
                "threshold": 0.001,
            }
        ),
    ]

    print_header("Baseline Strategy Runs")
    all_summaries: list[StrategyRunSummary] = []
    all_intents: dict[str, list[dict[str, Any]]] = {}

    for strategy in strategies:
        summary, intents = run_strategy(
            strategy=strategy,
            bars=bars,
            workflow_name="dynamic_strategy",
        )
        all_summaries.append(summary)
        all_intents[summary.strategy_id] = intents

        print_section(summary.strategy_id, "")
        print_section("  signals", summary.signal_count)
        print_section("  latest action", summary.latest_action)
        print_section("  latest reason", summary.latest_reason)

    print_header("Canonical SignalIntent Example")
    first_strategy_with_signal = next(
        (strategy_id for strategy_id, intents in all_intents.items() if intents),
        "",
    )
    if first_strategy_with_signal:
        print(json.dumps(all_intents[first_strategy_with_signal][-1], indent=2, default=str))
    else:
        print("No strategy produced a signal on the synthetic bars.")

    print_header("Strategy Comparison")
    comparison = [
        {
            "strategy_id": summary.strategy_id,
            "workflow": summary.workflow_name,
            "bars": summary.bars_processed,
            "signals": summary.signal_count,
            "latest_action": summary.latest_action,
        }
        for summary in all_summaries
    ]
    print(json.dumps(comparison, indent=2, default=str))


if __name__ == "__main__":
    main()
