from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from haruquant.utils import (
    BOARD_BASELINE_TTL_POLICY,
    FixedClock,
    SystemClock,
    evaluate_board_baseline_freshness,
    evaluate_freshness,
    is_stale,
)


UTC = timezone.utc


def test_system_clock_returns_utc_datetime():
    value = SystemClock().now()

    assert isinstance(value, datetime)
    assert value.tzinfo == UTC


def test_evaluate_freshness_reports_fresh_window():
    observed = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    clock = FixedClock(datetime(2026, 4, 8, 10, 0, 20, tzinfo=UTC))

    window = evaluate_freshness(observed, max_age_seconds=30, clock=clock)

    assert window.age_seconds == 20.0
    assert window.is_fresh is True
    assert window.is_stale is False
    assert window.expires_at == observed + timedelta(seconds=30)


def test_is_stale_returns_true_when_window_expired():
    observed = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    clock = FixedClock(datetime(2026, 4, 8, 10, 1, tzinfo=UTC))

    assert is_stale(observed, max_age_seconds=30, clock=clock) is True


def test_evaluate_freshness_rejects_negative_ttl():
    with pytest.raises(ValueError):
        evaluate_freshness(
            datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
            max_age_seconds=-1,
        )


def test_board_baseline_freshness_uses_documented_ttl_values():
    observed = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    clock = FixedClock(datetime(2026, 4, 8, 10, 0, 1, tzinfo=UTC))

    result = evaluate_board_baseline_freshness(
        {
            "best_bid_ask_tick": observed,
            "risk_decision": observed,
            "compliance_profile_and_approval_policy": observed,
        },
        clock=clock,
    )

    assert BOARD_BASELINE_TTL_POLICY["best_bid_ask_tick"][1] == 2
    assert BOARD_BASELINE_TTL_POLICY["risk_decision"][1] == 30
    assert BOARD_BASELINE_TTL_POLICY["compliance_profile_and_approval_policy"][1] == 900
    assert result.is_valid is True
    assert result.shortest_ttl_seconds == 2
    assert result.stale_artifacts == ()


def test_board_baseline_freshness_fails_closed_on_stale_artifact():
    observed = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    clock = FixedClock(datetime(2026, 4, 8, 10, 0, 3, tzinfo=UTC))

    result = evaluate_board_baseline_freshness(
        {
            "best_bid_ask_tick": observed,
            "account_equity_free_margin_snapshot": observed,
        },
        clock=clock,
    )

    assert result.is_valid is False
    assert len(result.stale_artifacts) == 1
    assert result.stale_artifacts[0].artifact_name == "best_bid_ask_tick"


def test_board_baseline_freshness_invalidates_on_material_proposal_change():
    observed = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    clock = FixedClock(datetime(2026, 4, 8, 10, 0, 1, tzinfo=UTC))

    result = evaluate_board_baseline_freshness(
        {
            "risk_decision": observed,
            "account_equity_free_margin_snapshot": observed,
        },
        proposal_materially_changed=True,
        clock=clock,
    )

    assert result.proposal_materially_changed is True
    assert result.is_valid is False


def test_board_baseline_freshness_requires_revalidation_after_long_pause():
    observed = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    clock = FixedClock(datetime(2026, 4, 8, 10, 0, 6, tzinfo=UTC))

    result = evaluate_board_baseline_freshness(
        {
            "account_equity_free_margin_snapshot": observed,
            "open_positions_snapshot": observed,
        },
        workflow_paused_at=observed,
        clock=clock,
    )

    assert result.shortest_ttl_seconds == 5
    assert result.workflow_pause_exceeded_shortest_ttl is True
    assert result.is_valid is False


def test_board_baseline_freshness_rejects_unknown_artifact():
    clock = FixedClock(datetime(2026, 4, 8, 10, 0, 1, tzinfo=UTC))

    with pytest.raises(ValueError):
        evaluate_board_baseline_freshness(
            {"unknown_artifact": datetime(2026, 4, 8, 10, 0, tzinfo=UTC)},
            clock=clock,
        )
