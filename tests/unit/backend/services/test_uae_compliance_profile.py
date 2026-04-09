from __future__ import annotations

from backend.services.compliance_rollout import seed_uae_enterprise_profile


def test_seed_uae_enterprise_profile_returns_production_baseline() -> None:
    profile = seed_uae_enterprise_profile()

    assert profile.compliance_profile_id == "comp_uae_enterprise"
    assert profile.active is True
    assert profile.jurisdictions == ("UAE",)
    assert profile.approvals.required_roles == ("risk_manager", "compliance")
    assert profile.metadata["board_baseline"] is True
