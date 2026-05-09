from __future__ import annotations

from agents._shared.testing_audit import assert_evaluator_module_declared


def test_evaluator_module_is_declared():
    assert_evaluator_module_declared(__file__)
