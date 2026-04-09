"""Execution readiness validators for pre-submit broker safety checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.core import Clock
from apps.core.time_utils import evaluate_freshness

from .metadata_cache import SymbolMetadataCacheEntry


@dataclass(frozen=True)
class ReadinessCheckResult:
    """Simple allow/deny result for one readiness validator."""

    allowed: bool
    reason_codes: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


def validate_market_open(metadata: SymbolMetadataCacheEntry) -> ReadinessCheckResult:
    """Reject execution when the market is closed for the target symbol."""

    if metadata.market_open:
        return ReadinessCheckResult(allowed=True, metadata={"symbol": metadata.symbol})
    return ReadinessCheckResult(
        allowed=False,
        reason_codes=("market_closed",),
        metadata={"symbol": metadata.symbol},
    )


def validate_symbol_tradability(metadata: SymbolMetadataCacheEntry) -> ReadinessCheckResult:
    """Reject execution when the symbol is currently not tradable."""

    if metadata.tradable:
        return ReadinessCheckResult(allowed=True, metadata={"symbol": metadata.symbol})
    return ReadinessCheckResult(
        allowed=False,
        reason_codes=("symbol_not_tradable",),
        metadata={"symbol": metadata.symbol},
    )


def validate_price_freshness(
    metadata: SymbolMetadataCacheEntry,
    *,
    clock: Clock | None = None,
) -> ReadinessCheckResult:
    """Reject execution when the cached price/metadata snapshot is stale."""

    freshness = evaluate_freshness(
        metadata.observed_at,
        max_age_seconds=metadata.max_age_seconds,
        clock=clock,
    )
    if freshness.is_fresh:
        return ReadinessCheckResult(
            allowed=True,
            metadata={"symbol": metadata.symbol, "expires_at": freshness.expires_at.isoformat()},
        )
    return ReadinessCheckResult(
        allowed=False,
        reason_codes=("stale_price_snapshot",),
        metadata={"symbol": metadata.symbol, "expires_at": freshness.expires_at.isoformat()},
    )


def validate_stop_and_freeze_levels(
    metadata: SymbolMetadataCacheEntry,
    *,
    stop_distance_points: float | None = None,
    modify_distance_points: float | None = None,
) -> ReadinessCheckResult:
    """Reject execution when requested stop or modification distances violate broker rules."""

    reasons: list[str] = []
    if stop_distance_points is not None and stop_distance_points < metadata.stop_level_points:
        reasons.append("stop_level_too_close")
    if modify_distance_points is not None and modify_distance_points < metadata.freeze_level_points:
        reasons.append("freeze_level_too_close")

    return ReadinessCheckResult(
        allowed=not reasons,
        reason_codes=tuple(reasons),
        metadata={
            "symbol": metadata.symbol,
            "stop_level_points": metadata.stop_level_points,
            "freeze_level_points": metadata.freeze_level_points,
        },
    )


def validate_fill_mode_compatibility(
    metadata: SymbolMetadataCacheEntry,
    *,
    requested_fill_mode: str,
) -> ReadinessCheckResult:
    """Reject execution when the requested fill mode is unsupported for the symbol."""

    if requested_fill_mode in metadata.supported_fill_modes:
        return ReadinessCheckResult(
            allowed=True,
            metadata={"symbol": metadata.symbol, "requested_fill_mode": requested_fill_mode},
        )
    return ReadinessCheckResult(
        allowed=False,
        reason_codes=("unsupported_fill_mode",),
        metadata={
            "symbol": metadata.symbol,
            "requested_fill_mode": requested_fill_mode,
            "supported_fill_modes": metadata.supported_fill_modes,
        },
    )


def validate_terminal_connectivity(*, connected: bool) -> ReadinessCheckResult:
    """Reject execution when terminal connectivity is unavailable."""

    if connected:
        return ReadinessCheckResult(allowed=True)
    return ReadinessCheckResult(
        allowed=False,
        reason_codes=("terminal_disconnected",),
    )


__all__ = [
    "ReadinessCheckResult",
    "validate_market_open",
    "validate_price_freshness",
    "validate_stop_and_freeze_levels",
    "validate_symbol_tradability",
    "validate_fill_mode_compatibility",
    "validate_terminal_connectivity",
]
