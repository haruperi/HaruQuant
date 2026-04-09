from __future__ import annotations

from backend.services.shadow import build_shadow_comparison_report


def test_build_shadow_comparison_report_computes_deltas_and_slippage() -> None:
    report = build_shadow_comparison_report(
        expected_fill_price=1.1000,
        realized_fill_price=1.1005,
        expected_pnl=125.0,
        realized_pnl=110.0,
    )

    assert round(report.fill_price_delta, 7) == 0.0005
    assert report.pnl_delta == -15.0
    assert round(report.slippage_bps, 4) == round((0.0005 / 1.1) * 10000.0, 4)
