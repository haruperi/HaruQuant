"""Shared error taxonomy and typed exceptions for Python/C++ integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ErrorDescriptor:
    """Normalized error payload shared with C++ bridge."""

    code: int
    name: str
    message: str
    domain: str = "trade"
    retryable: bool = False


class HaruError(Exception):
    """Base app error."""

    def __init__(self, descriptor: ErrorDescriptor, detail: str | None = None) -> None:
        self.descriptor = descriptor
        self.detail = detail
        text = detail or descriptor.message
        super().__init__(f"[{descriptor.name}] {text} (code={descriptor.code})")


class CppBridgeError(HaruError):
    """Base C++ bridge error."""


class CppTradeError(CppBridgeError):
    """Base C++ trade error."""


class CppInvalidRequestError(CppTradeError):
    """Invalid request."""


class CppInvalidVolumeError(CppTradeError):
    """Invalid volume."""


class CppInvalidPriceError(CppTradeError):
    """Invalid price."""


class CppInvalidStopsError(CppTradeError):
    """Invalid stops."""


class CppTradeDisabledError(CppTradeError):
    """Trade disabled."""


class CppMarketClosedError(CppTradeError):
    """Market closed."""


class CppNoMoneyError(CppTradeError):
    """Insufficient margin/money."""


class CppNoQuotesError(CppTradeError):
    """No quotes available."""


_DEFAULT = ErrorDescriptor(
    code=-1,
    name="UNKNOWN",
    message="Unknown error",
    domain="trade",
    retryable=False,
)

_CODE_TO_EXCEPTION: dict[int, type[CppTradeError]] = {
    10013: CppInvalidRequestError,
    10014: CppInvalidVolumeError,
    10015: CppInvalidPriceError,
    10016: CppInvalidStopsError,
    10017: CppTradeDisabledError,
    10018: CppMarketClosedError,
    10019: CppNoMoneyError,
    10021: CppNoQuotesError,
}


def descriptor_from_payload(payload: Mapping[str, Any] | None, *, fallback_code: int = -1) -> ErrorDescriptor:
    """Build an ErrorDescriptor from bridge payload."""
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


def trade_exception_from_descriptor(descriptor: ErrorDescriptor, detail: str | None = None) -> CppTradeError:
    """Return typed trade exception for taxonomy descriptor."""
    exc_type = _CODE_TO_EXCEPTION.get(descriptor.code, CppTradeError)
    return exc_type(descriptor=descriptor, detail=detail)

