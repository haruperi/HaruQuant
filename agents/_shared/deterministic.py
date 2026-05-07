"""Shared deterministic helpers for HaruQuant agents."""

from __future__ import annotations

from collections.abc import Iterable


def unique_preserve_order(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


__all__ = ["contains_any", "unique_preserve_order"]
