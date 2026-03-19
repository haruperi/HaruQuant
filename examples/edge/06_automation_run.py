#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.api.routes.edge import _run_edge_lab_symbol_profile_sync


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the backend Edge automation pipeline on MT5 data.")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--bars", type=int, default=300)
    parser.add_argument("--save-snapshot", action="store_true")
    parser.add_argument("--use-cache", action="store_true")
    parser.add_argument("--force-rerun", action="store_true")
    parser.add_argument("--user-id", type=int, default=1)
    args = parser.parse_args()

    result = _run_edge_lab_symbol_profile_sync(
        symbol=args.symbol,
        timeframe=args.timeframe,
        data_source="mt5",
        range_by="bars",
        start_date=None,
        end_date=None,
        number_of_bars=args.bars,
        metric_families=None,
        save_snapshot=args.save_snapshot,
        use_cache=args.use_cache,
        force_rerun=args.force_rerun,
        trigger_type="example",
        run_reason="examples.edge.06_automation_run",
        user_id=args.user_id,
    )

    print("Automation Run")
    print(f"status={result.get('status')}")
    print(f"symbol={result.get('symbol')} timeframe={result.get('timeframe')}")
    print(f"final_score={result.get('scorecard_summary', {}).get('final_score')}")
    print(f"final_label={result.get('scorecard_summary', {}).get('final_label')}")
    print(f"readiness={result.get('scorecard_summary', {}).get('readiness_label')}")
    print(f"snapshot_saved={result.get('snapshot_saved')}")
    print(f"stage_timings={result.get('automation_metadata', {}).get('stage_timings')}")


if __name__ == "__main__":
    main()
