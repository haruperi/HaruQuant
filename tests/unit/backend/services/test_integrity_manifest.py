from __future__ import annotations

from haruquant.strategy import generate_integrity_manifest


def test_generate_integrity_manifest_produces_stable_hash_manifest() -> None:
    first = generate_integrity_manifest(
        {
            "log_001": "hash_b",
            "evidence_001": "hash_a",
        }
    )
    second = generate_integrity_manifest(
        {
            "evidence_001": "hash_a",
            "log_001": "hash_b",
        }
    )

    assert first["manifest_hash"] == second["manifest_hash"]
    assert first["entries"] == {"evidence_001": "hash_a", "log_001": "hash_b"}
