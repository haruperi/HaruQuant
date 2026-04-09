"""Execution readiness validators for pre-submit broker safety checks."""

from __future__ import annotations

from dataclasses import dataclass, field

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


__all__ = [
    "ReadinessCheckResult",
    "validate_market_open",
]
