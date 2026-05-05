from datetime import datetime, timedelta, timezone

from haruquant.utils import FixedClock
from haruquant.risk import MarketSnapshot


UTC = timezone.utc


def test_market_snapshot_hot_freshness_window() -> None:
    observed_at = datetime(2026, 4, 9, 10, 0, 0, tzinfo=UTC)
    snapshot = MarketSnapshot.from_policy(
        snapshot_id="mktsnap_hot_001",
        symbol="EURUSD",
        snapshot_type="best_bid_ask_tick",
        observed_at=observed_at,
        best_bid=1.08231,
        best_ask=1.08236,
    )

    freshness = snapshot.evaluate(clock=FixedClock(observed_at + timedelta(seconds=1)))

    assert snapshot.freshness_class == "HOT"
    assert snapshot.max_age_seconds == 2
    assert freshness.is_fresh is True


def test_market_snapshot_warm_freshness_window() -> None:
    observed_at = datetime(2026, 4, 9, 10, 0, 0, tzinfo=UTC)
    snapshot = MarketSnapshot(
        snapshot_id="mktsnap_warm_001",
        symbol="EURUSD",
        snapshot_type="spread_snapshot",
        observed_at=observed_at,
        freshness_class="WARM",
        max_age_seconds=60,
        spread_points=1.8,
    )

    freshness = snapshot.evaluate(clock=FixedClock(observed_at + timedelta(seconds=30)))

    assert freshness.is_fresh is True
    assert freshness.age_seconds == 30.0


def test_market_snapshot_cool_freshness_window_can_expire() -> None:
    observed_at = datetime(2026, 4, 9, 10, 0, 0, tzinfo=UTC)
    snapshot = MarketSnapshot(
        snapshot_id="mktsnap_cool_001",
        symbol="EURUSD",
        snapshot_type="symbol_tradability_status",
        observed_at=observed_at,
        freshness_class="COOL",
        max_age_seconds=600,
        tradable=True,
    )

    freshness = snapshot.evaluate(clock=FixedClock(observed_at + timedelta(seconds=601)))

    assert freshness.is_stale is True
    assert freshness.expires_at == observed_at + timedelta(seconds=600)
