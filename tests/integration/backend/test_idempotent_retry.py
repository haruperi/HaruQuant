"""Integration tests for idempotent retry scenarios (Playbook §13)."""

from __future__ import annotations

import hashlib
import json


def _simple_idempotency_key(action: str, target: str, user: int) -> str:
    """Simplified idempotency key for integration testing."""
    raw = json.dumps({"action": action, "target": target, "user": user}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def test_idempotency_key_is_deterministic():
    """Same input always produces same key."""
    key1 = _simple_idempotency_key("place_order", "order_123", 42)
    key2 = _simple_idempotency_key("place_order", "order_123", 42)
    assert key1 == key2


def test_idempotency_key_differs_for_different_input():
    """Different input produces different key."""
    key1 = _simple_idempotency_key("place_order", "order_123", 42)
    key2 = _simple_idempotency_key("place_order", "order_456", 42)
    assert key1 != key2


def test_duplicate_detection_simulation():
    """Simulate duplicate detection workflow."""
    executed_keys = set()

    def execute_with_idempotency_check(action: str, target: str, user: int) -> dict:
        key = _simple_idempotency_key(action, target, user)
        if key in executed_keys:
            return {"status": "duplicate", "key": key}
        executed_keys.add(key)
        return {"status": "executed", "key": key}

    # First execution
    result1 = execute_with_idempotency_check("place_order", "order_1", 1)
    assert result1["status"] == "executed"

    # Duplicate attempt
    result2 = execute_with_idempotency_check("place_order", "order_1", 1)
    assert result2["status"] == "duplicate"
    assert result1["key"] == result2["key"]

    # Different order, should execute
    result3 = execute_with_idempotency_check("place_order", "order_2", 1)
    assert result3["status"] == "executed"
