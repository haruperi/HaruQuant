from __future__ import annotations

from datetime import datetime, timezone

from haruquant.risk import PositionExposure
from haruquant.risk import PortfolioSnapshotAssemblyInput, assemble_portfolio_snapshot


def test_assemble_portfolio_snapshot_builds_complete_snapshot() -> None:
    snapshot = assemble_portfolio_snapshot(
        PortfolioSnapshotAssemblyInput(
            portfolio_id="portfolio_001",
            observed_at=datetime(2026, 4, 9, 14, 0, tzinfo=timezone.utc),
            positions=(
                PositionExposure(
                    symbol="EURUSD",
                    currency="USD",
                    strategy_family="trend",
                    notional_exposure=1200.0,
                    direction="buy",
                ),
                PositionExposure(
                    symbol="USDJPY",
                    currency="JPY",
                    strategy_family="carry",
                    notional_exposure=700.0,
                    direction="sell",
                ),
                PositionExposure(
                    symbol="EURUSD",
                    currency="USD",
                    strategy_family="trend",
                    notional_exposure=300.0,
                    direction="buy",
                ),
            ),
        ),
        snapshot_id="portfolio_snap_001",
    )

    assert snapshot.snapshot_id == "portfolio_snap_001"
    assert snapshot.portfolio_id == "portfolio_001"
    assert snapshot.open_position_count == 3
    assert snapshot.gross_exposure == 2200.0
    assert snapshot.net_exposure == 800.0
    assert snapshot.symbols == ("EURUSD", "USDJPY")


def test_assemble_portfolio_snapshot_handles_empty_positions() -> None:
    snapshot = assemble_portfolio_snapshot(
        PortfolioSnapshotAssemblyInput(
            portfolio_id="portfolio_001",
            observed_at=datetime(2026, 4, 9, 14, 0, tzinfo=timezone.utc),
            positions=(),
        ),
        snapshot_id="portfolio_snap_002",
    )

    assert snapshot.open_position_count == 0
    assert snapshot.gross_exposure == 0.0
    assert snapshot.net_exposure == 0
    assert snapshot.symbols == ()
