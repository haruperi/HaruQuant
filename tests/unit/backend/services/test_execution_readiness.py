from __future__ import annotations

from datetime import datetime, timezone

from apps.core import FixedClock
from backend.services import (
    SymbolMetadataCacheEntry,
    validate_market_open,
    validate_price_freshness,
    validate_symbol_tradability,
)


UTC = timezone.utc


def _metadata(*, market_open: bool = True, tradable: bool = True) -> SymbolMetadataCacheEntry:
    return SymbolMetadataCacheEntry(
        snapshot_id="meta_001",
        symbol="EURUSD",
        observed_at=datetime(2026, 4, 9, 10, 0, tzinfo=UTC),
        market_open=market_open,
        tradable=tradable,
        supported_fill_modes=("IOC", "FOK"),
        stop_level_points=10,
        freeze_level_points=5,
        tick_size=0.0001,
        point_value=10.0,
        contract_size=100000.0,
        max_age_seconds=5,
    )


def test_validate_market_open_rejects_closed_market() -> None:
    result = validate_market_open(_metadata(market_open=False))

    assert result.allowed is False
    assert result.reason_codes == ("market_closed",)


def test_validate_symbol_tradability_rejects_non_tradable_symbol() -> None:
    result = validate_symbol_tradability(_metadata(tradable=False))

    assert result.allowed is False
    assert result.reason_codes == ("symbol_not_tradable",)


def test_validate_price_freshness_rejects_stale_snapshot() -> None:
    result = validate_price_freshness(
        _metadata(),
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 6, tzinfo=UTC)),
    )

    assert result.allowed is False
    assert result.reason_codes == ("stale_price_snapshot",)
