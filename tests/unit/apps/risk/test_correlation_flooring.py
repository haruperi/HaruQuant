from __future__ import annotations

import numpy as np

from apps.risk.core.portfolio_risk_engine import PortfolioRiskEngine
from apps.risk.limits import RiskLimits
from apps.risk.metrics import math as risk_math


def test_core_engine_preserves_observed_correlations_in_standard_mode():
    corr_mat = np.array([[1.0, -0.40], [-0.40, 1.0]], dtype=float)
    adjusted = PortfolioRiskEngine().apply_corr_floors(
        corr_mat,
        RiskLimits(min_pair_corr=0.20, stressed_corr_floor=0.60, use_stressed_corr=False),
    )

    assert float(adjusted[0, 1]) == -0.40
    assert float(adjusted[1, 0]) == -0.40


def test_core_engine_applies_floor_only_in_stressed_mode():
    corr_mat = np.array([[1.0, -0.40], [-0.40, 1.0]], dtype=float)
    adjusted = PortfolioRiskEngine().apply_corr_floors(
        corr_mat,
        RiskLimits(min_pair_corr=0.20, stressed_corr_floor=0.60, use_stressed_corr=True),
    )

    assert float(adjusted[0, 1]) == 0.60
    assert float(adjusted[1, 0]) == 0.60


def test_state_math_preserves_standard_and_applies_stressed_floor_consistently():
    corr_mat = np.array([[1.0, 0.10], [0.10, 1.0]], dtype=float)

    standard = risk_math.apply_corr_floors(
        corr_mat,
        RiskLimits(min_pair_corr=0.20, stressed_corr_floor=0.75, use_stressed_corr=False),
    )
    stressed = risk_math.apply_corr_floors(
        corr_mat,
        RiskLimits(min_pair_corr=0.20, stressed_corr_floor=0.75, use_stressed_corr=True),
    )

    assert float(standard[0, 1]) == 0.10
    assert float(stressed[0, 1]) == 0.75
