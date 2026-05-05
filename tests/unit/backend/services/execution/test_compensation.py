"""Tests for execution compensation plans."""

from __future__ import annotations

import pytest

from services.execution.compensation import (
    CompensationPlan,
    CompensationRegistry,
    OrderCompensationPlan,
    PositionCompensationPlan,
)


class TestOrderCompensationPlan:
    def test_execute_cancel_entry(self) -> None:
        plan = OrderCompensationPlan("o1")
        ctx = {"order_type": "entry", "order_id": "ord123"}
        assert plan.execute(ctx) is True
        assert any(e["action"] == "cancel_order" for e in plan.log_entries)

    def test_execute_offsetting_exit(self) -> None:
        plan = OrderCompensationPlan("o2")
        ctx = {
            "order_type": "exit",
            "symbol": "EURUSD",
            "volume": 0.5,
        }
        assert plan.execute(ctx) is True
        assert any(e["action"] == "offsetting_order" for e in plan.log_entries)

    def test_execute_unknown_type(self) -> None:
        plan = OrderCompensationPlan("o3")
        ctx = {"order_type": "unknown"}
        assert plan.execute(ctx) is False

    def test_validate_with_order_id(self) -> None:
        plan = OrderCompensationPlan("o4")
        assert plan.validate({"order_id": "ord1"}) is True

    def test_validate_with_symbol(self) -> None:
        plan = OrderCompensationPlan("o5")
        assert plan.validate({"symbol": "EURUSD"}) is True

    def test_validate_empty(self) -> None:
        plan = OrderCompensationPlan("o6")
        assert plan.validate({}) is False


class TestPositionCompensationPlan:
    def test_execute_close(self) -> None:
        plan = PositionCompensationPlan("p1")
        ctx = {"compensation_action": "close", "symbol": "EURUSD", "position_id": "pos1"}
        assert plan.execute(ctx) is True
        assert any(e["action"] == "close_position" for e in plan.log_entries)

    def test_execute_reduce(self) -> None:
        plan = PositionCompensationPlan("p2")
        ctx = {
            "compensation_action": "reduce",
            "symbol": "GBPUSD",
            "target_volume": 0.3,
            "position_id": "pos2",
        }
        assert plan.execute(ctx) is True
        assert any(e["action"] == "reduce_position" for e in plan.log_entries)

    def test_execute_adjust_stop(self) -> None:
        plan = PositionCompensationPlan("p3")
        ctx = {
            "compensation_action": "adjust_stop",
            "symbol": "EURUSD",
            "new_stop_loss": 1.0850,
            "position_id": "pos3",
        }
        assert plan.execute(ctx) is True
        assert any(e["action"] == "adjust_stop_loss" for e in plan.log_entries)

    def test_execute_unknown_action(self) -> None:
        plan = PositionCompensationPlan("p4")
        ctx = {"compensation_action": "unknown", "symbol": "X", "position_id": "Y"}
        assert plan.execute(ctx) is False

    def test_validate(self) -> None:
        plan = PositionCompensationPlan("p5")
        assert plan.validate({"symbol": "EURUSD", "position_id": "pos1"}) is True
        assert plan.validate({"symbol": ""}) is False
        assert plan.validate({"position_id": ""}) is False


class TestCompensationRegistry:
    def test_register_and_get(self) -> None:
        reg = CompensationRegistry()
        reg.register("C", OrderCompensationPlan)
        plan = reg.get_plan("C", "act1")
        assert plan is not None
        assert isinstance(plan, OrderCompensationPlan)
        assert plan.action_id == "act1"

    def test_get_unknown_class(self) -> None:
        reg = CompensationRegistry()
        assert reg.get_plan("Z", "act1") is None

    def test_has_plan(self) -> None:
        reg = CompensationRegistry()
        reg.register("D", PositionCompensationPlan)
        assert reg.has_plan("D") is True
        assert reg.has_plan("X") is False

    def test_registered_classes(self) -> None:
        reg = CompensationRegistry()
        reg.register("A", OrderCompensationPlan)
        reg.register("B", PositionCompensationPlan)
        classes = reg.registered_classes
        assert "A" in classes
        assert "B" in classes

    def test_default_registry(self) -> None:
        from services.execution.compensation.registry import default_registry
        # Default registry should have plans for C, D, E
        assert default_registry.has_plan("C") is True
        assert default_registry.has_plan("D") is True
        assert default_registry.has_plan("E") is True
