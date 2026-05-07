"""Simple deterministic replay clock for Python-side simulator playback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass
class ReplayClock:
    """Deterministic replay cursor over pre-built timeline points."""

    timeline: List[object]
    index: int = 0

    @classmethod
    def from_timeline(cls, timeline: Iterable[object]) -> "ReplayClock":
        return cls(list(timeline), index=0)

    @property
    def finished(self) -> bool:
        return self.index >= len(self.timeline)

    @property
    def current(self) -> Optional[object]:
        if self.finished:
            return None
        return self.timeline[self.index]

    def reset(self) -> None:
        self.index = 0

    def advance(self) -> Optional[object]:
        if self.finished:
            return None
        current = self.timeline[self.index]
        self.index += 1
        return current

    def step(self, count: int = 1) -> Optional[object]:
        if count <= 0:
            return self.current
        out = None
        for _ in range(count):
            out = self.advance()
            if out is None:
                break
        return out
