"""Expected-versus-realized comparison reporting for shadow workflows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShadowComparisonReport:
    """Stable shadow comparison summary."""

    expected_fill_price: float
    realized_fill_price: float
    expected_pnl: float
    realized_pnl: float
    fill_price_delta: float
    pnl_delta: float
    slippage_bps: float


def build_shadow_comparison_report(
    *,
    expected_fill_price: float,
    realized_fill_price: float,
    expected_pnl: float,
    realized_pnl: float,
) -> ShadowComparisonReport:
    """Compare expected shadow outcomes with realized market outcomes."""

    fill_price_delta = float(realized_fill_price - expected_fill_price)
    pnl_delta = float(realized_pnl - expected_pnl)
    slippage_bps = 0.0
    if expected_fill_price:
        slippage_bps = float((fill_price_delta / expected_fill_price) * 10000.0)
    return ShadowComparisonReport(
        expected_fill_price=float(expected_fill_price),
        realized_fill_price=float(realized_fill_price),
        expected_pnl=float(expected_pnl),
        realized_pnl=float(realized_pnl),
        fill_price_delta=fill_price_delta,
        pnl_delta=pnl_delta,
        slippage_bps=slippage_bps,
    )
