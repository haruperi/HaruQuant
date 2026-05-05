"""Secrets isolation and rotation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


_REDACTED = "********"


@dataclass(frozen=True)
class SecretRef:
    """Versioned secret reference without exposing secret material."""

    secret_id: str
    version: str
    created_at: datetime
    active: bool = True


@dataclass(frozen=True)
class SecretRotationPolicy:
    """Minimal rotation policy metadata."""

    secret_id: str
    max_age_days: int
    overlap_versions: int = 2


def redact_secret_mapping(values: Mapping[str, object]) -> dict[str, object]:
    """Redact secret-like keys before logging or diagnostics."""

    redacted: dict[str, object] = {}
    for key, value in values.items():
        normalized = key.lower()
        if any(token in normalized for token in ("secret", "token", "password", "key")):
            redacted[key] = _REDACTED
        else:
            redacted[key] = value
    return redacted


def select_active_secret_version(
    refs: tuple[SecretRef, ...],
    *,
    policy: SecretRotationPolicy,
) -> SecretRef:
    """Resolve the newest active secret version within the allowed overlap set."""

    candidates = [ref for ref in refs if ref.secret_id == policy.secret_id and ref.active]
    if not candidates:
        raise ValueError(f"no active secret versions found for '{policy.secret_id}'")

    ordered = sorted(candidates, key=lambda item: item.created_at, reverse=True)
    return ordered[: max(policy.overlap_versions, 1)][0]
