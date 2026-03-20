#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from _workflow_common import DEFAULT_OUTPUT_DIR, build_progressive_outputs, get_db, save_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Edge Scorecard and optionally save a snapshot.")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--bars", type=int, default=300)
    parser.add_argument("--save-snapshot", action="store_true")
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()

    outputs = build_progressive_outputs(args.symbol, args.timeframe, args.bars)
    scorecard = outputs["scorecard"] or {}

    print("Scorecard")
    print(f"symbol={args.symbol} timeframe={args.timeframe}")
    print(f"final_score={scorecard.get('finalScore'):.2f} label={scorecard.get('finalLabel')}")
    print(f"confidence={scorecard.get('overallConfidence')} readiness={scorecard.get('readiness_label')}")
    primary = ((scorecard.get("strategyFit") or {}).get("primary") or {})
    if primary:
        print(f"primary_strategy={primary.get('archetype')} fit={primary.get('fitScore'):.1f}")

    if args.export:
        outdir = DEFAULT_OUTPUT_DIR / "05_scorecard_snapshot"
        path = save_json(outdir / f"{args.symbol}_{args.timeframe}_scorecard.json", scorecard)
        print(f"saved_json={path}")

    if args.save_snapshot:
        db = get_db()
        snapshot_id = db.save_profile_snapshot(
            {
                "dataset": outputs["dataset"],
                "core_metric_profile": outputs["core_metric"],
                "seasonality_result": outputs["seasonality"],
                "market_structure_profile": outputs["market_structure"],
                "scorecard_report": outputs["scorecard"],
                "automation_metadata": {
                    "trigger_type": "example",
                    "run_reason": "examples.edge.05_scorecard_snapshot",
                },
                "artifacts": [],
            },
            user_id=1,
        )
        print(f"snapshot_id={snapshot_id}")
        if snapshot_id and args.export:
            db.export_profile_snapshot_reports(snapshot_id)
            db.export_profile_snapshot_metrics_parquet(snapshot_id)
            print(f"exported_snapshot_artifacts_for={snapshot_id}")


if __name__ == "__main__":
    main()
