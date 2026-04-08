from __future__ import annotations

from apps.core.errors import (
    BrokerError,
    ErrorContext,
    DomainError,
    InfrastructureError,
    PolicyError,
    ValidationError,
    envelope_from_mapping,
)


def test_domain_error_serializes_with_context():
    error = DomainError(
        "workflow_blocked",
        "Workflow cannot proceed",
        details={"state": "blocked"},
        context=ErrorContext(
            workflow_id="wf_123",
            correlation_id="corr_123",
            environment="test",
        ),
    )

    payload = error.to_dict()

    assert payload["category"] == "domain"
    assert payload["code"] == "workflow_blocked"
    assert payload["details"]["state"] == "blocked"
    assert payload["context"]["workflow_id"] == "wf_123"


def test_error_categories_are_distinct():
    assert ValidationError("invalid_contract", "bad").to_dict()["category"] == "validation"
    assert PolicyError("policy_denied", "denied").to_dict()["category"] == "policy"
    assert BrokerError("broker_timeout", "timeout", retryable=True).retryable is True
    assert InfrastructureError("db_unavailable", "db down").to_dict()["category"] == "infrastructure"


def test_envelope_from_mapping_round_trips():
    payload = {
        "code": "stale_snapshot",
        "category": "validation",
        "message": "Snapshot is stale",
        "retryable": False,
        "details": {"snapshot": "account"},
        "context": {
            "workflow_id": "wf_999",
            "correlation_id": "corr_999",
            "causation_id": "evt_999",
            "environment": "paper",
            "metadata": {"ttl_seconds": 5},
        },
    }

    envelope = envelope_from_mapping(payload)

    assert envelope.code == "stale_snapshot"
    assert envelope.category == "validation"
    assert envelope.context.environment == "paper"
    assert envelope.context.metadata["ttl_seconds"] == 5
