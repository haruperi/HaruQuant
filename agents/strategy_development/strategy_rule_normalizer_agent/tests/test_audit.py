from __future__ import annotations

from agents._shared.testing_audit import assert_audit_or_evidence_declared


def test_audit_or_evidence_contract_is_declared():
    assert_audit_or_evidence_declared(__file__)
