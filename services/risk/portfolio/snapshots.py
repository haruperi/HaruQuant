"""Portfolio snapshot assembly helpers for portfolio analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from services.utils.logger import logger
from services.risk import (
    PortfolioSnapshot,
    PositionExposure,
    calculate_exposure_summary,
)


@dataclass(frozen=True)
class PortfolioSnapshotAssemblyInput:
    """Inputs required to assemble a current portfolio snapshot."""

    portfolio_id: str
    observed_at: datetime
    positions: tuple[PositionExposure, ...]


def assemble_portfolio_snapshot(
    request: PortfolioSnapshotAssemblyInput,
    *,
    snapshot_id: str,
) -> PortfolioSnapshot:
    """Assemble a canonical portfolio snapshot from normalized open positions."""

    summary = calculate_exposure_summary(request.positions)
    symbols = tuple(sorted({position.symbol for position in request.positions}))
    return PortfolioSnapshot.from_policy(
        snapshot_id=snapshot_id,
        portfolio_id=request.portfolio_id,
        observed_at=request.observed_at,
        open_position_count=summary.position_count,
        gross_exposure=summary.gross_exposure,
        net_exposure=summary.net_exposure,
        symbols=symbols,
    )


__all__ = [
    "PortfolioSnapshotAssemblyInput",
    "assemble_portfolio_snapshot",
]
