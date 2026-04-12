#!/usr/bin/env python
"""Example 04: Market Structure.

Type: live-broker dependent manual demo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from _workflow_common import build_progressive_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Edge Market Structure on real MT5 data.")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--bars", type=int, default=300)
    args = parser.parse_args()

    outputs = build_progressive_outputs(args.symbol, args.timeframe, args.bars)
    summary = outputs["market_structure"]["summary"]
    strategy_fit = ((summary.get("strategy_fit") or {}).get("primary") or {})

    print("Market Structure")
    print(f"symbol={args.symbol} timeframe={args.timeframe}")
    print(f"verdict={summary.get('verdict')} final_score={summary.get('final_score'):.2f}")
    print(f"trend_bias={summary.get('trend_bias_score'):.2f} reversion_bias={summary.get('reversion_bias_score'):.2f}")
    print(f"decision_confidence={summary.get('decision_confidence_score'):.2f}")
    print(f"regime_state={summary.get('regime_state')}")
    if strategy_fit:
        print(f"primary_strategy_fit={strategy_fit.get('archetype')} ({strategy_fit.get('fit_score'):.1f})")


if __name__ == "__main__":
    main()
