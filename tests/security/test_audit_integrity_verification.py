from __future__ import annotations

from backend.services.audit import generate_integrity_manifest, sign_audit_evidence, verify_audit_signature


def test_audit_integrity_verification_detects_manifest_or_signature_tampering() -> None:
    manifest = generate_integrity_manifest(
        {
            "evidence_001": "hash_a",
            "log_001": "hash_b",
        }
    )
    signature = sign_audit_evidence(manifest, secret_key="audit-secret")

    assert verify_audit_signature(
        manifest,
        secret_key="audit-secret",
        signature=signature["signature"],
    ) is True
    assert verify_audit_signature(
        {
            **manifest,
            "entries": {"evidence_001": "hash_changed", "log_001": "hash_b"},
        },
        secret_key="audit-secret",
        signature=signature["signature"],
    ) is False
