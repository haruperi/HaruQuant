from __future__ import annotations

import pytest

from backend.common.optimistic import (
    ConcurrencyState,
    StaleVersionError,
    apply_version_update,
    ensure_version,
)


def test_concurrency_state_returns_next_version():
    state = ConcurrencyState(current_version=7)

    assert state.next_version() == 8


def test_ensure_version_accepts_matching_version():
    ensure_version(expected_version=3, current_version=3)


def test_ensure_version_rejects_stale_version():
    with pytest.raises(StaleVersionError) as exc:
        ensure_version(expected_version=2, current_version=5)

    assert exc.value.expected_version == 2
    assert exc.value.current_version == 5


def test_apply_version_update_increments_after_validation():
    state = apply_version_update(expected_version=9, current_version=9)

    assert state.current_version == 10
