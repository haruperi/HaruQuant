from __future__ import annotations

from haruquant.risk import seed_internal_non_regulated_profile


def test_seed_internal_non_regulated_profile_returns_active_internal_profile() -> None:
    profile = seed_internal_non_regulated_profile()

    assert profile.compliance_profile_id == "comp_internal_non_regulated"
    assert profile.active is True
    assert profile.jurisdictions == ("internal",)
    assert profile.metadata["regulatory_tier"] == "internal"
