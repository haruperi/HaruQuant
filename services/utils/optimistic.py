"""Optimistic concurrency helpers for versioned records."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConcurrencyState:
    """Current concurrency state for a versioned record."""

    current_version: int

    def next_version(self) -> int:
        return self.current_version + 1


class StaleVersionError(ValueError):
    """Raised when a write is attempted with a stale expected version."""

    def __init__(self, expected_version: int, current_version: int) -> None:
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(
            f"Stale version: expected {expected_version}, current {current_version}"
        )


def ensure_version(*, expected_version: int, current_version: int) -> None:
    """Validate that the caller still holds the latest record version."""

    if expected_version != current_version:
        raise StaleVersionError(
            expected_version=expected_version,
            current_version=current_version,
        )


def apply_version_update(*, expected_version: int, current_version: int) -> ConcurrencyState:
    """Validate the current version and return the incremented state."""

    ensure_version(
        expected_version=expected_version,
        current_version=current_version,
    )
    return ConcurrencyState(current_version=current_version + 1)
