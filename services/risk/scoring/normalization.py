"""Shared normalization helpers for explainable risk scores."""

from __future__ import annotations


def clamp_score(value: float) -> float:
    return float(max(0.0, min(100.0, value)))


def inverse_ratio_score(value: float | None, good: float, bad: float) -> float:
    """Map a risk ratio into a 0-100 score where lower is better."""
    if value is None:
        return 50.0
    if value <= good:
        return 100.0
    if value >= bad:
        return 0.0
    span = max(bad - good, 1e-9)
    return clamp_score(100.0 * (1.0 - ((value - good) / span)))


def direct_ratio_score(value: float | None, bad: float, good: float) -> float:
    """Map a helpful ratio into a 0-100 score where higher is better."""
    if value is None:
        return 50.0
    if value <= bad:
        return 0.0
    if value >= good:
        return 100.0
    span = max(good - bad, 1e-9)
    return clamp_score(100.0 * ((value - bad) / span))


def confidence_from_inputs(count: int) -> float:
    if count <= 1:
        return 0.4
    if count == 2:
        return 0.7
    return 0.9


def confidence_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.6:
        return "medium"
    return "low"
