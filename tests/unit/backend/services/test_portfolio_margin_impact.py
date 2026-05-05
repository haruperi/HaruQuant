from __future__ import annotations

import pytest

from haruquant.risk import calculate_projected_margin_impact


def test_calculate_projected_margin_impact_updates_margin_utilization() -> None:
    impact = calculate_projected_margin_impact(
        balance=10000.0,
        equity=10250.0,
        free_margin=7000.0,
        margin_used=3000.0,
        projected_margin_delta=500.0,
    )

    assert impact.margin_used == pytest.approx(3500.0)
    assert impact.free_margin == pytest.approx(6500.0)
    assert impact.utilization_ratio == pytest.approx(3500.0 / 10000.0)


def test_calculate_projected_margin_impact_rejects_negative_projected_margin_used() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        calculate_projected_margin_impact(
            balance=10000.0,
            equity=10250.0,
            free_margin=7000.0,
            margin_used=3000.0,
            projected_margin_delta=-4000.0,
        )
