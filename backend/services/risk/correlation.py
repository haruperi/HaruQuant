"""Correlation concentration helpers for portfolio risk checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorrelationPair:
    """Pairwise correlation input with gross portfolio weights."""

    left_key: str
    right_key: str
    left_weight: float
    right_weight: float
    correlation: float


@dataclass(frozen=True)
class CorrelationConcentration:
    """Aggregated pair and portfolio concentration from correlation inputs."""

    pair_concentrations: dict[str, float]
    portfolio_concentration: float
    breached_pairs: tuple[str, ...]
    threshold: float


def calculate_correlation_concentration(
    pairs: tuple[CorrelationPair, ...],
    *,
    threshold: float,
) -> CorrelationConcentration:
    """Calculate weighted pair concentration from pairwise correlations."""

    pair_concentrations: dict[str, float] = {}
    portfolio_concentration = 0.0
    for pair in pairs:
        weighted_concentration = abs(pair.correlation) * pair.left_weight * pair.right_weight
        pair_key = f"{pair.left_key}:{pair.right_key}"
        pair_concentrations[pair_key] = weighted_concentration
        portfolio_concentration += weighted_concentration

    breached_pairs = tuple(
        key for key, value in sorted(pair_concentrations.items()) if value > threshold
    )
    return CorrelationConcentration(
        pair_concentrations=pair_concentrations,
        portfolio_concentration=portfolio_concentration,
        breached_pairs=breached_pairs,
        threshold=threshold,
    )


__all__ = [
    "CorrelationConcentration",
    "CorrelationPair",
    "calculate_correlation_concentration",
]
