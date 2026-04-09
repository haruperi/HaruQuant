"""Projected portfolio impact helpers."""

from __future__ import annotations

from dataclasses import dataclass


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


__all__ = [
    "ProjectedVarEsImpact",
    "calculate_projected_var_es_impact",
]
