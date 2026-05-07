"""Timeline reconstruction helpers for replay-backed risk workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass(frozen=True)
class TimelinePoint:
    """One replay capture point."""

    frame_index: int
    frame_timestamp: pd.Timestamp
    capture_timestamp: pd.Timestamp


class TimelineReconstructor:
    """Build deterministic replay capture plans from merged market timelines."""

    def build_timeline(
        self,
        data: pd.DataFrame,
        frame_mode: str = "bar",
    ) -> List[TimelinePoint]:
        if data is None or data.empty:
            return []
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Replay timeline data must use a DatetimeIndex.")

        mode = str(frame_mode).strip().lower()
        if mode not in {"bar", "tick", "timestamp"}:
            raise ValueError("frame_mode must be one of: bar, tick, timestamp.")

        points: List[TimelinePoint] = []
        if mode in {"tick", "timestamp"}:
            unique_times = pd.DatetimeIndex(pd.Index(data.index).unique()).sort_values()
            for idx, ts in enumerate(unique_times):
                timestamp = pd.Timestamp(ts)
                points.append(
                    TimelinePoint(
                        frame_index=idx,
                        frame_timestamp=timestamp,
                        capture_timestamp=timestamp,
                    )
                )
            return points

        if "source_bar_time" in data.columns:
            grouped = data.groupby("source_bar_time", sort=True)
            for idx, (frame_timestamp, frame_data) in enumerate(grouped):
                points.append(
                    TimelinePoint(
                        frame_index=idx,
                        frame_timestamp=pd.Timestamp(frame_timestamp),
                        capture_timestamp=pd.Timestamp(frame_data.index[-1]),
                    )
                )
            return points

        unique_times = pd.DatetimeIndex(pd.Index(data.index).unique()).sort_values()
        for idx, ts in enumerate(unique_times):
            timestamp = pd.Timestamp(ts)
            points.append(
                TimelinePoint(
                    frame_index=idx,
                    frame_timestamp=timestamp,
                    capture_timestamp=timestamp,
                )
            )
        return points

    def timeline_signature(
        self,
        timeline: List[TimelinePoint],
        frame_mode: str = "bar",
    ) -> str:
        if not timeline:
            return f"{frame_mode}:empty"
        first = timeline[0].frame_timestamp.isoformat()
        last = timeline[-1].frame_timestamp.isoformat()
        return f"{frame_mode}:{len(timeline)}:{first}:{last}"
