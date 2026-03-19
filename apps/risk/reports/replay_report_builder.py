"""Replay and what-if report builder."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


def build_replay_report(
    replay_frames: list[dict[str, Any]],
    *,
    run: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build a compact report from stored replay frames."""
    first = replay_frames[0] if replay_frames else {}
    last = replay_frames[-1] if replay_frames else {}
    return {
        "generated_at": datetime.now().isoformat(),
        "run": run,
        "frame_count": len(replay_frames),
        "first_timestamp": first.get("frame_timestamp"),
        "last_timestamp": last.get("frame_timestamp"),
        "frames": replay_frames,
        "summary": {
            "start_overall_score": (first.get("score_summary_json") or {}).get("overall_risk_quality_score"),
            "end_overall_score": (last.get("score_summary_json") or {}).get("overall_risk_quality_score"),
            "last_governance_status": ((last.get("cockpit_payload_json") or {}).get("governance") or {}).get("status"),
            "last_regime_name": ((last.get("cockpit_payload_json") or {}).get("regime") or {}).get("name"),
            "what_if_available": any(frame.get("what_if_summary_json") for frame in replay_frames),
        },
    }
