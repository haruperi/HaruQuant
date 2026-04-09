"""Shared clock and freshness helpers for migration-era services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Mapping, Protocol

from apps.utils.datetime_utils import parse_datetime


UTC = timezone.utc
FreshnessClass = Literal["HOT", "WARM", "COOL", "COLD"]
BoardBaselineArtifact = Literal[
    "best_bid_ask_tick",
    "spread_snapshot",
    "symbol_tradability_status",
    "account_equity_free_margin_snapshot",
    "open_positions_snapshot",
    "risk_decision",
    "correlation_matrix",
    "regime_classification",
    "volatility_state_estimate",
    "economic_calendar_blackout_state",
    "strategy_lifecycle_state",
    "compliance_profile_and_approval_policy",
]

BOARD_BASELINE_TTL_POLICY: dict[BoardBaselineArtifact, tuple[FreshnessClass, int, str]] = {
    "best_bid_ask_tick": ("HOT", 2, "Block new entries; allow emergency exits per policy"),
    "spread_snapshot": ("HOT", 2, "Recompute before execution"),
    "symbol_tradability_status": ("HOT", 5, "Revalidate before execution"),
    "account_equity_free_margin_snapshot": ("HOT", 5, "Block new entries"),
    "open_positions_snapshot": ("HOT", 5, "Reconcile before execution"),
    "risk_decision": ("HOT", 30, "Invalidate and recompute"),
    "correlation_matrix": ("WARM", 60, "Recompute before risk approval"),
    "regime_classification": ("WARM", 300, "Re-evaluate before new entry"),
    "volatility_state_estimate": ("WARM", 300, "Re-evaluate sizing inputs"),
    "economic_calendar_blackout_state": ("WARM", 300, "Refresh before execution during active sessions"),
    "strategy_lifecycle_state": ("COOL", 600, "Refresh before approving live action"),
    "compliance_profile_and_approval_policy": (
        "COOL",
        900,
        "Refresh before policy-sensitive action",
    ),
}


class Clock(Protocol):
    """Minimal clock protocol used by workflow and TTL-sensitive services."""

    def now(self) -> datetime:
        """Return the current UTC timestamp."""


class SystemClock:
    """Clock implementation backed by the system wall clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True)
class FixedClock:
    """Deterministic clock for tests and replay-sensitive code."""

    current: datetime

    def now(self) -> datetime:
        return _to_utc(self.current)


def _to_utc(value: Any) -> datetime:
    parsed = parse_datetime(value, assume_tz="UTC")
    return parsed.astimezone(UTC)


@dataclass(frozen=True)
class FreshnessWindow:
    """A freshness result derived from an observed timestamp and a TTL."""

    observed_at: datetime
    checked_at: datetime
    max_age_seconds: int

    @property
    def age_seconds(self) -> float:
        return max((self.checked_at - self.observed_at).total_seconds(), 0.0)

    @property
    def expires_at(self) -> datetime:
        return self.observed_at + timedelta(seconds=self.max_age_seconds)

    @property
    def is_fresh(self) -> bool:
        return self.age_seconds <= float(self.max_age_seconds)

    @property
    def is_stale(self) -> bool:
        return not self.is_fresh


@dataclass(frozen=True)
class BoardBaselineArtifactWindow:
    """Freshness evaluation for one board-baseline artifact."""

    artifact_name: BoardBaselineArtifact
    freshness_class: FreshnessClass
    action_if_stale: str
    window: FreshnessWindow


@dataclass(frozen=True)
class BoardBaselineFreshnessEvaluation:
    """Aggregated board-baseline freshness decision for execution-critical inputs."""

    artifact_windows: tuple[BoardBaselineArtifactWindow, ...]
    checked_at: datetime
    shortest_ttl_seconds: int
    proposal_materially_changed: bool = False
    workflow_pause_exceeded_shortest_ttl: bool = False

    @property
    def stale_artifacts(self) -> tuple[BoardBaselineArtifactWindow, ...]:
        return tuple(window for window in self.artifact_windows if window.window.is_stale)

    @property
    def is_valid(self) -> bool:
        return (
            not self.stale_artifacts
            and not self.proposal_materially_changed
            and not self.workflow_pause_exceeded_shortest_ttl
        )


def evaluate_freshness(
    observed_at: Any,
    *,
    max_age_seconds: int,
    clock: Clock | None = None,
) -> FreshnessWindow:
    """Evaluate whether a timestamp is still fresh under a TTL window."""

    if max_age_seconds < 0:
        raise ValueError("max_age_seconds must be non-negative")

    active_clock = clock or SystemClock()
    return FreshnessWindow(
        observed_at=_to_utc(observed_at),
        checked_at=_to_utc(active_clock.now()),
        max_age_seconds=int(max_age_seconds),
    )


def evaluate_board_baseline_freshness(
    artifact_timestamps: Mapping[BoardBaselineArtifact, Any],
    *,
    proposal_materially_changed: bool = False,
    workflow_paused_at: Any | None = None,
    clock: Clock | None = None,
) -> BoardBaselineFreshnessEvaluation:
    """Evaluate execution-critical artifacts against the board TTL baselines."""

    if not artifact_timestamps:
        raise ValueError("artifact_timestamps must not be empty")

    active_clock = clock or SystemClock()
    checked_at = _to_utc(active_clock.now())
    artifact_windows: list[BoardBaselineArtifactWindow] = []
    shortest_ttl_seconds: int | None = None

    for artifact_name, observed_at in artifact_timestamps.items():
        if artifact_name not in BOARD_BASELINE_TTL_POLICY:
            raise ValueError(f"unsupported board-baseline artifact: {artifact_name}")

        freshness_class, max_age_seconds, action_if_stale = BOARD_BASELINE_TTL_POLICY[artifact_name]
        artifact_windows.append(
            BoardBaselineArtifactWindow(
                artifact_name=artifact_name,
                freshness_class=freshness_class,
                action_if_stale=action_if_stale,
                window=evaluate_freshness(
                    observed_at,
                    max_age_seconds=max_age_seconds,
                    clock=FixedClock(checked_at),
                ),
            )
        )
        shortest_ttl_seconds = (
            max_age_seconds
            if shortest_ttl_seconds is None
            else min(shortest_ttl_seconds, max_age_seconds)
        )

    workflow_pause_exceeded_shortest_ttl = False
    if workflow_paused_at is not None and shortest_ttl_seconds is not None:
        workflow_pause_exceeded_shortest_ttl = is_stale(
            workflow_paused_at,
            max_age_seconds=shortest_ttl_seconds,
            clock=FixedClock(checked_at),
        )

    return BoardBaselineFreshnessEvaluation(
        artifact_windows=tuple(artifact_windows),
        checked_at=checked_at,
        shortest_ttl_seconds=shortest_ttl_seconds or 0,
        proposal_materially_changed=proposal_materially_changed,
        workflow_pause_exceeded_shortest_ttl=workflow_pause_exceeded_shortest_ttl,
    )


def is_stale(
    observed_at: Any,
    *,
    max_age_seconds: int,
    clock: Clock | None = None,
) -> bool:
    """Return True when the observed timestamp is older than the TTL window."""

    return evaluate_freshness(
        observed_at,
        max_age_seconds=max_age_seconds,
        clock=clock,
    ).is_stale
