"""Shared error taxonomy and typed exceptions for trade validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ErrorDescriptor:
    """Normalized error payload for trade validation."""

    code: int
    name: str
    message: str
    domain: str = "trade"
    retryable: bool = False


class HaruError(Exception):
    """Base app error."""

    def __init__(self, descriptor: ErrorDescriptor, detail: str | None = None) -> None:
        self.descriptor = descriptor
        self.code = descriptor.name.lower()
        self.detail = detail
        text = detail or descriptor.message
        super().__init__(f"[{descriptor.name}] {text} (code={descriptor.code})")


class TradeError(HaruError):
    """Base trade error."""


class InvalidRequestError(TradeError):
    """Invalid request."""


class InvalidVolumeError(TradeError):
    """Invalid volume."""


class InvalidPriceError(TradeError):
    """Invalid price."""


class InvalidStopsError(TradeError):
    """Invalid stops."""


class TradeDisabledError(TradeError):
    """Trade disabled."""


class MarketClosedError(TradeError):
    """Market closed."""


class NoMoneyError(TradeError):
    """Insufficient margin/money."""


class NoQuotesError(TradeError):
    """No quotes available."""


_DEFAULT = ErrorDescriptor(
    code=-1,
    name="UNKNOWN",
    message="Unknown error",
    domain="trade",
    retryable=False,
)

_CODE_TO_EXCEPTION: dict[int, type[TradeError]] = {
    10013: InvalidRequestError,
    10014: InvalidVolumeError,
    10015: InvalidPriceError,
    10016: InvalidStopsError,
    10017: TradeDisabledError,
    10018: MarketClosedError,
    10019: NoMoneyError,
    10021: NoQuotesError,
}


def descriptor_from_payload(payload: Mapping[str, Any] | None, *, fallback_code: int = -1) -> ErrorDescriptor:
    """Build an ErrorDescriptor from broker/error payload."""
    if payload is None:
        return ErrorDescriptor(
            code=fallback_code,
            name=_DEFAULT.name,
            message=_DEFAULT.message,
            domain=_DEFAULT.domain,
            retryable=_DEFAULT.retryable,
        )
    return ErrorDescriptor(
        code=int(payload.get("code", fallback_code)),
        name=str(payload.get("name", _DEFAULT.name)),
        message=str(payload.get("message", _DEFAULT.message)),
        domain=str(payload.get("domain", _DEFAULT.domain)),
        retryable=bool(payload.get("retryable", _DEFAULT.retryable)),
    )


def trade_exception_from_descriptor(descriptor: ErrorDescriptor, detail: str | None = None) -> TradeError:
    """Return typed trade exception for taxonomy descriptor."""
    exc_type = _CODE_TO_EXCEPTION.get(descriptor.code, TradeError)
    return exc_type(descriptor=descriptor, detail=detail)


# ── Backward-compatible aliases ───────────────────────────────────────
# These names are imported by service modules throughout the codebase.

ValidationError = InvalidRequestError
PolicyError = InvalidRequestError
InfrastructureError = InvalidRequestError
DomainError = InvalidRequestError


class BrokerError(TradeError):
    """Legacy alias for broker-side errors."""


@dataclass(frozen=True)
class ErrorContext:
    """Lightweight error context container."""
    code: str = "unknown"
    detail: str = ""


@dataclass(frozen=True)
class ErrorEnvelope:
    """Envelope wrapping an error descriptor with optional context."""
    descriptor: ErrorDescriptor
    context: ErrorContext | None = None
