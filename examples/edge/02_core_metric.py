#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from _workflow_common import build_progressive_outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Edge Core Metric on real MT5 data.")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--bars", type=int, default=300)
    args = parser.parse_args()

    outputs = build_progressive_outputs(args.symbol, args.timeframe, args.bars)
    summary = outputs["core_metric"]["summary"]
    values = outputs["core_metric"]["values"][:12]

    print("Core Metric")
    print(f"symbol={args.symbol} timeframe={args.timeframe}")
    print(f"is_valid={summary.get('is_valid')} warnings={summary.get('warning_count')}")
    for row in values:
        print(f"{row['family']}.{row['metric_key']} = {row['value']}")


if __name__ == "__main__":
    main()
