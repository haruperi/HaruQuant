from __future__ import annotations

import pytest
from pydantic import BaseModel

from apps.contracts.schema_registry import (
    SchemaRegistry,
    SchemaRegistryError,
    is_backward_compatible,
)


class OrderV10(BaseModel):
    order_id: str
    symbol: str
    side: str
    volume: float
    submitted_at: str


class OrderV11Compatible(BaseModel):
    order_id: str
    symbol: str
    side: str
    volume: float
    submitted_at: str
    status: str | None = None


class OrderV11BreakingMissingField(BaseModel):
    order_id: str
    symbol: str
    side: str
    submitted_at: str


class OrderV11BreakingTypeChange(BaseModel):
    order_id: str
    symbol: str
    side: str
    volume: int
    submitted_at: str


def test_backward_compat_true_for_additive_optional_field() -> None:
    ok, reason = is_backward_compatible(OrderV10, OrderV11Compatible)
    assert ok is True
    assert reason == "compatible"


def test_backward_compat_false_when_field_removed() -> None:
    ok, reason = is_backward_compatible(OrderV10, OrderV11BreakingMissingField)
    assert ok is False
    assert "missing field" in reason


def test_backward_compat_false_when_type_changed() -> None:
    ok, reason = is_backward_compatible(OrderV10, OrderV11BreakingTypeChange)
    assert ok is False
    assert "field type changed" in reason


def test_registry_rejects_breaking_registration_when_guard_enabled() -> None:
    reg = SchemaRegistry()
    reg.register(name="api.order", version="1.0", model=OrderV10)
    with pytest.raises(SchemaRegistryError, match="backward compatibility failed"):
        reg.register(
            name="api.order",
            version="1.1",
            model=OrderV11BreakingMissingField,
            enforce_backward_compat_with="1.0",
        )
