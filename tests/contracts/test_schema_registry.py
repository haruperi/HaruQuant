from __future__ import annotations

from apps.contracts.schema_registry import (
    SchemaRegistry,
    TickMessage,
    create_default_schema_registry,
)


def test_default_registry_contains_core_contracts() -> None:
    reg = create_default_schema_registry()
    assert "1.0" in reg.list_versions(name="event.tick")
    assert "1.0" in reg.list_versions(name="event.bar")
    assert "1.0" in reg.list_versions(name="api.order")
    assert "1.0" in reg.list_versions(name="api.fill")
    assert "1.0" in reg.list_versions(name="storage.position")
    assert "1.0" in reg.list_versions(name="storage.run_manifest")
    assert "1.0" in reg.list_versions(name="storage.run_report")


def test_validate_tick_payload_success() -> None:
    reg = create_default_schema_registry()
    ok, msg = reg.validate(
        name="event.tick",
        version="1.0",
        payload={
            "provider": "mt5_ea",
            "schema_version": "1.0",
            "symbol": "EURUSD",
            "timestamp": "2026-02-17T12:00:00Z",
            "bid": 1.1000,
            "ask": 1.1002,
            "volume": 120.0,
        },
    )
    assert ok is True
    assert msg == "ok"


def test_validate_tick_payload_failure() -> None:
    reg = create_default_schema_registry()
    ok, msg = reg.validate(
        name="event.tick",
        version="1.0",
        payload={
            "provider": "mt5_ea",
            "schema_version": "1.0",
            "symbol": "EURUSD",
            "timestamp": "2026-02-17T12:00:00Z",
            "bid": 1.1003,
            "ask": 1.1001,
            "volume": 120.0,
        },
    )
    assert ok is False
    assert "ask must be greater than or equal to bid" in msg


def test_registry_validate_unknown_schema() -> None:
    reg = create_default_schema_registry()
    ok, msg = reg.validate(name="event.unknown", version="1.0", payload={})
    assert ok is False
    assert "schema not found" in msg


def test_register_new_version_with_compat_guard_passes() -> None:
    reg = SchemaRegistry()
    reg.register(name="event.tick", version="1.0", model=TickMessage)

    class TickV11(TickMessage):
        schema_version: str = "1.1"
        venue: str | None = None

    reg.register(
        name="event.tick",
        version="1.1",
        model=TickV11,
        enforce_backward_compat_with="1.0",
    )
    assert "1.1" in reg.list_versions(name="event.tick")
