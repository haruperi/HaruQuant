"""Shared Edge Lab session windows and helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

EDGE_SESSION_WINDOWS: dict[str, tuple[int, ...]] = {
    "sydney": tuple(range(0, 7)),
    "tokyo": tuple(range(2, 9)),
    "london": tuple(range(10, 17)),
    "ny": tuple(range(15, 22)),
}

EDGE_SESSION_ORDER: tuple[str, ...] = (
    "sydney",
    "tokyo",
    "sydney_tokyo",
    "london",
    "london_ny",
    "ny",
    "gap",
)


def active_sessions_for_hour(
    hour: int,
    session_windows: Mapping[str, Sequence[int]] | None = None,
) -> list[str]:
    windows = session_windows or EDGE_SESSION_WINDOWS
    active: list[str] = []
    for session_name, hours in windows.items():
        if int(hour) in hours:
            active.append(str(session_name))
    return active


def session_label_for_hour(
    hour: int,
    session_windows: Mapping[str, Sequence[int]] | None = None,
) -> str:
    active = active_sessions_for_hour(hour, session_windows=session_windows)
    return "_".join(active) if active else "gap"


def session_hours_payload(
    session_windows: Mapping[str, Sequence[int]] | None = None,
) -> dict[str, list[int]]:
    windows = session_windows or EDGE_SESSION_WINDOWS
    return {str(name): [int(hour) for hour in hours] for name, hours in windows.items()}
