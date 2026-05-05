from datetime import datetime, timezone

from services.execution import SymbolMetadataCache, SymbolMetadataCacheEntry


UTC = timezone.utc


def test_symbol_metadata_cache_retrieves_symbol_entry() -> None:
    cache = SymbolMetadataCache()
    entry = SymbolMetadataCacheEntry(
        snapshot_id="symmeta_001",
        symbol="EURUSD",
        observed_at=datetime(2026, 4, 9, 10, 0, 0, tzinfo=UTC),
        market_open=True,
        tradable=True,
        supported_fill_modes=("ioc", "fok"),
        stop_level_points=20,
        freeze_level_points=10,
        tick_size=0.00001,
        point_value=0.0001,
        contract_size=100000.0,
        max_age_seconds=5,
    )

    cache.put(entry)

    cached = cache.get("EURUSD")

    assert cached is not None
    assert cached.symbol == "EURUSD"
    assert cached.supported_fill_modes == ("ioc", "fok")


def test_symbol_metadata_cache_retrieves_subset_for_multiple_symbols() -> None:
    cache = SymbolMetadataCache()
    cache.put(
        SymbolMetadataCacheEntry(
            snapshot_id="symmeta_001",
            symbol="EURUSD",
            observed_at=datetime(2026, 4, 9, 10, 0, 0, tzinfo=UTC),
            market_open=True,
            tradable=True,
            supported_fill_modes=("ioc",),
            stop_level_points=20,
            freeze_level_points=10,
            tick_size=0.00001,
            point_value=0.0001,
            contract_size=100000.0,
            max_age_seconds=5,
        )
    )
    cache.put(
        SymbolMetadataCacheEntry(
            snapshot_id="symmeta_002",
            symbol="USDJPY",
            observed_at=datetime(2026, 4, 9, 10, 0, 0, tzinfo=UTC),
            market_open=True,
            tradable=False,
            supported_fill_modes=("fok",),
            stop_level_points=15,
            freeze_level_points=5,
            tick_size=0.001,
            point_value=0.01,
            contract_size=100000.0,
            max_age_seconds=5,
        )
    )

    cached = cache.get_many(("EURUSD", "XAUUSD", "USDJPY"))

    assert tuple(cached.keys()) == ("EURUSD", "USDJPY")
    assert cached["USDJPY"].tradable is False
