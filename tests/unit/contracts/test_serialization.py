from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from backend.contracts import (
    CanonicalEnvelope,
    Originator,
    canonical_json_dumps,
    deserialize_contract,
    serialize_contract,
)


def test_canonical_json_dumps_sorts_keys_and_normalizes_values():
    payload = {
        "b": Decimal("1.2300"),
        "a": datetime(2026, 4, 8, 10, 15, 30, tzinfo=timezone.utc),
    }

    serialized = canonical_json_dumps(payload)

    assert serialized == '{"a":"2026-04-08T10:15:30Z","b":"1.2300"}'


def test_serialize_and_deserialize_contract_round_trip():
    envelope = CanonicalEnvelope(
        contract_type="WorkflowIntent",
        workflow_id="wf_123",
        correlation_id="corr_123",
        causation_id="evt_123",
        timestamp_utc=datetime(2026, 4, 8, 10, 15, 30, tzinfo=timezone.utc),
        originator=Originator(type="agent", id="strategy_agent_v1"),
        environment="paper",
        operating_mode="MODE-001",
        payload={"goal": "review_trade"},
    )

    serialized = serialize_contract(envelope)
    restored = deserialize_contract(serialized, CanonicalEnvelope)

    assert restored == envelope


def test_canonical_json_dumps_rejects_nan():
    payload = {"value": float("nan")}

    try:
        canonical_json_dumps(payload)
    except ValueError:
        pass
    else:
        raise AssertionError("NaN payload unexpectedly serialized")
