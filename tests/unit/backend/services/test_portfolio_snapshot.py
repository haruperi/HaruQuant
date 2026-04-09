from datetime import datetime, timedelta, timezone

from apps.core.time_utils import FixedClock
from backend.services.risk import PortfolioSnapshot


UTC = timezone.utc


def test_portfolio_snapshot_uses_open_positions_hot_ttl_policy() -> None:
    observed_at = datetime(2026, 4, 9, 10, 0, 0, tzinfo=UTC)
    snapshot = PortfolioSnapshot.from_policy(
        snapshot_id="portsnap_001",
        portfolio_id="pf_live_01",
        observed_at=observed_at,
        open_position_count=3,
        gross_exposure=125_000.0,
        net_exposure=42_500.0,
        symbols=("EURUSD", "GBPUSD", "USDJPY"),
    )

    freshness = snapshot.evaluate(clock=FixedClock(observed_at + timedelta(seconds=2)))

    assert snapshot.freshness_class == "HOT"
    assert snapshot.max_age_seconds == 5
    assert freshness.is_fresh is True


def test_portfolio_snapshot_expires_after_hot_window() -> None:
    observed_at = datetime(2026, 4, 9, 10, 0, 0, tzinfo=UTC)
    snapshot = PortfolioSnapshot.from_policy(
        snapshot_id="portsnap_002",
        portfolio_id="pf_live_01",
        observed_at=observed_at,
        open_position_count=4,
        gross_exposure=150_000.0,
        net_exposure=61_000.0,
        symbols=("EURUSD", "GBPUSD", "USDJPY", "XAUUSD"),
    )

    freshness = snapshot.evaluate(clock=FixedClock(observed_at + timedelta(seconds=7)))

    assert freshness.is_stale is True
    assert snapshot.expires_at == observed_at + timedelta(seconds=5)
