from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.contracts import CanonicalEnvelope, Originator


def test_canonical_envelope_accepts_required_fields():
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

    assert envelope.schema_version == "1.0.0"
    assert envelope.environment == "paper"
    assert envelope.operating_mode == "MODE-001"
    assert envelope.originator.type == "agent"


def test_canonical_envelope_requires_core_fields():
    with pytest.raises(ValidationError):
        CanonicalEnvelope(
            contract_type="WorkflowIntent",
            workflow_id="wf_123",
            correlation_id="corr_123",
            originator=Originator(type="agent", id="strategy_agent_v1"),
            environment="paper",
            operating_mode="MODE-001",
            payload={},
        )


def test_canonical_envelope_rejects_invalid_environment():
    with pytest.raises(ValidationError):
        CanonicalEnvelope(
            contract_type="WorkflowIntent",
            workflow_id="wf_123",
            correlation_id="corr_123",
            causation_id="evt_123",
            originator=Originator(type="agent", id="strategy_agent_v1"),
            environment="sandbox",
            operating_mode="MODE-001",
            payload={},
        )


def test_canonical_envelope_rejects_invalid_operating_mode():
    with pytest.raises(ValidationError):
        CanonicalEnvelope(
            contract_type="WorkflowIntent",
            workflow_id="wf_123",
            correlation_id="corr_123",
            causation_id="evt_123",
            originator=Originator(type="agent", id="strategy_agent_v1"),
            environment="paper",
            operating_mode="MODE-999",
            payload={},
        )


def test_originator_rejects_invalid_type():
    with pytest.raises(ValidationError):
        Originator(type="system", id="svc_1")
