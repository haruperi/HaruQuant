from __future__ import annotations

from datetime import datetime, timezone

from haruquant.utils import SecretRef, SecretRotationPolicy, redact_secret_mapping, select_active_secret_version


def test_redact_secret_mapping_masks_secret_like_keys() -> None:
    redacted = redact_secret_mapping(
        {
            "api_key": "abc123",
            "bearer_token": "xyz456",
            "database_url": "sqlite:///tmp/test.db",
            "mt5_password": "secret-pass",
        }
    )

    assert redacted["api_key"] == "********"
    assert redacted["bearer_token"] == "********"
    assert redacted["mt5_password"] == "********"
    assert redacted["database_url"] == "sqlite:///tmp/test.db"


def test_select_active_secret_version_picks_newest_active_version() -> None:
    refs = (
        SecretRef(
            secret_id="mt5",
            version="v1",
            created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
            active=True,
        ),
        SecretRef(
            secret_id="mt5",
            version="v2",
            created_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
            active=True,
        ),
    )

    selected = select_active_secret_version(
        refs,
        policy=SecretRotationPolicy(secret_id="mt5", max_age_days=30, overlap_versions=2),
    )

    assert selected.version == "v2"
