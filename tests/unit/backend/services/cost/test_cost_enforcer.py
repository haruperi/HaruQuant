"""Tests for cost enforcement service."""

from __future__ import annotations

from services.execution.cost import CostEnforcer, cost_enforcer


def test_enforcer_initializes() -> None:
    e = CostEnforcer()
    assert e.tracker is not None


def test_record_and_get_cost() -> None:
    e = CostEnforcer()
    e.record_cost("t1", "sp1", "test-model", 100, 50)
    cost = e.get_current_cost("t1")
    assert cost >= 0.0  # Cost depends on model pricing config


def test_workflow_budget_check() -> None:
    e = CostEnforcer()
    # Very low cost should pass
    assert e.check_workflow_budget(0.01) is True


def test_fallback_model() -> None:
    e = CostEnforcer()
    model = e.get_fallback_model()
    assert isinstance(model, str) and len(model) > 0


def test_singleton() -> None:
    assert cost_enforcer is not None
    assert isinstance(cost_enforcer, CostEnforcer)
