"""Projected portfolio impact helpers."""

from __future__ import annotations

from dataclasses import dataclass

from services.risk import MarginUtilization, calculate_margin_utilization

from services.utils.logger import logger

@dataclass(frozen=True)
class ProjectedVarEsImpact:
    """Projected VaR and expected shortfall after a portfolio change."""

    current_var: float
    projected_var: float
    current_expected_shortfall: float
    projected_expected_shortfall: float
    exposure_ratio: float


def calculate_projected_var_es_impact(
    *,
    current_var: float,
    current_expected_shortfall: float,
    current_gross_exposure: float,
    target_gross_exposure: float,
) -> ProjectedVarEsImpact:
    """Project VaR and ES by scaling with gross exposure change."""

    if current_gross_exposure < 0:
        raise ValueError("current_gross_exposure must be non-negative")
    if target_gross_exposure < 0:
        raise ValueError("target_gross_exposure must be non-negative")

    exposure_ratio = 0.0 if current_gross_exposure == 0 else target_gross_exposure / current_gross_exposure
    return ProjectedVarEsImpact(
        current_var=current_var,
        projected_var=current_var * exposure_ratio,
        current_expected_shortfall=current_expected_shortfall,
        projected_expected_shortfall=current_expected_shortfall * exposure_ratio,
        exposure_ratio=exposure_ratio,
    )


def calculate_projected_margin_impact(
    *,
    balance: float,
    equity: float,
    free_margin: float,
    margin_used: float,
    projected_margin_delta: float,
) -> MarginUtilization:
    """Project margin utilization after an additive margin change."""

    projected_margin_used = margin_used + projected_margin_delta
    if projected_margin_used < 0:
        raise ValueError("projected margin used must be non-negative")

    projected_free_margin = free_margin - projected_margin_delta
    return calculate_margin_utilization(
        balance=balance,
        equity=equity,
        free_margin=projected_free_margin,
        margin_used=projected_margin_used,
    )


__all__ = [
    "ProjectedVarEsImpact",
    "calculate_projected_margin_impact",
    "calculate_projected_var_es_impact",
]
