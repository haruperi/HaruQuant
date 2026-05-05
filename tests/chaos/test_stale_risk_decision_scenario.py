from __future__ import annotations

from datetime import datetime, timezone

from services.utils import FixedClock
from services.risk import enforce_risk_decision_expiry


def test_stale_risk_decision_chaos_scenario_blocks_execution() -> None:
    validity = enforce_risk_decision_expiry(
        freshness_expiry=datetime(2026, 4, 9, 10, 0, tzinfo=timezone.utc),
        clock=FixedClock(datetime(2026, 4, 9, 10, 0, 1, tzinfo=timezone.utc)),
    )

    assert validity.valid is False
    assert validity.reason_codes == ("risk_decision_expired",)
