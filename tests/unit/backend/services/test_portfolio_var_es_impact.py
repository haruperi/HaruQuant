from __future__ import annotations

import pytest

from services.risk.portfolio import calculate_projected_var_es_impact


def test_calculate_projected_var_es_impact_scales_metrics_by_exposure_ratio() -> None:
    impact = calculate_projected_var_es_impact(
        current_var=120.0,
        current_expected_shortfall=180.0,
        current_gross_exposure=1000.0,
        target_gross_exposure=1250.0,
    )

    assert impact.exposure_ratio == pytest.approx(1.25)
    assert impact.projected_var == pytest.approx(150.0)
    assert impact.projected_expected_shortfall == pytest.approx(225.0)


def test_calculate_projected_var_es_impact_rejects_negative_exposure() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        calculate_projected_var_es_impact(
            current_var=120.0,
            current_expected_shortfall=180.0,
            current_gross_exposure=-1.0,
            target_gross_exposure=1000.0,
        )
