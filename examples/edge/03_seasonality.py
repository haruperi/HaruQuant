#!/usr/bin/env python
"""Example 03: Seasonality.

Type: live-broker dependent manual demo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from _workflow_common import build_progressive_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Edge Seasonality on real MT5 data.")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--bars", type=int, default=300)
    args = parser.parse_args()

    outputs = build_progressive_outputs(args.symbol, args.timeframe, args.bars)
    seasonality = outputs["seasonality"]
    windows = seasonality.get("opportunity_windows") or {}

    print("Seasonality")
    print(f"symbol={args.symbol} timeframe={args.timeframe}")
    print(f"filtered_rows={seasonality.get('meta', {}).get('filtered_rows')}")
    print("Best sessions:")
    for row in (windows.get("best_sessions") or [])[:3]:
        print(f"  {row['session']}: {row['opportunity_score']:.1f}/100")
    print("Best hours:")
    for row in (windows.get("best_hours") or [])[:3]:
        print(f"  hour {row['hour']}: {row['opportunity_score']:.1f}/100")


if __name__ == "__main__":
    main()
