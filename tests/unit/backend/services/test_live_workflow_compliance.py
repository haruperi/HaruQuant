from __future__ import annotations

import pytest

from haruquant.utils import ValidationError
from haruquant.risk import require_live_execution_profile


def test_require_live_execution_profile_rejects_missing_profile_for_live_modes() -> None:
    with pytest.raises(ValidationError, match="compliance profile"):
        require_live_execution_profile(
            compliance_profile_id=None,
            operating_mode="MODE-003",
        )


def test_require_live_execution_profile_allows_attached_profile_for_live_modes() -> None:
    profile_id = require_live_execution_profile(
        compliance_profile_id="comp_uae_enterprise",
        operating_mode="MODE-004",
    )

    assert profile_id == "comp_uae_enterprise"
