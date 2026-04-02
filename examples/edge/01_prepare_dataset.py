#!/usr/bin/env python
"""Example 01: Prepare Dataset.

Type: live-broker dependent manual demo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from _workflow_common import prepare_mt5_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare one Edge Lab dataset from MT5.")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--bars", type=int, default=300)
    args = parser.parse_args()

    prepared = prepare_mt5_dataset(args.symbol, args.timeframe, args.bars)
    print("Prepared dataset")
    print(f"symbol={args.symbol} timeframe={args.timeframe} rows={len(prepared.data)}")
    print(f"valid={prepared.report.is_valid}")
    print(f"warnings={len(prepared.report.warnings)} fatal_errors={len(prepared.report.fatal_errors)}")
    print(prepared.data[["Open", "High", "Low", "Close", "Volume", "Spread", "session"]].tail(5).to_string())


if __name__ == "__main__":
    main()
