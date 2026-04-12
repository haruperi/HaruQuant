"""Profile-aware calibration aggregation for Market Structure."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from backend.services.research.market_structure_calibration import evaluate_calibration_candidates
from backend.services.research.market_structure_profiles import resolve_market_structure_profile


def evaluate_profile_calibration(
    run_rows: Iterable[Dict[str, Any]],
    validation_rows: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    grouped_runs: Dict[str, List[Dict[str, Any]]] = {}
    validation_list = list(validation_rows)

    for run in run_rows:
        symbol = str(run.get("symbol") or "")
        timeframe = str(run.get("timeframe") or "")
        profile = resolve_market_structure_profile(symbol, timeframe)
        grouped_runs.setdefault(profile["profile_key"], []).append(run)

    rows: List[Dict[str, Any]] = []
    for profile_key, runs in grouped_runs.items():
        report = evaluate_calibration_candidates(runs, validation_list)
        best = report.get("best")
        if not best:
            continue
        symbol_group, timeframe_group = profile_key.split("::", 1)
        rows.append(
            {
                "profile_key": profile_key,
                "symbol_class": symbol_group,
                "timeframe_bucket": timeframe_group,
                "candidate_count": report.get("total_candidates", 0),
                "best": best,
            }
        )

    rows.sort(
        key=lambda item: (
            float(((item.get("best") or {}).get("accuracy")) or 0.0),
            int(((item.get("best") or {}).get("matched_runs")) or 0),
        ),
        reverse=True,
    )
    return {
        "profile_count": len(rows),
        "rows": rows,
    }
