from __future__ import annotations

from datetime import datetime, timezone

from services.utils import FixedClock
from services.execution import SymbolMetadataCacheEntry, validate_price_freshness


def test_stale_market_data_chaos_scenario_fails_closed() -> None:
    metadata = SymbolMetadataCacheEntry(
        snapshot_id="snap_001",
        symbol="EURUSD",
        observed_at=datetime(2026, 4, 9, 10, 0, tzinfo=timezone.utc),
        market_open=True,
        tradable=True,
        supported_fill_modes=("market",),
        stop_level_points=10,
        freeze_level_points=5,
        tick_size=0.0001,
        point_value=10.0,
        contract_size=100000.0,
        max_age_seconds=2,
    )

    result = validate_price_freshness(
        metadata,
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 3, tzinfo=timezone.utc)),
    )

    assert result.allowed is False
    assert result.reason_codes == ("stale_price_snapshot",)
