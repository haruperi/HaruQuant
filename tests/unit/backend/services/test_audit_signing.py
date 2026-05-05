from __future__ import annotations

from haruquant.strategy import sign_audit_evidence, verify_audit_signature


def test_sign_and_verify_audit_evidence_signature() -> None:
    payload = {
        "manifest_hash": "hash_001",
        "entries": {"log_001": "hash_a"},
    }
    signature = sign_audit_evidence(payload, secret_key="secret-key")

    assert verify_audit_signature(
        payload,
        secret_key="secret-key",
        signature=signature["signature"],
    ) is True


def test_verify_audit_signature_rejects_tampered_payload() -> None:
    payload = {
        "manifest_hash": "hash_001",
        "entries": {"log_001": "hash_a"},
    }
    signature = sign_audit_evidence(payload, secret_key="secret-key")

    assert verify_audit_signature(
        {
            "manifest_hash": "hash_002",
            "entries": {"log_001": "hash_a"},
        },
        secret_key="secret-key",
        signature=signature["signature"],
    ) is False
