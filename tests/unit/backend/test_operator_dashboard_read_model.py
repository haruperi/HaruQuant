"""Retired backend-era test.

The legacy backend package has been removed. This test targeted the retired
structure and is kept as a placeholder until a canonical services/api test is
written for the same behavior.
"""

import pytest

pytestmark = pytest.mark.skip(reason="retired backend-era test pending canonical replacement")
