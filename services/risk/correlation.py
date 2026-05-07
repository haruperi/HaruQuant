"""Correlation concentration helpers for portfolio risk checks."""

from __future__ import annotations

from dataclasses import dataclass

from services.utils.logger import logger

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


DEFAULT_CLUSTERS = {
    "usd_major": {"symbols": {"EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"}, "max_cluster_exposure_pct": 0.35},
    "safe_haven": {"symbols": {"USDJPY", "USDCHF", "XAUUSD"}, "max_cluster_exposure_pct": 0.25},
}


def symbol_cluster(symbol: str) -> str:
    """Return the configured cluster for a symbol."""

    for cluster_id, cluster in DEFAULT_CLUSTERS.items():
        if symbol in cluster["symbols"]:
            return cluster_id
    return "single_symbol"


def correlation_impact(proposal: dict[str, object], portfolio_snapshot: dict[str, object]) -> dict[str, object]:
    """Calculate post-trade cluster exposure."""

    symbol = str(proposal.get("symbol", "UNKNOWN"))
    cluster = symbol_cluster(symbol)
    current = float(portfolio_snapshot.get("currency_cluster_exposure", portfolio_snapshot.get("correlation_impact", 0.0)))
    proposed = float(proposal.get("cluster_exposure_impact", 0.0))
    return {"cluster_id": cluster, "current_cluster_exposure": current, "proposed_cluster_exposure": proposed, "post_cluster_exposure": current + proposed}


def correlation_failures(impact: dict[str, object], thresholds: dict[str, object]) -> list[str]:
    """Return deterministic correlation or currency-cluster failures."""

    max_allowed = float(thresholds.get("max_currency_cluster_exposure_pct", 0.35))
    if float(impact["post_cluster_exposure"]) > max_allowed:
        return ["max_currency_cluster_exposure"]
    return []


__all__ = [
    "CorrelationConcentration",
    "CorrelationPair",
    "correlation_failures",
    "correlation_impact",
    "calculate_correlation_concentration",
    "symbol_cluster",
]
