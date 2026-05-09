from __future__ import annotations

from agents._shared.testing_audit import assert_permission_boundary_declared


def test_permission_boundary_is_declared():
    assert_permission_boundary_declared(__file__)
