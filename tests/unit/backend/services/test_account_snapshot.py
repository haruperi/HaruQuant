from datetime import datetime, timedelta, timezone

from apps.core.time_utils import FixedClock
from backend.services.risk import AccountSnapshot


UTC = timezone.utc


def test_account_snapshot_uses_hot_account_ttl_policy() -> None:
    observed_at = datetime(2026, 4, 9, 10, 0, 0, tzinfo=UTC)
    snapshot = AccountSnapshot.from_policy(
        snapshot_id="acctsnap_001",
        account_id="acct_live_01",
        observed_at=observed_at,
        balance=100_000.0,
        equity=100_250.0,
        free_margin=82_100.0,
        margin_used=18_150.0,
        currency="USD",
    )

    freshness = snapshot.evaluate(clock=FixedClock(observed_at + timedelta(seconds=4)))

    assert snapshot.freshness_class == "HOT"
    assert snapshot.max_age_seconds == 5
    assert freshness.is_fresh is True


def test_account_snapshot_expires_after_hot_window() -> None:
    observed_at = datetime(2026, 4, 9, 10, 0, 0, tzinfo=UTC)
    snapshot = AccountSnapshot.from_policy(
        snapshot_id="acctsnap_002",
        account_id="acct_live_01",
        observed_at=observed_at,
        balance=100_000.0,
        equity=99_900.0,
        free_margin=79_500.0,
        margin_used=20_400.0,
        currency="USD",
    )

    freshness = snapshot.evaluate(clock=FixedClock(observed_at + timedelta(seconds=6)))

    assert freshness.is_stale is True
    assert snapshot.expires_at == observed_at + timedelta(seconds=5)
